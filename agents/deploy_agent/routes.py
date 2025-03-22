from flask import request, jsonify
import os
import subprocess
from agents.utils.logger import setup_agent_logger

logger = setup_agent_logger('helm-agent')

def register_routes(blueprint, repo_analyzer):
    @blueprint.route('/health')
    def health():
        """
        Health check endpoint that also verifies access to templates and dependencies
        """
        try:
            # Check if template directory exists and contains required templates
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
            required_templates = [
                "csharp_library.groovy",
                "aspnet_service.groovy",
                "node_service.groovy",
                "website.groovy"
            ]
            # ...existing health check code...
            return jsonify({"status": "healthy"}), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({"status": "unhealthy", "error": str(e)}), 500

    @blueprint.route('/execute', methods=['POST'])
    def execute():
        # ...existing execute route code...
        pass

    return blueprint