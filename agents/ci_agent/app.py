import sys
import os
from flask import Blueprint, Flask
from agents.utils.logger import setup_agent_logger
from agents.ci_agent.repo_analyzer import RepoAnalyzer
from prometheus_flask_exporter import PrometheusMetrics
import logging
from agents.ci_agent.routes import register_routes

logger = setup_agent_logger('ci-agent')

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
    metrics = PrometheusMetrics(app, registry_name='ci_agent_registry')
    metrics.info('app_info', 'Application info', version='1.0.0', service='ci_agent')
    
    # Initialize blueprint and routes
    blueprint = Blueprint('ci_agent', __name__)
    
    # Use OpenAI for LLM capabilities
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if openai_api_key:
        llm_url = f"openai:{openai_api_key}"
    else:
        # Fallback to a default URL if no API key is available
        llm_url = os.environ.get('CUSTOM_LLM_URL', 'http://localhost:8000/v1')
        
    repo_analyzer = RepoAnalyzer(llm_url)
    register_routes(blueprint, repo_analyzer)
    
    # Register blueprint
    app.register_blueprint(blueprint)
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001)