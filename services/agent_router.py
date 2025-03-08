from typing import Dict, Any, Optional
import requests
from utils.logger import logger
import config

class AgentRouter:
    def __init__(self):
        self.agent_urls = {
            'ci': config.CI_AGENT_URL,
            'helm': config.HELM_AGENT_URL,
            'deploy': config.DEPLOY_AGENT_URL
        }
        self.headers = {
            "Content-Type": "application/json"
        }

    def route_task(self, agent_type: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Routes the task to appropriate AI agent
        """
        if agent_type not in self.agent_urls:
            logger.error(f"Unknown agent type: {agent_type}")
            return None

        try:
            response = requests.post(
                f"{self.agent_urls[agent_type]}/execute",
                headers=self.headers,
                json=task_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling {agent_type} agent: {str(e)}")
            return None

    def process_tasks(self, tasks: list) -> Dict[str, Any]:
        """
        Processes multiple tasks and collects results
        """
        results = {
            'success': [],
            'failed': []
        }

        for task in tasks:
            agent_type = task.get('type')
            if not agent_type:
                results['failed'].append({
                    'task': task,
                    'error': 'Missing agent type'
                })
                continue

            response = self.route_task(agent_type, task)
            if response and response.get('status') == 'success':
                results['success'].append({
                    'task': task,
                    'result': response
                })
            else:
                results['failed'].append({
                    'task': task,
                    'error': 'Agent execution failed'
                })

        return results
