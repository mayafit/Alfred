"""
Configuration module for the application.
Contains environment-specific settings and feature flags.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Application settings
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
SECRET_KEY = os.environ.get('SESSION_SECRET', 'devops-automation-secret-key')

# Database settings
DATABASE_URL = os.environ.get('DATABASE_URL')

# Service URLs
MAIN_SERVICE_URL = os.environ.get('MAIN_SERVICE_URL', 'http://localhost:5000')
CI_AGENT_URL = os.environ.get('CI_AGENT_URL', 'http://localhost:9001')
HELM_AGENT_URL = os.environ.get('HELM_AGENT_URL', 'http://localhost:9002')
DEPLOY_AGENT_URL = os.environ.get('DEPLOY_AGENT_URL', 'http://localhost:9003')

# Jira integration
JIRA_URL = os.environ.get('JIRA_URL', 'https://your-domain.atlassian.net')
JIRA_USERNAME = os.environ.get('JIRA_USERNAME', '')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN', '')
JIRA_PROJECT_KEY = os.environ.get('JIRA_PROJECT_KEY', 'GTMS')  # Default project key for Jira ticket creation
JIRA_PROJECT_NAME = os.environ.get('JIRA_PROJECT_NAME', 'Go to Market Sample')  # Default project name

# AI providers (Primary provider is the first available in this order)
# Options: 'openai', 'gemini', 'other_llm'
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openai')

# OpenAI
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. Do not change this unless explicitly requested by the user
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.1'))
OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '2000'))

# Google Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-pro')
GEMINI_URL = os.environ.get('GEMINI_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent')
GEMINI_TEMPERATURE = float(os.environ.get('GEMINI_TEMPERATURE', '0.1'))
GEMINI_MAX_TOKENS = int(os.environ.get('GEMINI_MAX_TOKENS', '2000'))

# Other LLM (e.g., local deployment, Anthropic, etc.)
OTHER_LLM_URL = os.environ.get('OTHER_LLM_URL', 'http://localhost:11434/api/generate')  # Default for Ollama
OTHER_LLM_MODEL = os.environ.get('OTHER_LLM_MODEL', 'llama3')
OTHER_LLM_API_KEY = os.environ.get('OTHER_LLM_API_KEY', '')
OTHER_LLM_TEMPERATURE = float(os.environ.get('OTHER_LLM_TEMPERATURE', '0.1'))
OTHER_LLM_MAX_TOKENS = int(os.environ.get('OTHER_LLM_MAX_TOKENS', '2000'))

# Prometheus metrics
ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'True').lower() in ('true', '1', 't')
METRICS_PORT = int(os.environ.get('METRICS_PORT', 8000))

# Feature flags
ENABLE_JIRA_INTEGRATION = os.environ.get('ENABLE_JIRA_INTEGRATION', 'False').lower() in ('true', '1', 't')
ENABLE_AUTHENTICATION = os.environ.get('ENABLE_AUTHENTICATION', 'False').lower() in ('true', '1', 't')
DISABLE_TASK_VALIDATION = os.environ.get('DISABLE_TASK_VALIDATION', 'False').lower() in ('true', '1', 't')

# Simulation mode - disabled by default
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() in ('true', '1', 't')
SIMULATION_INTERVAL = int(os.environ.get('SIMULATION_INTERVAL', 30))  # seconds
SIMULATION_EVENT_COUNT = int(os.environ.get('SIMULATION_EVENT_COUNT', 3))  # events per interval
SIMULATION_JIRA_EVENTS = os.environ.get('SIMULATION_JIRA_EVENTS', 'False').lower() in ('true', '1', 't')  # Generate Jira webhook events
SIMULATION_JIRA_INTERVAL = int(os.environ.get('SIMULATION_JIRA_INTERVAL', 60))  # seconds between Jira events