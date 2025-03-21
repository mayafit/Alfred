from typing import Dict, Any

def validate_jira_webhook(payload: Dict[Any, Any]) -> bool:
    """
    Validates if the incoming Jira webhook payload has required fields and DevOps identifiers
    """
    try:
        if not payload.get('issue'):
            return False

        issue = payload['issue']
        fields = issue.get('fields', {})
        if not fields:
            return False

        # Check for team field with value "devops"
        team_field = fields.get('customfield_team') or fields.get('team')
        has_devops_team = team_field and str(team_field).lower() == 'devops'

        # Check for devops label
        labels = fields.get('labels', [])
        has_devops_label = any(label.lower() == 'devops' for label in labels)

        # Issue must have either devops team or label
        if not (has_devops_team or has_devops_label):
            return False

        if not fields.get('description'):
            return False

        return True
    except Exception:
        return False

def validate_ai_response(response: Dict[Any, Any]) -> bool:
    """
    Validates if the AI service response is properly structured
    """
    try:
        if not isinstance(response, dict):
            return False

        required_fields = ['status', 'tasks']
        if not all(field in response for field in required_fields):
            return False

        if response['status'] not in ['success', 'error']:
            return False

        if response['status'] == 'success':
            if not isinstance(response['tasks'], list):
                return False

            valid_task_types = ['ci', 'helm', 'deploy']
            for task in response['tasks']:
                if not isinstance(task, dict):
                    return False
                if 'type' not in task or task['type'] not in valid_task_types:
                    return False
                if 'description' not in task or 'parameters' not in task:
                    return False

        return True
    except Exception:
        return False