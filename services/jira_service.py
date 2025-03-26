from typing import Dict, Any, Optional, List
from jira import JIRA
from utils.logger import logger
import config
import os

class JiraService:
    def __init__(self):
        # Only initialize Jira client if credentials are available
        self.jira = None
        if config.JIRA_URL and hasattr(config, 'JIRA_USERNAME') and config.JIRA_API_TOKEN:
            try:
                self.jira = JIRA(
                    server=config.JIRA_URL,
                    basic_auth=(config.JIRA_USERNAME, config.JIRA_API_TOKEN)
                )
                logger.info("Jira client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Jira client: {str(e)}")
                self.jira = None

    def get_issue_description(self, issue_key: str) -> Optional[str]:
        """
        Retrieves the description of a Jira issue
        """
        if not self.jira:
            logger.error("Jira client not initialized")
            return None
            
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
        if not self.jira:
            logger.error("Jira client not initialized")
            return False
            
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
        if not self.jira:
            logger.error("Jira client not initialized")
            return False
            
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
            
    def create_issue(self, project_key: str, summary: str, description: str, 
                     issue_type: str = "Task", labels: list = None) -> Optional[str]:
        """
        Creates a new Jira issue
        
        Args:
            project_key: The project key in Jira (e.g., 'DEV', 'OPS')
            summary: Issue summary/title
            description: Full issue description
            issue_type: Issue type (Task, Bug, Story, etc.)
            labels: List of labels to apply to the issue
            
        Returns:
            The key of the created issue (e.g., 'DEV-123') or None if creation failed
        """
        if not self.jira:
            logger.error("Jira client not initialized")
            return None
            
        try:
            # Default to "Task" if issue_type is not provided
            if not issue_type:
                issue_type = "Task"
                
            # Create the issue fields dictionary
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            
            # Add labels if provided
            if labels is not None:
                issue_dict['labels'] = labels
                
            # Create the issue
            new_issue = self.jira.create_issue(fields=issue_dict)
            logger.info(f"Created Jira issue: {new_issue.key}")
            
            return new_issue.key
        except Exception as e:
            logger.error(f"Error creating Jira issue: {str(e)}")
            return None
