"""
Task routes for creating and managing direct task requests.
These routes handle the creation of tasks directly from the UI
rather than just through Jira webhooks.
"""

from flask import Blueprint, request, jsonify, render_template, current_app
import json
import os
import requests
from datetime import datetime

from services.ai_service import AIService
from services.agent_router import AgentRouter
from services.jira_service import JiraService
from utils.logger import log_system_event
import config

task_bp = Blueprint('task', __name__)
ai_service = AIService()
agent_router = AgentRouter()
jira_service = JiraService()

@task_bp.route('/', methods=['GET'])
def task_page():
    """Render the task creation page"""
    # List of sample projects for the dropdown
    projects = [
        "Go to Market Sample",
        "E-Commerce Platform",
        "Mobile Banking App",
        "Customer Portal",
        "Data Analytics Platform",
        "Inventory Management System"
    ]
    
    return render_template('task.html', projects=projects)

@task_bp.route('/create', methods=['POST'])
def create_task():
    """Process a task creation request"""
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    project = data.get('project', 'Go to Market Sample')
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({"status": "error", "message": "No task description provided"}), 400
    
    # Log the task received event
    event_data = {
        "project": project,
        "prompt_length": len(prompt),
        "source": "task_page"
    }
    task_received_event = log_system_event(
        event_type="task_received",
        service="main",
        description=f"Received direct task request for project: {project}",
        event_data=event_data
    )
    
    # Process the prompt with AI service
    try:
        # Log that we're starting AI analysis
        ai_analysis_event = log_system_event(
            event_type="ai_analysis",
            service="main",
            description="Analyzing task description with AI service",
            event_data={"prompt_length": len(prompt)}
        )
        
        parsed_data = ai_service.parse_description(prompt)
        
        if not parsed_data:
            log_system_event(
                event_type="error",
                service="main",
                description="Failed to parse task description with AI service",
                event_data={"prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt}
            )
            return jsonify({
                "status": "error", 
                "message": "Failed to parse task description. Please try again with more details."
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
                
                jira_key = jira_service.create_issue(
                    project_key=project.replace(" ", "_").upper(),
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