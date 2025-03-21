from flask import Flask, request, jsonify
from agents.utils.logger import setup_agent_logger
import logging
import os
import json

app = Flask(__name__)
logger = setup_agent_logger('helm-agent')

def validate_helm_request(data):
    """
    Validate incoming Helm chart request data
    """
    if not isinstance(data, dict):
        return False, "Invalid request format"

    if 'parameters' not in data:
        return False, "Missing parameters field"

    params = data['parameters']
    required_fields = ['repository', 'service_ports', 'environment_variables']

    for field in required_fields:
        if field not in params:
            return False, f"Missing required field: {field}"

    if not isinstance(params['service_ports'], list):
        return False, "service_ports must be a list"

    if not isinstance(params['environment_variables'], dict):
        return False, "environment_variables must be a dictionary"

    return True, None

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "helm-agent"
    })

@app.route('/execute', methods=['POST'])
def execute():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        # Validate request
        is_valid, error_message = validate_helm_request(data)
        if not is_valid:
            logger.error(f"Invalid request: {error_message}")
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400

        repository = data['parameters']['repository']
        service_ports = data['parameters']['service_ports']
        env_vars = data['parameters']['environment_variables']

        logger.info(f"Creating Helm chart for {repository}")
        logger.debug(f"Service ports: {service_ports}")
        logger.debug(f"Environment variables: {env_vars}")

        # Here we'd implement the actual Helm chart creation
        # For now, we'll return a mock success response
        response = {
            "status": "success",
            "message": "Helm chart created successfully",
            "details": {
                "repository": repository,
                "chart_name": repository.split('/')[-1],
                "service_ports": service_ports,
                "environment_variables": env_vars
            }
        }

        logger.info(f"Successfully created Helm chart for {repository}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error creating Helm chart: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to create Helm chart: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9002, debug=True)