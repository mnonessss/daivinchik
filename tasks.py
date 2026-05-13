import asyncio
import concurrent.futures

from sqlalchemy import select

from celery_app import celery_app
from database import async_session_maker
from models import Users
from ranking.service import recalculate_user_ranking, warmup_feed_cache


def _run_async(coro):
    """Run async code from sync Celery tasks (works under eager mode inside ASGI loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


async def _recalculate_all_rankings_impl():
    async with async_session_maker() as db:
        user_ids = (
            await db.execute(select(Users.id))
        ).scalars().all()
        for user_id in user_ids:
            await recalculate_user_ranking(db, user_id)
            await warmup_feed_cache(db, user_id)
    return len(user_ids)


@celery_app.task(name="tasks.recalculate_all_rankings")
def recalculate_all_rankings():
    return _run_async(_recalculate_all_rankings_impl())


@celery_app.task(name="tasks.recalculate_user_ranking")
def recalculate_user_ranking_task(user_id):
    async def _run():
        async with async_session_maker() as db:
            ranking = await recalculate_user_ranking(db, user_id)
            await warmup_feed_cache(db, user_id)
            return ranking.final_score if ranking else None

    return _run_async(_run())
