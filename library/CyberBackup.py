#!/usr/bin/python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import os
import subprocess

# Используем set для быстрого поиска (O(1))
SUPPORTED_COMPONENTS = {
    "AcronisCentralizedManagementServer", "BackupAndRecoveryAgent", 
    "BackupAndRecoveryBootableComponents", "CommunigateAgentFeature", 
    "K8sAgentFeature", "MailionAgentFeature", "MySQLAgentFeature",
    "OVirtAgentFeature", "OracleAgentFeature", "PostgreSqlAgentFeature", 
    "StorageServer", "WorkmailAgentFeature"
}
SERVICE_NAME = "acronis_mms.service"

DOCUMENTATION = r'''
---
module: acronis_agent
short_description: Install or uninstall Acronis Cyber Protect agents
description:
    - This module installs or uninstalls Acronis agents using the command-line installer.
    - Note: Passing passwords via CLI arguments might expose them in process lists (ps aux). 
      Ensure the target node is secured.
options:
    installer:
        description: Path to the Acronis installer executable.
        type: path
        required: true
    state:
        description: Desired state of the agent.
        type: str
        default: present
        choices: ['present', 'absent']
    components:
        description: List of components to install.
        type: list
        elements: str
        default: []
    server:
        description: Acronis management server address.
        type: str
    registration_method:
        description: Method to register the agent.
        type: str
        default: token
        choices: ['token', 'credentials']
    token:
        description: Registration token.
        type: str
        no_log: true
    login:
        description: Registration login.
        type: str
    password:
        description: Registration password.
        type: str
        no_log: true
    language:
        description: Installer language.
        type: str
        default: ru
    skip_registration:
        description: Skip agent registration during installation.
        type: bool
        default: false
'''

EXAMPLES = r'''
- name: Install agent with token
  acronis_agent:
    installer: /tmp/AcronisAgent.x86_64
    components:
      - BackupAndRecoveryAgent
    server: management.acronis.com
    registration_method: token
    token: "my-secret-token"

- name: Uninstall agent
  acronis_agent:
    installer: /tmp/AcronisAgent.x86_64
    state: absent
'''

RETURN = r'''
stdout:
  description: Standard output from the installer.
  returned: always
  type: str
stderr:
  description: Standard error from the installer.
  returned: always
  type: str
'''

def run_command(cmd):
    """Запускает команду и возвращает результат."""
    return subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True
    )

def is_installed():
    """
    Проверяет, установлен ли сервис в systemd.
    LoadState=loaded означает, что юнит найден и установлен.
    """
    result = run_command(["systemctl", "show", "-p", "LoadState", "--value", SERVICE_NAME])
    return result.stdout.strip() == "loaded"

def build_command(params):
    """Формирует список аргументов для инсталлятора."""
    cmd = [
        params["installer"],
        "--auto",
        "--id", ",".join(params["components"]),
        f'--language={params["language"]}'
    ]
    
    if params["skip_registration"]:
        cmd.append("--skip-registration")
        return cmd

    cmd.append(f'--rain={params["server"]}')
    
    if params["registration_method"] == "token":
        cmd.append(f'--token={params["token"]}')
    else:
        cmd.extend([
            f'--login={params["login"]}',
            f'--password={params["password"]}'
        ])
        
    return cmd

def main():
    module = AnsibleModule(
        argument_spec=dict(
            installer=dict(type="path", required=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            components=dict(type="list", elements="str", default=[]),
            server=dict(type="str"),
            registration_method=dict(type="str", default="token", choices=["token", "credentials"]),
            token=dict(type="str", no_log=True),
            login=dict(type="str"),
            password=dict(type="str", no_log=True),
            language=dict(type="str", default="ru"),
            skip_registration=dict(type="bool", default=False)
        ),
        supports_check_mode=True
    )

    params = module.params
    state = params["state"]
    
    # --- Валидация ТОЛЬКО при установке ---
    if state == "present":
        if not params["skip_registration"]:
            if not params["server"]:
                module.fail_json(msg="'server' is required when skip_registration=False")
            if params["registration_method"] == "token" and not params["token"]:
                module.fail_json(msg="'token' is required when registration_method=token")
            if params["registration_method"] == "credentials" and (not params["login"] or not params["password"]):
                module.fail_json(msg="'login' and 'password' are required when registration_method=credentials")

    # --- Проверка инсталлера ---
    if not os.path.isfile(params["installer"]):
        module.fail_json(msg=f"Installer not found or is not a file: {params['installer']}")
    
    if not os.access(params["installer"], os.X_OK):
        try:
            os.chmod(params["installer"], 0o755)
        except Exception as e:
            module.fail_json(msg=f"Failed to chmod installer: {str(e)}")

    # --- Проверка компонентов (только при установке) ---
    if state == "present":
        unsupported = set(params["components"]) - SUPPORTED_COMPONENTS
        if unsupported:
            module.fail_json(msg=f"Unsupported components: {', '.join(unsupported)}")

    # --- Логика Check Mode ---
    currently_installed = is_installed()
    if state == "present":
        changed = not currently_installed
    else:
        changed = currently_installed
        
    if module.check_mode:
        module.exit_json(changed=changed)

    # --- Выполнение действий ---
    if state == "present":
        if currently_installed:
            module.exit_json(changed=False, installed=True, msg="Agent is already installed.")
            
        result = run_command(build_command(params))
        if result.returncode != 0:
            module.fail_json(msg="Installation failed", stdout=result.stdout, stderr=result.stderr)
            
        if not is_installed():
            module.fail_json(msg="Installation finished, but service is not found in systemd.", 
                             stdout=result.stdout, stderr=result.stderr)
                             
        module.exit_json(changed=True, installed=True, stdout=result.stdout, stderr=result.stderr)
        
    else:  # state == "absent"
        if not currently_installed:
            module.exit_json(changed=False, installed=False, msg="Agent is already absent.")
            
        result = run_command([params["installer"], "--auto", "--uninstall"])
        if result.returncode != 0:
            module.fail_json(msg="Uninstallation failed", stdout=result.stdout, stderr=result.stderr)
            
        module.exit_json(changed=True, installed=False, stdout=result.stdout, stderr=result.stderr)            
  
if __name__ == "__main__":
    main()
