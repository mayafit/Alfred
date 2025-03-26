"""
SmolAgent-based Helm chart generator

This module provides a lightweight, AI-powered agent for generating
Helm charts based on repository analysis. It analyzes Dockerfiles,
docker-compose files, and other configuration to generate appropriate
Helm chart configurations.
"""

import os
import json
import logging
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Tuple, Optional
import yaml

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class SmolHelmAgent:
    """
    SmolAgent-based Helm chart generator that analyzes repositories
    and generates appropriate Helm charts.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize the Helm chart generator agent.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: The model to use for generating Helm configurations
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
    def clone_repository(self, repository_url: str, branch: str = "main") -> str:
        """
        Clone a repository to a temporary directory.
        
        Args:
            repository_url: The URL of the Git repository
            branch: The branch to checkout
            
        Returns:
            Path to the cloned repository
        """
        repo_dir = None
        try:
            repo_dir = tempfile.mkdtemp()
            logger.info(f"Cloning repository {repository_url} (branch: {branch}) to {repo_dir}")
            
            clone_cmd = f"git clone {repository_url} {repo_dir}"
            if branch != "main":
                clone_cmd += f" --branch {branch}"
                
            subprocess.check_output(clone_cmd, shell=True)
            
            # Verify the clone succeeded
            if not os.path.exists(os.path.join(repo_dir, ".git")):
                raise Exception(f"Failed to clone repository {repository_url}")
                
            return repo_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {str(e)}")
            if repo_dir and os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            raise
        except Exception as e:
            logger.error(f"Error cloning repository: {str(e)}")
            if repo_dir and os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            raise
    
    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyze the repository to identify key components:
        - Dockerfile(s)
        - docker-compose.yml
        - package.json/requirements.txt
        - Other configuration files
        
        Args:
            repo_path: Path to the cloned repository
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "has_dockerfile": False,
            "dockerfile_paths": [],
            "has_docker_compose": False,
            "docker_compose_path": None,
            "language": None,
            "dependencies": [],
            "package_managers": [],
            "port_mappings": [],
            "environment_variables": {},
            "volumes": [],
            "services": []
        }
        
        # Check for Dockerfile(s)
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.lower() == "dockerfile":
                    analysis["has_dockerfile"] = True
                    dockerfile_path = os.path.relpath(os.path.join(root, file), repo_path)
                    analysis["dockerfile_paths"].append(dockerfile_path)
                    
                    # Parse Dockerfile for relevant details
                    with open(os.path.join(root, file), 'r') as f:
                        dockerfile_content = f.read()
                        
                    # Extract exposed ports
                    for line in dockerfile_content.split('\n'):
                        if line.strip().startswith('EXPOSE'):
                            ports = line.strip().split('EXPOSE')[1].strip().split()
                            for port in ports:
                                if port not in analysis["port_mappings"]:
                                    analysis["port_mappings"].append(port)
                        
                        # Extract environment variables
                        if line.strip().startswith('ENV'):
                            env_parts = line.strip().split('ENV')[1].strip().split('=', 1)
                            if len(env_parts) == 2:
                                analysis["environment_variables"][env_parts[0].strip()] = env_parts[1].strip()
                
                # Check for docker-compose.yml
                if file.lower() in ["docker-compose.yml", "docker-compose.yaml"]:
                    analysis["has_docker_compose"] = True
                    analysis["docker_compose_path"] = os.path.relpath(os.path.join(root, file), repo_path)
                    
                    # Parse docker-compose.yml for services, ports, volumes, etc.
                    try:
                        with open(os.path.join(root, file), 'r') as f:
                            compose_data = yaml.safe_load(f)
                            
                        if compose_data and 'services' in compose_data:
                            for service_name, service_config in compose_data['services'].items():
                                service_info = {
                                    "name": service_name,
                                    "image": service_config.get('image', ''),
                                    "build": service_config.get('build', None),
                                    "ports": service_config.get('ports', []),
                                    "environment": service_config.get('environment', {}),
                                    "volumes": service_config.get('volumes', []),
                                    "depends_on": service_config.get('depends_on', [])
                                }
                                analysis["services"].append(service_info)
                                
                                # Add ports from this service
                                for port in service_config.get('ports', []):
                                    if port not in analysis["port_mappings"]:
                                        analysis["port_mappings"].append(port)
                                        
                                # Add environment variables
                                if isinstance(service_config.get('environment', {}), dict):
                                    analysis["environment_variables"].update(service_config.get('environment', {}))
                                elif isinstance(service_config.get('environment', []), list):
                                    for env_var in service_config.get('environment', []):
                                        if '=' in env_var:
                                            key, value = env_var.split('=', 1)
                                            analysis["environment_variables"][key] = value
                                            
                                # Add volumes
                                for volume in service_config.get('volumes', []):
                                    if volume not in analysis["volumes"]:
                                        analysis["volumes"].append(volume)
                    except Exception as e:
                        logger.warning(f"Failed to parse docker-compose.yml: {str(e)}")
                
                # Detect language and dependencies
                if file.lower() == "package.json":
                    analysis["language"] = "javascript/nodejs"
                    analysis["package_managers"].append("npm")
                    
                    try:
                        with open(os.path.join(root, file), 'r') as f:
                            package_data = json.load(f)
                            
                        dependencies = package_data.get('dependencies', {})
                        for dep_name, dep_version in dependencies.items():
                            analysis["dependencies"].append(f"{dep_name}@{dep_version}")
                    except Exception as e:
                        logger.warning(f"Failed to parse package.json: {str(e)}")
                        
                elif file.lower() == "requirements.txt":
                    analysis["language"] = "python"
                    analysis["package_managers"].append("pip")
                    
                    try:
                        with open(os.path.join(root, file), 'r') as f:
                            requirements = f.readlines()
                            
                        for req in requirements:
                            req = req.strip()
                            if req and not req.startswith('#'):
                                analysis["dependencies"].append(req)
                    except Exception as e:
                        logger.warning(f"Failed to parse requirements.txt: {str(e)}")
                        
                elif file.lower() == "go.mod":
                    analysis["language"] = "go"
                    analysis["package_managers"].append("go modules")
                
                elif file.lower() == "cargo.toml":
                    analysis["language"] = "rust"
                    analysis["package_managers"].append("cargo")
        
        return analysis
    
    def generate_helm_chart(self, analysis: Dict[str, Any], app_name: str, namespace: str) -> Dict[str, Any]:
        """
        Generate Helm chart based on the repository analysis.
        
        Args:
            analysis: Repository analysis
            app_name: Application name
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with generated Helm chart files
        """
        # Create a temporary directory for the Helm chart
        chart_dir = tempfile.mkdtemp()
        
        prompt = self._create_helm_generation_prompt(analysis, app_name, namespace)
        
        try:
            # Generate the Helm chart configuration using LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            helm_files = json.loads(response.choices[0].message.content)
            
            # Write the generated files to the chart directory
            for filename, content in helm_files.items():
                # Create subdirectories if needed
                filepath = os.path.join(chart_dir, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, 'w') as f:
                    f.write(content)
            
            # Package the Helm chart
            package_cmd = f"cd {chart_dir} && helm package ."
            subprocess.check_output(package_cmd, shell=True)
            
            # Get the path to the packaged Helm chart
            helm_package = None
            for file in os.listdir(chart_dir):
                if file.endswith('.tgz'):
                    helm_package = os.path.join(chart_dir, file)
                    break
            
            return {
                "chart_dir": chart_dir,
                "helm_files": helm_files,
                "helm_package": helm_package
            }
            
        except Exception as e:
            logger.error(f"Error generating Helm chart: {str(e)}")
            shutil.rmtree(chart_dir)
            raise
    
    def _create_helm_generation_prompt(self, analysis: Dict[str, Any], app_name: str, namespace: str) -> str:
        """
        Create a prompt for LLM to generate a Helm chart.
        
        Args:
            analysis: Repository analysis
            app_name: Application name
            namespace: Kubernetes namespace
            
        Returns:
            Prompt string
        """
        has_dockerfile = "Yes" if analysis["has_dockerfile"] else "No"
        has_docker_compose = "Yes" if analysis["has_docker_compose"] else "No"
        
        dockerfile_details = ""
        if analysis["has_dockerfile"]:
            dockerfile_details = "Dockerfile paths: " + ", ".join(analysis["dockerfile_paths"])
        
        services_details = ""
        if analysis["services"]:
            services_details = "Services from docker-compose.yml:\n"
            for service in analysis["services"]:
                services_details += f"- {service['name']}\n"
                services_details += f"  Image: {service['image']}\n"
                services_details += f"  Ports: {service['ports']}\n"
                services_details += f"  Environment variables: {service['environment']}\n"
                services_details += f"  Volumes: {service['volumes']}\n"
        
        environment_vars = ""
        if analysis["environment_variables"]:
            environment_vars = "Environment variables:\n"
            for key, value in analysis["environment_variables"].items():
                environment_vars += f"- {key}={value}\n"
        
        ports = ""
        if analysis["port_mappings"]:
            ports = "Port mappings:\n"
            for port in analysis["port_mappings"]:
                ports += f"- {port}\n"
        
        language = analysis["language"] if analysis["language"] else "Unknown"
        
        dependencies = ""
        if analysis["dependencies"]:
            dependencies = "Dependencies:\n"
            for dep in analysis["dependencies"]:
                dependencies += f"- {dep}\n"
        
        prompt = f"""
Generate a Helm chart for a Kubernetes application with the following details:

Application Name: {app_name}
Kubernetes Namespace: {namespace}
Language: {language}
Has Dockerfile: {has_dockerfile}
{dockerfile_details}
Has docker-compose.yml: {has_docker_compose}
{services_details}
{environment_vars}
{ports}
{dependencies}

Create the following Helm chart files:
1. Chart.yaml - Standard Helm chart metadata
2. values.yaml - Default values file that includes configuration for the image, service, ingress, etc.
3. templates/deployment.yaml - Kubernetes Deployment manifest
4. templates/service.yaml - Kubernetes Service manifest
5. templates/ingress.yaml - Kubernetes Ingress manifest
6. templates/configmap.yaml - ConfigMap for environment variables
7. templates/serviceaccount.yaml - ServiceAccount for the application
8. templates/helpers.tpl - Helm helper templates
9. templates/NOTES.txt - Installation notes

Return the result as a JSON object where keys are filenames and values are the file contents. 
For example:
{{
  "Chart.yaml": "apiVersion: v2\\nname: example\\n...",
  "values.yaml": "replicaCount: 1\\n...",
  "templates/deployment.yaml": "apiVersion: apps/v1\\n..."
}}

Ensure that you generate files that will work with Helm v3. Use best practices for Kubernetes manifests.
Include appropriate resource requests and limits, liveness and readiness probes, etc.
"""
        
        return prompt
    
    def process_helm_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Helm chart generation task.
        
        Args:
            task_data: A dictionary containing task information
                The task should contain 'parameters' with:
                - repository: Git repository URL
                - branch: Git branch (optional, defaults to "main")
                - app_name: Application name
                - namespace: Kubernetes namespace
        
        Returns:
            Dictionary with the result of the Helm chart generation
        """
        temp_dir = None
        chart_dir = None
        
        try:
            # Validate that task_data contains the required parameters
            if 'parameters' not in task_data:
                return {"status": "error", "message": "Missing parameters field"}

            params = task_data['parameters']
            required_fields = ['repository', 'app_name', 'namespace']
            missing_fields = [field for field in required_fields if field not in params]
            
            if missing_fields:
                return {
                    "status": "error", 
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }

            repository = params['repository']
            branch = params.get('branch', 'main')
            app_name = params['app_name']
            namespace = params['namespace']

            logger.info(f"Processing Helm chart generation for {repository} (branch: {branch})")
            
            # Clone the repository
            temp_dir = self.clone_repository(repository, branch)
            
            # Analyze the repository
            analysis = self.analyze_repository(temp_dir)
            
            # Generate the Helm chart
            helm_chart = self.generate_helm_chart(analysis, app_name, namespace)
            chart_dir = helm_chart["chart_dir"]
            
            # Prepare the result
            result = {
                "status": "success",
                "message": f"Generated Helm chart for {app_name}",
                "details": {
                    "repository": repository,
                    "branch": branch,
                    "app_name": app_name,
                    "namespace": namespace,
                    "analysis": analysis,
                    "chart_files": helm_chart["helm_files"],
                    "package_path": helm_chart["helm_package"]
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Helm task: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process Helm task: {str(e)}"
            }
        finally:
            # Clean up temporary directories
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if chart_dir and os.path.exists(chart_dir):
                shutil.rmtree(chart_dir)