import sys
import os
from flask import Blueprint, request, jsonify, Flask
from agents.utils.logger import setup_agent_logger
from prometheus_flask_exporter import PrometheusMetrics
import subprocess
import logging
import json
from agents.deploy_agent.routes import register_routes
from prometheus_client import REGISTRY, Collector
from agents.deploy_agent.smol_deploy_agent import SmolDeployAgent

# Create Blueprint first
deploy_agent_bp = Blueprint('deploy_agent', __name__)
logger = setup_agent_logger('deploy-agent')

# Initialize the SmolDeployAgent
# Using OpenAI for LLM capabilities with the OPENAI_API_KEY environment variable
smol_deploy_agent = SmolDeployAgent(api_key=os.environ.get('OPENAI_API_KEY'))


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
    
    # Initialize metrics with a unique registry name to avoid collisions
    try:
        # Try to unregister the app_info metric if it exists to avoid duplicates
        for collector in list(REGISTRY._collector_to_names.keys()):
            if 'app_info' in REGISTRY._collector_to_names.get(collector, []):
                REGISTRY.unregister(collector)
                logger.info("Unregistered existing app_info metric")
                break
                
        metrics = PrometheusMetrics(app, registry_name='deploy_agent_registry')
        metrics.info('deploy_agent_info', 'Application info', version='1.0.0', service='deploy_agent')
    except Exception as e:
        logger.warning(f"Prometheus metrics initialization error: {str(e)}")
        # Create metrics without info to avoid errors
        metrics = PrometheusMetrics(app, registry_name='deploy_agent_registry')
    
    # Register the deploy_agent_bp blueprint
    app.register_blueprint(deploy_agent_bp)
    
    return app

# Create the application instance
app = create_app()
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

    # Optional validation for specific fields
    if 'service_ports' in params and not isinstance(params['service_ports'], list):
        return False, "service_ports must be a list"

    if 'environment_variables' in params and not isinstance(params['environment_variables'], dict):
        return False, "environment_variables must be a dictionary"
        
    if 'cluster_details' in params and not isinstance(params['cluster_details'], dict):
        return False, "cluster_details must be a dictionary"
        
    if 'helm_values' in params and not (isinstance(params['helm_values'], dict) or 
                                         isinstance(params['helm_values'], str)):
        return False, "helm_values must be a dictionary or a string path to a values file"

    return True, None

@deploy_agent_bp.route('/health')
def health():
    """
    Health check endpoint that also verifies access to required tools (helm, kubectl, git)
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
            
        # Check kubectl command availability
        try:
            kubectl_output = subprocess.check_output(["kubectl", "version", "--client"]).decode().strip()
            kubectl_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            kubectl_available = False
            kubectl_output = "Kubectl command not available"
            logger.error(kubectl_output)

        # Check OpenAI API key
        openai_key_available = os.environ.get('OPENAI_API_KEY') is not None

        # Check if all required tools are available
        all_available = git_available and helm_available and kubectl_available and openai_key_available
        
        if not all_available:
            status_code = 500
            status = "unhealthy"
            
            # Build error message
            error_messages = []
            if not git_available:
                error_messages.append("Git command not available")
            if not helm_available:
                error_messages.append("Helm command not available")
            if not kubectl_available:
                error_messages.append("Kubectl command not available")
            if not openai_key_available:
                error_messages.append("OpenAI API key not set")
                
            error_message = "; ".join(error_messages)
        else:
            status_code = 200
            status = "healthy"
            error_message = None

        return jsonify({
            "status": status,
            "service": "deploy-agent",
            "git_available": git_available,
            "git_version": git_output if git_available else None,
            "helm_available": helm_available,
            "helm_version": helm_output if helm_available else None,
            "kubectl_available": kubectl_available,
            "kubectl_version": kubectl_output if kubectl_available else None,
            "openai_key_available": openai_key_available,
            "error": error_message
        }), status_code
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "service": "deploy-agent",
            "error": str(e)
        }), 500

@deploy_agent_bp.route('/execute', methods=['POST'])
def execute():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        # New validation logic adapted for SmolDeployAgent
        if 'parameters' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing parameters field"
            }), 400

        params = data['parameters']
        # Check for updated required fields for SmolDeployAgent
        required_fields = ['repository', 'namespace']
        missing_fields = [field for field in required_fields if field not in params]
        
        if missing_fields:
            logger.error(f"Missing required fields: {', '.join(missing_fields)}")
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # If 'cluster_details' is not provided, add an empty dict
        if 'cluster_details' not in params:
            params['cluster_details'] = {}
            logger.warning("No cluster_details provided, using default local configuration")

        repository = params['repository']
        namespace = params['namespace']

        logger.info(f"Deploying {repository} to namespace {namespace}")
        
        # Use SmolDeployAgent to process the deployment
        result = smol_deploy_agent.process_deployment_task(data)
        
        # Log the result
        if result["status"] == "success":
            logger.info(f"Successfully deployed {repository} to {namespace}")
        else:
            logger.error(f"Failed to deploy {repository} to {namespace}: {result.get('message', 'Unknown error')}")
        
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
        logger.error(f"Error processing deployment: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process deployment: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9003, debug=True)