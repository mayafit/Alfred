#!/usr/bin/env python3
import os
import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ci-agent-runner")

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_ci_agent():
    """
    Run the CI agent on port 9001
    """
    try:
        # Import from the correct location using the proper path
        from agents.ci_agent.app import app
        
        logger.info("Starting CI agent on port 9001")
        app.run(host='0.0.0.0', port=9001, debug=True)
    except ImportError as e:
        logger.error(f"Failed to import CI agent: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting CI agent: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_ci_agent()