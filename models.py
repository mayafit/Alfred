from datetime import datetime
from app import db

class TaskHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), nullable=False)  # 'ci', 'helm', 'deploy'
    repository = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'running', 'completed', 'failed'
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'task_type': self.task_type,
            'repository': self.repository,
            'status': self.status,
            'details': self.details,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class SystemMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    service_name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    response_time = db.Column(db.Float)
    error_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'service_name': self.service_name,
            'status': self.status,
            'response_time': self.response_time,
            'error_count': self.error_count
        }

class SystemEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)  # 'task_received', 'ai_analysis', 'agent_triggered', etc.
    service = db.Column(db.String(50), nullable=False)  # 'main', 'ci_agent', 'helm_agent', 'deploy_agent'
    description = db.Column(db.Text, nullable=False)  # Detailed description of the event
    event_data = db.Column(db.JSON)  # Additional data related to the event
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'service': self.service,
            'description': self.description,
            'event_data': self.event_data
        }
