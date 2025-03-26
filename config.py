import os

# App settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-replace-in-production')

# OpenAI configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.2'))
OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '1000'))


# API settings
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
JIRA_USERNAME = os.environ.get('JIRA_USERNAME')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL', JIRA_USERNAME)  # Usually email is the username in Jira
JIRA_BASE_URL = os.environ.get('JIRA_BASE_URL', 'https://your-domain.atlassian.net')
JIRA_URL = JIRA_BASE_URL  # Added for backward compatibility

# AI service settings
# OpenAI configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.2'))
OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '1000'))

# Google Gemini configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-pro')
GEMINI_URL = os.environ.get('GEMINI_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent')
GEMINI_TEMPERATURE = float(os.environ.get('GEMINI_TEMPERATURE', '0.2'))
GEMINI_MAX_TOKENS = int(os.environ.get('GEMINI_MAX_TOKENS', '1000'))

# Other LLM configuration (like local Llama, etc.)
OTHER_LLM_URL = os.environ.get('OTHER_LLM_URL', 'http://0.0.0.0:1234/v1/chat/completions')
OTHER_LLM_API_KEY = os.environ.get('OTHER_LLM_API_KEY')
OTHER_LLM_TEMPERATURE = float(os.environ.get('OTHER_LLM_TEMPERATURE', '0.2'))
OTHER_LLM_MAX_TOKENS = int(os.environ.get('OTHER_LLM_MAX_TOKENS', '1000'))

# LLM provider selection - "openai", "gemini", or "other"
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')

# Agent settings
LLAMA_SERVER_URL = os.environ.get('LLAMA_SERVER_URL', 'http://localhost:8080')
CI_AGENT_URL = os.environ.get('CI_AGENT_URL', 'http://localhost:9001')
HELM_AGENT_URL = os.environ.get('HELM_AGENT_URL', 'http://localhost:9002')
DEPLOY_AGENT_URL = os.environ.get('DEPLOY_AGENT_URL', 'http://localhost:9003')

# Monitoring settings
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
ENABLE_PROMETHEUS = os.environ.get('ENABLE_PROMETHEUS', 'True').lower() == 'true'

# Simulation mode settings
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'
SIMULATION_INTERVAL = int(os.environ.get('SIMULATION_INTERVAL', '30'))  # In seconds
SIMULATION_EVENT_COUNT = int(os.environ.get('SIMULATION_EVENT_COUNT', '3'))  # Number of events per interval