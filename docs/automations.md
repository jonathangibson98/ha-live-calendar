# Automation examples

Replace `calendar.family` with your entity.

## Notify when an event is added

```yaml
alias: Calendar - new event added
triggers:
  - trigger: event
    event_type: live_calendar_changed
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.added | length > 0 }}"
actions:
  - action: notify.notify
    data:
      title: "New event in {{ trigger.event.data.calendar }}"
      message: "{{ trigger.event.data.added | map(attribute='summary') | join(', ') }}"
```

## Warn when an event is moved or edited

```yaml
alias: Calendar - event changed
triggers:
  - trigger: event
    event_type: live_calendar_changed
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.updated | length > 0 }}"
actions:
  - action: persistent_notification.create
    data:
      message: "Updated: {{ trigger.event.data.updated | map(attribute='summary') | join(', ') }}"
```

## Do something when an event starts

```yaml
alias: Calendar - event started
triggers:
  - trigger: calendar
    event: start
    entity_id: calendar.family
    offset: "-0:10:0"   # ten minutes before
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
```

## Read upcoming events

```yaml
action: calendar.get_events
target:
  entity_id: calendar.family
data:
  duration:
    days: 7
response_variable: agenda
```

## Force a refresh from an automation

```yaml
action: homeassistant.update_entity
target:
  entity_id: calendar.family
```
