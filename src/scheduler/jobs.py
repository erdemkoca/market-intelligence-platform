import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session
from src.services.ingestion.zefix_ingestion import ZefixIngestionService
from src.services.scoring.lead_scorer import LeadScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_zefix_ingestion():
    """Daily Zefix ingestion job."""
    logger.info("Starting scheduled Zefix ingestion...")
    async with async_session() as session:
        try:
            service = ZefixIngestionService(session)
            job_id = await service.ingest()
            await session.commit()
            logger.info(f"Scheduled Zefix ingestion completed: {job_id}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Scheduled Zefix ingestion failed: {e}", exc_info=True)


async def run_lead_scoring():
    """Daily lead scoring job."""
    logger.info("Starting scheduled lead scoring...")
    async with async_session() as session:
        try:
            scorer = LeadScorer(session)
            count = await scorer.score_all()
            await session.commit()
            logger.info(f"Scheduled lead scoring completed: {count} leads scored")
        except Exception as e:
            await session.rollback()
            logger.error(f"Scheduled lead scoring failed: {e}", exc_info=True)


def main():
    scheduler = AsyncIOScheduler()

    # Zefix ingestion: daily at 05:00
    scheduler.add_job(run_zefix_ingestion, "cron", hour=5, minute=0, id="zefix_daily")

    # Lead scoring: daily at 08:00
    scheduler.add_job(run_lead_scoring, "cron", hour=8, minute=0, id="scoring_daily")

    scheduler.start()
    logger.info("Scheduler started. Jobs: zefix_daily (05:00), scoring_daily (08:00)")

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
