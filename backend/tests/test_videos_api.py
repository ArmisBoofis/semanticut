import uuid
from uuid import UUID

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.video import IngestionJob, Video


async def test_post_and_get_videos_happy_path(video_client):
    create = await video_client.post(
        "/videos",
        json={"label": "Interview A", "storage_path": "/data/videos/demo.mp4"},
    )
    assert create.status_code == 201
    body = create.json()
    assert body["label"] == "Interview A"
    assert body["storage_path"] == "/data/videos/demo.mp4"
    assert body["ingestion_status"] == "pending"
    assert "id" in body
    assert "created_at" in body

    listed = await video_client.get("/videos")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == body["id"]
    assert items[0]["label"] == "Interview A"
    assert items[0]["ingestion_status"] == "pending"
    assert items[0]["ingestion_phase"] is None
    assert items[0]["ingestion_progress_percent"] is None
    assert items[0]["error_code"] is None
    assert items[0]["error_message"] is None


async def test_get_videos_includes_phase_and_progress_when_set(video_client, video_engine):
    create = await video_client.post(
        "/videos",
        json={"label": "Interview B", "storage_path": "/data/videos/demo.mp4"},
    )
    assert create.status_code == 201
    body = create.json()
    video_id = UUID(body["id"])

    async_session = async_sessionmaker(
        video_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        await session.execute(
            update(IngestionJob)
            .where(IngestionJob.video_id == video_id)
            .values(phase="transcoding", progress_percent=42),
        )
        await session.commit()

    listed = await video_client.get("/videos")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["ingestion_phase"] == "transcoding"
    assert items[0]["ingestion_progress_percent"] == 42
    assert items[0]["error_code"] is None
    assert items[0]["error_message"] is None


async def test_get_videos_includes_failed_error_details(
    video_client,
    video_engine,
):
    create = await video_client.post(
        "/videos",
        json={"label": "Interview C", "storage_path": "/data/videos/demo.mp4"},
    )
    assert create.status_code == 201
    body = create.json()
    video_id = UUID(body["id"])

    async_session = async_sessionmaker(
        video_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        await session.execute(
            update(IngestionJob)
            .where(IngestionJob.video_id == video_id)
            .values(
                status="failed",
                phase="transcribing",
                progress_percent=55,
                error_code="TRANSCRIPTION_FAILED",
                error_message="transcription layer crashed",
            ),
        )
        await session.commit()

    listed = await video_client.get("/videos")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["ingestion_status"] == "failed"
    assert items[0]["ingestion_phase"] == "transcribing"
    assert items[0]["ingestion_progress_percent"] == 55
    assert items[0]["error_code"] == "TRANSCRIPTION_FAILED"
    assert items[0]["error_message"] == "transcription layer crashed"


async def test_post_videos_validation_error_shape(video_client):
    r = await video_client.post("/videos", json={})
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "message" in err


async def test_post_videos_domain_error_unsupported_media(video_client):
    r = await video_client.post(
        "/videos",
        json={"label": "x", "storage_path": "/data/x.txt"},
    )
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "UNSUPPORTED_MEDIA"
    assert "message" in err


async def test_delete_video_happy_path_removes_video_and_job(video_client, video_engine):
    create = await video_client.post(
        "/videos",
        json={"label": "Interview A", "storage_path": "/data/videos/demo.mp4"},
    )
    assert create.status_code == 201
    video_id = create.json()["id"]

    async_session = async_sessionmaker(
        video_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        n_jobs = await session.scalar(select(func.count()).select_from(IngestionJob))
        assert n_jobs == 1

    delete = await video_client.delete(f"/videos/{video_id}")
    assert delete.status_code == 204
    assert delete.content == b""

    listed = await video_client.get("/videos")
    assert listed.status_code == 200
    assert listed.json() == []

    async with async_session() as session:
        n_jobs = await session.scalar(select(func.count()).select_from(IngestionJob))
        assert n_jobs == 0
        n_videos = await session.scalar(select(func.count()).select_from(Video))
        assert n_videos == 0


async def test_delete_video_succeeds_while_job_running(video_client, video_engine):
    create = await video_client.post(
        "/videos",
        json={"label": "Interview A", "storage_path": "/data/videos/demo.mp4"},
    )
    assert create.status_code == 201
    video_id = UUID(create.json()["id"])

    async_session = async_sessionmaker(
        video_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        await session.execute(
            update(IngestionJob)
            .where(IngestionJob.video_id == video_id)
            .values(status="running"),
        )
        await session.commit()

    delete = await video_client.delete(f"/videos/{video_id}")
    assert delete.status_code == 204


async def test_delete_video_unknown_id_returns_404(video_client):
    unknown = str(uuid.uuid4())
    r = await video_client.delete(f"/videos/{unknown}")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert "message" in err


async def test_delete_video_malformed_uuid_returns_400(video_client):
    r = await video_client.delete("/videos/not-a-uuid")
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "message" in err


async def test_get_video_status_happy_path(video_client):
    create = await video_client.post(
        "/videos",
        json={"label": "Interview A", "storage_path": "/data/videos/demo.mp4"},
    )
    assert create.status_code == 201
    body = create.json()
    video_id = body["id"]

    r = await video_client.get(f"/videos/{video_id}/status")
    assert r.status_code == 200
    st = r.json()
    assert st["video_id"] == video_id
    assert st["status"] == "pending"
    assert "job_id" in st
    assert st["phase"] is None
    assert st["progress_percent"] is None
    assert st["error_code"] is None
    assert st["error_message"] is None
    assert "created_at" in st
    assert "updated_at" in st


async def test_get_video_status_unknown_id_returns_404(video_client):
    unknown = str(uuid.uuid4())
    r = await video_client.get(f"/videos/{unknown}/status")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_FOUND"


async def test_get_video_status_malformed_uuid_returns_400(video_client):
    r = await video_client.get("/videos/not-a-uuid/status")
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"


async def test_post_upload_video_happy_path(video_client, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "video_storage_root", str(tmp_path))

    create = await video_client.post(
        "/videos/upload",
        data={"label": "Upload A"},
        files={"file": ("clip.mp4", b"not-real-video-bytes", "video/mp4")},
    )
    assert create.status_code == 201
    body = create.json()
    assert body["label"] == "Upload A"
    assert body["storage_path"].startswith("uploads/")
    assert body["storage_path"].endswith(".mp4")
    assert body["ingestion_status"] == "pending"
    assert "id" in body
    assert "created_at" in body

    rel = body["storage_path"]
    disk = tmp_path.joinpath(*rel.split("/"))
    assert disk.is_file()
    assert disk.read_bytes() == b"not-real-video-bytes"


async def test_post_upload_video_rejects_bad_extension(video_client, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "video_storage_root", str(tmp_path))

    r = await video_client.post(
        "/videos/upload",
        data={"label": "x"},
        files={"file": ("clip.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "UNSUPPORTED_MEDIA"
    assert "message" in err


async def test_post_upload_video_rejects_oversize(video_client, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "video_storage_root", str(tmp_path))
    monkeypatch.setattr(settings, "video_upload_max_bytes", 10)

    r = await video_client.post(
        "/videos/upload",
        data={"label": "x"},
        files={"file": ("clip.mp4", b"x" * 20, "video/mp4")},
    )
    assert r.status_code == 413
    err = r.json()["error"]
    assert err["code"] == "PAYLOAD_TOO_LARGE"
    assert "message" in err
