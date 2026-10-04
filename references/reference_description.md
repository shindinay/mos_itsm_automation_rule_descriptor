## **Описание**

<c #0f1115>Правило автоматизации закрывает запрос, который долго находится в ожидании ответа от клиента. Если ответ так и не поступил, запрос переводится в статус «Завершено» с причиной «Нет ответа», а в запрос добавляется комментарий для заявителя.</c>

## **История изменений**

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
10.11.22
</td><td style="text-align:left">
Добавлена проверка на инициатора если его нет то берется предыдущий
</td><td style="text-align:left">
\-
</td></tr><tr><td>
2
</td><td>
21.11.22
</td><td>
Если нет member_was - member берется из последнего комментария который поставил запрос в ожидание.
</td><td>

</td></tr><tr><td>
3
</td><td>
19.11.22
</td><td>
Автоматизация не срабатывает если к запросу привязан РП
7 дней - [Запрос 3639991 Автоматизация и роботизация функционального решения](https://4me.4me.mos.ru/requests/3639991)
</td><td>

</td></tr><tr><td>
4
</td><td>
26.03.26
</td><td>
срок закрытия запроса берется из КЕ пространства, а не константа
</td><td>

</td></tr></table>

## Настройки правила

<table><tr><td style="background-color:rgb(221, 221, 221)" data-colwidth="119">
**Параметр**
</td><td style="background-color:rgb(221, 221, 221)">
**Значение / Описание**
</td></tr><tr><td>
Триггер
</td><td>
`after_delay` — запускается после задержки по времени
</td></tr><tr><td>
Условие
</td><td>
`is_await and is_can_start and is_not_empty and is_no_wf and is_active_account` — запрос в ожидании клиента, время закрытия наступило, поле `close_time` заполнено, РП не привязан, пространство применения совпадает
</td></tr></table>

## Выражения

<table><tr><th style="text-align:left;background-color:rgb(221, 221, 221)" data-colwidth="158">
**Имя выражения**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)">
**Логика**
</th></tr><tr><td>
is_await
</td><td>
`status = waiting_for_customer` — проверка, что статус «Ожидание действий клиента»
</td></tr><tr><td>
is_can_start
</td><td>
`now.iso8601 >= custom_fields.close_time` — проверка, что текущее время не меньше времени закрытия
</td></tr><tr><td>
fl_team
</td><td>
`service_instance.first_line_team` — первая линия поддержки компонента услуги
</td></tr><tr><td>
is_not_empty
</td><td>
`custom_fields.close_time != ""` — проверка, что поле close_time заполнено
</td></tr><tr><td>
req_by
</td><td>
`requested_by` — инициатор запроса
</td></tr><tr><td>
req_by_active
</td><td>
`req_by.disabled != true` — проверка, что учётная запись инициатора активна
</td></tr><tr><td>
id
</td><td>
`id` — идентификатор запроса
</td></tr><tr><td>
is_no_mem
</td><td>
`member = nil` — проверка, что участник не установлен
</td></tr><tr><td>
real_mebmer
</td><td>
`notes.select(medium = default)\[last\].person` — автор последнего комментария типа default
</td></tr><tr><td>
mem_was
</td><td>
`member_was ? member_was : real_mebmer` — предыдущий участник или, если его нет, автор последнего комментария
</td></tr><tr><td>
set_member
</td><td>
`is_no_mem ? mem_was : member` — кого установить участником: предыдущего или текущего
</td></tr><tr><td>
is_now_wf
</td><td>
`workflow = null` — проверка, что workflow не привязан
</td></tr><tr><td>
domain
</td><td>
`find_all(ci, rule_account.id).select(product.id = 101).detect(label = rule_account.id)` — КЕ пространства с продуктом 101 и меткой аккаунта правила
</td></tr><tr><td>
is_no_wf
</td><td>
`workflow = null` — проверка отсутствия workflow
</td></tr><tr><td>
days_to_response
</td><td>
`domain.custom_fields.days_to_response` — срок ответа из КЕ пространства
</td></tr><tr><td>
close_text
</td><td>
"К сожалению, период ожидания предоставления от Вас информации истек (он составляет {{days_to_response}} дней)..." — текст комментария об истечении срока ожидания
</td></tr><tr><td>
close_text_disabled
</td><td>
"Учетная запись инициатора отключена." — текст для отключённого инициатора
</td></tr><tr><td>
close_text
</td><td>
`req_by_active ? close_text : close_text_disabled` — выбор текста в зависимости от активности инициатора
</td></tr></table>

## Действия

<table><tr><th style="text-align:left;background-color:rgb(221, 221, 221)" data-colwidth="275">
**Действие**
</th><th style="text-align:left;background-color:rgb(221, 221, 221)">
**Описание**
</th></tr><tr><td>
action1: add note '{{close_text}}'
</td><td>
Добавляет комментарий с текстом close_text
</td></tr><tr><td>
action2: set status = completed
</td><td>
Устанавливает статус «Завершено»
</td></tr><tr><td>
action3: set completion_reason = no_reply
</td><td>
Устанавливает причину завершения «no_reply»
</td></tr><tr><td>
action4: set member = set_member
</td><td>
Устанавливает участника в значение set_member
</td></tr></table>