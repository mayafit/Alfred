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
            jira_service.add_comment(issue_key, ai_response['message'])
            return jsonify({'status': 'error', 'message': ai_response['message']}), 400

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

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})
