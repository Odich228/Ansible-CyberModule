# Ansible Module: Acronis Cyber Protect Agent

[![Ansible](https://img.shields.io/badge/Ansible-2.9+-blue.svg)](https://www.ansible.com/)
[![Python](https://img.shields.io/badge/Python-3.6+-green.svg)](https://www.python.org/)

Кастомный Ansible-модуль для автоматизации установки и удаления *Cyber Backup** агентов на Linux-хостах.

## 📖 Описание

Модуль `CyberBackup_agent` позволяет полностью автоматизировать развертывание агентов CyberBackup в инфраструктуре любой масштаба. Он использует официальный CLI-инсталлятор CyberBackup и поддерживает все основные сценарии регистрации агента на сервере управления.

### Что умеет модуль

✅ **Установка агента** с выбором компонентов  
✅ **Удаление агента** одной командой  
✅ **Три метода регистрации**: по токену, по логину/паролю, без регистрации  
✅ **Идемпотентность** — повторный запуск не ломает систему  
✅ **Check mode** — безопасный dry-run перед реальными изменениями  
✅ **Проверка сервиса** — модуль сам проверяет, что `acronis_mms.service` появился в systemd  
✅ **Валидация компонентов** — защита от опечаток в названиях  

## 🚀 Быстрый старт

### 1. Структура проекта

```
acronis/
├── library/
│   └── CyberBackup.py              # Сам модуль
├── CyberBackup_18_64-bit.x86_64      # Инсталлятор Acronis
├── inventory                         # Список хостов
├── install.yml                       # Плейбук установки
└── uninstall.yml                     # Плейбук удаления
```

### 2. Inventory

Создайте файл `inventory`:

```ini
[acronis_servers]
<<Server IP>>
<<Server IP>>
<<Server IP>>

[acronis_servers:vars]
ansible_user=root
```

### 3. Установка агента

Создайте `install.yml`:

```yaml
---
- name: Install Acronis agent
  hosts: acronis_servers
  become: true

  tasks:
    - name: Copy installer to hosts
      ansible.builtin.copy:
        src: CyberBackup_18_64-bit.x86_64
        dest: /tmp/CyberBackup_18_64-bit.x86_64
        mode: '0755'

    - name: Install Acronis agent
      CyberBackup:
        installer: /tmp/CyberBackup_18_64-bit.x86_64
        state: present
        components:
          - BackupAndRecoveryAgent
          - BackupAndRecoveryBootableComponents
        server: management.acronis.com
        registration_method: token
        token: "YOUR_TOKEN_HERE"
        language: ru

    - name: Ensure service is running
      ansible.builtin.systemd:
        name: acronis_mms.service
        state: started
        enabled: true
```

Запуск:

```bash
ansible-playbook -i inventory install.yml
```

### 4. Удаление агента

Создайте `uninstall.yml`:

```yaml
---
- name: Uninstall Acronis agent
  hosts: acronis_servers
  become: true

  tasks:
    - name: Copy installer to hosts
      ansible.builtin.copy:
        src: CyberBackup_18_64-bit.x86_64
        dest: /tmp/CyberBackup_18_64-bit.x86_64
        mode: '0755'

    - name: Stop Acronis service
      ansible.builtin.systemd:
        name: acronis_mms.service
        state: stopped
        enabled: false
      ignore_errors: true

    - name: Uninstall Acronis agent
      CyberBackup:
        installer: /tmp/CyberBackup_18_64-bit.x86_64
        state: absent

    - name: Remove installer
      ansible.builtin.file:
        path: /tmp/CyberBackup_18_64-bit.x86_64
        state: absent
```

Запуск:

```bash
ansible-playbook -i inventory uninstall.yml
```

## 📋 Параметры модуля

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|:------------:|:------------:|----------|
| `installer` | path | ✅ | — | Путь к инсталлятору CyberBackup на целевом хосте |
| `state` | str | ❌ | `present` | Состояние агента: `present` (установить) или `absent` (удалить) |
| `components` | list | ❌ | `[]` | Список компонентов для установки |
| `server` | str | ⚠️ | — | Адрес сервера управления Acronis (обязателен при регистрации) |
| `registration_method` | str | ❌ | `token` | Метод регистрации: `token` или `credentials` |
| `token` | str | ⚠️ | — | Токен регистрации (если выбран метод `token`) |
| `login` | str | ⚠️ | — | Логин (если выбран метод `credentials`) |
| `password` | str | ⚠️ | — | Пароль (если выбран метод `credentials`) |
| `language` | str | ❌ | `ru` | Язык инсталлятора |
| `skip_registration` | bool | ❌ | `false` | Пропустить регистрацию агента |

> ⚠️ Параметр обязателен только при определённых условиях (см. раздел "Условные зависимости").

### Условные зависимости

| Если... | ...то обязательно укажите |
|---------|---------------------------|
| `state: present` и `skip_registration: false` | `server` |
| `registration_method: token` | `token` |
| `registration_method: credentials` | `login` и `password` |

## 🧩 Поддерживаемые компоненты

| Компонент | Описание |
|-----------|----------|
| `AcronisCentralizedManagementServer` | Центральный сервер управления |
| `BackupAndRecoveryAgent` | Агент резервного копирования (основной) |
| `BackupAndRecoveryBootableComponents` | Загрузочные компоненты |
| `CommunigateAgentFeature` | Интеграция с CommuniGate |
| `K8sAgentFeature` | Защита Kubernetes |
| `MailionAgentFeature` | Защита Mailion |
| `MySQLAgentFeature` | Защита MySQL |
| `OVirtAgentFeature` | Защита oVirt |
| `OracleAgentFeature` | Защита Oracle |
| `PostgreSqlAgentFeature` | Защита PostgreSQL |
| `StorageServer` | Сервер хранилища |
| `WorkmailAgentFeature` | Защита Workmail |

## 💡 Примеры использования

### Установка с логином и паролем

```yaml
- name: Install with credentials
  CyberBackup:
    installer: /tmp/CyberBackup_18_64-bit.x86_64
    state: present
    components:
      - BackupAndRecoveryAgent
      - MySQLAgentFeature
    server: management.acronis.com
    registration_method: credentials
    login: admin@company.com
    password: "{{ vault_acronis_password }}"
    language: ru
```

### Установка без регистрации

```yaml
- name: Install without registration
  CyberBackup:
    installer: /tmp/CyberBackup_18_64-bit.x86_64
    state: present
    components:
      - BackupAndRecoveryAgent
    skip_registration: true
    language: ru
```

### Проверка без изменений (dry-run)

```bash
ansible-playbook -i inventory install.yml --check --diff
```

### Запуск только на одном хосте

```bash
ansible-playbook -i inventory install.yml --limit 172.20.1.41
```

## ⚙️ Как это работает

```
┌──────────────────────┐           ┌──────────────────────┐
│   Control Node       │           │   Target Host        │
│                      │           │                      │
│ 1. Читает playbook   │           │                      │
│ 2. Копирует модуль   │───SSH────>│ 3. Запуск модуля     │
│    в /tmp/...        │           │    (Python)          │
│                      │           │                      │
│                      │           │ 4. Проверка systemd  │
│                      │           │ 5. Запуск инсталлера │
│                      │           │ 6. Проверка сервиса  │
│                      │<──JSON────│ 7. Возврат результата│
│ 8. Вывод в консоль   │           │                      │
└──────────────────────┘           └──────────────────────┘
```

## 🔍 Troubleshooting

### Ошибка: `Installer not found`

Проверьте, что инсталлятор скопирован на хост:

```bash
ansible acronis_servers -i inventory -m shell -a "ls -la /tmp/CyberBackup_18_64-bit.x86_64"
```

### Ошибка: `Service acronis_mms.service not found after install`

Инсталлятор завершился, но сервис не появился. Проверьте логи:

```bash
journalctl -u acronis_mms.service
cat /var/log/acronis/install.log
```


### Подробный вывод для отладки

```bash
ansible-playbook -i inventory install.yml -vvv
```


Создано для автоматизации развертывания CyberBackup в корпоративной инфраструктуре.
