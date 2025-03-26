import sys
import os
from flask import Blueprint, request, jsonify, Flask
from agents.utils.logger import setup_agent_logger
from prometheus_flask_exporter import PrometheusMetrics
import subprocess
import logging
import json
import config
from prometheus_client import REGISTRY, Collector

# Set up logger
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

def register_routes_for_app(blueprint):
    """
    Register all routes with the provided blueprint
    """
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

            templates_exist = all(
                os.path.exists(os.path.join(template_dir, template))
                for template in required_templates
            )

            # Check git command availability
            try:
                subprocess.run(["git", "--version"], check=True, capture_output=True)
                git_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                git_available = False
                logger.error("Git command not available")

            if not templates_exist:
                logger.error("Missing required Jenkins templates")
                return jsonify({
                    "status": "unhealthy",
                    "service": "helm-agent",
                    "error": "Missing required templates"
                }), 500

            if not git_available:
                return jsonify({
                    "status": "unhealthy",
                    "service": "helm-agent",
                    "error": "Git command not available"
                }), 500

            return jsonify({
                "status": "healthy",
                "service": "helm-agent",
                "templates_available": True,
                "git_available": True
            })
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "service": "helm-agent",
                "error": str(e)
            }), 500

    @blueprint.route('/execute', methods=['POST'])
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

        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                "status": "error",
                "message": error_msg,
                "details": {
                    "command": e.cmd,
                    "exit_code": e.returncode,
                    "output": e.output.decode() if e.output else None
                }
            }), 500
        except Exception as e:
            logger.error(f"Error creating Helm chart: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to create Helm chart: {str(e)}"
            }), 500
    
    # Return the blueprint with routes registered
    return blueprint

def create_app():
    app = Flask(__name__)
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'connect_args': {
            'sslmode': 'require' if os.environ.get('POSTGRES_SSL', 'true').lower() == 'true' else 'prefer'
        }
    }
    
    # Initialize metrics with registry_name to avoid collisions
    # Create a separate registry to avoid collisions with the main app
    try:
        # Try to unregister the app_info metric if it exists to avoid duplicates
        for collector in list(REGISTRY._collector_to_names.keys()):
            if 'app_info' in REGISTRY._collector_to_names.get(collector, []):
                REGISTRY.unregister(collector)
                logger.info("Unregistered existing app_info metric")
                break
                
        metrics = PrometheusMetrics(app, registry_name='helm_agent_registry')
        metrics.info('helm_agent_info', 'Application info', version='1.0.0', service='helm_agent')
    except Exception as e:
        logger.warning(f"Prometheus metrics initialization error: {str(e)}")
        # Create metrics without info to avoid errors
        metrics = PrometheusMetrics(app, registry_name='helm_agent_registry')
    
    # Create and register the blueprint
    helm_agent_bp = Blueprint('helm_agent', __name__)
    
    # Register routes with the blueprint
    register_routes_for_app(helm_agent_bp)
    
    # Register blueprint with the app
    app.register_blueprint(helm_agent_bp)
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9002, debug=True)