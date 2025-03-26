import os

# App settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-replace-in-production')

# API settings
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
JIRA_USERNAME = os.environ.get('JIRA_USERNAME')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL', JIRA_USERNAME)  # Usually email is the username in Jira
JIRA_BASE_URL = os.environ.get('JIRA_BASE_URL', 'https://your-domain.atlassian.net')
JIRA_URL = JIRA_BASE_URL  # Added for backward compatibility

# AI service settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
LOCAL_LLM_URL = os.environ.get('LOCAL_LLM_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent')
LOCAL_LLM_API_KEY = os.environ.get('LOCAL_LLM_API_KEY')
USE_LOCAL_LLM = os.environ.get('USE_LOCAL_LLM', 'True').lower() == 'true'

# Agent settings
LLAMA_SERVER_URL = os.environ.get('LLAMA_SERVER_URL', 'http://localhost:8080')
CI_AGENT_URL = os.environ.get('CI_AGENT_URL', 'http://localhost:9001')
HELM_AGENT_URL = os.environ.get('HELM_AGENT_URL', 'http://localhost:9002')
DEPLOY_AGENT_URL = os.environ.get('DEPLOY_AGENT_URL', 'http://localhost:9003')

# Monitoring settings
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
ENABLE_PROMETHEUS = os.environ.get('ENABLE_PROMETHEUS', 'True').lower() == 'true'