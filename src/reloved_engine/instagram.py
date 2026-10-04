"""Instagram carousel publishing through Meta's official Instagram API."""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, cast
from urllib.parse import quote, urlparse
from uuid import uuid4

import requests  # type: ignore[import-untyped]
from PIL import Image

from reloved_engine.jobs import JobError, load_job

DEFAULT_GRAPH_API_VERSION = "v26.0"
DEFAULT_GRAPH_ROOT = "https://graph.instagram.com"
FACEBOOK_GRAPH_ROOT = "https://graph.facebook.com"
SLIDE_COUNT = 6


class InstagramPublishError(RuntimeError):
    """Raised when Meta rejects or cannot complete an Instagram operation."""


class _Response(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


class _Session(Protocol):
    def get(self, url: str, **kwargs: Any) -> _Response: ...

    def post(self, url: str, **kwargs: Any) -> _Response: ...


def final_slide_paths(job_file: str | Path, post_id: str) -> list[Path]:
    """Return and validate six Instagram-compatible JPEGs for an approved post."""
    job = load_job(job_file)
    post = next((item for item in job["posts"] if item["id"] == post_id), None)
    if post is None:
        raise JobError(f"Unknown post ID: {post_id}")
    if post["status"] != "APPROVED":
        raise JobError("Only APPROVED posts can be published")
    directory = Path(job_file).parent / "assets" / post_id / "instagram"
    paths = [directory / f"slide-{index}.jpg" for index in range(1, SLIDE_COUNT + 1)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise JobError(
            f"Missing Instagram images: {', '.join(missing)}; run reloved instagram-assets first"
        )
    for path in paths:
        try:
            with Image.open(path) as image:
                ratio = image.width / image.height
                if image.format != "JPEG" or not 320 <= image.width <= 1440 or not 0.8 <= ratio <= 1.91:
                    raise JobError(f"Image does not meet Instagram publishing specifications: {path}")
        except OSError as error:
            raise JobError(f"Cannot read Instagram image: {path}") from error
        if path.stat().st_size > 8 * 1024 * 1024:
            raise JobError(f"Instagram image exceeds 8 MiB: {path}")
    return paths


def build_caption(job_file: str | Path, post_id: str) -> str:
    """Build the Instagram caption from the reviewed draft and its hashtags."""
    job = load_job(job_file)
    post = next((item for item in job["posts"] if item["id"] == post_id), None)
    if post is None:
        raise JobError(f"Unknown post ID: {post_id}")
    caption = post["draft"]["caption"].strip()
    hashtags = " ".join(post["draft"]["hashtags"])
    return f"{caption}\n\n{hashtags}" if hashtags else caption


def image_urls_from_base(base_url: str) -> list[str]:
    """Create the six slide URLs from a public directory URL."""
    base = base_url.rstrip("/")
    return [f"{base}/slide-{index}.jpg" for index in range(1, SLIDE_COUNT + 1)]


def validate_image_urls(image_urls: Sequence[str]) -> list[str]:
    """Validate Meta-fetchable HTTPS image URLs without making network calls."""
    urls = list(image_urls)
    if len(urls) != SLIDE_COUNT:
        raise JobError(f"Exactly {SLIDE_COUNT} image URLs are required")
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise JobError(f"Instagram image URLs must be public HTTPS URLs: {url}")
        if parsed.username or parsed.password:
            raise JobError("Instagram image URLs must not contain embedded credentials")
    return urls


def publication_receipt_path(job_file: str | Path, post_id: str) -> Path:
    return Path(job_file).parent / "assets" / post_id / "instagram_publication.json"


def reel_publication_receipt_path(job_file: str | Path, post_id: str) -> Path:
    return Path(job_file).parent / "assets" / post_id / "instagram_reel_publication.json"


class InstagramPublisher:
    """Small client for Instagram's create-container then publish workflow."""

    def __init__(
        self,
        instagram_user_id: str,
        access_token: str,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        graph_root: str = DEFAULT_GRAPH_ROOT,
        session: _Session | None = None,
        poll_interval: float = 2.0,
        max_status_checks: int = 60,
        sleep: Callable[[float], None] = time.sleep,
        audio_access_token: str | None = None,
    ) -> None:
        if not instagram_user_id.strip():
            raise JobError("INSTAGRAM_USER_ID is required")
        if not access_token.strip():
            raise JobError("INSTAGRAM_ACCESS_TOKEN is required")
        if not api_version.startswith("v"):
            raise JobError("Instagram API version must look like v26.0")
        self.instagram_user_id = instagram_user_id.strip()
        self.access_token = access_token.strip()
        self.audio_access_token = (audio_access_token or access_token).strip()
        self.api_version = api_version
        self.graph_root = graph_root.rstrip("/")
        self.session = session or requests.Session()
        self.poll_interval = poll_interval
        self.max_status_checks = max_status_checks
        self.sleep = sleep

    def account(self) -> dict[str, Any]:
        """Fetch the connected professional account for setup verification."""
        fields = (
            "id,username"
            if self.graph_root == FACEBOOK_GRAPH_ROOT
            else "id,username,account_type,media_count"
        )
        payload = self._get(
            self.instagram_user_id,
            {"fields": fields},
        )
        return payload

    def publish_carousel(self, image_urls: Sequence[str], caption: str) -> dict[str, Any]:
        """Create six image containers, assemble them, and publish the carousel."""
        urls = validate_image_urls(image_urls)
        child_ids: list[str] = []
        for image_url in urls:
            child = self._post(
                f"{self.instagram_user_id}/media",
                {"image_url": image_url, "is_carousel_item": "true"},
            )
            child_id = self._required_id(child, "child media container")
            self._wait_until_ready(child_id)
            child_ids.append(child_id)

        carousel = self._post(
            f"{self.instagram_user_id}/media",
            {"media_type": "CAROUSEL", "children": ",".join(child_ids), "caption": caption},
        )
        carousel_id = self._required_id(carousel, "carousel container")
        self._wait_until_ready(carousel_id)
        published = self._post(
            f"{self.instagram_user_id}/media_publish",
            {"creation_id": carousel_id},
        )
        media_id = self._required_id(published, "published media")
        try:
            details = self._get(media_id, {"fields": "id,permalink,timestamp"})
        except InstagramPublishError:
            # The publish already succeeded. Preserve its ID so the caller can
            # write an idempotency receipt instead of risking a duplicate post.
            details = {}
        return {
            "media_id": media_id,
            "permalink": details.get("permalink"),
            "timestamp": details.get("timestamp"),
            "container_id": carousel_id,
            "child_container_ids": child_ids,
        }

    def trending_audio(self, audio_type: str = "music") -> dict[str, Any]:
        """Return the first currently trending audio asset exposed to this account."""
        if self.graph_root != FACEBOOK_GRAPH_ROOT:
            raise JobError(
                "Trending Instagram audio requires Facebook Login and graph.facebook.com"
            )
        if audio_type not in {"music", "original_sound"}:
            raise JobError("audio_type must be music or original_sound")
        payload = self._request(
            "get",
            "ig_audio",
            params={
                "audio_type": audio_type,
                "user_id": self.instagram_user_id,
                "access_token": self.audio_access_token,
            },
        )
        assets = payload.get("audio")
        if not isinstance(assets, list) or not assets:
            raise InstagramPublishError("Instagram returned no authorized trending audio")
        asset = assets[0]
        if not isinstance(asset, dict) or not isinstance(asset.get("audio_id"), str):
            raise InstagramPublishError("Instagram returned an invalid trending audio asset")
        return cast(dict[str, Any], asset)

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        audio_id: str,
        *,
        audio_volume: int = 100,
        video_volume: int = 0,
        share_to_feed: bool = True,
    ) -> dict[str, Any]:
        """Create and publish a Reel with an Instagram catalog audio asset."""
        parsed = urlparse(video_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise JobError("Instagram Reel video URL must be public HTTPS without credentials")
        if not audio_id.strip():
            raise JobError("An Instagram audio_id is required for the Reel")
        if not 0 <= audio_volume <= 100 or not 0 <= video_volume <= 100:
            raise JobError("Reel audio volumes must be between 0 and 100")
        container = self._post(
            f"{self.instagram_user_id}/media",
            {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": str(share_to_feed).lower(),
                "audio_configuration": json.dumps(
                    {
                        "audio_id": audio_id.strip(),
                        "audio_volume": audio_volume,
                        "video_volume": video_volume,
                    },
                    separators=(",", ":"),
                ),
            },
        )
        container_id = self._required_id(container, "Reel container")
        self._wait_until_ready(container_id)
        published = self._post(
            f"{self.instagram_user_id}/media_publish", {"creation_id": container_id}
        )
        media_id = self._required_id(published, "published Reel")
        try:
            details = self._get(media_id, {"fields": "id,permalink,timestamp"})
        except InstagramPublishError:
            details = {}
        return {
            "media_id": media_id,
            "permalink": details.get("permalink"),
            "timestamp": details.get("timestamp"),
            "container_id": container_id,
            "audio_id": audio_id.strip(),
        }

    def _wait_until_ready(self, container_id: str) -> None:
        for attempt in range(self.max_status_checks):
            status = self._get(container_id, {"fields": "status_code,status"})
            status_code = str(status.get("status_code", "")).upper()
            if status_code == "FINISHED":
                return
            if status_code in {"ERROR", "EXPIRED"}:
                detail = status.get("status") or status_code
                raise InstagramPublishError(f"Instagram container {container_id} failed: {detail}")
            if attempt + 1 < self.max_status_checks:
                self.sleep(self.poll_interval)
        raise InstagramPublishError(f"Instagram container {container_id} did not become ready in time")

    def _url(self, path: str) -> str:
        safe_path = "/".join(quote(part, safe="") for part in path.split("/"))
        return f"{self.graph_root}/{self.api_version}/{safe_path}"

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self._request("get", path, params={**params, "access_token": self.access_token})

    def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        return self._request("post", path, data={**data, "access_token": self.access_token})

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = getattr(self.session, method)(self._url(path), timeout=30, **kwargs)
        except requests.RequestException as error:
            raise InstagramPublishError(
                f"Instagram API request failed: {self._redact(error)}"
            ) from error
        try:
            payload = response.json()
        except ValueError as error:
            raise InstagramPublishError(f"Instagram API request failed: {error}") from error
        if not isinstance(payload, dict):
            raise InstagramPublishError("Instagram API returned an invalid response")
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = (
                str(error_payload.get("message", "unknown Meta API error"))
                .replace(self.access_token, "[REDACTED]")
                .replace(self.audio_access_token, "[REDACTED]")
            )
            code = error_payload.get("code")
            suffix = f" (code {code})" if code is not None else ""
            raise InstagramPublishError(f"Instagram API rejected the request: {message}{suffix}")
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            raise InstagramPublishError(
                f"Instagram API request failed: {self._redact(error)}"
            ) from error
        return cast(dict[str, Any], payload)

    def _redact(self, error: Exception) -> str:
        return (
            str(error)
            .replace(self.access_token, "[REDACTED]")
            .replace(self.audio_access_token, "[REDACTED]")
        )

    @staticmethod
    def _required_id(payload: dict[str, Any], label: str) -> str:
        object_id = payload.get("id")
        if not isinstance(object_id, str) or not object_id:
            raise InstagramPublishError(f"Instagram did not return an ID for the {label}")
        return object_id


def publish_post(
    job_file: str | Path,
    post_id: str,
    image_urls: Sequence[str],
    publisher: InstagramPublisher,
    allow_republish: bool = False,
) -> dict[str, Any]:
    """Publish an approved rendered post and atomically save a non-secret receipt."""
    final_slide_paths(job_file, post_id)
    urls = validate_image_urls(image_urls)
    receipt_path = publication_receipt_path(job_file, post_id)
    if receipt_path.exists() and not allow_republish:
        raise JobError(
            f"Instagram publication already recorded at {receipt_path}; "
            "use --allow-republish only when a second post is intentional"
        )
    result = publisher.publish_carousel(urls, build_caption(job_file, post_id))
    receipt = {
        "version": 1,
        "post_id": post_id,
        "instagram_user_id": publisher.instagram_user_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "image_urls": urls,
        **result,
    }
    _atomic_write(receipt_path, receipt)
    return receipt


def publish_reel_post(
    job_file: str | Path,
    post_id: str,
    video_url: str,
    audio: dict[str, Any],
    publisher: InstagramPublisher,
    allow_republish: bool = False,
) -> dict[str, Any]:
    """Publish an approved Reel and atomically save an idempotency receipt."""
    receipt_path = reel_publication_receipt_path(job_file, post_id)
    if receipt_path.exists() and not allow_republish:
        raise JobError(
            f"Instagram Reel publication already recorded at {receipt_path}; "
            "a second post must be explicitly implemented"
        )
    audio_id = audio.get("audio_id")
    if not isinstance(audio_id, str):
        raise JobError("Instagram audio asset is missing audio_id")
    result = publisher.publish_reel(video_url, build_caption(job_file, post_id), audio_id)
    receipt = {
        "version": 1,
        "post_id": post_id,
        "instagram_user_id": publisher.instagram_user_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "video_url": video_url,
        "audio": {
            key: value
            for key, value in audio.items()
            if key in {"audio_id", "title", "display_artist", "ig_username", "audio_type"}
        },
        **result,
    }
    _atomic_write(receipt_path, receipt)
    return receipt


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
