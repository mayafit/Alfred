import requests
from flask import Flask, request, jsonify
from services.jira_service import JiraService
from services.ai_service import AIService
from services.agent_router import AgentRouter
from utils.validators import validate_jira_webhook, validate_ai_response
from utils.logger import logger
import config
import os
from flask_sqlalchemy import SQLAlchemy
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram

# Initialize Flask-SQLAlchemy
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Configure the SQLAlchemy part of the app instance
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get("SESSION_SECRET")

    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)

    # Static information as metric
    metrics.info('app_info', 'Application info', version='1.0.0')

    # Initialize plugins
    db.init_app(app)

    with app.app_context():
        # Import routes
        from routes.dashboard import dashboard

        # Register blueprints
        app.register_blueprint(dashboard)

        # Create database tables
        db.create_all()

        return app

app = create_app()
app.secret_key = config.SECRET_KEY

jira_service = JiraService()
ai_service = AIService()
agent_router = AgentRouter()

# Add some custom metrics
task_counter = Counter('task_total', 'Total number of tasks processed', ['type', 'status'])
task_processing_time = Histogram('task_processing_seconds', 'Time spent processing tasks')

@app.route('/')
def index():
    return jsonify({'message': 'DevOps Automation Service'})

@app.route('/health')
def health_check():
    try:
        # Check if the CI agent Blueprint routes are registered
        ci_routes = [rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith('ci_agent')]

        return jsonify({
            'status': 'healthy',
            'services': {
                'main_app': True,
                'jira': True,
                'ai': True,
                'ci_agent': len(ci_routes) > 0,
                'routes': {
                    'ci_agent': [str(rule) for rule in ci_routes]
                }
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/test/analyze', methods=['POST'])
def test_analysis():
    """
    Test endpoint for AI task analysis without Jira integration
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.json
        description = data.get('description')
        if not description:
            return jsonify({'error': 'Description is required'}), 400

        # Parse description using AI service
        ai_response = ai_service.parse_description(description)
        logger.debug(f"AI Response: {ai_response}")

        if not ai_response:
            error_message = "Unable to parse the task description"
            logger.error(error_message)
            return jsonify({'status': 'error', 'message': error_message}), 400

        # Process tasks with appropriate agents
        results = agent_router.process_tasks(ai_response['tasks'])

        return jsonify({
            'status': 'success',
            'message': 'Tasks processed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/jira', methods=['POST'])
def jira_webhook():
    try:
        payload = request.json

        if not validate_jira_webhook(payload):
            return jsonify({'error': 'Invalid webhook payload'}), 400

        issue_key = payload['issue']['key']
        description = payload['issue']['fields']['description']

        # Parse description using AI service
        ai_response = ai_service.parse_description(description)

        if not ai_response or not validate_ai_response(ai_response):
            error_message = "Unable to parse the task description. Please ensure it follows the required format."
            jira_service.add_comment(issue_key, error_message)
            return jsonify({'status': 'error', 'message': error_message}), 400

        if ai_response['status'] == 'error':
            # Check if this is a system error
            is_system_error = ai_response.get('system_error', False)
            error_message = ai_response['message']

            # Log additional details if available
            if is_system_error and 'log_details' in ai_response:
                logger.error(f"System error details for {issue_key}: {ai_response['log_details']}")

            jira_service.add_comment(issue_key, error_message)
            if is_system_error:
                jira_service.update_issue_status(issue_key, "Failed")
            return jsonify({'status': 'error', 'message': error_message}), 400

        # Process tasks with appropriate agents
        results = agent_router.process_tasks(ai_response['tasks'])

        # Update Jira with results
        success_count = len(results['success'])
        failed_count = len(results['failed'])

        status_message = f"Processed {success_count + failed_count} tasks:\n"
        status_message += f"- {success_count} tasks completed successfully\n"
        status_message += f"- {failed_count} tasks failed\n\n"

        if failed_count > 0:
            status_message += "Failed tasks:\n"
            for failed in results['failed']:
                status_message += f"- Task: {failed['task']}\n  Error: {failed['error']}\n"

        jira_service.add_comment(issue_key, status_message)

        if failed_count == 0:
            jira_service.update_issue_status(issue_key, "Done")
        else:
            jira_service.update_issue_status(issue_key, "Failed")

        return jsonify({
            'status': 'success',
            'message': 'Tasks processed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/test/ci', methods=['POST'])
def test_ci():
    """
    Test endpoint specifically for CI pipeline creation
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.json
        repository = data.get('repository')
        if not repository:
            return jsonify({'error': 'Repository URL is required'}), 400

        logger.info(f"Testing CI pipeline creation for repository: {repository}")

        # Create a CI task structure
        task = {
            "type": "ci",
            "description": "Set up CI pipeline",
            "parameters": {
                "repository": repository,
                "branch": data.get('branch', 'main'),
                "build_steps": data.get('build_steps', ["test", "lint", "build"])
            }
        }

        # Route the task directly to CI agent
        logger.info("Routing task to CI agent")
        result = agent_router.route_task('ci', task)
        if not result:
            logger.error("Failed to process CI task - no response from agent")
            return jsonify({
                'status': 'error',
                'message': 'Failed to process CI task'
            }), 500

        logger.info(f"CI agent response: {result}")
        return jsonify({
            'status': 'success',
            'message': 'CI pipeline created',
            'result': result
        })

    except Exception as e:
        logger.error(f"Error processing CI test request: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)