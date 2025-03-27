"""
Dashboard routes for displaying system metrics, events, and task history.
"""

from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta

from models import TaskHistory, SystemMetrics, SystemEvent
import config

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/')
def show_dashboard():
    """Display the main dashboard with system metrics and activity"""
    # Get system metrics for service status
    recent_metrics = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).limit(10).all()
    services = []
    service_names = set(metric.service_name for metric in recent_metrics)
    
    for service_name in service_names:
        # Get the most recent metric for this service
        service_metric = next(
            (m for m in recent_metrics if m.service_name == service_name), 
            None
        )
        
        if service_metric:
            services.append({
                'name': service_name,
                'status': service_metric.status,
                'response_time': service_metric.response_time,
                'error_count': service_metric.error_count
            })
    
    # Get active tasks (tasks with status 'running')
    active_tasks = TaskHistory.query.filter_by(status='running').order_by(TaskHistory.created_at.desc()).limit(5).all()
    
    # Get recent task history
    task_history = TaskHistory.query.order_by(TaskHistory.created_at.desc()).limit(10).all()
    
    # Get recent system events
    system_events = SystemEvent.query.order_by(SystemEvent.timestamp.desc()).limit(20).all()
    
    # Check if simulation mode is enabled
    simulation_enabled = config.SIMULATION_MODE
    
    return render_template(
        'dashboard.html',
        services=services,
        active_tasks=[task.to_dict() for task in active_tasks],
        task_history=[task.to_dict() for task in task_history],
        system_events=[event.to_dict() for event in system_events],
        simulation_enabled=simulation_enabled,
        config=config
    )

@dashboard.route('/api/dashboard/metrics')
def get_metrics():
    """Return the latest system metrics as JSON for AJAX updates"""
    # Get system metrics for service status
    recent_metrics = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).limit(10).all()
    services = []
    service_names = set(metric.service_name for metric in recent_metrics)
    
    for service_name in service_names:
        # Get the most recent metric for this service
        service_metric = next(
            (m for m in recent_metrics if m.service_name == service_name), 
            None
        )
        
        if service_metric:
            services.append({
                'name': service_name,
                'status': service_metric.status,
                'response_time': service_metric.response_time,
                'error_count': service_metric.error_count
            })
    
    # Get active tasks (tasks with status 'running')
    active_tasks = TaskHistory.query.filter_by(status='running').order_by(TaskHistory.created_at.desc()).limit(5).all()
    
    # Get recent task history
    task_history = TaskHistory.query.order_by(TaskHistory.created_at.desc()).limit(10).all()
    
    return jsonify({
        'services': services,
        'active_tasks': [task.to_dict() for task in active_tasks],
        'task_history': [task.to_dict() for task in task_history],
    })

@dashboard.route('/api/dashboard/events')
def get_events():
    """Return the latest system events as JSON for AJAX updates"""
    # Get recent system events
    system_events = SystemEvent.query.order_by(SystemEvent.timestamp.desc()).limit(50).all()
    
    return jsonify({
        'system_events': [event.to_dict() for event in system_events],
    })

def register_routes(app):
    """Register the dashboard routes with the Flask app"""
    app.register_blueprint(dashboard, name='dashboard_blueprint')