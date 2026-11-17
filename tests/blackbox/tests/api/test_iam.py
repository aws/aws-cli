"""IAM commands' requests and the files they write (upstream
tests/functional/iam)."""

import base64
import json
import platform
from typing import Final

import pytest

from apihelpers import ApiSession, Reply

pytestmark = pytest.mark.asyncio

CREATE_MFA: Final = (
    "iam create-virtual-mfa-device --virtual-mfa-device-name fiebaz"
)
SERIAL_NUMBER: Final = "arn:aws:iam::419278470775:mfa/fiebaz"
BASE32_SEED: Final = (
    "VFpYTVc2V1lIUFlFRFczSVhLUlpRUTJRVFdUSFRNRDNTQ0c3"
    "TkZDUVdQWDVETlNWM0IyUENaQVpWTEpQTlBOTA=="
)
QR_CODE_PNG: Final = (
    "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6CAIAAAAHjs1qAAAFi"
    "ElEQVR42u3bQW7jMBAEwPz/07vHvS0QeLpnZFVf7cgyWRTgJv"
    "PzR+Q1+TEEgrsI7iK4i+AugrsI7iK4i+AugrsI7iK4C+4iuIv"
    "gLoK7CO4iuIvgLoK7CO4iBe4/rfz/c391k7lLffK5v/r6tZu8"
    "Ofu444477rjjjjvuuOOOO+6xwcoZ/WTl5D53cNXlZqG2VPpXx"
    "h133HHHHXfccccdd9xxD09/rU7ZylZdVnvo5BY/7rjjjjvuuO"
    "OOO+64447713H/RFIOZW0944477rjjjjvuuOOOO+64417ZVM8"
    "ZPbLHXiOLO+6444477rjjjjvuuOP+fO5bC2lwMeQKoiN/ew0l"
    "7rjjjjvuuOOOO+644457uCLYGmivHuxeBmcfd6/ijrtXccfdq"
    "7jj7lXcH5han3Bkeedana9SgTvuuOOOO+6444477ri/hXttc7"
    "umMLc2tm5ycI4GnzJfWETijjvuuOOOO+6444477s9oZnKDlZv"
    "vGp2tnf/BNx8/NYA77rjjjjvuuOOOO+64v5V7rZkZHKzalXOw"
    "cg3J1qorFGK444477rjjjjvuuOOO+1u5fwLrSG9T6zEGxyr3F"
    "WqPwkeemcEdd9xxxx133HHHHXfcj3Kv4chNUo17rU7ZmtDjax"
    "J33HHHHXfccccdd9xxfw33rWYm12McOY/wBQupZgN33HHHHXf"
    "ccccdd9xxx/2DwTpy0Pzm2sh9oyOgc+sZd9xxxx133HHHHXfc"
    "ccc9liOVSE3SkYIot2KPFES444477rjjjjvuuOOO+/u4DzYzg"
    "xoGpyH35q3R2Nrb758awB133HHHHXfccccdd9zfyj23NmpX3j"
    "omkBuc3N7+4DIr+MYdd9xxxx133HHHHXfc38q91gkcUZi7jcG"
    "d/9xIHnkG4Y477rjjjjvuuOOOO+6430gOR20hbVUTW4cIrg0O"
    "7rjjjjvuuOOOO+644/4a7keKi8G+6At273Nv3vpc3HHHHXfcc"
    "ccdd9xxxx332LjXyocanUfgqJ0pqNU4uOOOO+6444477rjjjj"
    "vuS13E1l53jc5Ndjf144477rjjjjvuuOOOO+64x77Skf352mZ"
    "+7VhEbo62DiBE6jvccccdd9xxxx133HHHHffs9A8WNbnprz0a"
    "tv7rYPDrP/IQAe6444477rjjjjvuuON+lPvguK//ci+TrS3Rw"
    "Z7q5nMEd9xxxx133HHHHXfccce9VSDkippcY5A7nrBVaxyp2n"
    "DHHXfccccdd9xxxx133FuTVFs5tUttlVq5pZJ7cCy0arjjjjv"
    "uuOOOO+6444477tmd8K0SIDdnNXZHirj+YwV33HHHHXfccccd"
    "d9xxfw33mu+bHUiObK4By7E7jgF33HHHHXfccccdd9xxfw33W"
    "hcx+Kt/a1Zyn5tbZltkcccdd9xxxx133HHHHXfcb4DOnRp4Yg"
    "eSQ/l9jRDuuOOOO+6444477rjjjntM4WCBMGhlcHByt1GrcbZ"
    "OSeCOO+6444477rjjjjvuuD8htUMENcFbN1mrcXIfhDvuuOOO"
    "O+6444477rjjvvSrP3cbg3NWG7pcMTV4OuPtRSTuuOOOO+644"
    "4477rjjfoV7rXvZWjlbVr6+5CkUNbjjjjvuuOOOO+6444477q"
    "sacn+7VeMcaYRyVdsjDxHgjjvuuOOOO+6444477rinNNR6myf"
    "exlbXpJnBHXfccccdd9xxxx133J/PvbAFPT5nN4upLQy44447"
    "7rjjjjvuuOOOO+4t7rWx27pybY/9iLMjvQ3uuOOOO+6444477"
    "rjjjvvSfB/Zr86t58H53qpxBpdoYZxxxx133HHHHXfccccd99"
    "dwF3lKcBfcRXAXwV0EdxHcRXAXwV0EdxHcRXAXwV1wF8FdBHc"
    "R3EVwF8FdBHcR3EVwF8Fd5F/+AgASajf850wfAAAAAElFTkSu"
    "QmCC"
)
# Upstream's device. A blob reply is the service's bytes, so the wire
# carries upstream's base64 text, which the CLI keeps as is and decodes
# into the outfile.
MFA_REPLY: Final = {
    "VirtualMFADevice": {
        "Base32StringSeed": base64.b64decode(BASE32_SEED),
        "SerialNumber": SERIAL_NUMBER,
        "QRCodePNG": base64.b64decode(QR_CODE_PNG),
    }
}
POSIX_ONLY: Final = pytest.mark.skipif(
    platform.system() not in ("Darwin", "Linux"),
    reason="Permissions test not valid on Windows.",
)


async def test_create_open_id_connect_provider(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "iam create-open-id-connect-provider --url https://example.com"
        " --thumbprint-list 990F4193972F2BECF12DDEDA5237F9C952F20D9E",
        {
            "Url": "https://example.com",
            "ThumbprintList": ["990F4193972F2BECF12DDEDA5237F9C952F20D9E"],
        },
    )


@pytest.mark.parametrize(
    ("method", "datum", "name", "relative"),
    [
        pytest.param(
            "Base32StringSeed", BASE32_SEED, "fiebaz.b32", False, id="base32"
        ),
        pytest.param(
            "QRCodePNG", QR_CODE_PNG, "fiebaz.png", False, id="qrcode"
        ),
        pytest.param(
            "QRCodePNG",
            QR_CODE_PNG,
            "filename.png",
            True,
            id="relative-filename",
        ),
    ],
)
async def test_create_virtual_mfa_device_saves_bootstrap_datum(
    api: ApiSession, method: str, datum: str, name: str, relative: bool
) -> None:
    # A relative outfile is relative to the working directory.
    outfile = name if relative else str(api.cwd / name)
    result = await api.assert_params_for_cmd(
        [
            *CREATE_MFA.split(),
            "--outfile",
            outfile,
            "--bootstrap-method",
            method,
        ],
        {"VirtualMFADeviceName": "fiebaz"},
        replies=MFA_REPLY,
    )
    assert (api.cwd / name).read_bytes() == base64.b64decode(datum)
    # Neither datum is left in the output.
    assert json.loads(result.stdout) == {
        "VirtualMFADevice": {"SerialNumber": SERIAL_NUMBER}
    }


@pytest.mark.parametrize(
    "outfile",
    [
        pytest.param("/some/bad/filename.png", id="bad-filename"),
        pytest.param("some/bad/filename.png", id="bad-relative-filename"),
    ],
)
async def test_create_virtual_mfa_device_rejects_unwritable_outfile(
    api: ApiSession, outfile: str
) -> None:
    result = await api.run(
        f"{CREATE_MFA} --outfile {outfile} --bootstrap-method QRCodePNG",
        replies=MFA_REPLY,
        expected_rc=252,
    )
    # The path is checked before the request.
    assert result.calls == ()


async def test_create_virtual_mfa_device_bad_response(
    api: ApiSession,
) -> None:
    # Creating a device whose name is taken; upstream's 409.
    message = "MFADevice entity at the and name already exists."
    error = {
        "Error": {
            "Code": "EntityAlreadyExists",
            "Message": message,
            "Type": "Sender",
        }
    }
    await api.assert_params_for_cmd(
        f"{CREATE_MFA} --outfile foo --bootstrap-method QRCodePNG",
        stderr_contains=message,
        expected_rc=254,
        replies=Reply(error, status=409),
    )
    assert not (api.cwd / "foo").exists()


@POSIX_ONLY
@pytest.mark.parametrize(
    "existing",
    [
        pytest.param(False, id="new-file"),
        pytest.param(True, id="existing-file"),
    ],
)
async def test_create_virtual_mfa_device_outfile_permissions(
    api: ApiSession, existing: bool
) -> None:
    outfile = api.cwd / "fiebaz_perms.b32"
    if existing:
        outfile.write_bytes(b"existing")
        outfile.chmod(0o644)
    await api.assert_params_for_cmd(
        [
            *CREATE_MFA.split(),
            "--outfile",
            str(outfile),
            "--bootstrap-method",
            "Base32StringSeed",
        ],
        {"VirtualMFADeviceName": "fiebaz"},
        replies=MFA_REPLY,
    )
    assert outfile.stat().st_mode & 0o7777 == 0o600
    assert outfile.read_bytes() == base64.b64decode(BASE32_SEED)


async def test_list_access_keys_with_no_paginate(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "iam list-access-keys --no-paginate --max-items 1", {"MaxItems": 1}
    )
