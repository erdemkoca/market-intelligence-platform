"""Manual ingestion trigger script.

Usage:
    python -m scripts.run_ingestion zefix
"""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from src.database import async_session
from src.services.ingestion.zefix_ingestion import ZefixIngestionService


async def run_zefix():
    async with async_session() as session:
        service = ZefixIngestionService(session)
        job_id = await service.ingest()
        await session.commit()
        print(f"Ingestion completed. Job ID: {job_id}")


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "zefix"

    if source == "zefix":
        asyncio.run(run_zefix())
    else:
        print(f"Unknown source: {source}")
        print("Available sources: zefix")
        sys.exit(1)


if __name__ == "__main__":
    main()
