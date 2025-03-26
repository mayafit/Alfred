import logging
import os
import sys

def setup_agent_logger(agent_name: str):
    """
    Configure logging for agent services
    """
    logger = logging.getLogger(agent_name)
    logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'False').lower() == 'true' else logging.INFO)
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    
    return logger