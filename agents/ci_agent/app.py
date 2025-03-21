import os
from flask import Blueprint, request, jsonify
from agents.utils.logger import setup_agent_logger

# Create Blueprint
app = Blueprint('ci_agent', __name__)
logger = setup_agent_logger('ci-agent')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ci-agent"
    })

@app.route('/execute', methods=['POST'])
def execute():
    """Simple execution endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        # For now, just log and return success
        logger.info(f"Received CI request: {data}")

        return jsonify({
            "status": "success",
            "message": "CI request received",
            "data": data
        })

    except Exception as e:
        logger.error(f"Error processing CI request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process CI request: {str(e)}"
        }), 500