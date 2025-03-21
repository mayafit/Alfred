from flask import Flask, request, jsonify
from agents.utils.logger import setup_agent_logger
import logging
import os
import json

app = Flask(__name__)
logger = setup_agent_logger('deploy-agent')

def validate_deploy_request(data):
    """
    Validate incoming deployment request data
    """
    if not isinstance(data, dict):
        return False, "Invalid request format"

    if 'parameters' not in data:
        return False, "Missing parameters field"

    params = data['parameters']
    required_fields = ['repository', 'namespace']

    for field in required_fields:
        if field not in params:
            return False, f"Missing required field: {field}"

    return True, None

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "deploy-agent"
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
        is_valid, error_message = validate_deploy_request(data)
        if not is_valid:
            logger.error(f"Invalid request: {error_message}")
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400

        repository = data['parameters']['repository']
        namespace = data['parameters']['namespace']

        logger.info(f"Deploying {repository} to namespace {namespace}")

        # Here we'd implement the actual deployment logic
        # For now, we'll return a mock success response
        response = {
            "status": "success",
            "message": "Deployment completed successfully",
            "details": {
                "repository": repository,
                "namespace": namespace,
                "deployed_version": "1.0.0",
                "status": "Running"
            }
        }

        logger.info(f"Successfully deployed {repository} to {namespace}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing deployment: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process deployment: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9003, debug=True)