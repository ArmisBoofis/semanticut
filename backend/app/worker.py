"""Background ingestion worker: polls for pending jobs and runs the pipeline."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import update

from app.db import async_session_maker
from app.models.video import IngestionJob
from app.services.ingestion_service import claim_next_pending_job, run_ingestion_for_job

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2.0


async def worker_loop() -> None:
    while True:
        try:
            async with async_session_maker() as session:
                async with session.begin():
                    claimed = await claim_next_pending_job(session)
            if claimed is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            job_id, video_id = claimed
            try:
                await run_ingestion_for_job(job_id, video_id)
            except Exception as exc:
                logger.exception("ingestion failed for job %s: %s", job_id, exc)
                async with async_session_maker() as session:
                    await session.execute(
                        update(IngestionJob)
                        .where(IngestionJob.id == job_id)
                        .values(
                            status=IngestionJob.STATUS_FAILED,
                            error_code="INTERNAL_ERROR",
                            error_message="Unexpected ingestion error. Check server logs.",
                        )
                    )
                    await session.commit()
        except Exception:
            logger.exception("worker iteration failed")
            await asyncio.sleep(5.0)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
