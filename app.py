from flask import Flask, request, jsonify
from services.jira_service import JiraService
from services.ai_service import AIService
from services.agent_router import AgentRouter
from utils.validators import validate_jira_webhook, validate_ai_response
from utils.logger import logger
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

jira_service = JiraService()
ai_service = AIService()
agent_router = AgentRouter()

@app.route('/')
def index():
    return jsonify({'message': 'DevOps Automation Service'})

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'services': {
            'jira': True,
            'ai': True,
            'agent_router': True
        }
    })

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)