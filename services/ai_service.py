from typing import Dict, Any, Optional
import requests
from utils.logger import logger
import config

class AIService:
    def __init__(self):
        self.base_url = config.AI_SERVICE_URL
        self.headers = {
            "Authorization": f"Bearer {config.AI_SERVICE_TOKEN}",
            "Content-Type": "application/json"
        }

    def parse_description(self, description: str) -> Optional[Dict[str, Any]]:
        """
        Sends the issue description to AI service for parsing
        """
        try:
            response = requests.post(
                f"{self.base_url}/parse",
                headers=self.headers,
                json={"description": description}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling AI service: {str(e)}")
            return None
