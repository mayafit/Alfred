"""
Task routes for creating and managing direct task requests.
These routes handle the creation of tasks directly from the UI
rather than just through Jira webhooks.
"""
import json
from flask import Blueprint, render_template, request, jsonify

import config
from utils.logger import log_system_event
from services.ai_service import AIService
from services.agent_router import AgentRouter
from services.jira_service import JiraService
from services.task_validator import TaskValidator

task_bp = Blueprint('task', __name__)
ai_service = AIService()
agent_router = AgentRouter()
jira_service = JiraService()
task_validator = TaskValidator()

@task_bp.route('/', methods=['GET'])
def task_page():
    """Render the task creation page"""
    return render_template('task.html')

@task_bp.route('/create', methods=['POST'])
def create_task():
    """Process a task creation request"""
    # Define prompt at a higher scope to avoid "possibly unbound" error
    prompt = ""
    try:
        # Get form data
        prompt = request.form.get('prompt', '')
        project = request.form.get('project', 'Go to Market Sample')
        
        if not prompt:
            return jsonify({
                "status": "error", 
                "message": "Task description is required"
            }), 400
        
        # Log task received event
        log_system_event(
            event_type="task_received",
            service="main",
            description=f"Received task request for {project}",
            event_data={"project": project, "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt}
        )
        
        # Process the prompt with AI service
        log_system_event(
            event_type="ai_analysis",
            service="main",
            description="Analyzing task description with AI service",
            event_data={"prompt_length": len(prompt)}
        )
        
        parsed_data = ai_service.parse_description(prompt)
        
        if not parsed_data or 'tasks' not in parsed_data or not parsed_data['tasks']:
            log_system_event(
                event_type="error",
                service="main",
                description="Failed to parse task description",
                event_data={"prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt}
            )
            return jsonify({
                "status": "error", 
                "message": "Failed to parse task description. Please try again with more details."
            }), 400
            
        # Validate if the tasks have all required details
        validation_result = task_validator.validate_tasks(parsed_data.get('tasks', []))
        if not validation_result["is_valid"]:
            # Log the validation failure
            log_system_event(
                event_type="warning",
                service="main",
                description="Incomplete task details provided",
                event_data={
                    "validation_result": validation_result,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt
                }
            )
            
            # Generate a detailed feedback message
            feedback_message = task_validator.generate_feedback_message(validation_result)
            
            return jsonify({
                "status": "error", 
                "message": "Tasks are missing required details",
                "validation_result": validation_result,
                "feedback_message": feedback_message
            }), 400
            
        # Create a Jira ticket if Jira is configured
        jira_key = None
        if hasattr(config, 'JIRA_URL') and config.JIRA_URL:
            try:
                # Log that we're creating a Jira ticket
                log_system_event(
                    event_type="jira_create",
                    service="main",
                    description=f"Creating Jira ticket for project: {project}",
                    event_data={"project": project}
                )
                
                # Create a summary from the first line or first 50 chars of prompt
                summary = prompt.split('\n')[0][:50]
                if len(summary) < len(prompt.split('\n')[0]):
                    summary += "..."
                
                # Always use the default project key "GTMS" for Jira tickets
                jira_key = jira_service.create_issue(
                    project_key="GTMS",
                    summary=summary,
                    description=prompt,
                    issue_type="Task",
                    labels=["devops"]
                )
                
                log_system_event(
                    event_type="jira_created",
                    service="main",
                    description=f"Jira ticket created: {jira_key}",
                    event_data={"jira_key": jira_key, "project": project}
                )
            except Exception as e:
                # Log the error but continue - the task can still be processed
                log_system_event(
                    event_type="warning",
                    service="main",
                    description=f"Failed to create Jira ticket: {str(e)}",
                    event_data={"project": project, "error": str(e)}
                )
        
        # Process tasks with the agent router
        log_system_event(
            event_type="agent_triggered",
            service="main",
            description="Routing tasks to appropriate agents",
            event_data={"task_count": len(parsed_data.get('tasks', [])), "tasks": parsed_data.get('tasks', [])}
        )
        
        # Execute the tasks with the agent router
        results = agent_router.process_tasks(parsed_data.get('tasks', []))
        
        # Log the task completion
        log_system_event(
            event_type="task_completed",
            service="main",
            description="Task processing completed",
            event_data={
                "results": results,
                "jira_key": jira_key
            }
        )
        
        # Return all the events along with the task processing results
        return jsonify({
            "status": "success",
            "message": "Task processed successfully",
            "jira_key": jira_key,
            "parsed_data": parsed_data,
            "results": results
        })
        
    except Exception as e:
        log_system_event(
            event_type="error",
            service="main",
            description=f"Error processing task: {str(e)}",
            event_data={"error": str(e), "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt}
        )
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500

@task_bp.route('/events', methods=['GET'])
def get_recent_task_events():
    """Get recent events related to the task processing"""
    from models import SystemEvent, db
    
    try:
        # Get most recent 20 events, ordered by timestamp descending
        events = SystemEvent.query.order_by(SystemEvent.timestamp.desc()).limit(20).all()
        return jsonify([event.to_dict() for event in events])
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to retrieve events: {str(e)}"}), 500

def register_routes(app):
    """Register the task routes with the Flask app"""
    app.register_blueprint(task_bp, url_prefix='/task')