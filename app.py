# Import required libraries
import requests
from flask import Flask, request, jsonify
# Import custom services and utilities
from services.jira_service import JiraService
from services.ai_service import AIService
from services.agent_router import AgentRouter
from services.task_validator import TaskValidator
from utils.validators import validate_jira_webhook, validate_ai_response
from utils.logger import logger, log_system_event
import config
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
# Import Prometheus monitoring tools
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram
import logging

# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with custom base class
db = SQLAlchemy(model_class=Base)

def create_app():
    """
    Factory function to create and configure the Flask application
    """
    app = Flask(__name__)

    # Configure database connection
    database_url = os.environ.get('DATABASE_URL')
    # Handle legacy postgres:// URLs by converting to postgresql://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Set up SQLAlchemy configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Configure connection pool and SSL settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,  # Recycle connections every 5 minutes
        'pool_pre_ping': True,  # Check connection validity before use
        'connect_args': {
            'sslmode': 'require' if os.environ.get('POSTGRES_SSL', 'true').lower() == 'true' else 'prefer'
        }
    }
    app.secret_key = os.environ.get("SESSION_SECRET")

    # Set up Prometheus monitoring with unique registry
    metrics = PrometheusMetrics(app, registry_name='main_app_registry')
    metrics.info('app_info', 'Application info', version='1.0.0', service='main_app')

    # Initialize database
    db.init_app(app)

    with app.app_context():
        # Import and register routes
        from routes.dashboard import dashboard
        app.register_blueprint(dashboard)

        try:
            # Create all database tables
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

        return app

# Initialize application and services
app = create_app()
app.secret_key = config.SECRET_KEY

# Create service instances
jira_service = JiraService()
ai_service = AIService()
agent_router = AgentRouter()
task_validator = TaskValidator()
# SMS service has been removed as per user request

# Define Prometheus metrics
task_counter = Counter('task_total', 'Total number of tasks processed', ['type', 'status'])
task_processing_time = Histogram('task_processing_seconds', 'Time spent processing tasks')

@app.route('/')
def index():
    """Root endpoint that redirects to the task creation page"""
    from flask import redirect, url_for
    return redirect(url_for('task.task_page'))

@app.route('/health')
def health_check():
    """
    Health check endpoint that verifies core services and routes
    Returns detailed status of various components
    """
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
    Test endpoint for analyzing tasks using AI without Jira integration
    Accepts task descriptions and returns processed results
    """
    try:
        # Log request details
        logger.info("[test_analysis:129] Starting test analysis request")
        logger.debug(f"[test_analysis:130] Request headers: {dict(request.headers)}")
        
        # Log system event for task received
        log_system_event(
            event_type="task_received",
            service="main",
            description="Test analysis request received",
            event_data={"endpoint": "/test/analyze", "method": "POST"}
        )

        if not request.is_json:
            logger.error("[test_analysis:133] Request content-type is not application/json")
            log_system_event(
                event_type="error",
                service="main",
                description="Invalid request format - not JSON",
                event_data={"endpoint": "/test/analyze"}
            )
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.json
        logger.debug(f"[test_analysis:137] Received request data: {data}")

        description = data.get('description')
        if not description:
            logger.error("[test_analysis:141] Missing required field 'description' in request")
            log_system_event(
                event_type="error",
                service="main",
                description="Missing required field 'description'",
                event_data={"endpoint": "/test/analyze"}
            )
            return jsonify({'error': 'Description is required'}), 400

        # Parse description using AI service
        logger.info(f"[test_analysis:145] Sending description to AI service (length: {len(description)})")
        logger.debug(f"[test_analysis:146] Description content: {description[:200]}...")
        
        log_system_event(
            event_type="ai_analysis",
            service="main",
            description="Sending task description to AI service for analysis",
            event_data={"description_length": len(description)}
        )
        
        ai_response = ai_service.parse_description(description)
        logger.debug(f"[test_analysis:149] AI Response raw: {ai_response}")

        if not ai_response:
            error_message = "Unable to parse the task description"
            logger.error(f"[test_analysis:153] AI service returned empty response for input: {description[:100]}...")
            log_system_event(
                event_type="error",
                service="main",
                description="AI service returned empty response",
                event_data={"description_preview": description[:100]}
            )
            return jsonify({'status': 'error', 'message': error_message}), 400

        # Process tasks with appropriate agents
        task_count = len(ai_response.get('tasks', []))
        logger.info(f"[test_analysis:158] Processing {task_count} tasks from AI response")
        logger.debug(f"[test_analysis:159] Tasks to process: {ai_response.get('tasks', [])}")
        
        log_system_event(
            event_type="agent_triggered",
            service="main",
            description=f"Processing {task_count} tasks from AI analysis",
            event_data={"task_count": task_count, "task_types": [task.get('type') for task in ai_response.get('tasks', [])]}
        )
        
        results = agent_router.process_tasks(ai_response['tasks'])
        success_count = len(results.get('success', []))
        failed_count = len(results.get('failed', []))
        
        logger.info(f"[test_analysis:162] Task processing complete. Success: {success_count}, Failed: {failed_count}")
        logger.debug(f"[test_analysis:163] Detailed results: {results}")
        
        # Create detailed event data including failure reasons if any
        event_data = {
            "success_count": success_count,
            "failed_count": failed_count,
        }
        
        # Add failure details if there are any failures
        if failed_count > 0:
            failure_details = []
            for failed_task in results.get('failed', []):
                task_type = failed_task.get('task', {}).get('type', 'unknown')
                error = failed_task.get('error', 'Unknown error')
                failure_details.append({"task_type": task_type, "error": error})
            
            event_data["failure_details"] = failure_details
            
            # Enhance description with failure reasons
            task_error_descriptions = [f"{detail['task_type']}: {detail['error']}" for detail in failure_details]
            description = f"Task processing complete. Success: {success_count}, Failed: {failed_count}. Failures: {', '.join(task_error_descriptions)}"
        else:
            description = f"Task processing complete. Success: {success_count}, Failed: {failed_count}"
        
        log_system_event(
            event_type="task_completed",
            service="main",
            description=description,
            event_data=event_data
        )

        return jsonify({
            'status': 'success',
            'message': 'Tasks processed',
            'results': results
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"[test_analysis:172] Error processing request: {str(e)}")
        logger.error(f"[test_analysis:173] Stack trace: {error_trace}")
        logger.error(f"[test_analysis:174] Request data: {request.get_data()}")
        
        log_system_event(
            event_type="error",
            service="main",
            description=f"Exception in test_analysis: {str(e)}",
            event_data={"error_trace": error_trace}
        )
        
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/webhook/jira', methods=['POST'])
def jira_webhook():
    """
    Webhook endpoint for Jira integration
    Processes Jira issue updates, analyzes tasks, and updates issue status
    """
    try:
        logger.info("Received Jira webhook request")
        
        # Log system event for Jira webhook received
        log_system_event(
            event_type="webhook_received",
            service="main",
            description="Jira webhook request received",
            event_data={"endpoint": "/webhook/jira", "method": "POST"}
        )
        
        payload = request.json
        
        # Log and validate webhook payload
        logger.debug(f"Validating webhook payload: {payload}")
        if not validate_jira_webhook(payload):
            logger.error("Invalid webhook payload received")
            log_system_event(
                event_type="error",
                service="main",
                description="Invalid Jira webhook payload",
                event_data={"endpoint": "/webhook/jira"}
            )
            return jsonify({'error': 'Invalid webhook payload'}), 400

        issue_key = payload['issue']['key']
        description = payload['issue']['fields']['description']
        logger.info(f"Processing Jira issue {issue_key}")
        logger.debug(f"Issue description: {description}")
        
        log_system_event(
            event_type="task_received",
            service="main",
            description=f"Processing Jira issue {issue_key}",
            event_data={"issue_key": issue_key, "description_length": len(description)}
        )

        # Parse description using AI service
        logger.info(f"Sending description to AI service for parsing")
        
        log_system_event(
            event_type="ai_analysis",
            service="main",
            description=f"Sending issue {issue_key} description to AI service for analysis",
            event_data={"issue_key": issue_key, "description_length": len(description)}
        )
        
        ai_response = ai_service.parse_description(description)
        logger.debug(f"AI service response: {ai_response}")

        if not ai_response or not validate_ai_response(ai_response):
            logger.error(f"AI service failed to parse description for issue {issue_key}")
            error_message = "Unable to parse the task description. Please ensure it follows the required format."
            
            log_system_event(
                event_type="error",
                service="main",
                description=f"AI service failed to parse description for issue {issue_key}",
                event_data={"issue_key": issue_key, "error": "Invalid or empty AI response"}
            )
            
            jira_service.add_comment(issue_key, error_message)
            return jsonify({'status': 'error', 'message': error_message}), 400
            
        # Validate if tasks have all required details
        validation_result = task_validator.validate_tasks(ai_response.get('tasks', []))
        if not validation_result["is_valid"]:
            logger.warning(f"Tasks for issue {issue_key} are missing required details")
            
            # Generate a detailed feedback message
            feedback_message = "⚠️ Tasks are missing required details:\n\n"
            feedback_message += task_validator.generate_feedback_message(validation_result)
            feedback_message += "\nPlease update the description with the missing information and try again."
            
            # Log the validation failure
            log_system_event(
                event_type="warning",
                service="main",
                description=f"Incomplete task details for issue {issue_key}",
                event_data={
                    "issue_key": issue_key, 
                    "validation_result": validation_result
                }
            )
            
            # Add a comment to the Jira issue
            jira_service.add_comment(issue_key, feedback_message)
            
            return jsonify({
                'status': 'error', 
                'message': 'Tasks are missing required details',
                'details': validation_result
            }), 400

        if ai_response['status'] == 'error':
            # Check if this is a system error
            is_system_error = ai_response.get('system_error', False)
            error_message = ai_response['message']
            logger.error(f"AI service returned error for {issue_key}: {error_message}")

            # Log additional details if available
            log_data = {"issue_key": issue_key, "error_message": error_message, "is_system_error": is_system_error}
            if is_system_error and 'log_details' in ai_response:
                logger.error(f"System error details for {issue_key}: {ai_response['log_details']}")
                log_data["log_details"] = ai_response['log_details']
            
            log_system_event(
                event_type="error",
                service="main",
                description=f"AI service error for issue {issue_key}: {error_message}",
                event_data=log_data
            )

            jira_service.add_comment(issue_key, error_message)
            if is_system_error:
                logger.info(f"Updating issue {issue_key} status to Failed due to system error")
                jira_service.update_issue_status(issue_key, "Failed")
            return jsonify({'status': 'error', 'message': error_message}), 400

        # Process tasks with appropriate agents
        task_count = len(ai_response['tasks'])
        logger.info(f"Processing {task_count} tasks for issue {issue_key}")
        
        log_system_event(
            event_type="agent_triggered",
            service="main",
            description=f"Processing {task_count} tasks for issue {issue_key}",
            event_data={
                "issue_key": issue_key, 
                "task_count": task_count,
                "task_types": [task.get('type') for task in ai_response['tasks']]
            }
        )
        
        results = agent_router.process_tasks(ai_response['tasks'])
        logger.debug(f"Task processing results: {results}")

        # Update Jira with results
        success_count = len(results['success'])
        failed_count = len(results['failed'])
        logger.info(f"Task processing complete. Success: {success_count}, Failed: {failed_count}")
        
        # Create detailed event data including failure reasons if any
        event_data = {
            "issue_key": issue_key,
            "success_count": success_count, 
            "failed_count": failed_count,
            "success_tasks": [s.get('task') for s in results.get('success', [])],
        }
        
        # Add failure details if there are any failures
        if failed_count > 0:
            failure_details = []
            for failed_task in results.get('failed', []):
                task_type = failed_task.get('task', {}).get('type', 'unknown')
                error = failed_task.get('error', 'Unknown error')
                failure_details.append({"task_type": task_type, "error": error})
            
            event_data["failure_details"] = failure_details
            event_data["failed_tasks"] = [f.get('task') for f in results.get('failed', [])]
            
            # Enhance description with failure reasons
            task_error_descriptions = [f"{detail['task_type']}: {detail['error']}" for detail in failure_details]
            description = f"Task processing complete for issue {issue_key}. Success: {success_count}, Failed: {failed_count}. Failures: {', '.join(task_error_descriptions)}"
        else:
            description = f"Task processing complete for issue {issue_key}. Success: {success_count}, Failed: {failed_count}"
        
        log_system_event(
            event_type="task_completed",
            service="main",
            description=description,
            event_data=event_data
        )

        status_message = f"Processed {success_count + failed_count} tasks:\n"
        status_message += f"- {success_count} tasks completed successfully\n"
        status_message += f"- {failed_count} tasks failed\n\n"

        if failed_count > 0:
            logger.warning(f"Some tasks failed for issue {issue_key}")
            status_message += "Failed tasks:\n"
            for failed in results['failed']:
                logger.error(f"Task failure in {issue_key}: {failed['task']} - {failed['error']}")
                status_message += f"- Task: {failed['task']}\n  Error: {failed['error']}\n"
                
                log_system_event(
                    event_type="error",
                    service="main",
                    description=f"Task failure in issue {issue_key}: {failed['task']}",
                    event_data={"issue_key": issue_key, "task": failed['task'], "error": failed['error']}
                )

        logger.info(f"Adding status comment to issue {issue_key}")
        jira_service.add_comment(issue_key, status_message)

        if failed_count == 0:
            logger.info(f"All tasks successful, updating issue {issue_key} status to Done")
            jira_service.update_issue_status(issue_key, "Done")
            
            log_system_event(
                event_type="jira_update",
                service="main",
                description=f"Updated issue {issue_key} status to Done",
                event_data={"issue_key": issue_key, "new_status": "Done"}
            )
        else:
            logger.warning(f"Some tasks failed, updating issue {issue_key} status to Failed")
            jira_service.update_issue_status(issue_key, "Failed")
            
            log_system_event(
                event_type="jira_update",
                service="main",
                description=f"Updated issue {issue_key} status to Failed",
                event_data={"issue_key": issue_key, "new_status": "Failed"}
            )

        logger.info(f"Webhook processing complete for issue {issue_key}")
        
        log_system_event(
            event_type="webhook_completed",
            service="main",
            description=f"Webhook processing complete for issue {issue_key}",
            event_data={"issue_key": issue_key, "success": True}
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Tasks processed',
            'results': results
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        
        log_system_event(
            event_type="error",
            service="main",
            description=f"Exception in jira_webhook: {str(e)}",
            event_data={"error_trace": error_trace}
        )
        
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/test/ci', methods=['POST'])
def test_ci():
    """
    Test endpoint for CI pipeline creation
    Allows direct testing of CI pipeline setup without Jira integration
    """
    try:
        # Log system event for CI test request received
        log_system_event(
            event_type="task_received",
            service="main",
            description="CI pipeline creation test request received",
            event_data={"endpoint": "/test/ci", "method": "POST"}
        )
        
        if not request.is_json:
            log_system_event(
                event_type="error",
                service="main",
                description="Invalid request format - not JSON",
                event_data={"endpoint": "/test/ci"}
            )
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.json
        repository = data.get('repository')
        if not repository:
            log_system_event(
                event_type="error",
                service="main",
                description="Missing required field 'repository'",
                event_data={"endpoint": "/test/ci"}
            )
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
        
        log_system_event(
            event_type="agent_triggered",
            service="main",
            description=f"Directly triggering CI agent for repository: {repository}",
            event_data={
                "repository": repository,
                "branch": data.get('branch', 'main'),
                "build_steps": data.get('build_steps', ["test", "lint", "build"])
            }
        )

        # Route the task directly to CI agent
        logger.info("Routing task to CI agent")
        result = agent_router.route_task('ci', task)
        
        if not result:
            logger.error("Failed to process CI task - no response from agent")
            log_system_event(
                event_type="error",
                service="main",
                description=f"CI agent failed to process task for repository: {repository}",
                event_data={"repository": repository, "error": "No response from agent"}
            )
            return jsonify({
                'status': 'error',
                'message': 'Failed to process CI task'
            }), 500

        logger.info(f"CI agent response: {result}")
        
        log_system_event(
            event_type="task_completed",
            service="main",
            description=f"CI pipeline created for repository: {repository}",
            event_data={
                "repository": repository,
                "success": True,
                "ci_status": result.get('status'),
                "jenkinsfile_generated": result.get('jenkinsfile_generated', False)
            }
        )
        
        return jsonify({
            'status': 'success',
            'message': 'CI pipeline created',
            'result': result
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error processing CI test request: {str(e)}")
        
        log_system_event(
            event_type="error",
            service="main",
            description=f"Exception in test_ci: {str(e)}",
            event_data={"error_trace": error_trace}
        )
        
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    # Run the Flask application in debug mode
    app.run(host='0.0.0.0', port=5000, debug=True)