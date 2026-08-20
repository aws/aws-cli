"""Shared test utilities for functional2 tests."""

from __future__ import annotations

import asyncio
import json
import os
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from localstub.server import AsyncHTTPTestServer, HTTPResponse
from localstub.tlsproxy import AsyncTLSInterceptProxy

_MODEL_DIR = (
    Path(__file__).resolve().parents[2] / "awscli" / "botocore" / "data"
)


def _get_xml_ns(member_info: dict) -> str:
    """Get the XML namespace URI from a member's xmlNamespace metadata.

    Mirrors botocore's serialization logic: the namespace is declared
    on the payload member definition as xmlNamespace.uri.
    """
    ns_meta = member_info.get("xmlNamespace")
    if isinstance(ns_meta, dict):
        return ns_meta.get("uri", "")
    if isinstance(ns_meta, str):
        return ns_meta
    return ""


_model_cache: dict[str, dict] = {}


def _load_model(service: str) -> dict:
    service_dir = _MODEL_DIR / service
    latest = sorted(service_dir.iterdir())[-1]
    with open(latest / "service-2.json") as f:
        return json.load(f)


def _get_model(service: str) -> dict:
    if service not in _model_cache:
        _model_cache[service] = _load_model(service)
    return _model_cache[service]


def _get_shape(name: str, model: dict) -> dict:
    return model["shapes"][name]


def _get_op(name: str, model: dict) -> dict:
    return model["operations"][name]


def _input_shape(op_name: str, model: dict) -> dict:
    return _get_shape(_get_op(op_name, model)["input"]["shape"], model)


def _build_wire_to_sdk(op_name: str, model: dict) -> dict[str, str]:
    input_sh = _input_shape(op_name, model)
    reverse = {}
    for name, member in input_sh["members"].items():
        loc = member.get("location", "")
        wire = member.get("locationName", name)
        if loc == "header":
            reverse[wire.lower()] = name
        elif loc == "querystring":
            reverse[wire] = name
    return reverse


def _parse_xml_value(
    element: ET.Element, shape: dict, model: dict, ns: str = ""
) -> str | list | dict | None:
    ns_prefix = f"{{{ns}}}" if ns else ""
    shape_type = shape.get("type")
    if shape_type in ("string", "integer", "timestamp", "long"):
        return element.text
    if shape_type == "structure":
        result = {}
        for member_name, member_info in shape.get("members", {}).items():
            member_shape = _get_shape(member_info["shape"], model)
            xml_name = member_info.get("locationName", member_name)
            if member_shape.get("type") == "list":
                if member_shape.get("flattened"):
                    items = element.findall(xml_name)
                    if not items and ns_prefix:
                        items = element.findall(f"{ns_prefix}{xml_name}")
                    if items:
                        item_shape = _get_shape(
                            member_shape["member"]["shape"], model
                        )
                        result[member_name] = [
                            _parse_xml_value(item, item_shape, model, ns)
                            for item in items
                        ]
                else:
                    wrapper = element.find(xml_name)
                    if wrapper is None and ns_prefix:
                        wrapper = element.find(f"{ns_prefix}{xml_name}")
                    if wrapper is not None:
                        item_xml_name = member_shape["member"].get(
                            "locationName", member_name
                        )
                        items = wrapper.findall(item_xml_name)
                        if not items and ns_prefix:
                            items = wrapper.findall(
                                f"{ns_prefix}{item_xml_name}"
                            )
                        item_shape = _get_shape(
                            member_shape["member"]["shape"], model
                        )
                        result[member_name] = [
                            _parse_xml_value(item, item_shape, model, ns)
                            for item in items
                        ]
            else:
                child = element.find(xml_name)
                if child is None and ns_prefix:
                    child = element.find(f"{ns_prefix}{xml_name}")
                if child is not None:
                    result[member_name] = _parse_xml_value(
                        child, member_shape, model, ns
                    )
        return result
    return element.text


def _parse_body(
    body: str | bytes, op_name: str, param_name: str, model: dict
) -> dict | list | None:
    if not body:
        return None
    input_sh = _input_shape(op_name, model)
    member_info = input_sh["members"][param_name]
    shape = _get_shape(member_info["shape"], model)
    ns = _get_xml_ns(member_info)
    root = ET.fromstring(
        body if isinstance(body, str) else body.decode("utf-8")
    )
    return _parse_xml_value(root, shape, model, ns)


def _assert_subset(actual, expected, path: str):
    if isinstance(expected, dict):
        assert isinstance(
            actual, dict
        ), f"{path}: expected dict, got {type(actual)}"
        for k, v in expected.items():
            assert (
                k in actual
            ), f"{path}: missing key {k!r}, have {list(actual.keys())}"
            _assert_subset(actual[k], v, f"{path}.{k}")
    elif isinstance(expected, list):
        assert isinstance(
            actual, list
        ), f"{path}: expected list, got {type(actual)}"
        for i, item in enumerate(expected):
            found = any(_matches(a, item) for a in actual)
            assert found, f"{path}[{i}]: {item!r} not found in {actual!r}"
    else:
        assert (
            actual == expected
        ), f"{path}: expected {expected!r}, got {actual!r}"


def _matches(actual, expected) -> bool:
    try:
        _assert_subset(actual, expected, "")
        return True
    except AssertionError:
        return False


def assert_operation(request, service: str, operation_name: str, /, **params):
    """Assert a request matches the given operation (generic, model-driven).

    Verifies HTTP method, static query params from the URI pattern,
    required members, and each param's presence at its model-specified
    wire location (header, querystring, uri, or body payload).

    For uri params, performs a generic check that the value appears
    somewhere in the request URI (host + path). Service-specific wrappers
    (e.g. assert_s3_operation) add stricter structural checks.

    Args:
        request: The captured HTTP request.
        service: The botocore service name (e.g. "s3", "s3control").
        operation_name: The API operation name (e.g. "PutObject").
        **params: Expected parameters to assert.
    """
    model = _get_model(service)
    op = _get_op(operation_name, model)
    input_sh = _input_shape(operation_name, model)
    method = op["http"]["method"]
    uri_pattern = op["http"]["requestUri"]

    assert (
        request.method == method
    ), f"{operation_name}: expected {method}, got {request.method}"

    _, _, static_query = uri_pattern.partition("?")
    if static_query:
        actual_qs = parse_qs(urlparse(request.path).query)
        for item in static_query.split("&"):
            if "=" in item:
                k, v = item.split("=", 1)
                assert actual_qs.get(k) == [v], (
                    f"{operation_name}: expected ?{k}={v}, "
                    f"got {actual_qs.get(k)!r} in {request.path}"
                )
            else:
                assert (
                    item in request.path
                ), f"{operation_name}: expected ?{item} in {request.path}"

    wire_to_sdk = _build_wire_to_sdk(operation_name, model)
    resolved = {}
    for key, value in params.items():
        if key in input_sh["members"]:
            resolved[key] = value
        elif key.lower() in wire_to_sdk:
            resolved[wire_to_sdk[key.lower()]] = value
        else:
            raise ValueError(
                f"{operation_name}: unknown param {key!r}. "
                f"Not an SDK name or recognized wire name."
            )

    parsed_url = urlparse(request.path)
    actual_qs = parse_qs(parsed_url.query)
    payload_member = input_sh.get("payload")
    host = request.headers.get("host", "")
    full_uri = host + parsed_url.path

    for req_name in input_sh.get("required", []):
        member = input_sh["members"].get(req_name, {})
        loc = member.get("location", "")
        wire_name = member.get("locationName", req_name)
        if loc == "header":
            assert (
                request.headers.get(wire_name) is not None
                or request.headers.get(wire_name.lower()) is not None
            ), (
                f"{operation_name}: required header {wire_name} "
                f"({req_name}) is missing"
            )
        elif loc == "querystring":
            assert wire_name in actual_qs, (
                f"{operation_name}: required query param {wire_name} "
                f"({req_name}) is missing"
            )
        elif loc == "uri":
            assert req_name in resolved, (
                f"{operation_name}: required uri param {req_name!r} "
                f"must be provided to assert_operation to assert the correct operation"
            )

    for param_name, expected in resolved.items():
        member = input_sh["members"][param_name]
        loc = member.get("location", "")
        wire_name = member.get("locationName", param_name)

        if loc == "header":
            actual = request.headers.get(wire_name) or request.headers.get(
                wire_name.lower()
            )
            assert actual == expected, (
                f"{operation_name}.{param_name}: "
                f"expected {wire_name}={expected!r}, got {actual!r}"
            )
        elif loc == "headers":
            prefix = wire_name.lower()
            assert isinstance(
                expected, dict
            ), f"{operation_name}.{param_name}: expected dict for prefix headers"
            for k, v in expected.items():
                hdr = f"{prefix}{k.lower()}"
                actual = request.headers.get(hdr)
                assert actual == v, (
                    f"{operation_name}.{param_name}[{k}]: "
                    f"expected {hdr}={v!r}, got {actual!r}"
                )
        elif loc == "querystring":
            actual_list = actual_qs.get(wire_name, [])
            actual = actual_list[0] if actual_list else None
            assert actual == expected, (
                f"{operation_name}.{param_name}: "
                f"expected ?{wire_name}={expected!r}, got {actual!r}"
            )
        elif loc == "uri":
            assert expected in full_uri, (
                f"{operation_name}.{param_name}: "
                f"expected {expected!r} in URI, got {full_uri!r}"
            )
        elif not loc and payload_member == param_name:
            actual_body = _parse_body(
                request.body, operation_name, param_name, model
            )
            _assert_subset(
                actual_body, expected, f"{operation_name}.{param_name}"
            )


def assert_s3_operation(
    request,
    operation_name: str,
    /,
    addressing_style: str = "virtual",
    **params,
):
    """Assert a request matches an S3 operation.

    Calls assert_operation for generic model-driven checks, then adds
    S3-specific structural assertions for Bucket and Key based on the
    addressing style (virtual-hosted or path-style).

    Args:
        request: The captured HTTP request.
        operation_name: The S3 API operation name (e.g. "PutObject").
        addressing_style: "virtual" (default) or "path".
        **params: Expected parameters to assert.
    """
    assert_operation(request, "s3", operation_name, **params)

    # S3-specific: verify Bucket/Key placement based on addressing style.
    parsed_url = urlparse(request.path)
    host = request.headers.get("host", "")

    bucket = params.get("Bucket")
    key = params.get("Key")

    if bucket is not None:
        if bucket.startswith("arn:"):
            resource = bucket.split(":", 5)[-1]
            name = resource.split("/")[-1].split(":")[-1]
            assert name in host, (
                f"{operation_name}.Bucket: "
                f"expected {name!r} (from ARN) in host, got {host!r}"
            )
        elif addressing_style == "path":
            assert parsed_url.path.startswith(f"/{bucket}"), (
                f"{operation_name}.Bucket: "
                f"expected path-style /{bucket}/..., "
                f"got {parsed_url.path!r}"
            )
        else:
            assert bucket in host, (
                f"{operation_name}.Bucket: "
                f"expected {bucket!r} in host, got {host!r}"
            )

    if key is not None:
        if addressing_style == "path":
            assert parsed_url.path.endswith(f"/{key}"), (
                f"{operation_name}.Key: "
                f"expected path ending with /{key}, "
                f"got {parsed_url.path!r}"
            )
        else:
            assert parsed_url.path == f"/{key}", (
                f"{operation_name}.Key: "
                f"expected /{key}, got {parsed_url.path!r}"
            )


def cli_env(proxy: AsyncTLSInterceptProxy) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_MAX_ATTEMPTS": "1",
        "AWS_CONFIG_FILE": "",
        "AWS_SHARED_CREDENTIALS_FILE": "",
        "HTTPS_PROXY": proxy.endpoint_url,
        "AWS_CA_BUNDLE": str(proxy.ca.ca_pem_path()),
    }


@asynccontextmanager
async def mock_server(on_headers_received=None):
    """Async context manager that yields (server, proxy) for blackbox tests."""
    async with (
        AsyncHTTPTestServer(on_headers_received=on_headers_received) as server,
        AsyncTLSInterceptProxy(server=server) as proxy,
    ):
        yield server, proxy


def setup_responses(
    server: AsyncHTTPTestServer, responses: list[HTTPResponse]
) -> None:
    """Configure server to return responses in order."""
    server.set_response_sequence(responses)


def xml_response(xml: str) -> HTTPResponse:
    return HTTPResponse.raw(
        xml.encode(), headers={"Content-Type": "application/xml"}
    )


def format_requests(server: AsyncHTTPTestServer) -> str:
    """Format captured requests for inclusion in assertion messages."""
    lines = [
        f"  [{i}] {r.method} {r.path} Host={r.headers.get('host')}"
        for i, r in enumerate(server.requests)
    ]
    return (
        f"requests({len(server.requests)}):\n" + "\n".join(lines)
        if lines
        else "requests(0): <none>"
    )


def get_query_params(request) -> dict[str, list[str]]:
    """Parse query string params from a recorded request's path."""
    parsed = urlparse(request.path)
    return parse_qs(parsed.query)


async def run_cli(
    aws_cli: str, args: list[str], env: dict, stdin: bytes | None = None
) -> tuple[bytes, bytes, int]:
    proc = await asyncio.create_subprocess_exec(
        aws_cli,
        *args,
        env=env,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=stdin)
    return stdout, stderr, proc.returncode


def list_objects_xml(
    contents: list[dict] | None = None,
    common_prefixes: list[str] | None = None,
    is_truncated: bool = False,
    next_continuation_token: str | None = None,
    prefix: str | None = None,
) -> str:
    xml = (
        '<?xml version="1.0" ?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    )
    if prefix is None:
        xml += "<Prefix/>"
    else:
        xml += f"<Prefix>{prefix}</Prefix>"
    if is_truncated:
        xml += "<IsTruncated>true</IsTruncated>"
    if next_continuation_token:
        xml += f"<NextContinuationToken>{next_continuation_token}</NextContinuationToken>"
    if contents:
        for obj in contents:
            xml += "<Contents>"
            xml += f"<Key>{obj['Key']}</Key>"
            xml += f"<Size>{obj['Size']}</Size>"
            xml += f"<LastModified>{obj['LastModified']}</LastModified>"
            xml += f"<ETag>{obj.get('ETag', 'd41d8cd98f00b204e9800998ecf8427e')}</ETag>"
            if "StorageClass" in obj:
                xml += f"<StorageClass>{obj['StorageClass']}</StorageClass>"
            xml += "</Contents>"
    if common_prefixes:
        for prefix in common_prefixes:
            xml += (
                f"<CommonPrefixes><Prefix>{prefix}</Prefix></CommonPrefixes>"
            )
    xml += "</ListBucketResult>"
    return xml


def delete_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=204)


def error_response(
    code: str = "InternalError",
    message: str = "Internal Server Error",
    status: int = 500,
) -> HTTPResponse:
    body = (
        '<?xml version="1.0" ?>'
        f"<Error><Code>{code}</Code><Message>{message}</Message></Error>"
    )
    return HTTPResponse.raw(
        body.encode(),
        status=status,
        headers={"Content-Type": "application/xml"},
    )


def create_bucket_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=200, headers={"Location": "/bucket"})


def delete_bucket_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=204)
