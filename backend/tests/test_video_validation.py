import pytest

from app.errors import AppError
from app.services.video_service import validate_registration


def test_validate_registration_accepts_minimal_mp4_path():
    label, path = validate_registration("Interview A", "/data/videos/demo.mp4")
    assert label == "Interview A"
    assert path == "/data/videos/demo.mp4"


def test_validate_registration_trims_whitespace():
    label, path = validate_registration("  x  ", "  /a/b.mp4  ")
    assert label == "x"
    assert path == "/a/b.mp4"


def test_validate_registration_rejects_empty_label():
    with pytest.raises(AppError) as exc:
        validate_registration("   ", "/a/b.mp4")
    assert exc.value.code == "VALIDATION_ERROR"


def test_validate_registration_rejects_unsupported_extension():
    with pytest.raises(AppError) as exc:
        validate_registration("x", "/a/b.txt")
    assert exc.value.code == "UNSUPPORTED_MEDIA"


def test_validate_registration_rejects_parent_dir_segments():
    with pytest.raises(AppError) as exc:
        validate_registration("x", "/data/../secret.mp4")
    assert exc.value.code == "INVALID_STORAGE_PATH"
