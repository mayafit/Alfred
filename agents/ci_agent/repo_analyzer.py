import os
import shutil
import tempfile
import requests
import logging
import re
import git
from typing import Optional, Dict, Any
import json

class RepoAnalyzer:
    def __init__(self, llm_url: str, work_dir: str = "/tmp/repos"):
        self.llm_url = llm_url
        self.work_dir = work_dir
        self.logger = logging.getLogger(__name__)
        
        # Determine LLM provider from URL prefix
        if self.llm_url.startswith("openai:"):
            self.provider = "openai"
            self.api_key = self.llm_url.split(":", 1)[1]
        elif "generativelanguage.googleapis.com" in self.llm_url:
            self.provider = "gemini"
        else:
            self.provider = "other"
            
        self.logger.info(f"Using LLM provider: {self.provider}")

        # Create working directory if it doesn't exist
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

    def clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """
        Clones a Git repository and returns the path to the cloned directory
        """
        try:
            # Create a unique directory name based on the repo URL
            repo_name = re.sub(r'[^\w\-_]', '_', repo_url.split('/')[-1].replace('.git', ''))
            repo_path = os.path.join(self.work_dir, f"{repo_name}_{tempfile.mktemp(dir='').split('/')[-1]}")
            
            # Remove existing directory if it exists
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
            
            # Clone the repository using GitPython
            self.logger.info(f"Cloning repository {repo_url} (branch: {branch}) to {repo_path}")
            git.Repo.clone_from(repo_url, repo_path, branch=branch)
            
            self.logger.info(f"Repository cloned successfully to {repo_path}")
            return repo_path
            
        except Exception as e:
            self.logger.error(f"Error cloning repository: {str(e)}")
            raise RuntimeError(f"Failed to clone repository: {str(e)}")

    def analyze_project_type(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyzes the repository and determines project type based on files present.
        Falls back to LLM analysis if available.
        """
        try:
            # Get list of files in repository
            file_list = []
            for root, _, files in os.walk(repo_path):
                for file in files:
                    file_path = os.path.relpath(os.path.join(root, file), repo_path)
                    # Skip .git directory files 
                    if not file_path.startswith('.git/'):
                        file_list.append(file_path)

            # Log file list for debugging
            self.logger.debug(f"Repository files:\n{json.dumps(file_list, indent=2)}")
            
            # Rule-based project type detection
            project_type, confidence, build_steps = self._detect_project_type(file_list)
            
            # Only use LLM if rule-based detection has low confidence
            if confidence < 0.7:
                llm_project_type, llm_confidence, llm_build_steps = self._analyze_with_llm(file_list)
                
                # Use LLM results if they have higher confidence
                if llm_confidence > confidence:
                    project_type = llm_project_type
                    confidence = llm_confidence
                    build_steps = llm_build_steps
            
            analysis = {
                "project_type": project_type,
                "confidence": confidence,
                "build_steps": build_steps
            }
            
            self.logger.info(f"Analysis result: {json.dumps(analysis, indent=2)}")
            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze repository: {str(e)}")
            # Return a default analysis with error information
            return {
                "project_type": "unknown",
                "confidence": 0.0,
                "build_steps": [],
                "error": str(e)
            }
    
    def _detect_project_type(self, file_list: list) -> tuple:
        """
        Uses rule-based approach to detect project type from file list
        Returns (project_type, confidence, build_steps)
        """
        # Check for Node.js project
        if any(f == 'package.json' for f in file_list):
            # It's a Node.js project
            if any(f.endswith('.tsx') or f.endswith('.jsx') for f in file_list):
                # React project
                return "node_service", 0.9, ["npm install", "npm test", "npm build"]
            elif any(f.endswith('.vue') for f in file_list):
                # Vue project
                return "node_service", 0.9, ["npm install", "npm test", "npm build"]
            elif any(f.endswith('.angular.json') or f == 'angular.json' for f in file_list):
                # Angular project
                return "node_service", 0.9, ["npm install", "ng test", "ng build"]
            else:
                # Generic Node.js
                return "node_service", 0.8, ["npm install", "npm test", "npm build"]
        
        # Check for Python project
        elif any(f == 'requirements.txt' or f == 'setup.py' or f == 'pyproject.toml' for f in file_list):
            if any(f.endswith('wsgi.py') for f in file_list) or any('django' in f.lower() for f in file_list):
                # Django project
                return "python", 0.9, ["pip install -r requirements.txt", "python manage.py test", "python manage.py collectstatic"]
            elif any('flask' in f.lower() for f in file_list):
                # Flask project
                return "python", 0.9, ["pip install -r requirements.txt", "pytest", "python build"]
            else:
                # Generic Python
                return "python", 0.8, ["pip install -r requirements.txt", "pytest"]
        
        # Check for Java project
        elif any(f == 'pom.xml' for f in file_list):
            # Maven project
            return "java", 0.9, ["mvn clean", "mvn test", "mvn package"]
        elif any(f == 'build.gradle' or f == 'build.gradle.kts' for f in file_list):
            # Gradle project
            return "java", 0.9, ["./gradlew clean", "./gradlew test", "./gradlew build"]
        
        # Check for .NET project
        elif any(f.endswith('.csproj') for f in file_list):
            if any(f.endswith('.razor') for f in file_list) or any(f.endswith('.cshtml') for f in file_list):
                # ASP.NET project
                return "aspnet_service", 0.9, ["dotnet restore", "dotnet test", "dotnet build", "dotnet publish"]
            else:
                # Generic .NET project
                return "csharp_library", 0.8, ["dotnet restore", "dotnet test", "dotnet build"]
        
        # Static website
        elif any(f == 'index.html' for f in file_list):
            return "website", 0.7, ["npm install", "npm build"]
        
        # Unknown project type
        return "unknown", 0.1, []
            
    def _analyze_with_llm(self, file_list: list) -> tuple:
        """
        Uses LLM to analyze the repository and determine project type
        Returns (project_type, confidence, build_steps)
        """
        try:
            # Common prompt for all LLM providers
            prompt = f"""You are a DevOps engineer analyzing a code repository.
Based on the following file list, determine the project type and relevant build configuration.
Respond with a JSON object containing:
- project_type: one of ["csharp_library", "aspnet_service", "node_service", "python", "java", "website"]
- confidence: confidence score between 0 and 1
- build_steps: list of required build steps

File list:
{json.dumps(file_list, indent=2)}

Response:"""

            # Call the appropriate provider's implementation
            if self.provider == "openai":
                result = self._analyze_with_openai(prompt)
            elif self.provider == "gemini":
                result = self._analyze_with_gemini(prompt)
            else:
                result = self._analyze_with_other_llm(prompt)

            if not result:
                raise ValueError("Empty response from LLM")

            # Try to extract JSON from the text response
            try:
                # Look for JSON-like content
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = result[json_start:json_end]
                    analysis = json.loads(json_text)
                else:
                    analysis = json.loads(result)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse LLM response as JSON: {result}")

            self.logger.info(f"LLM analysis result: {json.dumps(analysis, indent=2)}")

            if not all(k in analysis for k in ["project_type", "confidence", "build_steps"]):
                raise ValueError(f"Invalid response format from LLM: {analysis}")

            return analysis["project_type"], analysis["confidence"], analysis["build_steps"]

        except Exception as e:
            self.logger.error(f"Failed to analyze with LLM: {str(e)}")
            return "unknown", 0.0, []
            
    def _analyze_with_openai(self, prompt: str) -> Optional[str]:
        """
        Uses OpenAI to analyze the repository
        """
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            self.logger.debug("Sending analysis request to OpenAI")
            response = client.chat.completions.create(
                model="gpt-4o",  # The newest OpenAI model, released May 13, 2024
                messages=[
                    {"role": "system", "content": "You are a DevOps engineer analyzing code repositories."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error calling OpenAI: {str(e)}")
            return None
            
    def _analyze_with_gemini(self, prompt: str) -> Optional[str]:
        """
        Uses Google Gemini to analyze the repository
        """
        try:
            # Extract API key from URL if present as query parameter
            url = self.llm_url
            api_key = None
            if "?key=" in url:
                url, api_key = url.split("?key=", 1)
                
            self.logger.debug("Sending analysis request to Gemini")
            
            # Prepare request body for Google Gemini API
            request_body = {
                "contents": [{
                    "parts": [
                        {"text": prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1000,
                    "responseFormat": "JSON"
                }
            }
            
            # Headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Prepare URL with API key if available
            request_url = url
            if api_key:
                request_url = f"{url}?key={api_key}"
                
            # Make request
            response = requests.post(
                request_url,
                headers=headers,
                json=request_body,
                timeout=30
            )
            response.raise_for_status()
            
            # Process response
            result = response.json()
            
            # Extract content from Gemini response format
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"]
                
            self.logger.warning("Unexpected Gemini API response format")
            return None
            
        except Exception as e:
            self.logger.error(f"Error calling Gemini: {str(e)}")
            return None
            
    def _analyze_with_other_llm(self, prompt: str) -> Optional[str]:
        """
        Uses other LLM server to analyze the repository
        """
        try:
            self.logger.debug(f"Sending analysis request to custom LLM at {self.llm_url}")
            
            # Generic format for Llama-like API
            response = requests.post(
                f"{self.llm_url}/completion",
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
            return result
            
        except Exception as e:
            self.logger.error(f"Error calling custom LLM: {str(e)}")
            return None

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