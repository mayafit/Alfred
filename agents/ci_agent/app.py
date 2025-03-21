from flask import Flask, request, jsonify
from agents.utils.logger import setup_agent_logger
from repo_analyzer import RepoAnalyzer
import subprocess
import logging
import os
import json
import config

app = Flask(__name__)
logger = setup_agent_logger('ci-agent')
repo_analyzer = RepoAnalyzer(config.LLAMA_SERVER_URL)

def validate_ci_request(data):
    """
    Validate incoming CI request data
    """
    if not isinstance(data, dict):
        return False, "Invalid request format"

    if 'parameters' not in data:
        return False, "Missing parameters field"

    params = data['parameters']
    required_fields = ['repository', 'branch', 'build_steps']

    for field in required_fields:
        if field not in params:
            return False, f"Missing required field: {field}"

    if not isinstance(params['build_steps'], list):
        return False, "build_steps must be a list"

    return True, None

@app.route('/health')
def health():
    """
    Health check endpoint that also verifies access to templates and dependencies
    """
    try:
        # Check if template directory exists and contains required templates
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        required_templates = [
            "csharp_library.groovy",
            "aspnet_service.groovy",
            "node_service.groovy",
            "website.groovy"
        ]

        templates_exist = all(
            os.path.exists(os.path.join(template_dir, template))
            for template in required_templates
        )

        # Check git command availability
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            git_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            git_available = False
            logger.error("Git command not available")

        if not templates_exist:
            logger.error("Missing required Jenkins templates")
            return jsonify({
                "status": "unhealthy",
                "service": "ci-agent",
                "error": "Missing required templates"
            }), 500

        if not git_available:
            return jsonify({
                "status": "unhealthy",
                "service": "ci-agent",
                "error": "Git command not available"
            }), 500

        return jsonify({
            "status": "healthy",
            "service": "ci-agent",
            "templates_available": True,
            "git_available": True
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "service": "ci-agent",
            "error": str(e)
        }), 500

@app.route('/execute', methods=['POST'])
def execute():
    repo_path = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        # Validate request
        is_valid, error_message = validate_ci_request(data)
        if not is_valid:
            logger.error(f"Invalid request: {error_message}")
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400

        repository = data['parameters']['repository']
        branch = data['parameters']['branch']
        build_steps = data['parameters']['build_steps']

        logger.info(f"Processing CI pipeline for {repository} on branch {branch}")
        logger.debug(f"Build steps: {build_steps}")

        # Clone repository
        repo_path = repo_analyzer.clone_repository(repository, branch)
        logger.info(f"Repository cloned to {repo_path}")

        # Analyze project type
        analysis = repo_analyzer.analyze_project_type(repo_path)
        logger.info(f"Project analysis: {analysis}")

        # Generate Jenkinsfile
        repo_analyzer.generate_jenkins_file(repo_path, analysis['project_type'])
        logger.info("Generated Jenkinsfile")

        response = {
            "status": "success",
            "message": "CI pipeline created successfully",
            "details": {
                "repository": repository,
                "branch": branch,
                "project_type": analysis['project_type'],
                "confidence": analysis['confidence'],
                "build_steps": build_steps,
                "pipeline_status": "Pipeline configured and ready"
            }
        }

        logger.info(f"Successfully created CI pipeline for {repository}")
        return jsonify(response)

    except subprocess.CalledProcessError as e:
        error_msg = f"Git operation failed: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "message": error_msg,
            "details": {
                "command": e.cmd,
                "exit_code": e.returncode,
                "output": e.output.decode() if e.output else None
            }
        }), 500
    except Exception as e:
        logger.error(f"Error processing CI request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process CI request: {str(e)}"
        }), 500
    finally:
        # Cleanup
        if repo_path:
            repo_analyzer.cleanup(repo_path)

if __name__ == '__main__':
    # ALWAYS serve the CI agent on port 9001
    app.run(host='0.0.0.0', port=9001, debug=True)