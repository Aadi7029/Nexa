from app.tasks.celery_app import celery
import logging

logger = logging.getLogger("nexa.celery.wrappers")

@celery.task(name="process_normalized_message")
def wrapper_process_normalized_message(nm_id):
    """
    Compatibility wrapper:
    - ensures the short task name 'process_normalized_message' is registered
    - tries to delegate to the real implementation if found
    - otherwise logs and returns (safe no-op)
    """
    try:
        # Try likely locations for the real function
        try:
            from app.tasks.processor import process_normalized_message as real_fn
        except Exception:
            try:
                from app.tasks.handlers import process_normalized_message as real_fn
            except Exception:
                real_fn = None

        if real_fn:
            logger.info("Delegating process_normalized_message(%s) to real implementation", nm_id)
            return real_fn(nm_id)
        else:
            logger.warning("No real process_normalized_message found; noop for id=%s", nm_id)
            return None
    except Exception as exc:
        logger.exception("Wrapper failed for process_normalized_message(%s): %s", nm_id, exc)
        raise
