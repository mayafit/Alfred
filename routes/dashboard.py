from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta
from models import TaskHistory, SystemMetrics
from app import db

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
def show_dashboard():
    # Get current system status
    services = [
        {'name': 'Main Application', 'status': 'healthy'},
        {'name': 'CI Agent', 'status': 'healthy'},
        {'name': 'Helm Agent', 'status': 'healthy'},
        {'name': 'Deploy Agent', 'status': 'healthy'}
    ]

    # Get active tasks (last 24 hours)
    active_tasks = TaskHistory.query.filter(
        TaskHistory.status == 'running',
        TaskHistory.created_at >= datetime.utcnow() - timedelta(days=1)
    ).all()

    # Get task history (last 100 tasks)
    task_history = TaskHistory.query.order_by(
        TaskHistory.created_at.desc()
    ).limit(100).all()

    return render_template('dashboard.html',
                         services=services,
                         active_tasks=active_tasks,
                         task_history=task_history)

@dashboard.route('/api/dashboard/metrics')
def get_metrics():
    # Get latest system metrics
    latest_metrics = SystemMetrics.query.order_by(
        SystemMetrics.timestamp.desc()
    ).limit(10).all()

    # Get active tasks
    active_tasks = TaskHistory.query.filter(
        TaskHistory.status == 'running'
    ).all()

    return jsonify({
        'services': [metric.to_dict() for metric in latest_metrics],
        'active_tasks': [task.to_dict() for task in active_tasks]
    })
