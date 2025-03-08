from typing import Dict, Any, Optional
import json
import openai
from utils.logger import logger
import config

class AIService:
    def __init__(self):
        try:
            openai.api_key = config.AI_SERVICE_TOKEN
            if not openai.api_key or openai.api_key.strip() == "":
                raise ValueError("OpenAI API key is not configured")
            logger.debug("OpenAI API key configured")
        except Exception as e:
            logger.error(f"Error configuring OpenAI API key: {str(e)}")
            raise

        self.system_prompt = """You are a DevOps task analyzer. Your role is to analyze Jira ticket descriptions and extract structured DevOps tasks.

For valid DevOps-related descriptions, return a JSON object with:
- status: "success"
- tasks: list of tasks, each with:
  - type: one of ["ci", "helm", "deploy"]
  - description: detailed task description
  - parameters: relevant configuration parameters

For invalid or unclear descriptions, return:
- status: "error"
- message: explanation of what's missing or unclear

Example valid output:
{
    "status": "success",
    "tasks": [
        {
            "type": "ci",
            "description": "Build Docker image from main branch",
            "parameters": {"branch": "main", "dockerfile_path": "./Dockerfile"}
        },
        {
            "type": "deploy",
            "description": "Deploy to production using Helm chart",
            "parameters": {"environment": "production", "namespace": "app"}
        }
    ]
}"""

    def parse_description(self, description: str) -> Optional[Dict[str, Any]]:
        """
        Sends the issue description to ChatGPT for parsing
        """
        try:
            logger.debug(f"Sending description to OpenAI for parsing: {description[:100]}...")

            response = openai.ChatCompletion.create(
                model="gpt-4",  # Using GPT-4 for better task understanding
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": description}
                ],
                temperature=0.2,  # Lower temperature for more consistent outputs
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            # Extract the JSON response
            response_content = response.choices[0].message.content
            logger.debug(f"Received response from OpenAI: {response_content}")

            try:
                result = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
                return {
                    "status": "error",
                    "message": "Failed to parse AI response format",
                    "system_error": True
                }

            # Basic validation of response structure
            if "status" not in result:
                logger.error("Response missing required 'status' field")
                return {
                    "status": "error",
                    "message": "Invalid response format from AI service",
                    "system_error": True
                }

            if result["status"] == "success":
                if not isinstance(result.get("tasks"), list):
                    logger.error("Success response missing tasks list")
                    return {
                        "status": "error",
                        "message": "Invalid tasks format in AI response",
                        "system_error": True
                    }

            return result

        except openai.AuthenticationError as e:
            error_msg = f"OpenAI authentication error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": "Alfred failed - See Alfred's log",
                "system_error": True,
                "log_details": error_msg
            }
        except (openai.APIError, openai.APIConnectionError, openai.RateLimitError) as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": "Alfred failed - See Alfred's log",
                "system_error": True,
                "log_details": error_msg
            }
        except Exception as e:
            error_msg = f"Error parsing description with AI: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": "Alfred failed - See Alfred's log",
                "system_error": True,
                "log_details": error_msg
            }