def validate_ci_request(data):
    """
    Validate incoming CI request data
    """
    if not isinstance(data, dict):
        return False, "Invalid request format"

    if 'parameters' not in data:
        return False, "Missing parameters field"

    params = data['parameters']
    required_fields = ['repository', 'branch', 'build_steps']

    for field in required_fields:
        if field not in params:
            return False, f"Missing required field: {field}"

    if not isinstance(params['build_steps'], list):
        return False, "build_steps must be a list"

    return True, None