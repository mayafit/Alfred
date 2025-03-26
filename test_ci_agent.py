import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ci_agent():
    """
    Test the CI agent by sending a request to the /execute endpoint
    """
    url = "http://localhost:9001/execute"
    
    # Test data for a Node.js project
    payload = {
        "parameters": {
            "repository": "https://github.com/expressjs/express",
            "branch": "master",
            "build_steps": ["install", "test", "build", "deploy"]
        }
    }
    
    logger.info(f"Sending request to {url}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response content: {json.dumps(response.json(), indent=2)}")
        
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return None

if __name__ == "__main__":
    test_ci_agent()