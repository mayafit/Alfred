import os
import sys

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from agents.ci_agent.app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9001, debug=True)