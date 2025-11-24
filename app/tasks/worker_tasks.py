# app/tasks/worker_tasks.py
# import celery instance from package
from app.tasks.celery_app import celery
from app.db.session import async_session
from app.db.models import NormalizedMessage
# from services.ai_service import generate_reply_suggestions  # implement this

@celery.task(name="process_normalized_message")
def process_normalized_message(msg_id: int):
    # run async context inside sync Celery worker using trio/asyncio loop-runner if needed
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _process():
        async with async_session() as session:
            msg = await session.get(NormalizedMessage, msg_id)
            if not msg:
                return
            # Call AI service (this may be an HTTP call to your ai service)
            try:
                from app.services.ai_service import generate_reply_suggestions
            except Exception:
                async def generate_reply_suggestions(_):
                    return []

            suggestions = await generate_reply_suggestions({
                "text": msg.text,
                "sender_name": msg.sender_name,
                "platform": msg.platform,
            })
            # store suggestions in DB or in a suggestions table (omitted here)
            msg.processed = True
            session.add(msg)
            await session.commit()
    # Run the async processing in a fresh event loop to avoid conflicts
    # with Celery's process lifecycle and Windows event loop policy issues.
    def _run_coro_on_new_loop(coro):
        import asyncio, sys

        # On Windows, asyncpg/sqlalchemy async sometimes requires the
        # SelectorEventLoopPolicy; set it if available.
        if sys.platform.startswith("win"):
            policy_cls = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
            if policy_cls is not None:
                try:
                    asyncio.set_event_loop_policy(policy_cls())
                except Exception:
                    pass

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass

    _run_coro_on_new_loop(_process())
