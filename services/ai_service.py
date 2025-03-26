from typing import Dict, Any, Optional
import json
import requests
from openai import OpenAI
from utils.logger import logger
import config
import re
import os

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

        # Initialize AI client based on configuration
        try:
            if hasattr(config, 'OPENAI_API_KEY') and config.OPENAI_API_KEY:
                self.client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.provider = "openai"
                logger.debug("Successfully initialized OpenAI client")
            elif hasattr(config, 'LLAMA_SERVER_URL') and config.LLAMA_SERVER_URL:
                self.provider = "local"
                self.llama_url = config.LLAMA_SERVER_URL
                logger.debug(f"Successfully initialized local LLM client at {self.llama_url}")
            else:
                raise ValueError("No AI provider configuration found")
            
            self.ai_available = True
        except Exception as e:
            logger.warning(f"Could not initialize AI client: {str(e)}")
            self.ai_available = False

    def parse_description(self, description: str) -> Optional[Dict[str, Any]]:
        """
        Sends the issue description to AI service for parsing
        Falls back to rule-based parsing if AI is unavailable
        """
        try:
            # If AI is not available, use rule-based parsing
            if not self.ai_available:
                logger.warning("AI client not available, using fallback parser")
                return self._parse_description_fallback(description)

            logger.debug(f"Sending description to AI service for parsing: {description[:100]}...")

            if self.provider == "openai":
                response = self._call_openai(description)
            else:  # local LLM
                response = self._call_local_llm(description)

            # Extract the response content
            if not response:
                logger.warning("Empty response from AI service, using fallback")
                return self._parse_description_fallback(description)

            # Parse the JSON response
            try:
                result = json.loads(response)
                logger.info(f"Successfully parsed description with AI: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI response as JSON: {str(e)}")
                return self._parse_description_fallback(description)

        except Exception as e:
            logger.error(f"Error using AI service: {str(e)}", exc_info=True)
            return self._parse_description_fallback(description)

    def _call_openai(self, description: str) -> Optional[str]:
        """Make request to OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # or "gpt-3.5-turbo" for faster, cheaper responses
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": description}
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={ "type": "json_object" }
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling OpenAI: {str(e)}")
            return None

    def _call_local_llm(self, description: str) -> Optional[str]:
        """Make request to local LLM server (LM Studio, Ollama, or Google Gemini)"""
        try:
            # Get access token from environment
            access_token = os.environ.get('AI_SERVICE_TOKEN')
            if not access_token:
                logger.error("AI_SERVICE_TOKEN not found in environment variables")
                return None

            # Format the prompt with system message and user input
            full_prompt = f"{self.system_prompt}\n\nUser: {description}\n\nAssistant:"
            
            # Prepare request body for Google Gemini API
            request_body = {
                "contents": [{
                    "parts": [
                        {"text": full_prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1000,
                }
            }
            
            # Log the request body
            logger.debug(f"Sending request to LLM server with body: {json.dumps(request_body, indent=2)}")

            # Make request to local LLM server with key in query params
            response = requests.post(
                f"{self.llama_url}?key={access_token}",
                json=request_body,
                timeout=30
            )
            response.raise_for_status()
            
            # Extract the response content from Gemini API format
            result = response.json()
            # Gemini API returns the response in a different structure
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return None
        except Exception as e:
            logger.error(f"Error calling local LLM: {str(e)}")
            return None

    def _parse_description_fallback(self, description: str) -> Dict[str, Any]:
        """
        Rule-based fallback parser when AI is unavailable
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