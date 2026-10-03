import base64
import sys
from types import SimpleNamespace

from reloved_engine.image_generator import generate_images


def test_generates_three_images_and_reuses_them_across_six_slides(tmp_path, monkeypatch):
    calls = []

    class FakeImages:
        def generate(self, **kwargs):
            calls.append(kwargs)
            encoded = base64.b64encode(f"image-{len(calls)}".encode()).decode()
            return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])

    class FakeOpenAI:
        def __init__(self, api_key):
            assert api_key == "key"
            self.images = FakeImages()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    paths = generate_images([f"prompt-{index}" for index in range(1, 7)], tmp_path, "key")

    assert len(calls) == 3
    assert [call["prompt"] for call in calls] == ["prompt-1", "prompt-3", "prompt-6"]
    assert all(call["model"] == "gpt-image-1-mini" for call in calls)
    assert all(call["quality"] == "medium" for call in calls)
    assert len(paths) == 6
    assert [path.read_bytes() for path in paths] == [
        b"image-1",
        b"image-1",
        b"image-2",
        b"image-2",
        b"image-3",
        b"image-3",
    ]
