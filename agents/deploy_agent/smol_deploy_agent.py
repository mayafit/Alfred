"""
SmolAgent-based deployment agent for Kubernetes using Helm charts

This module provides a lightweight, AI-powered agent for handling
Kubernetes deployments through Helm charts. It interprets deployment
requirements, constructs appropriate Helm commands, and executes them.
"""

import os
import json
import logging
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Tuple, Optional

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class SmolDeployAgent:
    """
    SmolAgent-based deployment agent that processes deployment tasks,
    generates appropriate Helm commands, and executes them.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize the deployment agent.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: The model to use for generating deployment commands
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.helm_binary = self._find_helm_binary()
        self.kubectl_binary = self._find_kubectl_binary()

    def _find_helm_binary(self) -> str:
        """Find the helm binary in the system."""
        try:
            helm_path = subprocess.check_output(['which', 'helm']).decode().strip()
            logger.info(f"Found helm binary at {helm_path}")
            return helm_path
        except subprocess.CalledProcessError:
            logger.warning("Helm binary not found, using 'helm' assuming it's in PATH")
            return 'helm'

    def _find_kubectl_binary(self) -> str:
        """Find the kubectl binary in the system."""
        try:
            kubectl_path = subprocess.check_output(['which', 'kubectl']).decode().strip()
            logger.info(f"Found kubectl binary at {kubectl_path}")
            return kubectl_path
        except subprocess.CalledProcessError:
            logger.warning("kubectl binary not found, using 'kubectl' assuming it's in PATH")
            return 'kubectl'

    def process_deployment_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a deployment task and execute the necessary Helm commands.
        
        Args:
            task_data: A dictionary containing deployment task information
                The task should contain 'parameters' with:
                - repository: Git repository with Helm charts
                - namespace: Target Kubernetes namespace
                - cluster_details: Connection details for the target cluster
                - helm_values: Values to pass to Helm (can be a path or inline values)
                - release_name: Optional name for the Helm release
        
        Returns:
            Dictionary with the result of the deployment operation
        """
        try:
            # Validate that task_data contains the required parameters
            if 'parameters' not in task_data:
                return {"status": "error", "message": "Missing parameters field"}

            params = task_data['parameters']
            required_fields = ['repository', 'namespace', 'cluster_details']
            missing_fields = [field for field in required_fields if field not in params]
            
            if missing_fields:
                return {
                    "status": "error", 
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }

            repository = params['repository']
            namespace = params['namespace']
            cluster_details = params['cluster_details']
            helm_values = params.get('helm_values', {})
            release_name = params.get('release_name', repository.split('/')[-1])

            # Check if we have cluster access
            if not self._verify_cluster_access(cluster_details):
                return {
                    "status": "error",
                    "message": "Failed to connect to the target cluster"
                }

            # Generate and execute Helm commands
            commands = self._generate_helm_commands(repository, namespace, release_name, helm_values, cluster_details)
            
            # Execute commands
            results = {}
            for cmd_name, command in commands.items():
                try:
                    logger.info(f"Executing {cmd_name}: {command}")
                    output = subprocess.check_output(command, shell=True).decode()
                    results[cmd_name] = {
                        "status": "success",
                        "output": output
                    }
                except subprocess.CalledProcessError as e:
                    results[cmd_name] = {
                        "status": "error",
                        "error": str(e),
                        "output": e.output.decode() if e.output else ""
                    }
                    # Return immediately if a command fails
                    return {
                        "status": "error",
                        "message": f"Command '{cmd_name}' failed",
                        "details": results
                    }

            # Verify deployment
            deployment_status = self._verify_deployment(namespace, release_name)
            
            return {
                "status": "success" if deployment_status["status"] == "success" else "error",
                "message": "Deployment completed successfully" if deployment_status["status"] == "success" else "Deployment completed with issues",
                "details": {
                    "repository": repository,
                    "namespace": namespace,
                    "release_name": release_name,
                    "commands": results,
                    "deployment_verification": deployment_status
                }
            }
        
        except Exception as e:
            logger.error(f"Error processing deployment: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process deployment: {str(e)}"
            }

    def _verify_cluster_access(self, cluster_details: Dict[str, Any]) -> bool:
        """
        Verify that we have access to the target Kubernetes cluster.
        
        Args:
            cluster_details: Connection details for the target cluster
                Could include kubeconfig path, context name, etc.
        
        Returns:
            True if access verification succeeds, False otherwise
        """
        temp_dir = None
        try:
            # If kubeconfig is provided, set it up
            kubeconfig = cluster_details.get('kubeconfig')
            context = cluster_details.get('context')
            
            kubectl_cmd = f"{self.kubectl_binary} get nodes"
            
            if kubeconfig:
                # Create temporary file for kubeconfig if it's provided as content
                if isinstance(kubeconfig, dict) or isinstance(kubeconfig, str) and not os.path.isfile(kubeconfig):
                    temp_dir = tempfile.mkdtemp()
                    kubeconfig_path = os.path.join(temp_dir, 'kubeconfig')
                    
                    with open(kubeconfig_path, 'w') as f:
                        if isinstance(kubeconfig, dict):
                            json.dump(kubeconfig, f)
                        else:
                            f.write(kubeconfig)
                    
                    os.environ['KUBECONFIG'] = kubeconfig_path
                else:
                    os.environ['KUBECONFIG'] = kubeconfig
            
            if context:
                kubectl_cmd = f"{self.kubectl_binary} --context={context} get nodes"
            
            # Run the command to check cluster access
            logger.info(f"Verifying cluster access with: {kubectl_cmd}")
            subprocess.check_output(kubectl_cmd, shell=True)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to verify cluster access: {e.output.decode() if e.output else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error verifying cluster access: {str(e)}")
            return False
        finally:
            # Clean up temporary kubeconfig if created
            if temp_dir:
                shutil.rmtree(temp_dir)

    def _generate_helm_commands(self, repository: str, namespace: str, release_name: str, 
                               helm_values: Dict[str, Any], cluster_details: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate Helm commands for deployment based on provided parameters.
        
        This uses the LLM to generate appropriate commands based on the input parameters.
        
        Args:
            repository: Git repository with Helm charts
            namespace: Target Kubernetes namespace
            release_name: Helm release name
            helm_values: Values to pass to Helm
            cluster_details: Connection details for the target cluster
        
        Returns:
            Dictionary of command name to command string
        """
        # Create prompt for LLM to generate Helm commands
        prompt = f"""
Generate a sequence of Helm commands to deploy a Kubernetes application with the following details:

- Repository: {repository}
- Namespace: {namespace}
- Release Name: {release_name}
- Helm Values: {json.dumps(helm_values, indent=2)}
- Cluster Details: {json.dumps(cluster_details, indent=2)}

The commands should:
1. Ensure the namespace exists
2. Add/update required Helm repositories if needed
3. Install or upgrade the Helm chart
4. Verify the deployment status

Return the commands as a JSON object with descriptive keys and commands as values. For example:
{{
  "create_namespace": "kubectl create namespace example --dry-run=client -o yaml | kubectl apply -f -",
  "add_repo": "helm repo add example https://charts.example.com/",
  "install_chart": "helm upgrade --install example-release example/chart --namespace example",
  "verify_deployment": "kubectl -n example get pods"
}}

Ensure that any connection parameters from cluster_details (like kubeconfig paths or contexts) are properly included in the commands.
"""

        try:
            # Generate commands using LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            commands_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                commands = json.loads(commands_text)
                logger.info(f"Generated commands: {commands}")
                return commands
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {commands_text}")
                # Fall back to basic commands if parsing fails
                return self._get_default_commands(repository, namespace, release_name, helm_values, cluster_details)
                
        except Exception as e:
            logger.error(f"Error generating Helm commands with LLM: {str(e)}")
            # Fall back to basic commands
            return self._get_default_commands(repository, namespace, release_name, helm_values, cluster_details)

    def _get_default_commands(self, repository: str, namespace: str, release_name: str,
                             helm_values: Dict[str, Any], cluster_details: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate default Helm commands if LLM generation fails.
        
        Args:
            Same as _generate_helm_commands
        
        Returns:
            Dictionary of command name to command string
        """
        # Build command strings
        context_part = f"--context={cluster_details['context']}" if 'context' in cluster_details else ""
        
        # Create namespace command
        create_ns_cmd = f"{self.kubectl_binary} {context_part} create namespace {namespace} --dry-run=client -o yaml | {self.kubectl_binary} apply -f -"
        
        # Handle helm values
        values_file = ""
        values_args = ""
        temp_dir = None
        
        if helm_values:
            if isinstance(helm_values, str) and os.path.isfile(helm_values):
                # If helm_values is a path to an existing file
                values_args = f"--values {helm_values}"
            else:
                # If helm_values is a dictionary or JSON string
                # Create a temporary file to store values
                if isinstance(helm_values, str):
                    try:
                        helm_values = json.loads(helm_values)
                    except json.JSONDecodeError:
                        # If not valid JSON, treat as inline values string
                        values_args = f"--set {helm_values}"
                        helm_values = {}
                
                if isinstance(helm_values, dict) and helm_values:
                    # Convert dictionary to --set arguments
                    set_args = []
                    for k, v in helm_values.items():
                        if isinstance(v, (dict, list)):
                            # For complex values, we'll use a values file
                            temp_dir = tempfile.mkdtemp()
                            values_file = os.path.join(temp_dir, 'values.yaml')
                            with open(values_file, 'w') as f:
                                json.dump(helm_values, f)
                            values_args = f"--values {values_file}"
                            break
                        else:
                            # For simple values, use --set
                            set_args.append(f"{k}={v}")
                    
                    if set_args and not values_file:
                        values_args = f"--set {','.join(set_args)}"
        
        # Build default commands
        chart_path = repository
        if '/' not in repository or 'github.com' in repository:
            # It's likely a Git repo or chart name without repo prefix
            chart_path = f"./{release_name}"
            clone_cmd = f"git clone {repository} {release_name}"
        else:
            # It's likely a repo/chart format
            clone_cmd = None
            
        # Helm install/upgrade command
        install_cmd = f"{self.helm_binary} upgrade --install {release_name} {chart_path} --namespace {namespace} {values_args} {context_part}"
        
        # Verification command
        verify_cmd = f"{self.kubectl_binary} {context_part} -n {namespace} get pods"
        
        commands = {
            "create_namespace": create_ns_cmd,
            "install_chart": install_cmd,
            "verify_deployment": verify_cmd
        }
        
        if clone_cmd:
            commands["clone_repository"] = clone_cmd
            
        return commands

    def _verify_deployment(self, namespace: str, release_name: str) -> Dict[str, Any]:
        """
        Verify that the deployment was successful.
        
        Args:
            namespace: Kubernetes namespace
            release_name: Helm release name
        
        Returns:
            Dictionary with verification status and details
        """
        try:
            # Check Helm release status
            helm_status_cmd = f"{self.helm_binary} status {release_name} -n {namespace}"
            helm_status = subprocess.check_output(helm_status_cmd, shell=True).decode()
            
            # Check pods status
            pods_cmd = f"{self.kubectl_binary} get pods -n {namespace} -l app.kubernetes.io/instance={release_name} -o json"
            pods_output = subprocess.check_output(pods_cmd, shell=True).decode()
            pods_data = json.loads(pods_output)
            
            all_pods_ready = True
            pod_statuses = []
            
            for pod in pods_data.get('items', []):
                pod_name = pod['metadata']['name']
                pod_status = pod['status']['phase']
                pod_statuses.append({"name": pod_name, "status": pod_status})
                
                if pod_status != 'Running':
                    all_pods_ready = False
            
            return {
                "status": "success" if all_pods_ready else "warning",
                "message": "All pods are running" if all_pods_ready else "Some pods are not in Running state",
                "helm_status": helm_status,
                "pods": pod_statuses
            }
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "message": f"Failed to verify deployment: {str(e)}",
                "error": e.output.decode() if e.output else str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error verifying deployment: {str(e)}"
            }