import mimetypes
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse, Response

from app.deps import get_db_session
from app.errors import AppError
from app.schemas.video import (
    VideoCreatedResponse,
    VideoCreateRequest,
    VideoIngestionStatusResponse,
    VideoListItem,
    VideoSearchMatchResponse,
    VideoSearchRequest,
)
from app.services.ingestion_service import get_ingestion_status_payload, resolve_video_file_path
from app.services.search_service import search_best_segment
from app.services.video_service import (
    create_video_with_job,
    delete_video,
    get_video_by_id,
    ingestion_error_code_for_video,
    ingestion_error_message_for_video,
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


@router.get(
    "/videos/{video_id}/file",
    response_class=FileResponse,
)
async def get_video_file(
    video_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Stream the registered video file for browser playback (local/demo)."""
    video = await get_video_by_id(session, video_id)
    path = resolve_video_file_path(video.storage_path)
    if not path.is_file():
        raise AppError("NOT_FOUND", "fichier vidéo introuvable", 404)
    media_type, _ = mimetypes.guess_type(str(path))
    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        filename=f"{video.label}{path.suffix}",
    )


@router.post(
    "/videos/{video_id}/search",
    response_model=VideoSearchMatchResponse,
)
async def search_video(
    video_id: UUID,
    body: VideoSearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VideoSearchMatchResponse:
    """Return the best-matching transcript segment for a natural-language query."""
    return await search_best_segment(session, video_id, body.query)


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
            error_code=ingestion_error_code_for_video(v),
            error_message=ingestion_error_message_for_video(v),
            created_at=v.created_at,
        )
        for v in rows
    ]
