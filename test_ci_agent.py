#!/usr/bin/env python3
import os
import sys
import json
import requests
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ci-agent-tester")

def test_ci_agent(repo_url, branch="main", agent_url="http://localhost:9001"):
    """
    Test the CI agent by sending a request to generate a Jenkinsfile for a repository
    """
    try:
        # Prepare request payload
        payload = {
            "repository": {
                "url": repo_url,
                "branch": branch
            }
        }
        
        logger.info(f"Testing CI agent at {agent_url} with repo {repo_url} (branch: {branch})")
        
        # Make request to CI agent
        response = requests.post(
            f"{agent_url}/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Give it a longer timeout as cloning might take time
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Success! CI agent response: {json.dumps(result, indent=2)}")
            return True
        else:
            logger.error(f"Failed with status code {response.status_code}: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error testing CI agent: {str(e)}")
        return False

def run_health_check(agent_url="http://localhost:9001"):
    """
    Run a health check on the CI agent
    """
    try:
        logger.info(f"Running health check on CI agent at {agent_url}")
        
        # Make request to CI agent health endpoint
        response = requests.get(f"{agent_url}/health", timeout=10)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Health check passed: {json.dumps(result, indent=2)}")
            return True
        else:
            logger.error(f"Health check failed with status code {response.status_code}: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error running health check: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the CI agent")
    parser.add_argument("--repo", "-r", help="Repository URL to test with", required=True)
    parser.add_argument("--branch", "-b", help="Branch to check out", default="main")
    parser.add_argument("--url", "-u", help="CI agent URL", default="http://localhost:9001")
    parser.add_argument("--health", "-H", help="Run health check only", action="store_true")
    
    args = parser.parse_args()
    
    # Run requested tests
    if args.health:
        success = run_health_check(args.url)
    else:
        health_ok = run_health_check(args.url)
        if not health_ok:
            logger.warning("Health check failed, but proceeding with main test anyway")
        
        success = test_ci_agent(args.repo, args.branch, args.url)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)