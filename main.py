from flask import Flask
from app import app as main_app

# Import and register dashboard and simulation routes
from routes.dashboard import register_routes as register_dashboard_routes
from routes.simulation import register_routes as register_simulation_routes

with main_app.app_context():
    # Register dashboard routes
    register_dashboard_routes(main_app)
    
    # Register simulation routes
    register_simulation_routes(main_app)

# Export the app for Gunicorn to find
app = main_app

if __name__ == "__main__":
    # Always use port 5000 for the main application
    app.run(host='0.0.0.0', port=5000, debug=True)