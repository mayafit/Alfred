from typing import Dict, Any

def validate_jira_webhook(payload: Dict[Any, Any]) -> bool:
    """
    Validates if the incoming Jira webhook payload has required fields
    """
    try:
        if not payload.get('issue'):
            return False
        
        fields = payload['issue'].get('fields', {})
        if not fields:
            return False
            
        team_field = fields.get('customfield_team') or fields.get('team')
        if not team_field or team_field.lower() != 'devops':
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
    required_fields = ['status', 'tasks']
    if not all(field in response for field in required_fields):
        return False
        
    if response['status'] not in ['success', 'error']:
        return False
        
    if response['status'] == 'success' and not isinstance(response['tasks'], list):
        return False
        
    return True
