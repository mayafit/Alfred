from typing import Dict, Any, Optional
import json
import requests
from utils.logger import logger
import config
import re

class AIService:
    def __init__(self):
        self.system_prompt = """You are a DevOps task analyzer. Your role is to analyze descriptions and extract structured DevOps tasks.

For repository analysis, respond with JSON in this format:
{
    "project_type": "string (one of: csharp_library, aspnet_service, node_service, website)",
    "confidence": "float (0-1)",
    "build_steps": ["list of required build steps"]
}

Example valid output:
{
    "project_type": "node_service",
    "confidence": 0.95,
    "build_steps": ["install", "lint", "test", "build"]
}"""

        # Try to connect to Llama server on initialization
        try:
            response = requests.get(f"{config.LLAMA_SERVER_URL}/health")
            response.raise_for_status()
            logger.debug("Successfully connected to Llama server")
            self.llama_available = True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not connect to Llama server at startup: {str(e)}")
            self.llama_available = False
            # Don't raise the error, allow the service to start in fallback mode

    def parse_description(self, description: str) -> Optional[Dict[str, Any]]:
        """
        Sends the issue description to Llama server for parsing
        Falls back to rule-based parsing if Llama is unavailable
        """
        try:
            # If Llama is not available, use rule-based parsing
            if not self.llama_available:
                return self._parse_description_fallback(description)

            logger.debug(f"Sending description to Llama for parsing: {description[:100]}...")

            # Try Llama server
            try:
                health_check = requests.get(f"{config.LLAMA_SERVER_URL}/health", timeout=5)
                health_check.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Llama server is not accessible: {str(e)}")
                return self._parse_description_fallback(description)

            # Make request to Llama server
            response = requests.post(
                f"{config.LLAMA_SERVER_URL}/completion",
                json={
                    "prompt": f"{self.system_prompt}\n\nUser Description: {description}\n\nResponse:",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                    "stop": ["\n\n"]
                },
                timeout=30
            )
            response.raise_for_status()

            # Extract the response content
            response_data = response.json()
            if not response_data.get('content'):
                logger.warning("Empty response from Llama server, using fallback")
                return self._parse_description_fallback(description)

            # Parse the JSON response
            try:
                result = json.loads(response_data['content'])
                logger.info(f"Successfully parsed description with Llama: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Llama response as JSON: {str(e)}")
                return self._parse_description_fallback(description)

        except Exception as e:
            logger.warning(f"Error using Llama server, falling back to rule-based parsing: {str(e)}")
            return self._parse_description_fallback(description)

    def _parse_description_fallback(self, description: str) -> Dict[str, Any]:
        """
        Rule-based fallback parser when Llama is unavailable
        """
        logger.info("Using fallback description parser")

        # Simple rule-based parsing
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

        # Default response for unrecognized tasks
        return {
            "status": "success",
            "tasks": [{
                "type": "unknown",
                "description": "Task type not recognized",
                "parameters": {}
            }]
        }