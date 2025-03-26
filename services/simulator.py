"""
Simulator module for generating random events and tasks for demonstration purposes.
This module is used when the application is in simulation mode to generate realistic
looking data for the dashboard.
"""

import random
import time
import threading
import string
from datetime import datetime, timedelta
import uuid
import json
import requests

from utils.logger import logger, log_system_event
from models import db, TaskHistory, SystemMetrics
import config

# Global flags and variables to control the simulation
simulation_running = False
simulation_thread = None
simulation_jira_thread = None
last_jira_event_time = 0

# List of repositories for random selection
SAMPLE_REPOSITORIES = [
    "https://github.com/acme/frontend-app",
    "https://github.com/acme/backend-api",
    "https://github.com/acme/data-service",
    "https://github.com/acme/auth-service",
    "https://github.com/acme/message-queue",
    "https://github.com/acme/notification-service",
    "https://github.com/acme/monitoring-service",
    "https://github.com/acme/reporting-engine",
    "https://github.com/acme/user-service",
    "https://github.com/acme/payment-processor",
]

# Task types
TASK_TYPES = ["ci", "helm", "deploy"]

# Event types for system events
EVENT_TYPES = [
    "task_received", 
    "ai_analysis", 
    "agent_triggered", 
    "task_completed", 
    "error", 
    "warning"
]

# Services
SERVICES = ["main", "ci_agent", "helm_agent", "deploy_agent"]

# Description templates
TASK_DESCRIPTIONS = [
    "Create CI pipeline for {repo}",
    "Deploy {repo} to production",
    "Generate Helm charts for {repo}",
    "Update kubernetes configuration for {repo}",
    "Create build process for {repo}",
    "Setup monitoring for {repo}",
    "Configure autoscaling for {repo}",
    "Setup load balancing for {repo}",
    "Configure CI/CD pipeline for {repo}",
    "Implement deployment strategy for {repo}"
]

ERROR_MESSAGES = [
    "Failed to connect to repository: {repo}",
    "Invalid configuration in {repo}",
    "Build failed for {repo}",
    "Deployment error for {repo}",
    "Missing dependencies in {repo}",
    "Repository {repo} access denied",
    "Failed to authenticate with {repo}",
    "Timeout waiting for {repo} build",
    "Invalid Helm chart configuration for {repo}",
    "Kubernetes cluster unreachable during {repo} deployment"
]

SUCCESS_MESSAGES = [
    "Successfully deployed {repo}",
    "CI pipeline created for {repo}",
    "Helm charts generated for {repo}",
    "Kubernetes configuration updated for {repo}",
    "Build process configured for {repo}",
    "Monitoring setup completed for {repo}",
    "Autoscaling configured for {repo}",
    "Load balancing setup for {repo}",
    "CI/CD pipeline implemented for {repo}",
    "Deployment strategy configured for {repo}"
]

def generate_random_id():
    """Generate a random ID for simulated tasks"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_random_repo():
    """Select a random repository from the sample list"""
    return random.choice(SAMPLE_REPOSITORIES)

def generate_random_task_type():
    """Select a random task type"""
    return random.choice(TASK_TYPES)

def generate_random_service():
    """Select a random service"""
    return random.choice(SERVICES)

def generate_random_timestamp(min_days=0, max_days=7):
    """Generate a random timestamp within the past week"""
    days_ago = random.uniform(min_days, max_days)
    return datetime.utcnow() - timedelta(days=days_ago)

def generate_simulated_task_history(count=5):
    """Generate a list of simulated task history records"""
    tasks = []
    
    for _ in range(count):
        repo = generate_random_repo()
        task_type = generate_random_task_type()
        created_at = generate_random_timestamp()
        
        # Determine if the task should be completed or still running
        is_completed = random.random() > 0.2  # 80% chance of being completed
        
        if is_completed:
            completed_at = created_at + timedelta(minutes=random.uniform(5, 30))
            status = 'completed' if random.random() > 0.3 else 'failed'  # 70% success rate
        else:
            completed_at = None
            status = 'running'
        
        # Generate appropriate details
        if status == 'completed':
            details = {
                'message': random.choice(SUCCESS_MESSAGES).format(repo=repo.split('/')[-1]),
                'commit_id': ''.join(random.choices(string.hexdigits.lower(), k=40)),
                'build_number': random.randint(100, 999)
            }
        elif status == 'failed':
            details = {
                'error': random.choice(ERROR_MESSAGES).format(repo=repo.split('/')[-1]),
                'error_code': random.randint(1, 100),
                'failed_step': random.choice(['clone', 'build', 'test', 'deploy']),
                'logs_url': f"https://logs.example.com/{generate_random_id()}"
            }
        else:  # running
            details = {
                'status': 'in_progress',
                'current_step': random.choice(['clone', 'build', 'test', 'deploy']),
                'progress': random.randint(10, 90),
                'started_by': f"user_{random.randint(1000, 9999)}"
            }
            
        task = TaskHistory(
            task_type=task_type,
            repository=repo,
            status=status,
            details=details,
            created_at=created_at,
            completed_at=completed_at
        )
        tasks.append(task)
    
    return tasks

def generate_system_event(event_type=None, service=None):
    """Generate a simulated system event"""
    if not event_type:
        event_type = random.choice(EVENT_TYPES)
    
    if not service:
        service = random.choice(SERVICES)
    
    repo = generate_random_repo().split('/')[-1]
    
    # Create event description based on event type
    if event_type == "task_received":
        description = f"Received task request for {repo}"
        event_data = {
            "repository": repo,
            "endpoint": "/webhook/jira" if random.random() > 0.5 else "/test/analyze",
            "method": "POST"
        }
    elif event_type == "ai_analysis":
        description = f"Analyzing task description for {repo}"
        event_data = {
            "repository": repo,
            "description_length": random.randint(100, 1000)
        }
    elif event_type == "agent_triggered":
        task_count = random.randint(1, 3)
        task_types = random.sample(TASK_TYPES, k=min(task_count, len(TASK_TYPES)))
        description = f"Processing {task_count} tasks for {repo}"
        event_data = {
            "repository": repo,
            "task_count": task_count,
            "task_types": task_types
        }
    elif event_type == "task_completed":
        success_count = random.randint(0, 3)
        failed_count = random.randint(0, 2)
        
        # If there are failed tasks, add failure details
        if failed_count > 0:
            failure_details = []
            for _ in range(failed_count):
                task_type = random.choice(TASK_TYPES)
                error = random.choice(ERROR_MESSAGES).format(repo=repo)
                failure_details.append({"task_type": task_type, "error": error})
            
            task_error_descriptions = [f"{detail['task_type']}: {detail['error']}" for detail in failure_details]
            description = f"Task processing complete. Success: {success_count}, Failed: {failed_count}. Failures: {', '.join(task_error_descriptions)}"
            
            event_data = {
                "repository": repo,
                "success_count": success_count,
                "failed_count": failed_count,
                "failure_details": failure_details
            }
        else:
            description = f"Task processing complete. Success: {success_count}, Failed: {failed_count}"
            event_data = {
                "repository": repo,
                "success_count": success_count,
                "failed_count": failed_count
            }
    elif event_type == "error":
        error_msg = random.choice(ERROR_MESSAGES).format(repo=repo)
        description = f"Error: {error_msg}"
        event_data = {
            "repository": repo,
            "error": error_msg,
            "error_code": random.randint(400, 599)
        }
    elif event_type == "warning":
        description = f"Warning: Potential issue with {repo}"
        event_data = {
            "repository": repo,
            "warning_level": random.choice(["low", "medium", "high"]),
            "component": random.choice(["database", "network", "storage", "compute"])
        }
    else:
        description = f"Event related to {repo}"
        event_data = {"repository": repo}
    
    return {
        "event_type": event_type,
        "service": service,
        "description": description,
        "event_data": event_data
    }

def generate_system_metrics():
    """Generate simulated system metrics"""
    metrics = []
    
    # Generate metrics for each service
    for service in SERVICES:
        # Status is mostly healthy with occasional issues
        status = "healthy" if random.random() > 0.1 else "degraded"
        
        # Response time varies between 50-500ms, higher for degraded services
        base_response_time = random.uniform(50, 200)
        if status == "degraded":
            base_response_time *= 2
        
        # Error count is usually low, higher for degraded services
        error_count = 0 if status == "healthy" else random.randint(1, 10)
        
        metric = SystemMetrics(
            service_name=service,
            status=status,
            response_time=base_response_time,
            error_count=error_count
        )
        metrics.append(metric)
    
    return metrics

def simulate_cycle():
    """Run a single simulation cycle, generating events and tasks"""
    logger.info("Running simulation cycle")
    
    try:
        # Generate and store task history
        if random.random() > 0.7:  # 30% chance of new task history
            tasks = generate_simulated_task_history(count=random.randint(1, 3))
            for task in tasks:
                db.session.add(task)
        
        # Generate and store system metrics
        metrics = generate_system_metrics()
        for metric in metrics:
            db.session.add(metric)
        
        # Commit the changes
        db.session.commit()
    except Exception as e:
        logger.error(f"Error in simulation - storing DB records: {str(e)}")
    
    # Generate system events
    event_count = random.randint(1, config.SIMULATION_EVENT_COUNT)
    for _ in range(event_count):
        try:
            event = generate_system_event()
            log_system_event(
                event_type=event["event_type"],
                service=event["service"],
                description=event["description"],
                event_data=event["event_data"]
            )
        except Exception as e:
            logger.error(f"Error in simulation - generating event: {str(e)}")
    
    logger.info(f"Simulation cycle completed - generated {event_count} events")

def simulation_loop():
    """Main simulation loop that runs in a separate thread"""
    global simulation_running
    
    # Import app here to avoid circular imports
    from app import app
    
    logger.info("Starting simulation loop")
    
    while simulation_running:
        try:
            # Use app context for database operations
            with app.app_context():
                simulate_cycle()
            time.sleep(config.SIMULATION_INTERVAL)
        except Exception as e:
            logger.error(f"Error in simulation loop: {str(e)}")
            # Add a short sleep to prevent tight loops in case of error
            time.sleep(5)
    
    logger.info("Simulation loop stopped")

def simulate_jira_webhook():
    """Send a simulated Jira webhook to the application"""
    try:
        webhook_payload = generate_simulated_jira_webhook()
        
        # Make the request to the Jira webhook endpoint
        response = requests.post(
            f"{config.MAIN_SERVICE_URL}/webhook/jira",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully sent simulated Jira webhook: {webhook_payload['issue']['key']}")
            return True
        else:
            logger.error(f"Failed to send Jira webhook. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending simulated Jira webhook: {str(e)}")
        return False

def jira_webhook_loop():
    """Main loop for sending Jira webhook events"""
    global simulation_running, last_jira_event_time
    
    # Import app here to avoid circular imports
    from app import app
    
    logger.info("Starting Jira webhook simulation loop")
    
    while simulation_running:
        try:
            # Check if it's time to send a Jira webhook
            current_time = time.time()
            if current_time - last_jira_event_time >= config.SIMULATION_JIRA_INTERVAL:
                # Use app context for making requests
                with app.app_context():
                    simulate_jira_webhook()
                last_jira_event_time = current_time
            
            # Sleep for a short time to avoid tight loops
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in Jira webhook loop: {str(e)}")
            # Add a short sleep to prevent tight loops in case of error
            time.sleep(5)
    
    logger.info("Jira webhook simulation loop stopped")

def start_simulation():
    """Start the simulation threads"""
    global simulation_running, simulation_thread, simulation_jira_thread, last_jira_event_time
    
    if (simulation_thread and simulation_thread.is_alive()) or (simulation_jira_thread and simulation_jira_thread.is_alive()):
        logger.warning("Simulation already running")
        return False
    
    simulation_running = True
    last_jira_event_time = time.time()  # Reset the last event time
    
    # Start the regular simulation thread
    simulation_thread = threading.Thread(target=simulation_loop, daemon=True)
    simulation_thread.start()
    
    # Start the Jira webhook simulation thread if enabled
    if config.SIMULATION_JIRA_EVENTS:
        simulation_jira_thread = threading.Thread(target=jira_webhook_loop, daemon=True)
        simulation_jira_thread.start()
        logger.info("Jira webhook simulation started")
    
    logger.info("Simulation started")
    return True

def stop_simulation():
    """Stop the simulation threads"""
    global simulation_running
    
    simulation_running = False
    logger.info("Simulation stopping (may take a few seconds to complete)")
    return True

def get_simulation_status():
    """Get the current status of the simulation"""
    global simulation_thread, simulation_jira_thread, simulation_running
    
    is_running = simulation_thread is not None and simulation_thread.is_alive()
    jira_running = simulation_jira_thread is not None and simulation_jira_thread.is_alive()
    
    return {
        "enabled": config.SIMULATION_MODE,
        "running": is_running,
        "interval": config.SIMULATION_INTERVAL,
        "event_count": config.SIMULATION_EVENT_COUNT,
        "jira_events_enabled": config.SIMULATION_JIRA_EVENTS,
        "jira_events_running": jira_running,
        "jira_interval": config.SIMULATION_JIRA_INTERVAL
    }

def generate_simulated_jira_webhook():
    """Generate a simulated Jira webhook payload"""
    repo = generate_random_repo()
    repo_name = repo.split('/')[-1]
    issue_key = f"DEVOPS-{random.randint(100, 999)}"
    
    # Generate a random task description for the repository
    task_description = random.choice(TASK_DESCRIPTIONS).format(repo=repo_name)
    
    # Add details about what needs to be done
    build_steps = []
    if random.random() > 0.5:
        build_steps.append("npm install")
    if random.random() > 0.3:
        build_steps.append("npm test")
    build_steps.append("npm build")
    
    service_ports = [{"port": random.randint(3000, 9000), "targetPort": random.randint(3000, 9000)}]
    
    env_vars = {
        "NODE_ENV": random.choice(["development", "production", "staging"]),
        "LOG_LEVEL": random.choice(["debug", "info", "warn", "error"]),
        "DB_HOST": "db.example.com",
        "CACHE_ENABLED": "true" if random.random() > 0.5 else "false"
    }
    
    # Add detailed instructions in a format that would be recognized by the AI parser
    detailed_instructions = f"""
# DevOps Task Request

## Repository Information
- URL: {repo}
- Branch: main

## Task Details
Please complete the following DevOps tasks:

1. Create a CI pipeline for the repository
   - Use the following build steps: {', '.join(build_steps)}
   - Set up unit and integration tests

2. Generate Helm charts for deployment
   - Service ports: {service_ports[0]['port']}:{service_ports[0]['targetPort']}
   - Environment variables:
     - NODE_ENV: {env_vars['NODE_ENV']}
     - LOG_LEVEL: {env_vars['LOG_LEVEL']}
     - DB_HOST: {env_vars['DB_HOST']}
     - CACHE_ENABLED: {env_vars['CACHE_ENABLED']}

3. Deploy to Kubernetes cluster
   - Namespace: {repo_name}-{env_vars['NODE_ENV']}
   - Use rolling update strategy
   - Set resource limits appropriately

Please notify when these tasks are completed.
"""
    
    # Create the full webhook payload
    webhook_payload = {
        "webhook_event": "issue_created",
        "issue": {
            "key": issue_key,
            "fields": {
                "summary": task_description,
                "description": detailed_instructions,
                "customfield_team": "DevOps",
                "labels": ["devops", "automation"],
                "status": {
                    "name": "Open",
                    "id": "1"
                },
                "priority": {
                    "name": "Medium",
                    "id": "3"
                },
                "reporter": {
                    "name": f"user_{random.randint(1000, 9999)}",
                    "email": "user@example.com"
                }
            }
        },
        "user": {
            "name": f"user_{random.randint(1000, 9999)}",
            "email": "user@example.com"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return webhook_payload

def generate_simulated_workflow():
    """Generate a simulated workflow including all stages of a task"""
    repo = generate_random_repo()
    task_type = generate_random_task_type()
    repo_name = repo.split('/')[-1]
    events = []
    
    # 1. Task received
    events.append(generate_system_event(
        event_type="task_received",
        service="main"
    ))
    
    # 2. AI analysis
    events.append(generate_system_event(
        event_type="ai_analysis",
        service="main"
    ))
    
    # 3. Agent triggered
    events.append(generate_system_event(
        event_type="agent_triggered",
        service="main"
    ))
    
    # 4. Task completion (success or failure)
    success = random.random() > 0.3  # 70% success rate
    if success:
        events.append(generate_system_event(
            event_type="task_completed",
            service="main"
        ))
    else:
        # Generate failure event
        failure_event = generate_system_event(
            event_type="task_completed",
            service="main"
        )
        # Ensure it has failure details
        if "failure_details" not in failure_event["event_data"]:
            task_type = random.choice(TASK_TYPES)
            error = random.choice(ERROR_MESSAGES).format(repo=repo_name)
            failure_event["event_data"]["failed_count"] = 1
            failure_event["event_data"]["success_count"] = 0
            failure_event["event_data"]["failure_details"] = [
                {"task_type": task_type, "error": error}
            ]
            failure_event["description"] = f"Task processing complete. Success: 0, Failed: 1. Failures: {task_type}: {error}"
        
        events.append(failure_event)
        
        # Add an error event too
        events.append(generate_system_event(
            event_type="error",
            service=task_type + "_agent"
        ))
    
    return events