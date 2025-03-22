from flask import Flask
from app import app as main_app
#from agents.ci_agent.app import app as ci_agent_app

# Register CI agent routes under /ci prefix
#main_app.register_blueprint(ci_agent_app, url_prefix='/ci')

# Export the app for Gunicorn to find
app = main_app

if __name__ == "__main__":
    # Always use port 5000 for the main application
    app.run(host='0.0.0.0', port=5000, debug=True)