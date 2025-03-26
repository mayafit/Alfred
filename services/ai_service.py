from typing import Dict, Any, Optional
import json
import requests
import importlib
from utils.logger import logger
import config
import re
import os

# Try to import OpenAI dynamically
openai_module = None
try:
    openai_module = importlib.import_module('openai')
    logger.debug("Successfully imported OpenAI module")
except ImportError:
    logger.warning("OpenAI module not available, will try dynamic import when needed")

class AIService:
    def __init__(self):
        # Get reference to the global module
        global openai_module
        
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
            self.provider = config.LLM_PROVIDER.lower()
            
            if self.provider == "openai" and config.OPENAI_API_KEY:
                # Ensure OpenAI module is available
                if openai_module is None:
                    try:
                        openai_module = importlib.import_module('openai')
                        logger.debug("Successfully imported OpenAI module")
                    except ImportError:
                        logger.error("OpenAI package not installed")
                        raise ValueError("OpenAI module not available")
                
                # Initialize client
                self.client = openai_module.OpenAI(
                    api_key=config.OPENAI_API_KEY,
                    base_url=config.OPENAI_BASE_URL
                )
                logger.debug("Successfully initialized OpenAI client")
                self.ai_available = True
                
            elif self.provider == "gemini" and config.GEMINI_API_KEY:
                self.gemini_url = config.GEMINI_URL
                self.gemini_api_key = config.GEMINI_API_KEY
                logger.debug(f"Successfully initialized Google Gemini client")
                self.ai_available = True
                
            elif self.provider == "other" and config.OTHER_LLM_URL and config.OTHER_LLM_API_KEY:
                self.other_llm_url = config.OTHER_LLM_URL
                self.other_llm_api_key = config.OTHER_LLM_API_KEY
                logger.debug(f"Successfully initialized other LLM client at {config.OTHER_LLM_URL}")
                self.ai_available = True
                
            else:
                # Try fallbacks if preferred provider isn't available
                if config.OPENAI_API_KEY:
                    # Ensure OpenAI module is available for fallback
                    if openai_module is None:
                        try:
                            openai_module = importlib.import_module('openai')
                            logger.debug("Successfully imported OpenAI module for fallback")
                        except ImportError:
                            logger.error("OpenAI package not installed for fallback")
                            raise ValueError("OpenAI module not available")
                    
                    # Initialize client for fallback
                    self.client = openai_module.OpenAI(api_key=config.OPENAI_API_KEY)
                    self.provider = "openai"
                    logger.debug("Falling back to OpenAI client")
                    self.ai_available = True
                    
                elif config.GEMINI_API_KEY:
                    self.gemini_url = config.GEMINI_URL
                    self.gemini_api_key = config.GEMINI_API_KEY
                    self.provider = "gemini"
                    logger.debug("Falling back to Google Gemini client")
                    self.ai_available = True
                    
                elif config.OTHER_LLM_URL and config.OTHER_LLM_API_KEY:
                    self.other_llm_url = config.OTHER_LLM_URL
                    self.other_llm_api_key = config.OTHER_LLM_API_KEY
                    self.provider = "other"
                    logger.debug(f"Falling back to other LLM client")
                    self.ai_available = True
                    
                else:
                    raise ValueError("No AI provider configuration found")
                
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

            # Call the appropriate provider's implementation
            if self.provider == "openai":
                response = self._call_openai(description)
            elif self.provider == "gemini":
                response = self._call_gemini(description)
            elif self.provider == "other":
                response = self._call_other_llm(description)
            else:
                logger.error(f"Unknown provider: {self.provider}")
                return self._parse_description_fallback(description)

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
                # Try to extract JSON from the text response
                json_text = self._extract_json_from_text(response)
                try:
                    result = json.loads(json_text)
                    logger.info(f"Successfully extracted and parsed JSON from AI response")
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse AI response as JSON: {str(e)}")
                    return self._parse_description_fallback(description)

        except Exception as e:
            logger.error(f"Error using AI service: {str(e)}", exc_info=True)
            return self._parse_description_fallback(description)

    def _call_openai(self, description: str) -> Optional[str]:
        """Make request to OpenAI API"""
        try:
            # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": description}
                ],
                temperature=config.OPENAI_TEMPERATURE,
                max_tokens=config.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling OpenAI: {str(e)}")
            return None

    def _call_gemini(self, description: str) -> Optional[str]:
        """Make request to Google Gemini API"""
        try:
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
                    "temperature": config.GEMINI_TEMPERATURE,
                    "maxOutputTokens": config.GEMINI_MAX_TOKENS,
                    "responseFormat": "JSON"
                }
            }
            
            # Log the request body (without sensitive information)
            logger.debug(f"Sending request to Gemini API")

            # Make request to Gemini API
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add API key as query parameter or in Authorization header based on the API requirements
            url = f"{self.gemini_url}?key={self.gemini_api_key}"
            
            response = requests.post(
                url,
                headers=headers,
                json=request_body,
                timeout=30
            )
            response.raise_for_status()
            
            # Extract the response content from Gemini API format
            result = response.json()
            
            # Gemini API returns the response in a specific structure
            if "candidates" in result and len(result["candidates"]) > 0:
                text_content = result["candidates"][0]["content"]["parts"][0]["text"]
                # Clean up the response to ensure it's valid JSON
                return self._extract_json_from_text(text_content)
            
            logger.warning("Unexpected Gemini API response format")
            return None
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return None

    def _call_other_llm(self, description: str) -> Optional[str]:
        """Make request to other LLM server (e.g., local Llama, custom deployment)"""
        try:
            # Format the prompt with system message and user input
            full_prompt = f"{self.system_prompt}\n\nUser: {description}\n\nAssistant:"
            
            # Prepare request body based on LLM server's expected format
            # This is a generic format that may need customization
            request_body = {
                "prompt": full_prompt,
                "temperature": config.OTHER_LLM_TEMPERATURE,
                "max_tokens": config.OTHER_LLM_MAX_TOKENS,
                "format": "json"
            }
            
            # Log the request (without sensitive information)
            logger.debug(f"Sending request to custom LLM server")

            # Make request to LLM server
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.other_llm_api_key}"
            }
            
            response = requests.post(
                self.other_llm_url,
                headers=headers,
                json=request_body,
                timeout=30
            )
            response.raise_for_status()
            
            # Process response
            result = response.json()
            
            # Extract response based on the expected structure
            # This part may need customization based on the LLM server's response format
            if "text" in result:
                return self._extract_json_from_text(result["text"])
            elif "content" in result:
                return self._extract_json_from_text(result["content"])
            elif "response" in result:
                return self._extract_json_from_text(result["response"])
            
            logger.warning("Unexpected LLM server response format")
            return None
            
        except Exception as e:
            logger.error(f"Error calling custom LLM server: {str(e)}")
            return None
            
    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text that might contain additional content"""
        try:
            # Look for JSON-like content
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = text[json_start:json_end]
                # Validate it's valid JSON
                json.loads(json_text)  # Just to verify
                return json_text
            
            # If no valid JSON object found, return the original text
            return text
        except json.JSONDecodeError:
            # If the extracted text isn't valid JSON, return the original
            return text

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