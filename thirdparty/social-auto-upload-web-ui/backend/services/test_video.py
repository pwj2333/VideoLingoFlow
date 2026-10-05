"""Optional test-video lookup used by platform smoke-test endpoints."""
from pathlib import Path


def get_test_video() -> str | None:
    """Return a bundled test video when present; publishing does not require one."""
    candidates = [
        Path(__file__).resolve().parents[1] / "test_video.mp4",
        Path(__file__).resolve().parents[2] / "data" / "test_video.mp4",
    ]
    return next((str(path) for path in candidates if path.is_file()), None)
