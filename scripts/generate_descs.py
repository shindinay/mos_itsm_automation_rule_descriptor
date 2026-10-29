#!/usr/bin/env python3
"""Генерация описаний для всех правил автоматизации из backups/."""
import json
import os
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = SKILL_DIR / "backups"
DESC_DIR = SKILL_DIR / "afrtifacts"
os.makedirs(DESC_DIR, exist_ok=True)

RULE_IDS = {
    "template": [16207515, 16207516, 16207517, 16207518, 16207519, 16207520, 16207521, 16207522, 16207523, 16207524, 16207525, 16207526, 16207527],
    "task_3698": [1850442, 1850446, 1850460, 1896651, 1912401, 1912403, 2030311, 2030313, 12016323, 1850444, 1982929, 6514839, 2042983, 1849706],
    "task_7337": [2627475, 2964598, 2964596],
    "task_29151": [12013871, 12013875, 12013879, 12013883],
}

TRIGGER_MAP = {
    "on status update": "при изменении статуса записи",
    "on create": "при создании записи",
    "after delay": "после задержки по времени (after_delay)",
    "on note added": "при добавлении комментария",
    "on internal note added": "при добавлении внутреннего комментария",
    "on custom_fields update": "при обновлении пользовательских полей",
}

def parse_expressions(expr_text):
    """Парсит строку выражений в список пар (имя, формула)."""
    if not expr_text or not expr_text.strip():
        return []
    result = []
    for line in expr_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if ": " in line:
            name, formula = line.split(": ", 1)
            result.append((name.strip(), formula.strip()))
        elif line.endswith(":"):
            result.append((line[:-1].strip(), ""))
    return result

def parse_actions(actions_text):
    """Парсит строку действий в список."""
    if not actions_text or not actions_text.strip():
        return []
    result = []
    for line in actions_text.strip().split("\n"):
        line = line.strip()
        if line:
            result.append(line)
    return result

def parse_condition(condition):
    """Парсит условие в список имён выражений."""
    if not condition or condition == "true" or condition == "false":
        return []
    return [c.strip() for c in condition.split(" and ")]

def build_description(rule):
    """Создаёт описание правила в формате markdown по шаблону."""
    rid = rule["id"]
    name = rule["name"]
    trigger = rule.get("trigger", "")
    condition = rule.get("condition", "")
    expressions_text = rule.get("expressions", "")
    actions_text = rule.get("actions", "")
    existing_desc = rule.get("description", "")
    
    expr_list = parse_expressions(expressions_text)
    action_list = parse_actions(actions_text)
    cond_parts = parse_condition(condition)
    
    # Построить mapping expression_name -> formula
    expr_map = {e[0]: e[1] for e in expr_list}
    
    # Определение триггера
    trigger_desc = TRIGGER_MAP.get(trigger, trigger)
    
    # Описание правила
    # Берём существующее описание или формируем новое
    if existing_desc and existing_desc.strip():
        desc_text = existing_desc.strip()
    else:
        # Формируем автоматическое описание
        cond_desc = ""
        if cond_parts:
            cond_descriptions = []
            for part in cond_parts:
                if part in expr_map:
                    # Попробуем интерпретировать
                    formula = expr_map[part]
                    cond_descriptions.append(interpret_expr(part, formula))
                else:
                    cond_descriptions.append(part)
            cond_desc = ", ".join(cond_descriptions)
        
        parts_desc = []
        parts_desc.append(f"При срабатывании правила (триггер: {trigger_desc})")
        if cond_desc:
            parts_desc.append(f"проверяется условие: {cond_desc}")
        
        if action_list:
            actions_summary = []
            for a in action_list[:3]:
                actions_summary.append(extract_action_summary(a))
            if actions_summary:
                desc_text = " + ".join(actions_summary)
            else:
                desc_text = "Правило автоматизации"
        else:
            desc_text = "Правило автоматизации"
    
    # HTML таблица для истории изменений
    hist_table = f"""## **История изменений**

<table><tr><th style="text-align:left;background-color:rgb(221, 221, 221)" data-colwidth="39">
**№**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)">
**Дата**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)" data-colwidth="284">
**Запрос на изменение**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)">
**Автор изменения**
</th></tr><tr><td style="text-align:left">
1
</td><td style="text-align:left">
27.10.2026
</td><td style="text-align:left">
\-
</td><td style="text-align:left">
Первичное создание описания
</td></tr></table>"""
    
    # HTML таблица для настроек
    settings_rows = f"""<tr><td>
Триггер
</td><td>
`{trigger}` — {trigger_desc}
</td></tr>"""
    
    if cond_parts:
        cond_human = []
        for part in cond_parts:
            if part in expr_map:
                formula = expr_map[part]
                cond_human.append(interpret_expr(part, formula))
            else:
                cond_human.append(part)
        settings_rows += f"""<tr><td>
Условие
</td><td>
`{condition}` — {', '.join(cond_human)}
</td></tr>"""
    else:
        settings_rows += f"""<tr><td>
Условие
</td><td>
`{condition}`
</td></tr>"""
    
    settings_html = f"""## Настройки правила

<table><tr><td style="background-color:rgb(221, 221, 221)" data-colwidth="119">
**Параметр**
</td><td style="background-color:rgb(221, 221, 221)">
**Значение / Описание**
</td></tr>{settings_rows}</table>"""
    
    # Таблица выражений
    expr_rows = ""
    for name, formula in expr_list:
        logic = interpret_expr(name, formula)
        expr_rows += f"""<tr><td>
{name}
</td><td>
`{formula}` — {logic}
</td></tr>"""
    
    expr_html = f"""## Выражения

<table><tr><th style="text-align:left;background-color:rgb(221, 221, 221)" data-colwidth="158">
**Имя выражения**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)">
**Логика**
</th></tr>{expr_rows}</table>"""
    
    # Таблица действий
    action_rows = ""
    for action in action_list:
        action_desc = extract_action_summary(action)
        action_rows += f"""<tr><td>
{action}
</td><td>
{action_desc}
</td></tr>"""
    
    action_html = f"""## Действия

<table><tr><th style="text-align:left;background-color:rgb(221, 221, 221)" data-colwidth="275">
**Действие**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)">
**Описание**
</th></tr>{action_rows}</table>"""
    
    # Собираем финальное описание
    final = f"""## **Описание**

{desc_text}

{hist_table}

{settings_html}

{expr_html}

{action_html}"""
    
    return final

def interpret_expr(name, formula):
    """Интерпретирует выражение на русском."""
    formula = formula.strip()
    
    # Статусы
    if "= completed" in formula:
        return f"проверка, что статус «Завершено»"
    if "= assigned" in formula:
        return f"проверка, что статус «В работе» (assigned)"
    if "= in_progress" in formula:
        return f"проверка, что статус «В работе»"
    if "status_was = completed" in formula:
        return f"проверка, что предыдущий статус был «Завершено»"
    if "status_was != completed" in formula:
        return f"проверка, что предыдущий статус не был «Завершено»"
    if "status = assigned" in formula:
        return f"проверка, что статус «В работе»"
    if "status != completed" in formula:
        return f"проверка, что статус не «Завершено»"
    
    # Пользовательские поля
    if "custom_fields.requested_action" in formula:
        if "grant_roles" in formula:
            return f"проверка, что выбрано предоставление прав доступа"
        if "revoke_roles" in formula:
            return f"проверка, что выбран отзыв прав доступа"
    
    if "custom_fields.fired_flag" in formula:
        if "= null" in formula:
            return f"проверка, что флаг fired_flag не установлен (первый запуск)"
        return f"проверка флага fired_flag"
    
    if "custom_fields.account" in formula:
        if "!= null" in formula:
            return f"проверка, что пространство задано"
        return f"поле пространство"
    
    if "custom_fields.fio_global" in formula:
        if "!= null" in formula:
            return f"проверка, что список работников задан"
        return f"поле fio_global"
    
    if "custom_fields.lent_out_licences" in formula:
        if "!= null" in formula:
            return f"проверка, что список лицензий на отзыв задан"
        return f"поле lent_out_licences"
    
    if "workflow.status" in formula:
        if "= completed" in formula:
            return f"проверка, что РП завершён"
        return f"статус рабочего процесса"
    
    if "workflow.completion_reason" in formula:
        if "= complete" in formula:
            return f"проверка, что причина завершения — успешное"
        return f"причина завершения рабочего процесса"
    
    if "task != null" in formula:
        return f"проверка, что задача сгенерирована"
    if "task = null" in formula:
        return f"проверка, что задача не сгенерирована"
    
    if "member = SA" in formula or "member = find(person,3)" in formula:
        return f"проверка, что участник — служебная учётная запись"
    
    if "team != jarvis_team" or "team != find(team,835)" in formula:
        return f"проверка, что команда не jarvis"
    
    if "team = jarvis_team" or "team = find(team,835)" in formula:
        return f"проверка, что команда jarvis"
    
    # find() вызовы
    if "find(person," in formula and "custom_fields" in formula:
        return f"поиск лиц по полю custom_fields"
    if "find(ci," in formula:
        return f"поиск КЕ (конфигурационной единицы)"
    if "find(team," in formula:
        return f"поиск команды"
    if "find_all(person," in formula:
        return f"поиск всех лиц"
    if "find_all(ci," in formula:
        return f"поиск всех КЕ"
    
    # Логические операторы
    if "or " in formula:
        return f"логическое ИЛИ: {formula}"
    if " and " in formula:
        return f"логическое И: {formula}"
    if " then " in formula or " ? " in formula:
        return f"условный оператор: {formula}"
    
    # Массивы
    if ".count" in formula:
        return f"количество элементов в списке"
    if ".any?" in formula:
        return f"проверка наличия хотя бы одного элемента"
    if ".map(" in formula:
        return f"преобразование массива"
    if ".select(" in formula:
        return f"фильтрация массива"
    if "[last]" in formula:
        return f"последний элемент массива"
    if ".replace(" in formula:
        return f"замена подстроки"
    if "notes.select" in formula:
        return f"последний комментарий типа default"
    if "notes.select(medium" in formula:
        return f"последний комментарий"
    
    # Простые проверки
    if "= true" in formula or "= true" in formula:
        return f"проверка истинности"
    if "= false" in formula or "= null" in formula:
        return f"проверка пустого значения"
    if "!= 0" in formula:
        return f"проверка непустого списка"
    if "!= true" in formula:
        return f"проверка, что учётная запись не отключена"
    
    # Пространства
    if "ci_account.label" in formula and "itsm" in formula:
        return f"проверка, что пространство не совпадает с itsm (ДИТ Сервис-Менеджер)"
    
    # ol_domen
    if "ol_domen" in formula:
        return f"проверка, что инициатор входит в ol_domen пространства"
    
    # is_representative
    if "is_representative" in formula:
        return f"проверка, что инициатор запроса является представителем пространства"
    
    # not_sm
    if "not_sm" in formula:
        return f"проверка, что пространство не является СМ (Сервис-Менеджер)"
    
    # Статусы в действиях
    if "set status = " in formula:
        return f"установка статуса"
    if "set team = " in formula:
        return f"установка команды"
    if "set member = " in formula:
        return f"установка участника"
    
    # send email
    if "send email" in formula:
        return f"отправка email-письма"
    
    # add note
    if "add note" in formula:
        return f"добавление комментария"
    
    # update task
    if "update" in formula and "custom_fields" in formula:
        return f"обновление пользовательских полей задачи"
    if "update" in formula and "status" in formula:
        return f"обновление статуса задачи"
    
    # trigger
    if "trigger '" in formula:
        target = formula.split("trigger '")[1].rstrip("'")
        return f"перехватывает триггер '{target}'"
    
    # Прочее
    if "then " in formula:
        return f"условная логика"
    if "or " in formula:
        return f"условие ИЛИ"
    if "= " in formula and len(formula) < 40:
        return f"сравнение: {formula}"
    
    return formula


def extract_action_summary(action):
    """Извлекает краткое описание действия."""
    action = action.strip()
    
    if action.startswith("set status = "):
        status = action.split("set status = ")[1]
        status_map = {
            "completed": "Завершено",
            "assigned": "В работе",
            "canceled": "Отменено",
            "registered": "Зарегистрировано",
        }
        return f"устанавливает статус «{status_map.get(status, status)}»"
    
    if "set completion_reason" in action:
        return "устанавливает причину завершения"
    
    if "add note" in action:
        return "добавляет комментарий к записи"
    
    if "send email" in action:
        return "отправляет email-уведомление"
    
    if "set team" in action:
        return "изменяет команду запроса"
    
    if "set member" in action:
        return "изменяет участника запроса"
    
    if "set custom_fields" in action:
        return "обновляет пользовательское поле"
    
    if "update" in action:
        if "status" in action:
            return "обновляет статус связанной задачи"
        if "custom_fields" in action:
            return "обновляет поля связанной задачи"
        if "add comm" in action or "add note" in action:
            return "добавляет комментарий к связанной задаче"
    
    if "trigger '" in action:
        target = action.split("trigger '")[1].rstrip("'").rstrip('"')
        return f"срабатывает правило '{target}'"
    
    return action


# Генерация
for category, ids in RULE_IDS.items():
    for rid in ids:
        path = os.path.join(RULES_DIR, f"rule_{rid}.json")
        if not os.path.exists(path):
            print(f"ПРОПУСК: {path} не найден")
            continue
        
        with open(path, encoding="utf-8") as f:
            rule = json.load(f)
        
        desc = build_description(rule)
        out_path = os.path.join(DESC_DIR, f"desc_{rid}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(desc)
        
        print(f"OK: desc_{rid}.md ({len(desc)} символов)")

print("\nГенерация завершена.")
