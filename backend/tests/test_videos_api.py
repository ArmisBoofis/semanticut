import pytest


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
