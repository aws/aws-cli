"""Borrowed from the pip code base"""
from __future__ import annotations

from urllib.parse import urlsplit
from urllib.request import url2pathname

from packaging.utils import canonicalize_name

VCS = ["ftp", "ssh", "git", "hg", "bzr", "sftp", "svn"]
VALID_SCHEMAS = ["http", "https", "file"] + VCS


def is_url(name: str) -> bool:
    return get_url_scheme(name) in VALID_SCHEMAS


def get_url_scheme(url: str) -> str | None:
    if ":" not in url:
        return None
    return url.split(":", 1)[0].lower()


def url_to_path(url: str) -> str:
    _, netloc, path, _, _ = urlsplit(url)
    if not netloc or netloc == "localhost":  # According to RFC 8089, same as empty authority.
        netloc = ""
    else:
        raise ValueError(f"non-local file URIs are not supported on this platform: {url!r}")
    path = url2pathname(netloc + path)
    return path


def handle_binary_option(value: str, target: set[str], other: set[str]) -> None:
    new = value.split(",")
    while ":all:" in new:
        other.clear()
        target.clear()
        target.add(":all:")
        del new[: new.index(":all:") + 1]
        if ":none:" not in new:
            return
    for name in new:
        if name == ":none:":
            target.clear()
            continue
        name = canonicalize_name(name)
        other.discard(name)
        target.add(name)
