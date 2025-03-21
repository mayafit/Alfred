import os
import sys

# Add the agents directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ci_agent.app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9001, debug=True)
