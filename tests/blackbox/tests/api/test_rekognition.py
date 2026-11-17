"""Rekognition's image arguments: --image-bytes and the like read a file
into the image's Bytes (upstream tests/functional/rekognition)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

COLLECTION: Final = ("--collection-id", "foobar")
# The commands that take one image, with the arguments and parameters
# each needs besides it.
SINGLE_IMAGE: Final = [
    pytest.param("detect-faces", (), {}, id="detect-faces"),
    pytest.param("detect-labels", (), {}, id="detect-labels"),
    pytest.param(
        "detect-moderation-labels", (), {}, id="detect-moderation-labels"
    ),
    pytest.param("detect-text", (), {}, id="detect-text"),
    pytest.param(
        "index-faces",
        COLLECTION,
        {"CollectionId": "foobar"},
        id="index-faces",
    ),
    pytest.param(
        "recognize-celebrities", (), {}, id="recognize-celebrities"
    ),
    pytest.param(
        "search-faces-by-image",
        COLLECTION,
        {"CollectionId": "foobar"},
        id="search-faces-by-image",
    ),
]


@pytest.mark.parametrize(("command", "args", "params"), SINGLE_IMAGE)
async def test_image_file_does_populate_bytes_param(
    api: ApiSession,
    command: str,
    args: tuple[str, ...],
    params: dict[str, Any],
) -> None:
    image = api.cwd / "foo"
    image.write_bytes(b"mycontents")
    await api.assert_params_for_cmd(
        ["rekognition", command, *args, "--image-bytes", f"fileb://{image}"],
        {**params, "Image": {"Bytes": b"mycontents"}},
    )


@pytest.mark.parametrize(("command", "args", "params"), SINGLE_IMAGE)
async def test_image_bytes_still_works(
    api: ApiSession,
    command: str,
    args: tuple[str, ...],
    params: dict[str, Any],
) -> None:
    # Bytes in the image structure is base64: "foobar".
    await api.assert_params_for_cmd(
        ["rekognition", command, *args, "--image", "Bytes=Zm9vYmFy"],
        {**params, "Image": {"Bytes": b"foobar"}},
    )


async def test_compare_faces_image_files_populate_bytes_params(
    api: ApiSession,
) -> None:
    source = api.cwd / "foo"
    source.write_bytes(b"mycontents")
    target = api.cwd / "bar"
    target.write_bytes(b"othercontents")
    await api.assert_params_for_cmd(
        [
            "rekognition",
            "compare-faces",
            "--source-image-bytes",
            f"fileb://{source}",
            "--target-image-bytes",
            f"fileb://{target}",
        ],
        {
            "SourceImage": {"Bytes": b"mycontents"},
            "TargetImage": {"Bytes": b"othercontents"},
        },
    )


async def test_compare_faces_image_bytes_still_work(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "rekognition compare-faces --source-image Bytes=Zm9v"
        " --target-image Bytes=YmFy",
        {"SourceImage": {"Bytes": b"foo"}, "TargetImage": {"Bytes": b"bar"}},
    )
