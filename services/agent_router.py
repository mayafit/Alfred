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
                json=task_data,
                timeout=30  # Add timeout to prevent hanging
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

            # Log task processing
            logger.info(f"Processing task type: {agent_type}")
            logger.debug(f"Task details: {task}")

            response = self.route_task(agent_type, task)
            if response and response.get('status') == 'success':
                results['success'].append({
                    'task': task,
                    'result': response
                })
                logger.info(f"Successfully completed {agent_type} task")
            else:
                error_msg = 'Agent execution failed' if response else 'Agent unavailable'
                results['failed'].append({
                    'task': task,
                    'error': error_msg
                })
                logger.error(f"Failed to process {agent_type} task: {error_msg}")

        # Log summary
        logger.info(f"Task processing complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
        return results