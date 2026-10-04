#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI-помощник скилла mos_itsm_automation_rule_descriptor.

Работает с REST API МосИТСМ (R-Сервис/Xurrent-совместимым):
  GET   {api_base}/automation_rules/{id}
  PATCH {api_base}/automation_rules/{id}   (обновляет ТОЛЬКО поле description)

Команды:
  get             - скачать правило целиком в JSON (бэкап/анализ)
  set-description - записать описание из файла в поле description (с автоматическим бэкапом)
  check           - сверить description с файлом (если задан) и проверить вёрстку description_html

Примеры:
  python ar_rule.py get --rule https://community.itsm-qa.mos.ru/automation_rules/15361146
  python ar_rule.py set-description --rule 15361146 --env QA --file desc.md --yes
  python ar_rule.py check --rule 15361146 --file desc.md
"""
import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = SKILL_DIR / "skill_env.json"
BACKUP_DIR = SKILL_DIR / "backups"

# Корпоративные сертификаты не установлены в системное хранилище — работаем без проверки TLS
SSL_CTX = ssl._create_unverified_context()


def load_env():
    with open(ENV_FILE, encoding="utf-8") as f:
        return json.load(f)


def resolve_api_base(env_name: str, env_cfg: dict) -> str:
    key = f"MOSITSM_API_URL_{env_name.upper()}"
    base = env_cfg.get(key)
    if not base:
        raise SystemExit(f"В {ENV_FILE.name} нет ключа {key}")
    return base.rstrip("/")


def resolve_token(env_name: str, token_arg, env_cfg: dict) -> str:
    if token_arg:
        return token_arg
    key = f"MOSITSM_PERS_TOKEN_{env_name.upper()}"
    token = env_cfg.get(key, "")
    if not token:
        raise SystemExit(
            f"Токен не задан: ни через --token, ни ключ {key} в {ENV_FILE.name}"
        )
    return token


def parse_rule_id(rule_arg: str) -> str:
    """Принимает и ID, и полную ссылку вида .../automation_rules/15361146."""
    rule_arg = rule_arg.strip().rstrip("/")
    m = re.search(r"(\d+)$", rule_arg)
    if not m:
        raise SystemExit(f"Не удалось извлечь ID правила из: {rule_arg!r}")
    return m.group(1)


def api_request(method: str, url: str, token: str, account: str, payload=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-4me-Account": account,
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {url}\n{body[:2000]}")


def do_get(args, env_cfg):
    base = resolve_api_base(args.env, env_cfg)
    token = resolve_token(args.env, args.token, env_cfg)
    rule_id = parse_rule_id(args.rule)
    status, rule = api_request("GET", f"{base}/automation_rules/{rule_id}", token, env_cfg["MOSITSM_ACCOUNT"])
    out = Path(args.out) if args.out else BACKUP_DIR / f"rule_{rule_id}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rule, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"HTTP {status}; правило {rule_id} сохранено: {out}")
    print(f"name={rule.get('name')!r}; trigger={rule.get('trigger')!r}; description_len={len(rule.get('description') or '')}")


def check_rendered_html(html: str) -> int:
    """Считает экранированные табличные теги в description_html.

    Серверный рендерер экранирует HTML-таблицы, свёрстанные «в одну строку»,
    — они превращаются в нечитаемый текст вида &lt;/th&gt;&lt;th&gt;.
    """
    escaped = sum(html.count(f"&lt;{tag}") for tag in ("table", "tr", "td", "th"))
    return escaped


def do_set_description(args, env_cfg):
    base = resolve_api_base(args.env, env_cfg)
    token = resolve_token(args.env, args.token, env_cfg)
    account = env_cfg["MOSITSM_ACCOUNT"]
    rule_id = parse_rule_id(args.rule)
    new_desc = Path(args.file).read_text(encoding="utf-8")
    if len(new_desc.encode("utf-8")) > 64_000:
        raise SystemExit("Описание больше 64KB — API его не примет, сократите текст.")

    if not args.no_backup:
        status, rule = api_request("GET", f"{base}/automation_rules/{rule_id}", token, account)
        bdir = Path(args.backup_dir) if args.backup_dir else BACKUP_DIR
        bdir.mkdir(parents=True, exist_ok=True)
        bpath = bdir / f"rule_{rule_id}_{datetime.now():%Y%m%d_%H%M%S}.json"
        bpath.write_text(json.dumps(rule, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Бэкап текущего описания: {bpath}")

    if args.dry_run:
        print(f"DRY-RUN: PATCH {base}/automation_rules/{rule_id} (только description, {len(new_desc)} символов)")
        return

    if not args.yes:
        print("Не задан --yes — запись не выполняется. Первые 500 символов нового описания:")
        print(new_desc[:500])
        return

    status, resp = api_request(
        "PATCH", f"{base}/automation_rules/{rule_id}", token, account,
        payload={"description": new_desc},
    )
    ok = resp.get("description") == new_desc
    print(f"HTTP {status}; updated_at={resp.get('updated_at')}; description совпадает: {ok}")
    if not ok:
        raise SystemExit("Сервер вернул иное описание — проверьте результат командой check")

    # Проверка вёрстки: серверный рендерер экранирует однострочные HTML-таблицы
    status, rule = api_request("GET", f"{base}/automation_rules/{rule_id}", token, account)
    escaped = check_rendered_html(rule.get("description_html") or "")
    tables = (rule.get("description_html") or "").count("<table>")
    print(f"Вёрстка description_html: таблиц <table>={tables}, экранированных тегов={escaped}")
    if escaped:
        raise SystemExit(
            "В description_html найдены экранированные теги — таблицы свёрстаны "
            "«в одну строку». Перепишите таблицы построчно (каждый тег и текст ячейки "
            "на своей строке, как в references/reference_description.md) и запишите снова."
        )


def do_check(args, env_cfg):
    base = resolve_api_base(args.env, env_cfg)
    token = resolve_token(args.env, args.token, env_cfg)
    rule_id = parse_rule_id(args.rule)
    status, rule = api_request("GET", f"{base}/automation_rules/{rule_id}", token, env_cfg["MOSITSM_ACCOUNT"])
    if args.file:
        local = Path(args.file).read_text(encoding="utf-8")
        print(f"HTTP {status}; description на сервере совпадает с {args.file}: {rule.get('description') == local}")
    else:
        print(f"HTTP {status}; description на сервере: {len(rule.get('description') or '')} символов")
    escaped = check_rendered_html(rule.get("description_html") or "")
    tables = (rule.get("description_html") or "").count("<table>")
    print(f"Вёрстка description_html: таблиц <table>={tables}, экранированных тегов={escaped}")
    if escaped:
        raise SystemExit(
            "В description_html найдены экранированные теги — таблицы свёрстаны "
            "«в одну строку». Перепишите таблицы построчно и запишите снова."
        )


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default=None, help="QA (по умолчанию из skill_env.json) или PROD")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name in ("get", "set-description", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("--rule", required=True, help="ID или ссылка на правило автоматизации")
        sp.add_argument("--token", default=None, help="Bearer-токен (иначе берётся из skill_env.json)")
        if name == "get":
            sp.add_argument("--out", default=None, help="куда сохранить JSON (по умолчанию backups/)")
        if name == "set-description":
            sp.add_argument("--file", required=True, help="файл с новым описанием (markdown)")
            sp.add_argument("--dry-run", action="store_true", help="показать план, ничего не писать")
            sp.add_argument("--yes", action="store_true", help="подтверждение записи (без него PATCH не выполняется)")
            sp.add_argument("--no-backup", action="store_true", help="не сохранять бэкап перед записью")
            sp.add_argument("--backup-dir", default=None)
        if name == "check":
            sp.add_argument("--file", default=None, help="файл для сравнения с description на сервере (необязательно)")

    args = p.parse_args()
    env_cfg = load_env()
    if args.env is None:
        args.env = env_cfg.get("MOSITSM_STAGE", "QA")

    if args.cmd == "get":
        do_get(args, env_cfg)
    elif args.cmd == "set-description":
        do_set_description(args, env_cfg)
    elif args.cmd == "check":
        do_check(args, env_cfg)


if __name__ == "__main__":
    main()
