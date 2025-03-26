import logging
import sys
import traceback

def setup_logger():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

def log_system_event(event_type, service, description, event_data=None):
    """
    Log a system event to the database.
    
    Args:
        event_type (str): Type of event (task_received, ai_analysis, agent_triggered, etc.)
        service (str): Service that generated the event (main, ci_agent, etc.)
        description (str): Detailed description of the event
        event_data (dict, optional): Additional data related to the event
    
    Returns:
        SystemEvent: The created system event object
    """
    # Import here to avoid circular imports
    from app import db
    from models import SystemEvent
    
    try:
        # Create a new system event
        event = SystemEvent(
            event_type=event_type,
            service=service,
            description=description,
            event_data=event_data or {}
        )
        
        # Add to database
        db.session.add(event)
        db.session.commit()
        
        # Also log to the console
        logger.info(f"SYSTEM EVENT [{service}] {event_type}: {description}")
        
        return event
    except Exception as e:
        logger.error(f"Failed to log system event: {str(e)}")
        logger.error(traceback.format_exc())
        # Make sure the session is clean
        try:
            db.session.rollback()
        except:
            pass
        return None
