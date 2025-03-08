import os

# Jira Configuration
JIRA_URL = os.getenv("JIRA_URL", "https://your-domain.atlassian.net")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")

# AI Service Configuration
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:9000")
AI_SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN")

# Agent Configuration
CI_AGENT_URL = os.getenv("CI_AGENT_URL", "http://localhost:9001")
HELM_AGENT_URL = os.getenv("HELM_AGENT_URL", "http://localhost:9002")
DEPLOY_AGENT_URL = os.getenv("DEPLOY_AGENT_URL", "http://localhost:9003")

# Flask Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
