"""Translate's file arguments (upstream tests/functional/translate)."""

from pathlib import Path
from typing import Final

import pytest

from apihelpers import ApiSession, argv

pytestmark = pytest.mark.asyncio

CONTENTS: Final = b"mycontents"
IMPORT: Final = (
    "translate import-terminology --name myterminology"
    " --merge-strategy OVERWRITE"
)
TRANSLATE: Final = (
    "translate translate-document --source-language-code FOO"
    " --target-language-code BAR"
)


@pytest.fixture
def data_file(api: ApiSession) -> Path:
    path = api.cwd / "foo"
    path.write_bytes(CONTENTS)
    return path



@pytest.mark.parametrize("data_format", ["CSV", "TMX"])
async def test_import_terminology_sends_data_file(
    api: ApiSession, data_file: Path, data_format: str
) -> None:
    run = await api.assert_params_for_cmd(
        argv(
            f"{IMPORT} --terminology-data Format={data_format}"
            " --data-file fileb://{data_file}",
            data_file=data_file,
        ),
        {
            "Name": "myterminology",
            "MergeStrategy": "OVERWRITE",
            "TerminologyData": {"File": CONTENTS, "Format": data_format},
        },
    )
    assert run.operations == ["ImportTerminology"]


@pytest.mark.parametrize(
    ("args", "message"),
    [
        pytest.param(
            " --terminology-data File=fileb://wrong.csv,Format=TMX"
            " --data-file fileb://right.csv",
            "File cannot be provided as part of the '--terminology-data'"
            " argument. Please use the '--data-file' option instead to"
            " specify a file.",
            id="file-in-terminology-data",
        ),
        pytest.param(
            " --terminology-data Format=TMX", "--data-file", id="no-file"
        ),
        pytest.param(
            " --data-file fileb://{data_file}",
            'Missing required parameter in TerminologyData: "Format"',
            id="no-format",
        ),
    ],
)
async def test_import_terminology_rejects_bad_args(
    api: ApiSession, data_file: Path, args: str, message: str
) -> None:
    run = await api.assert_params_for_cmd(
        argv(IMPORT + args, data_file=data_file),
        expected_rc=252,
        stderr_contains=message,
    )
    assert run.calls == ()


async def test_translate_document_sends_document_content(
    api: ApiSession, data_file: Path
) -> None:
    run = await api.assert_params_for_cmd(
        argv(
            f"{TRANSLATE} --document ContentType=datatype"
            " --document-content fileb://{data_file}",
            data_file=data_file,
        ),
        {
            "Document": {"Content": CONTENTS, "ContentType": "datatype"},
            "SourceLanguageCode": "FOO",
            "TargetLanguageCode": "BAR",
        },
    )
    assert run.operations == ["TranslateDocument"]


@pytest.mark.parametrize(
    ("args", "message"),
    [
        pytest.param(
            "",
            "the following arguments are required: --document-content",
            id="original-argument",
        ),
        pytest.param(
            " --document-content fileb://{data_file}",
            "Content cannot be provided as a part of the '--document'"
            " argument. Please use the '--document-content' option instead"
            " to specify a file.",
            id="file-and-original-argument",
        ),
    ],
)
async def test_translate_document_rejects_content_in_document(
    api: ApiSession, data_file: Path, args: str, message: str
) -> None:
    run = await api.assert_params_for_cmd(
        argv(
            f"{TRANSLATE} --document Content=data,ContentType=datatype"
            + args,
            data_file=data_file,
        ),
        expected_rc=252,
        stderr_contains=message,
    )
    assert run.calls == ()
