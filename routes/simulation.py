"""
Simulation routes for managing the simulation mode.
These routes handle enabling, disabling, and configuring the simulation mode.
"""

from flask import Blueprint, request, jsonify, render_template, current_app
import os

from services.simulator import (
    get_simulation_status, 
    start_simulation, 
    stop_simulation,
    generate_simulated_workflow,
    simulation_running
)
import config

simulation_bp = Blueprint('simulation', __name__)

@simulation_bp.route('/status', methods=['GET'])
def simulation_status():
    """Get the current status of the simulation mode"""
    status = get_simulation_status()
    return jsonify(status)

@simulation_bp.route('/toggle', methods=['POST'])
def toggle_simulation():
    """Toggle the simulation mode on or off"""
    data = request.json or {}
    enabled = data.get('enabled', None)
    
    # If enabled is explicitly set, use that value
    if enabled is not None:
        # Update environment variable
        os.environ['SIMULATION_MODE'] = str(enabled)
        
        # Update the config value
        config.SIMULATION_MODE = enabled
        
        if enabled and not simulation_running:
            start_simulation()
        elif not enabled and simulation_running:
            stop_simulation()
            
        return jsonify({
            "status": "success",
            "simulation_mode": config.SIMULATION_MODE,
            "message": f"Simulation mode {'enabled' if config.SIMULATION_MODE else 'disabled'}"
        })
    else:
        # Toggle the current value
        config.SIMULATION_MODE = not config.SIMULATION_MODE
        os.environ['SIMULATION_MODE'] = str(config.SIMULATION_MODE)
        
        if config.SIMULATION_MODE and not simulation_running:
            start_simulation()
        elif not config.SIMULATION_MODE and simulation_running:
            stop_simulation()
        
        return jsonify({
            "status": "success",
            "simulation_mode": config.SIMULATION_MODE,
            "message": f"Simulation mode {'enabled' if config.SIMULATION_MODE else 'disabled'}"
        })

@simulation_bp.route('/config', methods=['POST'])
def configure_simulation():
    """Configure simulation parameters"""
    data = request.json or {}
    
    # Update interval if provided
    if 'interval' in data:
        interval = int(data['interval'])
        if interval < 5:
            interval = 5  # Minimum interval of 5 seconds
        
        os.environ['SIMULATION_INTERVAL'] = str(interval)
        config.SIMULATION_INTERVAL = interval
    
    # Update event count if provided
    if 'event_count' in data:
        event_count = int(data['event_count'])
        if event_count < 1:
            event_count = 1  # Minimum of 1 event per cycle
        elif event_count > 10:
            event_count = 10  # Maximum of 10 events per cycle
            
        os.environ['SIMULATION_EVENT_COUNT'] = str(event_count)
        config.SIMULATION_EVENT_COUNT = event_count
    
    return jsonify({
        "status": "success",
        "message": "Simulation configuration updated",
        "config": {
            "interval": config.SIMULATION_INTERVAL,
            "event_count": config.SIMULATION_EVENT_COUNT
        }
    })

@simulation_bp.route('/trigger', methods=['POST'])
def trigger_simulation():
    """Manually trigger a simulated workflow"""
    if not config.SIMULATION_MODE:
        return jsonify({
            "status": "error",
            "message": "Simulation mode is disabled"
        }), 400
    
    # Import utils for logging
    from utils.logger import log_system_event
    
    # Generate and log a simulated workflow
    events = generate_simulated_workflow()
    
    # Log each event with application context
    with current_app.app_context():
        for event in events:
            log_system_event(
                event_type=event["event_type"],
                service=event["service"],
                description=event["description"],
                event_data=event["event_data"]
            )
    
    return jsonify({
        "status": "success",
        "message": f"Triggered simulation with {len(events)} events"
    })

def register_routes(app):
    """Register the simulation routes with the Flask app"""
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    
    # Start simulation if enabled in config
    if config.SIMULATION_MODE:
        # Use app.app_context() to ensure database access works correctly
        with app.app_context():
            start_simulation()