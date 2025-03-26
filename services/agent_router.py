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

    def validate_agent_response(self, response: Dict[str, Any]) -> bool:
        """
        Validates the response format from an agent
        """
        if not isinstance(response, dict):
            return False

        # 'status' and 'message' are required fields
        if 'status' not in response or 'message' not in response:
            return False

        # For backward compatibility, we make 'details' optional
        # as some agents (like SmolDeployAgent) might include detailed information directly

        # Status must be one of 'success', 'error', or 'warning'
        if response['status'] not in ['success', 'error', 'warning']:
            return False

        return True

    def route_task(self, agent_type: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Routes the task to appropriate AI agent
        """
        if agent_type not in self.agent_urls:
            logger.error(f"Unknown agent type: {agent_type}")
            return None

        try:
            logger.info(f"Routing task to {agent_type} agent")
            logger.debug(f"Task data: {task_data}")

            response = requests.post(
                f"{self.agent_urls[agent_type]}/execute",
                headers=self.headers,
                json=task_data,
                timeout=30  # Add timeout to prevent hanging
            )
            response.raise_for_status()

            result = response.json()
            if not self.validate_agent_response(result):
                logger.error(f"Invalid response format from {agent_type} agent")
                return None

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling {agent_type} agent: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with {agent_type} agent: {str(e)}")
            return None

    def process_tasks(self, tasks: list) -> Dict[str, Any]:
        """
        Processes multiple tasks and collects results
        """
        results = {
            'success': [],
            'failed': []
        }

        logger.info(f"Processing {len(tasks)} tasks")

        for task in tasks:
            agent_type = task.get('type')
            if not agent_type:
                logger.error("Task missing required 'type' field")
                results['failed'].append({
                    'task': task,
                    'error': 'Missing agent type'
                })
                continue

            # Log task processing
            logger.info(f"Processing task type: {agent_type}")
            logger.debug(f"Task details: {task}")

            response = self.route_task(agent_type, task)
            if not response:
                error_msg = 'Agent unavailable'
                results['failed'].append({
                    'task': task,
                    'error': error_msg
                })
                logger.error(f"Failed to process {agent_type} task: {error_msg}")
            elif response.get('status') == 'success':
                results['success'].append({
                    'task': task,
                    'result': response
                })
                logger.info(f"Successfully completed {agent_type} task")
            elif response.get('status') == 'warning':
                # For warnings, we consider it a partial success but log the warning
                results['success'].append({
                    'task': task,
                    'result': response,
                    'warning': True
                })
                logger.warning(f"Completed {agent_type} task with warnings: {response.get('message')}")
            else:
                error_msg = f"Agent execution failed: {response.get('message', 'Unknown error')}"
                results['failed'].append({
                    'task': task,
                    'error': error_msg,
                    'details': response.get('details', {})
                })
                logger.error(f"Failed to process {agent_type} task: {error_msg}")

        # Log summary
        logger.info(f"Task processing complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
        return results