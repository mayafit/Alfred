import sys
import os
from flask import Blueprint, request, jsonify, Flask
from agents.utils.logger import setup_agent_logger
from prometheus_flask_exporter import PrometheusMetrics
import subprocess
import logging
import json
from prometheus_client import REGISTRY, Collector
from agents.helm_agent.smol_helm_agent import SmolHelmAgent

# Set up logger
logger = setup_agent_logger('helm-agent')

# Initialize the SmolHelmAgent
smol_helm_agent = SmolHelmAgent(api_key=os.environ.get('OPENAI_API_KEY'))

def validate_helm_request(data):
    """
    Validate incoming Helm chart request data
    """
    if not isinstance(data, dict):
        return False, "Invalid request format"

    if 'parameters' not in data:
        return False, "Missing parameters field"

    params = data['parameters']
    required_fields = ['repository', 'app_name', 'namespace']

    for field in required_fields:
        if field not in params:
            return False, f"Missing required field: {field}"

    # Optional field validations
    if 'service_ports' in params and not isinstance(params['service_ports'], list):
        return False, "service_ports must be a list"

    if 'environment_variables' in params and not isinstance(params['environment_variables'], dict):
        return False, "environment_variables must be a dictionary"
        
    if 'branch' in params and not isinstance(params['branch'], str):
        return False, "branch must be a string"

    return True, None

def register_routes_for_app(blueprint):
    """
    Register all routes with the provided blueprint
    """
    @blueprint.route('/health')
    def health():
        """
        Health check endpoint that also verifies access to required tools (helm, git)
        """
        try:
            # Check git command availability
            try:
                git_output = subprocess.check_output(["git", "--version"]).decode().strip()
                git_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                git_available = False
                git_output = "Git command not available"
                logger.error(git_output)

            # Check helm command availability
            try:
                helm_output = subprocess.check_output(["helm", "version"]).decode().strip()
                helm_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                helm_available = False
                helm_output = "Helm command not available"
                logger.error(helm_output)
                
            # Check OpenAI API key
            openai_key_available = os.environ.get('OPENAI_API_KEY') is not None

            # Check if all required tools are available
            all_available = git_available and helm_available and openai_key_available
            
            if not all_available:
                status_code = 500
                status = "unhealthy"
                
                # Build error message
                error_messages = []
                if not git_available:
                    error_messages.append("Git command not available")
                if not helm_available:
                    error_messages.append("Helm command not available")
                if not openai_key_available:
                    error_messages.append("OpenAI API key not set")
                    
                error_message = "; ".join(error_messages)
            else:
                status_code = 200
                status = "healthy"
                error_message = None

            return jsonify({
                "status": status,
                "service": "helm-agent",
                "git_available": git_available,
                "git_version": git_output if git_available else None,
                "helm_available": helm_available,
                "helm_version": helm_output if helm_available else None,
                "openai_key_available": openai_key_available,
                "error": error_message
            }), status_code
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

            # Extract parameters
            params = data['parameters']
            repository = params['repository']
            app_name = params['app_name']
            namespace = params['namespace']
            
            # Log optional parameters if present
            if 'service_ports' in params:
                logger.debug(f"Service ports: {params['service_ports']}")
            if 'environment_variables' in params:
                logger.debug(f"Environment variables: {params['environment_variables']}")
            if 'branch' in params:
                logger.debug(f"Branch: {params['branch']}")

            logger.info(f"Creating Helm chart for {repository} as {app_name} in namespace {namespace}")
            
            # Process the task using SmolHelmAgent
            result = smol_helm_agent.process_helm_task(data)
            
            # Log the result
            if result["status"] == "success":
                logger.info(f"Successfully created Helm chart for {repository}")
            else:
                logger.error(f"Failed to create Helm chart for {repository}: {result.get('message', 'Unknown error')}")
            
            return jsonify(result)

        except subprocess.CalledProcessError as e:
            error_msg = f"Command execution failed: {str(e)}"
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