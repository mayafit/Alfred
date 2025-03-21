import multiprocessing
import os
import sys
from logging.config import dictConfig

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

def run_main_app():
    from main import app
    app.run(host='0.0.0.0', port=5000, debug=True)

def run_ci_agent():
    from ci_agent_server import app
    app.run(host='0.0.0.0', port=9001, debug=True)

if __name__ == '__main__':
    # Create process pool
    processes = []

    # Start main application
    main_process = multiprocessing.Process(target=run_main_app)
    main_process.start()
    processes.append(main_process)

    # Start CI agent
    ci_process = multiprocessing.Process(target=run_ci_agent)
    ci_process.start()
    processes.append(ci_process)

    # Wait for all processes
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("Shutting down services...")
        for process in processes:
            process.terminate()