from typing import Dict, Any, Optional
from jira import JIRA
from utils.logger import logger
import config

class JiraService:
    def __init__(self):
        self.jira = JIRA(
            server=config.JIRA_URL,
            basic_auth=(config.JIRA_USERNAME, config.JIRA_API_TOKEN)
        )

    def get_issue_description(self, issue_key: str) -> Optional[str]:
        """
        Retrieves the description of a Jira issue
        """
        try:
            issue = self.jira.issue(issue_key)
            return issue.fields.description
        except Exception as e:
            logger.error(f"Error fetching issue description: {str(e)}")
            return None

    def add_comment(self, issue_key: str, comment: str) -> bool:
        """
        Adds a comment to a Jira issue
        """
        try:
            self.jira.add_comment(issue_key, comment)
            return True
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            return False

    def update_issue_status(self, issue_key: str, status: str) -> bool:
        """
        Updates the status of a Jira issue
        """
        try:
            issue = self.jira.issue(issue_key)
            transitions = self.jira.transitions(issue)
            
            for t in transitions:
                if t['name'].lower() == status.lower():
                    self.jira.transition_issue(issue, t['id'])
                    return True
            
            logger.warning(f"Status transition {status} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating issue status: {str(e)}")
            return False
