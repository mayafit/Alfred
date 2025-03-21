import os
import shutil
import subprocess
import requests
import logging
from typing import Optional, Dict, Any
import json

class RepoAnalyzer:
    def __init__(self, llama_url: str, work_dir: str = "/tmp/repos"):
        self.llama_url = llama_url
        self.work_dir = work_dir
        self.logger = logging.getLogger(__name__)

        # Create working directory if it doesn't exist
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

    def clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """
        Clones a Git repository and returns the path to the cloned directory
        """
        try:
            # Create a unique directory name from the repo URL
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            repo_path = os.path.join(self.work_dir, repo_name)

            # Remove existing directory if it exists
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)

            # Clone the repository
            self.logger.info(f"Cloning repository {repo_url} to {repo_path}")
            subprocess.run(["git", "clone", "-b", branch, repo_url, repo_path], check=True)

            return repo_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {str(e)}")
            raise

    def analyze_project_type(self, repo_path: str) -> Dict[str, Any]:
        """
        Uses Llama to analyze the repository and determine project type
        """
        try:
            # Get list of files in repository
            file_list = []
            for root, _, files in os.walk(repo_path):
                for file in files:
                    file_list.append(os.path.relpath(os.path.join(root, file), repo_path))

            # Log file list for debugging
            self.logger.debug(f"Repository files:\n{json.dumps(file_list, indent=2)}")

            # Prepare prompt for Llama
            prompt = f"""You are a DevOps engineer analyzing a code repository.
Based on the following file list, determine the project type and relevant build configuration.
Respond with a JSON object containing:
- project_type: one of ["csharp_library", "aspnet_service", "node_service", "website"]
- confidence: confidence score between 0 and 1
- build_steps: list of required build steps

File list:
{json.dumps(file_list, indent=2)}

Response:"""

            # Make request to Llama server
            self.logger.debug(f"Sending analysis request to Llama for {repo_path}")
            response = requests.post(
                f"{self.llama_url}/completion",
                json={
                    "prompt": prompt,
                    "temperature": 0.2,
                    "max_tokens": 500
                },
                timeout=30
            )
            response.raise_for_status()

            # Parse and validate response
            result = response.json().get("content")
            if not result:
                raise ValueError("Empty response from Llama")

            analysis = json.loads(result)
            self.logger.info(f"Analysis result: {json.dumps(analysis, indent=2)}")

            if not all(k in analysis for k in ["project_type", "confidence", "build_steps"]):
                raise ValueError("Invalid response format from Llama")

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze repository: {str(e)}")
            raise

    def generate_jenkins_file(self, repo_path: str, project_type: str) -> None:
        """
        Generates a Jenkinsfile in the repository based on the project type
        """
        try:
            # Read template file
            template_path = os.path.join(os.path.dirname(__file__), "templates", f"{project_type}.groovy")
            if not os.path.exists(template_path):
                raise ValueError(f"Template not found for project type: {project_type}")

            with open(template_path, "r") as f:
                template_content = f.read()

            # Write Jenkinsfile to repository
            jenkins_path = os.path.join(repo_path, "Jenkinsfile")
            self.logger.info(f"Generating Jenkinsfile at {jenkins_path}")

            with open(jenkins_path, "w") as f:
                f.write(template_content)

            self.logger.debug(f"Generated Jenkinsfile content:\n{template_content}")

        except Exception as e:
            self.logger.error(f"Failed to generate Jenkinsfile: {str(e)}")
            raise

    def cleanup(self, repo_path: str) -> None:
        """
        Cleans up the cloned repository
        """
        try:
            if os.path.exists(repo_path):
                self.logger.info(f"Cleaning up repository at {repo_path}")
                shutil.rmtree(repo_path)
        except Exception as e:
            self.logger.error(f"Failed to cleanup repository: {str(e)}")