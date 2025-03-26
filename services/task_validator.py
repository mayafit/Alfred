"""
Task validator service for validating tasks and providing detailed feedback.
"""
from typing import Dict, Any, List, Tuple

class TaskValidator:
    """
    Service for validating DevOps task details and identifying missing requirements
    """
    def __init__(self):
        """
        Initialize the task validator with required fields for each task type
        """
        # For each task type, define required parameters
        self.task_requirements = {
            "ci": {
                "required": ["repository"],
                "suggested": ["branch", "build_steps"]
            },
            "helm": {
                "required": ["repository", "app_name"],
                "suggested": ["namespace", "values"]
            },
            "deploy": {
                "required": ["repository", "namespace", "cluster_details"],
                "suggested": ["helm_values", "release_name"]
            }
        }
        
        # Parameter descriptions for feedback messages
        self.parameter_descriptions = {
            "repository": "Git repository URL (e.g., https://github.com/username/repo)",
            "branch": "Git branch to use (e.g., main, develop)",
            "build_steps": "List of build steps to include (e.g., test, lint, build)",
            "app_name": "Name of the application for Helm chart",
            "namespace": "Kubernetes namespace for deployment",
            "values": "Custom values for the Helm chart",
            "cluster_details": "Target Kubernetes cluster connection details",
            "helm_values": "Values to override in the Helm chart",
            "release_name": "Helm release name for deployment"
        }
    
    def validate_task(self, task: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validates if a task has all required fields
        
        Args:
            task: The task dictionary to validate
            
        Returns:
            Tuple containing:
            - Boolean indicating if all required fields are present
            - List of missing required field descriptions
            - List of suggested field descriptions that could improve task execution
        """
        # Default return for unknown task types
        if 'type' not in task or task['type'] not in self.task_requirements:
            return False, ["Unknown task type"], []
        
        task_type = task['type']
        parameters = task.get('parameters', {})
        
        # Check required fields
        required_fields = self.task_requirements[task_type]['required']
        missing_required = [field for field in required_fields if field not in parameters]
        
        # Check suggested fields
        suggested_fields = self.task_requirements[task_type]['suggested']
        missing_suggested = [field for field in suggested_fields if field not in parameters]
        
        # Convert field names to descriptions
        missing_required_desc = [
            f"{field}: {self.parameter_descriptions.get(field, 'Required field')}" 
            for field in missing_required
        ]
        
        missing_suggested_desc = [
            f"{field}: {self.parameter_descriptions.get(field, 'Suggested field')}" 
            for field in missing_suggested
        ]
        
        is_valid = len(missing_required) == 0
        
        return is_valid, missing_required_desc, missing_suggested_desc
    
    def validate_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates a list of tasks and provides detailed feedback
        
        Args:
            tasks: List of task dictionaries to validate
            
        Returns:
            Dictionary with validation results and missing requirements
        """
        results = []
        is_valid = True
        
        for i, task in enumerate(tasks):
            # Check task type
            if 'type' not in task:
                results.append({
                    "task_index": i,
                    "is_valid": False,
                    "missing_required": ["Task type is required"],
                    "missing_suggested": [],
                    "task": task
                })
                is_valid = False
                continue
                
            # Validate task
            task_valid, missing_required, missing_suggested = self.validate_task(task)
            
            results.append({
                "task_index": i,
                "is_valid": task_valid,
                "missing_required": missing_required,
                "missing_suggested": missing_suggested,
                "task": task
            })
            
            if not task_valid:
                is_valid = False
        
        return {
            "is_valid": is_valid,
            "task_results": results
        }
    
    def generate_feedback_message(self, validation_result: Dict[str, Any]) -> str:
        """
        Generates a human-readable feedback message from validation results
        
        Args:
            validation_result: The result from validate_tasks()
            
        Returns:
            A formatted string with feedback on missing requirements
        """
        message = ""
        
        for i, task_result in enumerate(validation_result.get('task_results', [])):
            task_type = task_result['task'].get('type', 'unknown')
            
            # Add task header
            message += f"Task {i+1} ({task_type.upper()}):\n"
            
            # Add missing required fields
            if task_result['missing_required']:
                message += "  Missing required fields:\n"
                for field in task_result['missing_required']:
                    message += f"  - {field}\n"
            
            # Add missing suggested fields
            if task_result['missing_suggested']:
                message += "  Suggested fields (optional but recommended):\n"
                for field in task_result['missing_suggested']:
                    message += f"  - {field}\n"
            
            # Add a spacer between tasks
            message += "\n"
        
        return message