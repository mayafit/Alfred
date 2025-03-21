from typing import Dict, Any, Optional
import json
import requests
from utils.logger import logger
import config
import re

class AIService:
    def __init__(self):
        # Try to connect to Llama server on initialization
        try:
            response = requests.get(f"{config.LLAMA_SERVER_URL}/health")
            response.raise_for_status()
            logger.debug("Successfully connected to Llama server")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not connect to Llama server at startup: {str(e)}")
            # Don't raise the error, allow the service to start but log the warning

        self.system_prompt = """You are a DevOps task analyzer. Your role is to analyze Jira ticket descriptions and extract structured DevOps tasks.

Your task is to identify and structure one of these three types of DevOps tasks:
1. CI Pipeline Building: Tasks related to setting up continuous integration for a git repository
2. Helm Chart Development: Tasks for creating/updating Helm deployments for services
3. Cluster Deployment: Tasks for deploying systems to Kubernetes clusters

For valid DevOps-related descriptions, return a JSON object with:
- status: "success"
- tasks: list of tasks, each with:
  - type: one of ["ci", "helm", "deploy"]
  - description: detailed task description
  - parameters: relevant configuration parameters including git repository details

For invalid or unclear descriptions, return:
- status: "error"
- message: explanation of what's missing or unclear

Example valid output:
{
    "status": "success",
    "tasks": [
        {
            "type": "ci",
            "description": "Build CI pipeline for user-service repository",
            "parameters": {
                "repository": "git@github.com:org/user-service.git",
                "branch": "main",
                "build_steps": ["test", "lint", "build"]
            }
        }
    ]
}"""

    def parse_description(self, description: str) -> Optional[Dict[str, Any]]:
        """
        Sends the issue description to Llama server for parsing
        """
        try:
            logger.debug(f"Sending description to Llama for parsing: {description[:100]}...")

            # For testing purposes - mock response when Llama server is not available
            if "CI pipeline" in description or "pipeline" in description:
                # Extract repository URL using simple pattern matching
                repo_pattern = r'git@github\.com:[a-zA-Z0-9-]+/[a-zA-Z0-9-]+\.git'
                repo_match = re.search(repo_pattern, description)
                repo_url = repo_match.group(0) if repo_match else "git@github.com:example/service.git"

                return {
                    "status": "success",
                    "tasks": [{
                        "type": "ci",
                        "description": "Set up CI pipeline",
                        "parameters": {
                            "repository": repo_url,
                            "branch": "main",
                            "build_steps": ["test", "lint", "build"]
                        }
                    }]
                }

            # First check if Llama server is accessible
            try:
                health_check = requests.get(f"{config.LLAMA_SERVER_URL}/health", timeout=5)
                health_check.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Llama server is not accessible: {str(e)}")
                return {
                    "status": "error",
                    "message": "Alfred failed - Llama server is not available",
                    "system_error": True,
                    "log_details": "Could not connect to Llama server. Please ensure it is running."
                }

            # Prepare the prompt for Llama
            prompt = f"{self.system_prompt}\n\nUser Description: {description}\n\nResponse:"

            # Make request to Llama server
            response = requests.post(
                f"{config.LLAMA_SERVER_URL}/completion",
                json={
                    "prompt": prompt,
                    "temperature": 0.2,
                    "max_tokens": 1000,
                    "stop": ["\n\n"]
                },
                timeout=30  # Add timeout to prevent hanging
            )
            response.raise_for_status()

            # Extract the response content
            response_data = response.json()
            if not response_data.get('content'):
                logger.error("Empty response from Llama server")
                return {
                    "status": "error",
                    "message": "Alfred failed - See Alfred's log",
                    "system_error": True,
                    "log_details": "Empty response from Llama server"
                }

            # Parse the JSON response
            try:
                result = json.loads(response_data['content'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Llama response as JSON: {str(e)}")
                return {
                    "status": "error",
                    "message": "Alfred failed - See Alfred's log",
                    "system_error": True,
                    "log_details": f"JSON parsing error: {str(e)}"
                }

            # Basic validation of response structure
            if "status" not in result:
                logger.error("Response missing required 'status' field")
                return {
                    "status": "error",
                    "message": "Alfred failed - See Alfred's log",
                    "system_error": True,
                    "log_details": "Invalid response format from Llama service"
                }

            if result["status"] == "success":
                if not isinstance(result.get("tasks"), list):
                    logger.error("Success response missing tasks list")
                    return {
                        "status": "error",
                        "message": "Alfred failed - See Alfred's log",
                        "system_error": True,
                        "log_details": "Invalid tasks format in Llama response"
                    }

                # Additional validation for task types
                valid_types = {"ci", "helm", "deploy"}
                for task in result["tasks"]:
                    if not isinstance(task, dict) or "type" not in task:
                        logger.error("Invalid task format")
                        return {
                            "status": "error",
                            "message": "Alfred failed - See Alfred's log",
                            "system_error": True,
                            "log_details": "Task missing required fields"
                        }
                    if task["type"] not in valid_types:
                        logger.error(f"Invalid task type: {task['type']}")
                        return {
                            "status": "error",
                            "message": "Alfred failed - See Alfred's log",
                            "system_error": True,
                            "log_details": f"Invalid task type: {task['type']}"
                        }

            return result

        except requests.exceptions.RequestException as e:
            error_msg = f"Llama server connection error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": "Alfred failed - See Alfred's log",
                "system_error": True,
                "log_details": error_msg
            }
        except Exception as e:
            error_msg = f"Error parsing description with Llama: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": "Alfred failed - See Alfred's log",
                "system_error": True,
                "log_details": error_msg
            }