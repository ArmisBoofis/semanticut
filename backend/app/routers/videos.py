from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.schemas.video import VideoCreatedResponse, VideoCreateRequest, VideoListItem
from app.services.video_service import (
    create_video_with_job,
    ingestion_phase_for_video,
    ingestion_progress_percent_for_video,
    ingestion_status_for_video,
    list_videos,
)

router = APIRouter(tags=["videos"])


@router.post(
    "/videos",
    response_model=VideoCreatedResponse,
    status_code=201,
)
async def register_video(
    body: VideoCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VideoCreatedResponse:
    video = await create_video_with_job(
        session,
        label=body.label,
        storage_path=body.storage_path,
    )
    await session.commit()
    return VideoCreatedResponse(
        id=video.id,
        label=video.label,
        storage_path=video.storage_path,
        ingestion_status=ingestion_status_for_video(video),
        created_at=video.created_at,
    )


@router.get("/videos", response_model=list[VideoListItem])
async def get_videos(
    session: AsyncSession = Depends(get_db_session),
) -> list[VideoListItem]:
    rows = await list_videos(session)
    return [
        VideoListItem(
            id=v.id,
            label=v.label,
            ingestion_status=ingestion_status_for_video(v),
            ingestion_phase=ingestion_phase_for_video(v),
            ingestion_progress_percent=ingestion_progress_percent_for_video(v),
            created_at=v.created_at,
        )
        for v in rows
    ]
