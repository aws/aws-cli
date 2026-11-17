#!/usr/bin/env python3
"""Capture and compare the AWS CLI parse chain, without dispatching.

The test-only capture executable calls the parsers, the global
checks, and, for an S3 lineage, the unpack loop and leftover check. A copied
environment supplies isolated config paths while preserving HOME. Both
parsers run in the testdata directory, so every parameter file in a case is
a fixture under it or a path that does not exist there.
--check is the pin-bump check; --write refreshes reviewable fixtures.
--fuzz adds every option prefix and a reproducible bounded random corpus.
"""

import argparse
import ast
import json
import os
import random
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# This harness lives two levels below the repository root (tests/argparse/).
ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "crates/awscli-argparse/src/testdata/awscli/cases.jsonl"
PATTERNS = ROOT / "crates/awscli-argparse/src/testdata/patterns.json"
# The working directory of both parsers; the parameter-file fixtures live in
# its `paramfile` subdirectory, which ARGPARSE_FIXTURES names.
FIXTURES = ROOT / "crates/awscli-argparse/src/testdata/awscli"
SEED = 0xA263A25E
STAGES = [
    "auto_prompt",
    "first_pass",
    "main",
    "dispatch",
    "top_level",
    "probe",
    "table",
    "unpack",
    "leftover",
]


def catalog() -> list[dict[str, Any]]:
    commands = [
        "",
        "s3 cp",
        "s3 cp ./a --recursive ./b",
        "--cli s3 ls",
        "--re s3 ls",
        "s3 --profile",
        "s3 ls --debug=1",
        "s3 cp --sse= ./a ./b",
        "s3 cp --storage-class STANDARD_I ./a ./b",
        "s3 cp --include --recursive ./a ./b",
        "s3 cp -- ./a ./b",
        "--cli-read-timeout abc s3 ls",
        '--query "[" --endpoint-url nope s3 ls',
        "s3 ls --query Contents --endpoint-url nope",
        "--query Contents[].Key s3 ls",
        "--cli-auto-prompt --no-cli-auto-prompt s3 ls",
        "--endpoint-url nope s3 ls",
        "s3 ls --request-payer",
        "s3 ls --request-payer s3://b",
        "s3 ls --request-payer -- s3://b",
        "s3 cp --tags k --v ./a ./b",
        "s3 mb s3://bucket --tags k --v",
        "s3 cp --grants a --quiet ./a ./b",
        's3 ls "--not an option"',
        "s3 ls -5",
        "s3 ls --page-size -5",
        "s3 ls --page-size --request-payer",
        "s3 cp --recur ./a s3://b/k",
        "s3 cp --sse- ./a ./b",
        "s3 ls help",
        "s3 help",
        "s3 help ls",
        "s3 cp ./a ./b --",
        "--version --region",
        "--region --version",
        "--profile s3 s3 ls",
        "s3 sync ./a s3://b --delete --size-only",
        "s33 ls",
        "ec2 describe-instances --region us-west-2",
        "ec2 --endpoint-url nope describe-instances",
        "help",
        "s3",
        "s3 ls --bogus",
        "s3 cp ./a ./b ./c",
        "s3 ls --page-size abc --bogus",
        "s3 ls file://missingfile",
        "s3 cp --metadata '{bad' ./a s3://b/k",
        "s3 cp a b --include x --exclude y --include z",
        "s3 cp a b --no-follow-symlinks --follow-symlinks",
        "s3 cp a b --follow-symlinks --no-follow-symlinks",
        "s3 mb s3://bucket --tags k v --tags x y",
        "--cli-read-timeout 0 --cli-connect-timeout -1 s3 ls",
        "--ca-bundle file.pem s3 ls",
        "--no-verify-ssl s3 ls",
        "--no-sign-request s3 ls",
        "s3 -- s3://bucket",
        "s3 ls -- -- --profile x",
        "s3 sycn",
        "s3 ls -h",
        "s3 ls --help",
        # --help: the help-mode retry of a failed main parse, and the help
        # that BasicCommand renders before it parses its own table.
        "--help",
        "--help help",
        "s3 --help",
        "s3 cp --help",
        "s3 cp --hel ./a",
        "s3 ls --bogus --page-size abc --help",
        "s3 ls --region --help",
        "--query --help s3 ls",
        "--region --help",
        "--region --output --cli-connect-timeout",
        "--query --version --help",
        "s3 sycn --help",
        "--endpoint-url nope s3 ls --help",
        "--cli-connect-timeout abc s3 ls --help",
        "s3 cp --tags k v ./a s3://b/k",
        "s3 sync ./a s3://b --tags k v --tags x y",
        "s3 mv ./a s3://b/k --tags k",
        "--deb= s3 ls",
        # Parameter files, leftovers, and the integer rules.
        "s3 cp --sse-c-key fileb://missing ./a s3://b/k",
        "s3 cp --sse-c-key fileb://missing ./a s3://b/k --bogus",
        "s3 cp ./a ./b -- --recursive",
        "s3 cp fileb://key s3://bucket/key --bogus",
        "s3 ls file://$ARGPARSE_FIXTURES/text.txt",
        "s3 ls file://$ARGPARSE_FIXTURES/utf8.txt",
        "s3 ls file://${ARGPARSE_FIXTURES}/empty.txt",
        "s3 ls --page-size file://$ARGPARSE_FIXTURES/page_size.txt",
        "s3 ls --page-size file://$ARGPARSE_FIXTURES/page_size.txt --bogus",
        "s3 ls --page-size file://$ARGPARSE_FIXTURES/empty.txt",
        "s3 ls --page-size file://$ARGPARSE_FIXTURES/text.txt",
        "s3 ls --page-size fileb://$ARGPARSE_FIXTURES/page_size.txt",
        "s3 ls --bucket-region fileb://$ARGPARSE_FIXTURES/page_size.txt",
        "s3 cp --sse-c-key fileb://$ARGPARSE_FIXTURES/binary.bin ./a s3://b/k",
        "s3 cp --sse-c-key file://$ARGPARSE_FIXTURES/binary.bin ./a s3://b/k",
        "s3 ls file://$ARGPARSE_FIXTURES",
        "s3 ls file://$ARGPARSE_FIXTURES/text.txt/x",
        "s3 ls file://$ARGPARSE_UNSET_VARIABLE/x",
        "s3 ls file://~nonexistentuser/x",
        "s3 ls file://",
        "s3 cp --metadata a=b ./a s3://b/k",
        "s3 cp --metadata file://$ARGPARSE_FIXTURES/text.txt ./a s3://b/k",
        # The map value chain: shorthand, JSON, the schema, and the policies.
        "s3 cp --metadata '' ./a s3://b/k",
        "s3 cp --metadata '[1]' ./a s3://b/k",
        "s3 cp --metadata a=[x,y] ./a s3://b/k",
        "s3 cp --metadata a==b ./a s3://b/k --bogus",
        "s3 cp --metadata a=b ./a s3://b/k --bogus",
        "s3 cp --metadata a=b,a=c ./a s3://b/k",
        "s3 cp --metadata a={b=c,d=[e]},f=g ./a s3://b/k",
        "s3 cp --metadata a=b,c ./a s3://b/k",
        "s3 cp --metadata =b ./a s3://b/k",
        "s3 cp --metadata a@=b ./a s3://b/k",
        "s3 cp --metadata file://$ARGPARSE_FIXTURES/map.json ./a s3://b/k",
        "s3 cp --metadata file://$ARGPARSE_FIXTURES/shorthand.txt ./a s3://b/k",
        "s3 ls --page-size 1_0",
        "s3 ls --page-size 99999999999999999999",
        "--cli-read-timeout 99999999999999999999 s3 ls",
        "--cli-read-timeout ' 60 ' s3 ls",
        "--cli-read-timeout 6__0 s3 ls",
        "s3 ls --page-size \uff11\uff10",
        "s3 presign s3://b/k --expires-in 1_0",
    ]
    result = [{"argv": shlex.split(text), "scope": "s3"} for text in commands]
    for case in result:
        argv = case["argv"]
        if not argv or argv[0] in {"--version", "--region", "--cli"}:
            case["scope"] = "global"
        if argv and argv[0] in {"s33", "ec2", "help", "--re", "--help"}:
            case["scope"] = "boundary"
    result.extend(
        [
            {"argv": ["s3", "cp"], "scope": "s3", "color": True},
            {"argv": ["s3", "sycn"], "scope": "s3", "color": True},
            {"argv": ["s3", "ls", "--debug='\"\n\t\\"], "scope": "global"},
            {
                "argv": ["s3", "ls", "--debug=1"],
                "scope": "global",
                "color": True,
            },
            {"argv": ["s3", "ls", "--debug=\u200b"], "scope": "global"},
            {"argv": ["s3", "ls", "--page-size", "x" * 250], "scope": "s3"},
            {
                "argv": ["--cli-connect-timeout", "x" * 250, "s3", "ls"],
                "scope": "global",
            },
            {
                "argv": ["s3", "cp", "--metadata", '{"a": 1}', "./a", "s3://b/k"],
                "scope": "s3",
            },
            {
                "argv": [
                    "s3",
                    "cp",
                    "a",
                    "b",
                    "--storage-class",
                    "x\n\nMaybe you meant:\n\nusage: bait",
                ],
                "scope": "s3",
            },
        ]
    )
    for value in metadata_values():
        result.append(
            {
                "argv": ["s3", "cp", "--metadata", value, "./a", "s3://b/k"],
                "scope": "s3",
            }
        )
    # JSONL separators are literal LF bytes; Unicode line separators belong
    # to the argv string, and embedded LF must survive JSON escaping.
    for separator in ("\u0085", "\u2028", "\u2029", "\n"):
        result.append(
            {
                "argv": ["s3", "ls", f"s3://bucket/a{separator}b"],
                "scope": "s3",
            }
        )
    for value in ("9223372036854775807", "-9223372036854775808", "000000"):
        result.append(
            {
                "argv": ["s3", "ls", "--cli-read-timeout", value],
                "scope": "global",
            }
        )
    for url in (" \tHTTPS://localhost", "scheme:value"):
        result.append({"argv": ["s3", "ls", "--endpoint-url", url], "scope": "global"})
    return result


def upstream_cases(source: Path) -> list[dict[str, Any]]:
    """Collect literal S3 command strings without executing upstream tests."""
    result = []
    for path in sorted((source / "tests/functional/s3").glob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            text = node.value.strip()
            if not text.startswith("s3 ") or "\n" in text:
                continue
            try:
                argv = shlex.split(text)
            except ValueError:
                continue
            result.append({"argv": argv, "scope": "s3"})
    return result


def unique(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = {}
    for case in cases:
        key = json.dumps([case["argv"], case.get("color", False)])
        result.setdefault(key, case)
    return list(result.values())


def option_cases(tables: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    groups = [(tables["globals"], ["s3", "ls"])]
    for command in tables["s3"]["subcommands"]:
        base = ["s3", command["name"]]
        for arg in command["arguments"]:
            if arg["positional"]:
                count = arg["nargs"] if isinstance(arg["nargs"], int) else 1
                base.extend(["s3://bucket/key"] * count)
        groups.append((command["arguments"], base))
    for arguments, base in groups:
        for arg in arguments:
            if arg["positional"]:
                continue
            name = "--" + arg["name"]
            if arg["action"] in {"store_true", "store_false", "version"}:
                values = []
            else:
                count = arg["nargs"] if isinstance(arg["nargs"], int) else 1
                values = [(arg["choices"] or ["1"])[0]] * count
                if arg["name"] == "endpoint-url":
                    values = ["https://localhost"]
            for length in range(3, len(name) + 1):
                prefix = name[:length]
                result.append({"argv": [*base, prefix, *values], "scope": "s3"})
                if len(values) == 1:
                    result.append(
                        {
                            "argv": [*base, prefix + "=" + values[0]],
                            "scope": "s3",
                        }
                    )
    return result


def metadata_values() -> list[str]:
    """--metadata values covering duplicate keys, arrays where strings are
    required, overwritten nonstandard numbers, lone surrogates, large
    integer tokens, number spellings, JSON syntax errors, and the shorthand
    grammar's edges."""
    digits = "1" * 4301
    return [
        '{"x":1,"x":"ok"}',
        '{"x":[65,66]}',
        '{"x":NaN,"x":"ok"}',
        '{"x":"\\ud800"}',
        '{"x":"\\ud83d\\ude00"}',
        f'{{"x":{digits}}}',
        f'{{"x":{digits},"x":"ok"}}',
        f'{{"x":[{digits}]}}',
        '{"x": 1E2, "y": -0, "z": 10.50, "w": [1e309, 1.0], "v": true}',
        '{"x": {"y": 1}, "z": null, "": 2}',
        '{"": 1}',
        "{",
        '{"a":\n"b"',
        "\u3000{}",
        ' {"k": "v"} \n',
        "{}",
        "a='x,y',b=",
        "a=b\nc==d",
        "a=\U0001f600",
        "\u00e9=b",
        "a=x\\,y",
        "a='x",
        "a=" + "[" * 33 + "x" + "]" * 33,
        '{"a":' + "[" * 33 + "]" * 33 + "}",
    ]


SHORTHAND_FRAGMENTS = [
    "a",
    "b",
    "=",
    ",",
    " ",
    "[",
    "]",
    "{",
    "}",
    "'",
    '"',
    "\\,",
    "\\",
    "\n",
    "@",
    "\u00e9",
    "\U0001f600",
    "x y",
    "a=b",
    "c=d",
]
JSON_FRAGMENTS = [
    '"x"',
    '"y"',
    ":",
    ",",
    " ",
    "1",
    "-0",
    "1.5",
    "1E2",
    "1e309",
    "NaN",
    "Infinity",
    "-Infinity",
    "null",
    "true",
    '"\\ud800"',
    '"\\udc00"',
    '"\\u00e9"',
    "[",
    "]",
    "{",
    "}",
    "1" * 4301,
    '"s"',
    "\n",
    "\t",
    '"x":"ok"',
    '"x":1',
    '"x":[1]',
]


def metadata_value(rng: random.Random) -> str:
    """A shorthand or JSON value assembled from grammar fragments."""
    if rng.random() < 0.5:
        return "".join(rng.choices(SHORTHAND_FRAGMENTS, k=rng.randrange(1, 8)))
    return "{" + "".join(rng.choices(JSON_FRAGMENTS, k=rng.randrange(0, 8)))


def fuzz_cases(tables: dict[str, Any], count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pool = [
        "",
        "--",
        "-",
        "-5",
        "-.5",
        "-5abc",
        "--not an option",
        "help",
        "s3",
        "cp",
        "ls",
        "x",
        "a",
        "b",
        "file://missing",
        "fileb://missing",
        "file://",
        "file://$ARGPARSE_FIXTURES/text.txt",
        "file://$ARGPARSE_FIXTURES/page_size.txt",
        "fileb://$ARGPARSE_FIXTURES/page_size.txt",
        "file://$ARGPARSE_FIXTURES/binary.bin",
        "fileb://$ARGPARSE_FIXTURES/binary.bin",
        "file://$ARGPARSE_FIXTURES",
        "file://~/x",
        "{bad",
        "a=b",
        "1_0",
        " 60 ",
        "6__0",
        "99999999999999999999",
        "-9223372036854775809",
        "\uff11\uff10",
        "\u00a010",
        "x" * 250,
        "--page-size",
        "--cli-read-timeout",
        "--metadata",
        "--sse-c-key",
        "--bucket-region",
        "--bogus",
        "--quiet=x",
        "--include",
        "--exclude",
        "--sse=",
        "--tags",
        "--grants",
        "--recursive",
        "--profile",
        "--debug",
        "--version",
        "--region",
        "--query",
        "--endpoint-url",
        "--cli",
        "--debug=\u200b",
        "--debug=\x80",
        "https://localhost",
        *metadata_values(),
    ]
    pool.extend("--" + arg["name"] for arg in tables["globals"])
    for command in tables["s3"]["subcommands"]:
        pool.extend(
            "--" + arg["name"] for arg in command["arguments"] if not arg["positional"]
        )
    result = option_cases(tables)
    for _ in range(count):
        base = rng.choice([[], ["s3"], ["s3", "ls"], ["s3", "cp"], ["ec2"], ["s33"]])
        argv = [*base, *rng.choices(pool, k=rng.randrange(10))]
        if rng.random() < 0.3:
            at = rng.randrange(len(argv) + 1)
            argv[at:at] = ["--metadata", metadata_value(rng)]
        result.append({"argv": argv, "scope": "s3"})
    return unique(result)


def native_error_text(error: dict[str, Any]) -> str:
    """Apply only the explicitly permitted repr text differences.

    Invalid-choice suggestions are compared exactly: the native parser ports
    difflib.get_close_matches.
    """
    if "native_text" in error:
        # The capture measured the native spelling of a schema report.
        return error["native_text"]
    text = error["text"]
    prefix = re.match(r"^argument [^:]+: ignored explicit argument ", text)
    if prefix is None:
        prefix = re.match(r"^invalid literal for int\(\) with base 10: ", text)
    if prefix is None:
        return text
    end = text.find("\n", prefix.end())
    end = len(text) if end < 0 else end
    try:
        value = ast.literal_eval(text[prefix.end() : end])
    except (ValueError, SyntaxError):
        # Precision-truncated repr is already checked byte for byte.
        return text
    quote = '"' if "'" in value and '"' not in value else "'"
    parts = [quote]
    for char in value:
        if char in {quote, "\\"}:
            parts.append("\\" + char)
        elif char in {"\n", "\r", "\t"}:
            parts.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[char])
        elif ord(char) < 32 or ord(char) == 127:
            parts.append(f"\\x{ord(char):02x}")
        else:
            parts.append(char)
    parts.append(quote)
    rendered = "".join(parts)
    return text[: prefix.end()] + rendered + text[end:]


RAW_KEYS = (
    "lineage",
    "first_pass",
    "first_pass_seen",
    "globals",
    "globals_seen",
    "args",
    "args_seen",
    "remaining",
    "skipped",
)
# argprocess._unpack_json_cli_arg's ParamError; the decoder's own words
# sit between the framing and the value it received.
JSON_FRAMING = re.compile(
    r"^Error parsing parameter '(?P<parameter>[^']*)': Invalid JSON: "
    r"(?P<message>[^\n]+)\nJSON received: (?P<value>.*)\Z",
    re.DOTALL,
)
# The tokens the json_nonstandard_number and json_invalid_unicode policies
# reject, as they appear in the value the native decoder received.
NONSTANDARD_NUMBER = re.compile(r'(?<![\w"])(NaN|-?Infinity)(?![\w"])')
LONE_SURROGATE = re.compile(r"\\u[dD][89a-fA-F][0-9a-fA-F]{2}")
# CPython's int() refusal that json_integer_digits does not port.
DIGITS_LIMIT_TEXT = "Exceeds the limit (4300 digits)"


def comparable(record: dict[str, Any], *, oracle: bool = False) -> dict[str, Any]:
    keys = ("outcome", "stage", *RAW_KEYS, "values", "error")
    result = {key: record[key] for key in keys}
    if result["error"] is not None:
        result["error"] = {
            "class": record["error"]["class"],
            "text": (
                native_error_text(record["error"])
                if oracle
                else record["error"]["text"]
            ),
            "dest": record["error"].get("dest"),
        }
    return result


def failed_at_or_before(oracle: dict[str, Any], stage: str, dest: str) -> bool:
    """Whether Python rejected at `stage` no later than `dest`, or earlier."""
    if oracle["outcome"] != "reject":
        return False
    if STAGES.index(oracle["stage"]) < STAGES.index(stage):
        return True
    if oracle["stage"] != stage:
        return False
    if stage != "unpack":
        return True
    order = list(oracle["args"])
    return order.index(oracle["error"]["dest"]) <= order.index(dest)


def policy_difference(native: dict[str, Any], oracle: dict[str, Any]) -> str | None:
    """The declared native policy that explains a rejection Python lacks.

    `integer_range` is the i64 policy for int() literals; `integer_unicode`
    is the ASCII-only port of int(), which Python's non-ASCII digits and
    whitespace pass. Neither applies when Python failed at that dest first.
    """
    error = native["error"]
    if native["outcome"] != "reject" or error is None:
        return json_digits_policy(native, oracle)
    dest = error.get("dest")
    if dest is None:
        return None
    if error.get("kind") == "invalid_json":
        return json_syntax_policy(native, oracle)
    if failed_at_or_before(oracle, native["stage"], dest):
        return json_digits_policy(native, oracle)
    text = error["text"]
    if text.startswith("integer outside the 64-bit range"):
        return "integer_range"
    prefix = "invalid literal for int() with base 10: "
    if not text.startswith(prefix):
        return None
    try:
        literal = ast.literal_eval(text[len(prefix) :])
    except (ValueError, SyntaxError):
        return None
    if any(ord(char) > 127 for char in literal):
        return "integer_unicode"
    return None


def failed_before(oracle: dict[str, Any], stage: str, dest: str) -> bool:
    """Whether Python rejected strictly before `dest` at `stage`."""
    if oracle["outcome"] != "reject":
        return False
    if STAGES.index(oracle["stage"]) < STAGES.index(stage):
        return True
    if oracle["stage"] != stage or stage != "unpack":
        return False
    order = list(oracle["args"])
    return order.index(oracle["error"]["dest"]) < order.index(dest)


def json_syntax_policy(native: dict[str, Any], oracle: dict[str, Any]) -> str | None:
    """The JSON policy behind a native "Invalid JSON" Python did not raise:
    a nonstandard number token or a lone surrogate escape in the value the
    decoder received. None when Python rejected the JSON too, or earlier.
    """
    error = native["error"]
    expected = oracle["error"]
    if (
        expected is not None
        and expected.get("comparison") == "json_syntax"
        and expected.get("dest") == error["dest"]
        and DIGITS_LIMIT_TEXT not in expected["text"]
    ):
        return None
    if failed_before(oracle, native["stage"], error["dest"]):
        return None
    framing = JSON_FRAMING.match(error["text"])
    if framing is None:
        return None
    if NONSTANDARD_NUMBER.search(framing.group("value")):
        return "json_nonstandard_number"
    if LONE_SURROGATE.search(framing.group("value")):
        return "json_invalid_unicode"
    return None


def json_digits_policy(native: dict[str, Any], oracle: dict[str, Any]) -> str | None:
    """json_integer_digits: Python's int() refused a token's digit count
    where the native decoder keeps the token as text."""
    expected = oracle["error"]
    if (
        oracle["outcome"] != "reject"
        or oracle["stage"] != "unpack"
        or expected is None
        or DIGITS_LIMIT_TEXT not in expected["text"]
    ):
        return None
    error = native["error"]
    if (
        native["outcome"] == "reject"
        and error is not None
        and error.get("kind") == "invalid_json"
        and error.get("dest") == expected.get("dest")
    ):
        return None
    return "json_integer_digits"


def classify_expected(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    if actual["skipped"]:
        expected["native_expectation"] = actual
        expected["comparison"] = "query_syntax_skipped"
    elif actual["outcome"] == "unsupported":
        # The native chain stops here and Python runs the invocation.
        expected["native_expectation"] = actual
        expected["comparison"] = "unpack_unsupported"
    elif policy := policy_difference(actual, expected):
        expected["native_expectation"] = actual
        expected["policy"] = policy
        expected["comparison"] = policy
    elif json_syntax_case(actual, expected):
        # The decoder's wording is native's own; the corpus test checks
        # the native record, and the framing comparison checks Python's.
        expected["native_expectation"] = actual
        expected["parameter"] = expected["error"]["parameter"]
        expected["comparison"] = "json_syntax"
    elif (
        expected["error"] is not None
        and expected["error"].get("comparison") == "json_number"
    ):
        expected["comparison"] = "json_number"
    elif (
        expected["error"] is not None
        and native_error_text(expected["error"]) != expected["error"]["text"]
    ):
        expected["comparison"] = "declared_diagnostic_difference"


def compare_unsupported(native: dict[str, Any], oracle: dict[str, Any]) -> bool:
    """A native stop at a dest is consistent unless Python failed earlier."""
    for key in RAW_KEYS:
        if native[key] != oracle[key]:
            return False
    if oracle["outcome"] == "reject" and oracle["stage"] == "unpack":
        order = list(oracle["args"])
        stopped = order.index(native["unsupported"])
        return order.index(oracle["error"]["dest"]) >= stopped
    return oracle["outcome"] in {"parsed", "reject"}


def json_syntax_case(native: dict[str, Any], oracle: dict[str, Any]) -> bool:
    """Whether both parsers rejected the same parameter's JSON syntax."""
    error = native["error"]
    expected = oracle["error"]
    return (
        error is not None
        and expected is not None
        and error.get("kind") == "invalid_json"
        and expected.get("comparison") == "json_syntax"
        and error.get("dest") == expected.get("dest")
    )


def compare_json_syntax(native: dict[str, Any], oracle: dict[str, Any]) -> bool:
    """The ParamError framing, parameter, class, dest, and received value
    match; the decoder's explanation is native's own."""
    if any(native[key] != oracle[key] for key in RAW_KEYS):
        return False
    error = native["error"]
    expected = oracle["error"]
    if error["class"] != expected["class"]:
        return False
    framing = JSON_FRAMING.match(error["text"])
    expected_framing = JSON_FRAMING.match(expected["text"])
    if framing is None or expected_framing is None:
        return False
    parameters = {
        framing.group("parameter"),
        expected_framing.group("parameter"),
        error.get("parameter"),
        expected.get("parameter"),
    }
    return len(parameters) == 1 and framing.group("value") == expected_framing.group(
        "value"
    )


def compare_policy(native: dict[str, Any], oracle: dict[str, Any], policy: str) -> bool:
    """A declared rejection is consistent when everything before it matches."""
    if native["stage"] == "unpack" or policy == "json_integer_digits":
        return all(native[key] == oracle[key] for key in RAW_KEYS)
    # A top-level rejection precedes the command parse Python went on to.
    return all(
        native[key] == oracle[key]
        for key in ("first_pass", "first_pass_seen", "globals_seen")
    )


def compare(native: dict[str, Any], oracle: dict[str, Any]) -> bool:
    if native["outcome"] == "unsupported":
        return compare_unsupported(native, oracle)
    if policy := policy_difference(native, oracle):
        return compare_policy(native, oracle, policy)
    if json_syntax_case(native, oracle):
        return compare_json_syntax(native, oracle)
    if native["skipped"] == ["query_syntax"]:
        # The native chain skips the --query syntax check; no later outcome is parity.
        # A help-mode retry that stands is the last main level.
        main = [
            level for level in oracle["levels"] if level["parser"] == "MainArgParser"
        ][-1]
        for key in ("first_pass", "first_pass_seen", "globals_seen"):
            if native[key] != oracle[key]:
                return False
        for key, value in main["namespace"].items():
            if (
                key not in {"verify_ssl", "read_timeout", "connect_timeout"}
                and native["globals"].get(key) != value
            ):
                return False
        return True
    return comparable(native) == comparable(oracle, oracle=True)


def run_capture(binary: Path, request: Path, env: dict[str, str]) -> str:
    return subprocess.run(
        [str(binary), str(request)],
        cwd=FIXTURES,
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=True,
        timeout=120,
    ).stdout


def capture_environment(request: Path) -> dict[str, str]:
    """Isolate the test-only capture executable for this request file.

    The hook forces color per request through FORCE_COLOR and NO_COLOR, so a
    pipe captures color variants. Width is pinned to 80 columns so terminal
    size cannot look like upstream drift in fixtures or parity runs. The
    text encoding of parameter files is pinned to UTF-8 through the locale,
    and ARGPARSE_FIXTURES names the fixture directory for `$VAR` expansion,
    for the same reason.
    """
    env = os.environ.copy()
    env.pop("AWS_CLI_FILE_ENCODING", None)
    env.pop("ARGPARSE_UNSET_VARIABLE", None)
    env.update(
        {
            "AWS_CLI_NATIVE_ROUTER": "python",
            "COLUMNS": "80",
            "LC_ALL": "C.UTF-8",
            "ARGPARSE_FIXTURES": "paramfile",
            "PYTHONPYCACHEPREFIX": str(request.parent / "pycache"),
        }
    )
    if os.name == "nt":
        # Windows reads parameter files in the ANSI code page and takes no
        # locale from the environment, so pin UTF-8 through the setting
        # both parsers honor there instead.
        env["AWS_CLI_FILE_ENCODING"] = "utf-8"
    return env


def run_cases(
    args: argparse.Namespace, cases: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with tempfile.TemporaryDirectory(prefix="argparse-") as directory:
        temp = Path(directory)
        request = temp / "requests.jsonl"
        request.write_text(
            "".join(json.dumps(case) + "\n" for case in cases),
            encoding="utf-8",
        )
        config = temp / "config"
        config.write_text("", encoding="utf-8")
        env = capture_environment(request)
        env.update(
            {
                "AWS_CONFIG_FILE": str(config),
                "AWS_SHARED_CREDENTIALS_FILE": str(config),
                "AWS_EC2_METADATA_DISABLED": "true",
            }
        )
        oracle_text = run_capture(args.capture_binary.resolve(), request, env)
        native_text = subprocess.run(
            [str(args.native_parser.resolve()), "parse", str(request)],
            cwd=FIXTURES,
            env=env,
            capture_output=True,
            encoding="utf-8",
            check=True,
            timeout=120,
        ).stdout
    return (
        [json.loads(line) for line in native_text.split("\n") if line],
        [json.loads(line) for line in oracle_text.split("\n") if line],
    )


def pattern_expectations(binary: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="argparse-patterns-") as directory:
        request = Path(directory) / "requests.jsonl"
        request.write_text('{"patterns":true}\n', encoding="utf-8")
        captured = run_capture(
            binary.resolve(), request, capture_environment(request)
        )
    return json.dumps(json.loads(captured), separators=(",", ":")) + "\n"


# Paramfile errno texts CPython itself spells differently by platform, recorded
# so a corpus captured on one host still states what the other must print. The
# interpreter, not this CLI, chooses these: Windows refuses a directory in
# CreateFileW with ERROR_ACCESS_DENIED and resolves a path through a regular file
# to ERROR_PATH_NOT_FOUND, where POSIX open(2) walks the components and answers
# EISDIR and ENOTDIR.
WINDOWS_ERRNO_TEXTS = {
    "[Errno 21] Is a directory": "[Errno 13] Permission denied",
    "[Errno 20] Not a directory": "[Errno 2] No such file or directory",
}


def windows_error_text(text: str) -> str | None:
    """The text a Windows host prints, or None when it prints the same one."""
    for posix, windows in WINDOWS_ERRNO_TEXTS.items():
        if posix in text:
            return text.replace(posix, windows)
    return None


def compact_records(records: list[dict[str, Any]]) -> str:
    for record in records:
        if record["error"] is not None:
            record["error"]["native_text"] = native_error_text(record["error"])
            windows_text = windows_error_text(record["error"]["native_text"])
            if windows_text is not None:
                record["error"]["windows_native_text"] = windows_text
            record["error"].setdefault("parameter", None)
        for level in record["levels"]:
            if level["error"] is not None:
                level["error"]["native_text"] = native_error_text(level["error"])
            # Engine tests rebuild each level's table from the grammar.
            level.pop("table")
    return "".join(
        json.dumps(record, separators=(",", ":")) + "\n" for record in records
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-binary", type=Path, required=True)
    parser.add_argument("--native-parser", type=Path, required=True)
    parser.add_argument("--aws-cli-source", type=Path)
    parser.add_argument("--native-tables", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fuzz", type=int)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "target/argparse-divergences.jsonl",
    )
    args = parser.parse_args()
    tables = json.loads(args.native_tables.read_text(encoding="utf-8"))
    if args.fuzz is not None:
        cases = fuzz_cases(tables, args.fuzz, args.seed)
    else:
        cases = catalog()
        if args.aws_cli_source:
            cases.extend(upstream_cases(args.aws_cli_source))
        cases = unique(cases)
    native, oracle = run_cases(args, cases)
    if len(native) != len(cases) or len(oracle) != len(cases):
        raise SystemExit("capture did not produce exactly one record per argv")
    divergences = []
    ledger = []
    skipped = 0
    for request, actual, expected in zip(cases, native, oracle):
        classify_expected(actual, expected)
        if actual["skipped"]:
            skipped += 1
        if "comparison" in expected:
            ledger.append(
                {
                    "argv": request["argv"],
                    "seed": args.seed,
                    "classification": expected["comparison"],
                    "native": actual,
                    "python": expected,
                }
            )
        if not compare(actual, expected):
            divergences.append(
                {
                    "argv": request["argv"],
                    "seed": args.seed,
                    "classification": "native_only_parity_failure",
                    "native": actual,
                    "python": expected,
                }
            )
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(
        "".join(json.dumps(row) + "\n" for row in [*ledger, *divergences]),
        encoding="utf-8",
    )
    print(
        f"{len(cases)} cases; native-only parity failures: {len(divergences)}; "
        f"declared differences and fallbacks: {len(ledger)}; "
        f"query checks skipped: {skipped}; seed: {args.seed}"
    )
    if divergences:
        print(f"A/B outcomes retained in {args.ledger}")
        raise SystemExit(1)
    if args.fuzz is not None:
        return
    fixtures = [(PATTERNS, pattern_expectations(args.capture_binary))]
    # The corpus records one POSIX run. CPython spells some errno texts
    # differently on Windows and expands `~user` against the profile
    # directory there, so only a POSIX host can regenerate the corpus or find
    # it stale; the A/B comparison above runs on every host.
    if os.name != "nt":
        fixtures.append((CORPUS, compact_records(oracle)))
    elif args.write:
        raise SystemExit(f"regenerate {CORPUS} on a POSIX host")
    else:
        print(f"{CORPUS.name} staleness is checked on POSIX hosts only")
    if args.write:
        for path, text in fixtures:
            # The checked-in fixtures keep LF on every host.
            path.write_text(text, encoding="utf-8", newline="\n")
    if args.check:
        for path, text in fixtures:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                raise SystemExit(f"{path} is stale; regenerate with --write")


if __name__ == "__main__":
    main()
