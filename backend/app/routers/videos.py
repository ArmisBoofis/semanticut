from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.deps import get_db_session
from app.errors import AppError
from app.schemas.video import (
    VideoCreatedResponse,
    VideoCreateRequest,
    VideoIngestionStatusResponse,
    VideoListItem,
)
from app.services.ingestion_service import get_ingestion_status_payload
from app.services.video_service import (
    create_video_with_job,
    delete_video,
    ingestion_phase_for_video,
    ingestion_progress_percent_for_video,
    ingestion_status_for_video,
    list_videos,
    register_video_from_upload,
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


@router.post(
    "/videos/upload",
    response_model=VideoCreatedResponse,
    status_code=201,
)
async def register_video_upload(
    session: AsyncSession = Depends(get_db_session),
    label: str = Form(...),
    file: UploadFile = File(...),
) -> VideoCreatedResponse:
    """Multipart registration: saves under VIDEO_STORAGE_ROOT/uploads and registers like POST /videos."""
    video = await register_video_from_upload(session, label=label, file=file)
    await session.commit()
    return VideoCreatedResponse(
        id=video.id,
        label=video.label,
        storage_path=video.storage_path,
        ingestion_status=ingestion_status_for_video(video),
        created_at=video.created_at,
    )


@router.delete(
    "/videos/{video_id}",
    status_code=204,
    response_class=Response,
)
async def remove_video(
    video_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await delete_video(session, video_id=video_id)
    await session.commit()
    return Response(status_code=204)


@router.get(
    "/videos/{video_id}/status",
    response_model=VideoIngestionStatusResponse,
)
async def get_video_ingestion_status(
    video_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> VideoIngestionStatusResponse:
    payload = await get_ingestion_status_payload(session, video_id)
    if payload is None:
        raise AppError("NOT_FOUND", "video not found", 404)
    return VideoIngestionStatusResponse(**payload)


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
