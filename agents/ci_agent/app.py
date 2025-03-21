from flask import Flask, request, jsonify
from agents.utils.logger import setup_agent_logger
import subprocess
import logging
import os
import json

app = Flask(__name__)
logger = setup_agent_logger('ci-agent')

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

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "ci-agent"
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
        is_valid, error_message = validate_ci_request(data)
        if not is_valid:
            logger.error(f"Invalid request: {error_message}")
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400

        repository = data['parameters']['repository']
        branch = data['parameters']['branch']
        build_steps = data['parameters']['build_steps']

        logger.info(f"Processing CI pipeline for {repository} on branch {branch}")
        logger.debug(f"Build steps: {build_steps}")

        # Here we'd implement the actual CI pipeline creation
        # For now, we'll return a mock success response
        response = {
            "status": "success",
            "message": "CI pipeline created successfully",
            "details": {
                "repository": repository,
                "branch": branch,
                "build_steps": build_steps,
                "pipeline_url": f"https://ci.example.com/pipelines/{repository.split('/')[-1]}"
            }
        }

        logger.info(f"Successfully created CI pipeline for {repository}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing CI request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process CI request: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)