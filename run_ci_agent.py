import os
import sys
from agents.ci_agent.app import app

if __name__ == "__main__":
    # Set environment variables if needed
    # os.environ["LLAMA_SERVER_URL"] = "..."
    
    # Run the CI agent on port 9001
    app.run(host="0.0.0.0", port=9001, debug=True)