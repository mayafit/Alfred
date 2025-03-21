# DevOps Automation Agents

This directory contains three specialized agents for handling different DevOps tasks:

## CI Agent (Port 9001)
Handles continuous integration pipeline setup and configuration:
- Repository setup
- Build step configuration
- Branch management

## Helm Agent (Port 9002)
Manages Helm chart creation and updates:
- Chart template generation
- Service configuration
- Environment variable management

## Deploy Agent (Port 9003)
Handles cluster deployments:
- Namespace management
- Deployment configuration
- Service status monitoring

## API Endpoints

Each agent provides two endpoints:

### Health Check
- **GET** `/health`
- Returns service health status

### Task Execution
- **POST** `/execute`
- Accepts task-specific JSON payloads
- Returns execution results

## Example Payloads

### CI Agent
```json
{
  "parameters": {
    "repository": "git@github.com:org/service.git",
    "branch": "main",
    "build_steps": ["test", "lint", "build"]
  }
}
```

### Helm Agent
```json
{
  "parameters": {
    "repository": "git@github.com:org/service.git",
    "service_ports": [80, 443],
    "environment_variables": {
      "NODE_ENV": "production",
      "PORT": "8080"
    }
  }
}
```

### Deploy Agent
```json
{
  "parameters": {
    "repository": "git@github.com:org/service.git",
    "namespace": "production"
  }
}
```

## Development

To run the agents locally:

1. Install dependencies:
```bash
pip install flask requests
```

2. Start each agent:
```bash
python ci_agent/app.py
python helm_agent/app.py
python deploy_agent/app.py
```

The agents will be available at their respective ports (9001, 9002, 9003).
