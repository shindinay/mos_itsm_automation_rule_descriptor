name: Продолжить РП - если итоговый список не пуст
trigger: on status update
condition: is_assigned and !is_all_save
expressions:
- to_dismiss_count: workflow.tasks.detect(category = approval).custom_fields.person_count
- is_assigned: status = assigned
- greater_than_40: to_dismiss_count > 30
- current_template_id: template.id
- option_1_to_cancel: workflow.tasks.reject(template.id = current_template_id).reject(status = completed).reject(status = canceled).reject(status = approved).reject(template.id = 35560)
- option_2_to_cancel: workflow.tasks.reject(template.id = current_template_id).reject(status = completed).reject(status = canceled).reject(status = approved).reject(template.id = 35476).reject(template.id = 35475).reject(template.id = 7411).reject(template.id = 4313)
- tasks_to_cancel: greater_than_40 ? option_1_to_cancel : option_2_to_cancel
actions:
- action1: set status = completed
- action2: add note 'Проверка завершена. Итоговый список лиц не пуст.'
- action3: update tasks_to_cancel set status = canceled
- action4: update tasks_to_cancel add note 'Задача не требуется, выбран иной путь РП'
task_template:
  id: 35503
  subject: Проверка списка лиц после согласования. Контроль активности лиц в МосИТСМ
existing_description: Для > 30 лицензий вызываем ручную задачу админов. Для <=30 лицензий производим отзыв автоматически
