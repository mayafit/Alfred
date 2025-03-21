import logging
import sys

def setup_agent_logger(agent_name: str):
    """
    Configure logging for agent services
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(agent_name)
