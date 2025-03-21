import os

# Jira Configuration
JIRA_URL = os.getenv("JIRA_URL", "https://your-domain.atlassian.net")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")

# LLama Server Configuration
LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:11434")  

# Agent Configuration
CI_AGENT_URL = os.getenv("CI_AGENT_URL", "http://localhost:9001")
HELM_AGENT_URL = os.getenv("HELM_AGENT_URL", "http://localhost:9002")
DEPLOY_AGENT_URL = os.getenv("DEPLOY_AGENT_URL", "http://localhost:9003")

# Flask Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"