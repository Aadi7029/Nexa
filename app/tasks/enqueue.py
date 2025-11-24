# app/tasks/enqueue.py
from app.tasks.celery_app import celery

async def push_message_to_queue(message_id: int):
    # push to celery
    # If called from async FastAPI code, we call delay asynchronously by delegating to threadpool
    from concurrent.futures import ThreadPoolExecutor
    import asyncio
    loop = asyncio.get_running_loop()
    def _call():
        celery.send_task("process_normalized_message", args=[message_id])
    await loop.run_in_executor(None, _call)
