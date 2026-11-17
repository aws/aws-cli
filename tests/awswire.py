from __future__ import annotations

import base64
import binascii
import copy
import importlib
import io
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from email.utils import parsedate_to_datetime
from html import escape
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import parse_qs, unquote, urlsplit
from xml.etree import ElementTree

from localstub import HTTPResponse, RecordedHTTPRequest

if TYPE_CHECKING:
    from awscli.botocore import serialize as botocore_serialize
    from awscli.botocore import session as botocore_session
    from awscli.botocore import utils as botocore_utils
else:
    importlib.import_module("awscli")
    import botocore.serialize as botocore_serialize
    import botocore.session as botocore_session
    import botocore.utils as botocore_utils

S3_XML_NAMESPACE: Final = "http://s3.amazonaws.com/doc/2006-03-01/"
S3_CONTROL_XML_NAMESPACE: Final = (
    "http://awss3control.amazonaws.com/doc/2018-08-20/"
)

_SERVICE_NAMES: Final = (
    "apigateway",
    "autoscaling",
    "cloudformation",
    "cloudfront",
    "cloudsearch",
    "cloudtrail",
    "codedeploy",
    "config",
    "datapipeline",
    "dsql",
    "dynamodb",
    "ecr",
    "ecr-public",
    "ecs",
    "ec2",
    "eks",
    "elasticache",
    "elasticbeanstalk",
    "elb",
    "events",
    "firehose",
    "iam",
    "iot",
    "kinesis",
    "lambda",
    "lightsail",
    "logs",
    "machinelearning",
    "mgn",
    "quicksight",
    "rds",
    "rekognition",
    "resourcegroupstaggingapi",
    "route53",
    "route53domains",
    "s3",
    "s3control",
    "servicecatalog",
    "ses",
    "sesv2",
    "signin",
    "sns",
    "sqs",
    "sso",
    "sso-oidc",
    "ssm",
    "sts",
    "translate",
    "workspaces",
)
_COMMAND_SERVICE_NAMES: Final = {
    "autoscale": "autoscaling",
    "awslambda": "lambda",
    "configservice": "config",
    "ddb": "dynamodb",
    "eventbridge": "events",
    "s3api": "s3",
}
_S3_CONTROL_OPERATIONS: Final = (
    "GetAccessPoint",
    "ListMultiRegionAccessPoints",
)
_XML_NAMESPACES: Final = {
    "s3": S3_XML_NAMESPACE,
    "s3control": S3_CONTROL_XML_NAMESPACE,
}

_OUTPUT_ROOT_NAMES: Final = {
    "CreateMultipartUpload": "InitiateMultipartUploadResult",
    "CopyObject": "CopyObjectResult",
    "DeleteObjects": "DeleteResult",
    "GetBucketLocation": "LocationConstraint",
    "GetObjectTagging": "Tagging",
    "ListBuckets": "ListAllMyBucketsResult",
    "ListObjects": "ListBucketResult",
    "ListObjectsV2": "ListBucketResult",
    "ListObjectVersions": "ListVersionsResult",
    "UploadPartCopy": "CopyPartResult",
}

_DUPLICATE_LITERAL_PREFERENCES: Final = {
    ("DELETE", "lifecycle"): "DeleteBucketLifecycle",
    ("GET", "lifecycle"): "GetBucketLifecycleConfiguration",
    ("GET", "notification"): "GetBucketNotificationConfiguration",
    ("PUT", "lifecycle"): "PutBucketLifecycleConfiguration",
    ("PUT", "notification"): "PutBucketNotificationConfiguration",
}

_SSE_KEY_MEMBERS: Final = {
    "SSECustomerKey",
    "CopySourceSSECustomerKey",
}

_SSE_MD5_MEMBERS: Final = {
    "SSECustomerKeyMD5",
    "CopySourceSSECustomerKeyMD5",
}

_CHUNK_HEADER = re.compile(rb"^([0-9a-fA-F]+)(?:;[^\r\n]*)?\r\n")
_ACCESS_POINT_COPY_SOURCE = re.compile(
    r"^(?P<bucket>arn:[^:]+:s3:[^:]*:[0-9]{12}:"
    r"accesspoint[/:][^/]+)/object/(?P<key>.*)$"
)


class WireBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReconstructedRequest:
    operation_model: Any
    params: dict[str, Any]
    wire_request: RecordedHTTPRequest


@dataclass(frozen=True)
class _RequestTarget:
    bucket: str | None
    key: str | None
    raw_path: str
    path: str
    query: dict[str, list[str]]
    uri_values: dict[str, str]


class AwsWireProtocol:
    def __init__(
        self,
        service_models: Mapping[str, Any],
        command_service_names: Mapping[str, str],
    ) -> None:
        self.service_models = dict(service_models)
        self.command_service_names = dict(command_service_names)

    def reconstruct(
        self,
        request: RecordedHTTPRequest,
        service_hint: str | None = None,
    ) -> ReconstructedRequest:
        target = self._request_target(request)
        service_name = self._service_name(request, service_hint)
        service_model = self.service_models[service_name]
        if service_name == "s3":
            operation_model = self._route_s3_operation(
                service_model,
                request,
                target,
            )
        elif service_name == "s3control":
            operation_model, uri_values = self._route_modeled_operation(
                service_model,
                request,
                target,
                _S3_CONTROL_OPERATIONS,
            )
            target = _RequestTarget(
                bucket=target.bucket,
                key=target.key,
                raw_path=target.raw_path,
                path=target.path,
                query=target.query,
                uri_values=uri_values,
            )
        else:
            operation_model, uri_values = self._route_operation(
                service_model,
                request,
                target,
            )
            target = _RequestTarget(
                bucket=target.bucket,
                key=target.key,
                raw_path=target.raw_path,
                path=target.path,
                query=target.query,
                uri_values=uri_values,
            )
        params = self._parse_params(operation_model, request, target)
        return ReconstructedRequest(operation_model, params, request)

    def serialize_parsed_response(
        self,
        operation_model: Any,
        parsed_response: Mapping[str, Any] | None,
        *,
        status_code: int | None = None,
        headers: Mapping[str, str] | None = None,
        request: RecordedHTTPRequest | None = None,
    ) -> HTTPResponse:
        response = dict(parsed_response or {})
        error = response.get("Error")
        if isinstance(error, Mapping) and "Code" in error:
            return self._error_response(
                operation_model,
                error,
                status_code or 400,
                headers,
            )

        serialized_headers, body = self._serialize_output(
            operation_model,
            response,
        )
        if headers is not None:
            serialized_headers.update(
                {str(name): str(value) for name, value in headers.items()}
            )
        status = status_code or int(
            operation_model.http.get("responseCode", 200)
        )
        return self._fix_response(
            operation_model.name,
            status,
            serialized_headers,
            body,
            request,
        )

    def serialize_queued_response(
        self,
        queued_response: Any,
        operation_model: Any,
        request: RecordedHTTPRequest,
    ) -> HTTPResponse:
        response = queued_response.on_http_request_sent(request)
        status = int(getattr(response, "status_code", 200))
        response_headers = getattr(response, "headers", {})
        body = self._body_bytes(getattr(response, "body", b""))
        headers = {
            str(name): str(value) for name, value in response_headers.items()
        }
        return self._fix_response(
            operation_model.name,
            status,
            headers,
            body,
            request,
        )

    def _request_target(
        self,
        request: RecordedHTTPRequest,
    ) -> _RequestTarget:
        split = urlsplit(request.effective_path)
        raw_path = split.path or "/"
        path = unquote(raw_path)
        query = parse_qs(split.query, keep_blank_values=True)
        host = request.headers.get("host", "").split(":", 1)[0]
        bucket = self._virtual_host_bucket(host)
        key: str | None = None

        path_value = path.lstrip("/")
        if bucket is not None:
            if path_value:
                key = path_value
        elif path_value:
            bucket, separator, remainder = path_value.partition("/")
            if separator:
                key = remainder

        uri_values = {
            name: value
            for name, value in (("Bucket", bucket), ("Key", key))
            if value is not None
        }
        return _RequestTarget(
            bucket,
            key,
            raw_path,
            path,
            query,
            uri_values,
        )

    def _service_name(
        self,
        request: RecordedHTTPRequest,
        service_hint: str | None,
    ) -> str:
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        if ".s3-control." in host or host.startswith("s3-control."):
            return "s3control"
        if host.startswith("s3-outposts.") and urlsplit(
            request.effective_path
        ).path.startswith("/v20180820/"):
            return "s3control"
        if self._virtual_host_bucket(host) is not None:
            return "s3"

        endpoint_matches = [
            service_name
            for service_name, service_model in self.service_models.items()
            if self._host_matches_endpoint(
                host,
                str(service_model.endpoint_prefix).lower(),
            )
        ]
        if endpoint_matches:
            return max(
                endpoint_matches,
                key=lambda name: len(
                    str(self.service_models[name].endpoint_prefix)
                ),
            )

        if service_hint is not None:
            service_name = self.command_service_names.get(
                service_hint,
                service_hint,
            )
            if service_name in self.service_models:
                return service_name
        raise WireBridgeError(
            f"could not identify service for host {host!r}"
        )

    def _host_matches_endpoint(self, host: str, endpoint: str) -> bool:
        return host == endpoint or host.startswith(
            (f"{endpoint}.", f"{endpoint}-fips."),
        )

    def _virtual_host_bucket(self, host: str) -> str | None:
        if not host:
            return None
        for marker in (".s3.", ".s3-", ".s3.dualstack."):
            marker_index = host.find(marker)
            if marker_index > 0:
                return host[:marker_index]
        return None

    def _route_s3_operation(
        self,
        service_model: Any,
        request: RecordedHTTPRequest,
        target: _RequestTarget,
    ) -> Any:
        method = request.method.upper()
        literal_matches = self._literal_operation_matches(
            service_model,
            method,
            target,
        )
        if literal_matches:
            return self._choose_literal_operation(
                service_model,
                method,
                target,
                literal_matches,
            )

        query = target.query
        headers = request.headers
        if method == "GET":
            if target.key is not None and "uploadId" in query:
                return service_model.operation_model("ListParts")
            if target.key is not None:
                return service_model.operation_model("GetObject")
            if target.bucket is not None:
                return service_model.operation_model("ListObjects")
            return service_model.operation_model("ListBuckets")
        if method == "HEAD":
            name = "HeadObject" if target.key is not None else "HeadBucket"
            return service_model.operation_model(name)
        if method == "PUT":
            if target.key is None:
                return service_model.operation_model("CreateBucket")
            if "uploadId" in query:
                name = (
                    "UploadPartCopy"
                    if "x-amz-copy-source" in headers
                    else "UploadPart"
                )
                return service_model.operation_model(name)
            name = (
                "CopyObject" if "x-amz-copy-source" in headers else "PutObject"
            )
            return service_model.operation_model(name)
        if method == "POST" and target.key is not None and "uploadId" in query:
            return service_model.operation_model(
                "CompleteMultipartUpload"
            )
        if method == "DELETE":
            if target.key is not None and "uploadId" in query:
                return service_model.operation_model(
                    "AbortMultipartUpload"
                )
            if target.key is not None:
                return service_model.operation_model("DeleteObject")
            if target.bucket is not None:
                return service_model.operation_model("DeleteBucket")

        raise WireBridgeError(
            f"could not route S3 request: {method} "
            f"{request.effective_path} host="
            f"{request.headers.get('host', '')}"
        )

    def _route_modeled_operation(
        self,
        service_model: Any,
        request: RecordedHTTPRequest,
        target: _RequestTarget,
        operation_names: tuple[str, ...],
    ) -> tuple[Any, dict[str, str]]:
        # A request URI may end in a literal query that tells two operations
        # on one path apart; the operation whose literal query the request
        # carries in full wins over one that names none.
        method = request.method.upper()
        best: tuple[int, Any, dict[str, str]] | None = None
        for operation_name in operation_names:
            operation_model = service_model.operation_model(operation_name)
            if operation_model.http["method"] != method:
                continue
            template, _, literal = str(
                operation_model.http["requestUri"]
            ).partition("?")
            uri_values = self._match_uri_template(template, target.raw_path)
            if uri_values is None:
                continue
            required = parse_qs(literal, keep_blank_values=True)
            if not all(
                name in target.query
                and set(values) - {""} <= set(target.query[name])
                for name, values in required.items()
            ):
                continue
            if best is None or len(required) > best[0]:
                best = (len(required), operation_model, uri_values)
        if best is not None:
            return best[1], best[2]
        raise WireBridgeError(
            f"could not route {service_model.service_name} request: "
            f"{method} {request.effective_path}"
        )

    def _route_operation(
        self,
        service_model: Any,
        request: RecordedHTTPRequest,
        target: _RequestTarget,
    ) -> tuple[Any, dict[str, str]]:
        protocol_name = str(service_model.resolved_protocol)
        if protocol_name in {"query", "ec2"}:
            operation = self._route_query_operation(service_model, request)
            return operation, {}
        if protocol_name == "json":
            operation = self._route_json_operation(service_model, request)
            return operation, {}
        if protocol_name in {"rest-json", "rest-xml"}:
            return self._route_modeled_operation(
                service_model,
                request,
                target,
                tuple(service_model.operation_names),
            )
        raise WireBridgeError(
            f"unsupported {service_model.service_name} protocol: "
            f"{protocol_name}"
        )

    def _match_uri_template(
        self,
        template: str,
        raw_path: str,
    ) -> dict[str, str] | None:
        template_parts = template.strip("/").split("/")
        path_parts = raw_path.strip("/").split("/")
        if len(template_parts) != len(path_parts):
            return None
        values: dict[str, str] = {}
        for template_part, path_part in zip(
            template_parts,
            path_parts,
            strict=True,
        ):
            if template_part.startswith("{") and template_part.endswith("}"):
                name = template_part[1:-1].removesuffix("+")
                values[name] = unquote(path_part)
            elif template_part != path_part:
                return None
        return values

    def _route_query_operation(
        self,
        service_model: Any,
        request: RecordedHTTPRequest,
    ) -> Any:
        body = (request.body or b"").decode("utf-8", errors="strict")
        actions = parse_qs(body).get("Action")
        if actions is None:
            actions = parse_qs(
                urlsplit(request.effective_path).query
            ).get("Action")
        if actions is not None and len(actions) == 1:
            operation_name = actions[0]
            if operation_name in service_model.operation_names:
                return service_model.operation_model(operation_name)
        raise WireBridgeError(
            f"could not route {service_model.service_name} request: "
            f"{request.method.upper()} {request.effective_path} body={body!r}"
        )

    def _route_json_operation(
        self,
        service_model: Any,
        request: RecordedHTTPRequest,
    ) -> Any:
        target = request.headers.get("x-amz-target")
        if target is None:
            raise WireBridgeError(
                f"missing x-amz-target for {service_model.service_name}"
            )
        operation_name = target.rsplit(".", 1)[-1]
        if operation_name not in service_model.operation_names:
            raise WireBridgeError(
                f"unknown {service_model.service_name} target: {target}"
            )
        return service_model.operation_model(operation_name)

    def _literal_operation_matches(
        self,
        service_model: Any,
        method: str,
        target: _RequestTarget,
    ) -> list[tuple[Any, tuple[tuple[str, str], ...]]]:
        matches: list[tuple[Any, tuple[tuple[str, str], ...]]] = []
        for operation_name in service_model.operation_names:
            operation = service_model.operation_model(operation_name)
            if operation.http["method"] != method:
                continue
            request_uri = str(operation.http["requestUri"])
            if "?" not in request_uri:
                continue
            template_path, raw_literals = request_uri.split("?", 1)
            expects_key = "{Key+}" in template_path
            if expects_key != (target.key is not None):
                continue
            literals = tuple(
                self._split_literal_query(item)
                for item in raw_literals.split("&")
            )
            if all(
                name in target.query
                and (value == "" or value in target.query.get(name, []))
                for name, value in literals
            ):
                matches.append((operation, literals))
        return matches

    def _split_literal_query(self, value: str) -> tuple[str, str]:
        name, separator, literal = value.partition("=")
        return name, literal if separator else ""

    def _choose_literal_operation(
        self,
        service_model: Any,
        method: str,
        target: _RequestTarget,
        matches: list[tuple[Any, tuple[tuple[str, str], ...]]],
    ) -> Any:
        max_literals = max(len(literals) for _, literals in matches)
        narrowed = [
            (operation, literals)
            for operation, literals in matches
            if len(literals) == max_literals
        ]

        query_scores = [
            (operation, literals, score)
            for operation, literals in narrowed
            if (
                score := self._required_query_match_score(
                    operation,
                    target,
                )
            )
            is not None
        ]
        if query_scores:
            max_query_score = max(score for _, _, score in query_scores)
            narrowed = [
                (operation, literals)
                for operation, literals, score in query_scores
                if score == max_query_score
            ]
        if len(narrowed) == 1:
            return narrowed[0][0]

        first_literal = narrowed[0][1][0][0]
        preferred_name = _DUPLICATE_LITERAL_PREFERENCES.get(
            (method, first_literal)
        )
        if preferred_name is not None:
            return service_model.operation_model(preferred_name)

        names = ", ".join(operation.name for operation, _ in narrowed)
        raise WireBridgeError(
            f"ambiguous S3 request route for {method} {target.path}: {names}"
        )

    def _required_query_match_score(
        self,
        operation: Any,
        target: _RequestTarget,
    ) -> int | None:
        input_shape = operation.input_shape
        if input_shape is None:
            return 0

        score = 0
        for member_name in input_shape.required_members:
            member_shape = input_shape.members[member_name]
            serialization = member_shape.serialization
            if serialization.get("location") != "querystring":
                continue
            wire_name = str(serialization.get("name", member_name))
            if wire_name not in target.query:
                return None
            score += 1
        return score

    def _parse_params(
        self,
        operation_model: Any,
        request: RecordedHTTPRequest,
        target: _RequestTarget,
    ) -> dict[str, Any]:
        input_shape = operation_model.input_shape
        if input_shape is None:
            return {}

        body, trailers = decode_aws_chunked(
            request.body or b"",
            request.headers.get("content-encoding"),
        )
        protocol_name = str(operation_model.service_model.resolved_protocol)
        params: dict[str, Any] = {}
        for member_name, member_shape in input_shape.members.items():
            serialization = member_shape.serialization
            location = serialization.get("location")
            wire_name = str(serialization.get("name", member_name))
            if location == "uri":
                value = self._uri_value(wire_name, target)
            elif location == "querystring":
                value = self._query_value(
                    target.query,
                    wire_name,
                    member_shape,
                )
            elif location == "header":
                value = request.headers.get(wire_name)
                if value is None:
                    value = trailers.get(wire_name.lower())
                if value is not None:
                    value = self._coerce_scalar(value, member_shape)
            elif location == "headers":
                value = self._header_map(
                    request,
                    wire_name,
                    member_shape,
                )
            else:
                value = None
            if value is not None:
                params[member_name] = value

        if protocol_name in {"query", "ec2"}:
            form = parse_qs(
                body.decode("utf-8", errors="strict"),
                keep_blank_values=True,
            )
            params.update(
                self._parse_query_structure(
                    form,
                    input_shape,
                    protocol_name,
                )
            )
        elif protocol_name in {"json", "rest-json"}:
            self._parse_json_body(params, body, input_shape)
        else:
            payload_name = input_shape.serialization.get("payload")
            if payload_name is not None:
                payload_shape = input_shape.members[payload_name]
                if payload_shape.type_name == "blob":
                    params[payload_name] = body
                elif body:
                    params[payload_name] = self._parse_xml_payload(
                        body,
                        payload_shape,
                    )
            elif body:
                parsed_body = self._parse_xml_payload(body, input_shape)
                if isinstance(parsed_body, Mapping):
                    params.update(parsed_body)

        self._normalize_params(params, request)
        return params

    def _parse_query_structure(
        self,
        form: Mapping[str, list[str]],
        shape: Any,
        protocol_name: str,
        prefix: str = "",
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for member_name, member_shape in shape.members.items():
            wire_name = self._query_member_name(
                member_name,
                member_shape,
                protocol_name,
            )
            member_prefix = f"{prefix}.{wire_name}" if prefix else wire_name
            value = self._parse_query_value(
                form,
                member_shape,
                member_prefix,
                protocol_name,
            )
            if value is not None:
                result[member_name] = value
        return result

    def _parse_query_value(
        self,
        form: Mapping[str, list[str]],
        shape: Any,
        prefix: str,
        protocol_name: str,
    ) -> Any:
        if shape.type_name == "structure":
            value = self._parse_query_structure(
                form,
                shape,
                protocol_name,
                prefix,
            )
            return value or None
        if shape.type_name == "list":
            return self._parse_query_list(
                form,
                shape,
                prefix,
                protocol_name,
            )
        if shape.type_name == "map":
            return self._parse_query_map(
                form,
                shape,
                prefix,
                protocol_name,
            )
        values = form.get(prefix)
        if values is None:
            return None
        return self._coerce_query_scalar(values[0], shape)

    def _parse_query_list(
        self,
        form: Mapping[str, list[str]],
        shape: Any,
        prefix: str,
        protocol_name: str,
    ) -> list[Any] | None:
        if protocol_name == "ec2":
            list_prefix = prefix
        elif shape.serialization.get("flattened"):
            member_name = shape.member.serialization.get("name")
            list_prefix = prefix
            if member_name is not None:
                list_prefix = ".".join(
                    [*prefix.split(".")[:-1], str(member_name)]
                )
        else:
            member_name = shape.member.serialization.get("name", "member")
            list_prefix = f"{prefix}.{member_name}"

        values: list[Any] = []
        index = 1
        while True:
            item_prefix = f"{list_prefix}.{index}"
            item = self._parse_query_value(
                form,
                shape.member,
                item_prefix,
                protocol_name,
            )
            if item is None:
                break
            values.append(item)
            index += 1
        if values:
            return values
        if prefix in form and form[prefix] == [""]:
            return []
        return None

    def _parse_query_map(
        self,
        form: Mapping[str, list[str]],
        shape: Any,
        prefix: str,
        protocol_name: str,
    ) -> dict[Any, Any] | None:
        entry_prefix = (
            prefix
            if shape.serialization.get("flattened")
            else f"{prefix}.entry"
        )
        key_name = self._query_member_name(
            "key",
            shape.key,
            protocol_name,
        )
        value_name = self._query_member_name(
            "value",
            shape.value,
            protocol_name,
        )
        result: dict[Any, Any] = {}
        index = 1
        while True:
            key = self._parse_query_value(
                form,
                shape.key,
                f"{entry_prefix}.{index}.{key_name}",
                protocol_name,
            )
            value = self._parse_query_value(
                form,
                shape.value,
                f"{entry_prefix}.{index}.{value_name}",
                protocol_name,
            )
            if key is None or value is None:
                break
            result[key] = value
            index += 1
        return result or None

    def _query_member_name(
        self,
        default_name: str,
        shape: Any,
        protocol_name: str,
    ) -> str:
        if protocol_name == "ec2":
            query_name = shape.serialization.get("queryName")
            if query_name is not None:
                return str(query_name)
            serialized_name = shape.serialization.get("name")
            if serialized_name is not None:
                value = str(serialized_name)
                return f"{value[:1].upper()}{value[1:]}"
        return str(shape.serialization.get("name", default_name))

    def _coerce_query_scalar(self, value: str, shape: Any) -> Any:
        if shape.type_name in {"integer", "long"}:
            return int(value)
        if shape.type_name in {"double", "float"}:
            return Decimal(value)
        if shape.type_name == "boolean":
            return value.lower() == "true"
        if shape.type_name == "blob":
            return base64.b64decode(value)
        return value

    def _parse_json_body(
        self,
        params: dict[str, Any],
        body: bytes,
        input_shape: Any,
    ) -> None:
        payload_name = input_shape.serialization.get("payload")
        if payload_name is not None:
            payload_shape = input_shape.members[payload_name]
            if payload_shape.type_name == "blob":
                params[payload_name] = body
                return
        if not body:
            return
        try:
            parsed = json.loads(body, parse_float=Decimal)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WireBridgeError(
                f"invalid JSON body for {input_shape.name}: {error}"
            ) from error
        if payload_name is not None:
            params[payload_name] = self._parse_json_shape(
                parsed,
                input_shape.members[payload_name],
            )
            return
        value = self._parse_json_shape(parsed, input_shape)
        if isinstance(value, Mapping):
            params.update(value)

    def _parse_json_shape(self, value: Any, shape: Any) -> Any:
        if shape.type_name == "structure" and not shape.is_document_type:
            if not isinstance(value, Mapping):
                return value
            wire_members = {
                str(member_shape.serialization.get("name", member_name)): (
                    member_name,
                    member_shape,
                )
                for member_name, member_shape in shape.members.items()
            }
            result: dict[str, Any] = {}
            for wire_name, member_value in value.items():
                modeled = wire_members.get(str(wire_name))
                if modeled is None:
                    continue
                member_name, member_shape = modeled
                result[member_name] = self._parse_json_shape(
                    member_value,
                    member_shape,
                )
            return result
        if shape.type_name == "list" and isinstance(value, list):
            return [
                self._parse_json_shape(item, shape.member) for item in value
            ]
        if shape.type_name == "map" and isinstance(value, Mapping):
            return {
                key: self._parse_json_shape(item, shape.value)
                for key, item in value.items()
            }
        if shape.type_name == "blob" and isinstance(value, str):
            return base64.b64decode(value)
        return value

    def _uri_value(
        self,
        wire_name: str,
        target: _RequestTarget,
    ) -> str | None:
        return target.uri_values.get(wire_name)

    def _query_value(
        self,
        query: dict[str, list[str]],
        wire_name: str,
        shape: Any,
    ) -> Any:
        values = query.get(wire_name)
        if values is None:
            return None
        if shape.type_name == "list":
            return [
                self._coerce_scalar(value, shape.member) for value in values
            ]
        return self._coerce_scalar(values[0], shape)

    def _header_map(
        self,
        request: RecordedHTTPRequest,
        prefix: str,
        shape: Any,
    ) -> dict[str, Any] | None:
        values: dict[str, Any] = {}
        lower_prefix = prefix.lower()
        for name, value in request.headers.items():
            if name.lower().startswith(lower_prefix):
                key = name[len(prefix) :]
                values[key] = self._coerce_scalar(value, shape.value)
        return values or None

    def _coerce_scalar(self, value: str, shape: Any) -> Any:
        if shape.type_name in ("integer", "long"):
            return int(value)
        if shape.type_name in ("double", "float"):
            return float(value)
        if shape.type_name == "boolean":
            return value.lower() == "true"
        if shape.type_name == "timestamp":
            return self._parse_timestamp(value)
        if shape.type_name == "blob":
            return base64.b64decode(value)
        if shape.type_name == "list":
            return [
                self._coerce_scalar(item.strip(), shape.member)
                for item in value.split(",")
            ]
        return value

    def _parse_timestamp(self, value: str) -> datetime:
        try:
            return botocore_utils.parse_timestamp(value)
        except (TypeError, ValueError):
            return parsedate_to_datetime(value)

    def _parse_xml_payload(
        self,
        body: bytes,
        shape: Any,
    ) -> Any:
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as error:
            raise WireBridgeError(
                f"invalid XML body for {shape.name}: {error}"
            ) from error
        return self._parse_xml_shape(root, shape)

    def _parse_xml_shape(self, element: Any, shape: Any) -> Any:
        if shape.type_name == "structure":
            result: dict[str, Any] = {}
            children = list(element)
            for member_name, member_shape in shape.members.items():
                wire_name = str(
                    member_shape.serialization.get("name", member_name)
                )
                if member_shape.type_name == "list":
                    value = self._parse_xml_list(
                        children,
                        wire_name,
                        member_shape,
                    )
                else:
                    child = self._find_xml_child(children, wire_name)
                    value = (
                        None
                        if child is None
                        else self._parse_xml_shape(child, member_shape)
                    )
                if value is not None:
                    result[member_name] = value
            return result
        if shape.type_name == "list":
            return [
                self._parse_xml_shape(child, shape.member)
                for child in list(element)
            ]
        if shape.type_name == "map":
            return self._parse_xml_map(element, shape)
        return self._coerce_scalar(element.text or "", shape)

    def _parse_xml_list(
        self,
        children: list[Any],
        wire_name: str,
        shape: Any,
    ) -> list[Any] | None:
        if shape.serialization.get("flattened"):
            matching = [
                child
                for child in children
                if self._xml_name(child.tag) == wire_name
            ]
        else:
            container = self._find_xml_child(children, wire_name)
            if container is None:
                return None
            item_name = str(shape.member.serialization.get("name", "member"))
            matching = [
                child
                for child in list(container)
                if self._xml_name(child.tag) == item_name
            ]
        return [
            self._parse_xml_shape(child, shape.member) for child in matching
        ]

    def _parse_xml_map(self, element: Any, shape: Any) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for entry in list(element):
            children = list(entry)
            key_element = self._find_xml_child(children, "key")
            value_element = self._find_xml_child(children, "value")
            if key_element is None or value_element is None:
                continue
            key = self._parse_xml_shape(key_element, shape.key)
            value = self._parse_xml_shape(value_element, shape.value)
            result[key] = value
        return result

    def _find_xml_child(
        self,
        children: list[Any],
        name: str,
    ) -> Any | None:
        return next(
            (child for child in children if self._xml_name(child.tag) == name),
            None,
        )

    def _xml_name(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _normalize_params(
        self,
        params: dict[str, Any],
        request: RecordedHTTPRequest,
    ) -> None:
        copy_source = params.get("CopySource")
        if isinstance(copy_source, str):
            params["CopySource"] = self._parse_copy_source(copy_source)

        for member_name in _SSE_KEY_MEMBERS:
            value = params.get(member_name)
            if isinstance(value, str):
                params[member_name] = self._decode_sse_key(value)
        for member_name in _SSE_MD5_MEMBERS:
            params.pop(member_name, None)

        content_encoding = params.get("ContentEncoding")
        if isinstance(content_encoding, str):
            encodings = [
                value.strip()
                for value in content_encoding.split(",")
                if value.strip() != "aws-chunked"
            ]
            if encodings:
                params["ContentEncoding"] = ",".join(encodings)
            else:
                params.pop("ContentEncoding")

        decoded_length = request.headers.get("x-amz-decoded-content-length")
        if decoded_length is not None and "ContentLength" in params:
            params["ContentLength"] = int(decoded_length)

    def _parse_copy_source(self, value: str) -> dict[str, str]:
        encoded_path, query_separator, encoded_query = value.lstrip(
            "/"
        ).partition("?")
        decoded_path = unquote(encoded_path)
        access_point = _ACCESS_POINT_COPY_SOURCE.fullmatch(decoded_path)
        if access_point is not None:
            result = {
                "Bucket": access_point["bucket"],
                "Key": access_point["key"],
            }
        else:
            encoded_bucket, path_separator, encoded_key = (
                encoded_path.partition("/")
            )
            result = {
                "Bucket": unquote(encoded_bucket),
                "Key": unquote(encoded_key) if path_separator else "",
            }
        version_ids = None
        if query_separator:
            version_ids = parse_qs(encoded_query).get("versionId")
        if version_ids:
            result["VersionId"] = version_ids[0]
        return result

    def _decode_sse_key(self, value: str) -> str | bytes:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            return value
        try:
            return decoded.decode("utf-8")
        except UnicodeDecodeError:
            return decoded

    def _serialize_output(
        self,
        operation_model: Any,
        parsed_response: dict[str, Any],
    ) -> tuple[dict[str, str], bytes]:
        protocol_name = str(operation_model.service_model.resolved_protocol)
        if protocol_name in {"query", "ec2"}:
            return self._serialize_query_output(
                operation_model,
                parsed_response,
            )
        if protocol_name == "json":
            return self._serialize_json_output(
                operation_model,
                parsed_response,
            )

        serialization_model = copy.deepcopy(operation_model)
        output_shape = serialization_model.output_shape
        if output_shape is None:
            return {}, b""

        self._fold_structured_payload(output_shape, parsed_response)

        endpoint = serialization_model.endpoint
        if endpoint is not None:
            endpoint.clear()
        serialization_model.input_shape = output_shape
        serialization_model.http["requestUri"] = "/"
        root_name = _OUTPUT_ROOT_NAMES.get(
            serialization_model.name,
            f"{serialization_model.name}Result",
        )
        output_shape.serialization["name"] = root_name
        service_name = str(operation_model.service_model.service_name)
        xml_namespace = _XML_NAMESPACES.get(service_name)
        if xml_namespace is not None:
            output_shape.serialization.setdefault(
                "xmlNamespace",
                {"uri": xml_namespace},
            )
        payload_name = output_shape.serialization.get("payload")
        if payload_name is not None:
            payload_shape = output_shape.members[payload_name]
            payload_shape.serialization.setdefault("name", root_name)
            if xml_namespace is not None:
                payload_shape.serialization.setdefault(
                    "xmlNamespace",
                    {"uri": xml_namespace},
                )
        serializer = botocore_serialize.create_serializer(
            protocol_name=protocol_name,
            include_validation=False,
        )
        serialized = serializer.serialize_to_request(
            parsed_response,
            serialization_model,
        )

        headers = {
            str(name): str(value)
            for name, value in serialized["headers"].items()
        }
        return headers, self._body_bytes(serialized["body"])

    def _serialize_json_output(
        self,
        operation_model: Any,
        parsed_response: Mapping[str, Any],
    ) -> tuple[dict[str, str], bytes]:
        output_shape = operation_model.output_shape
        if output_shape is None:
            return {}, b""
        value = self._json_wire_value(parsed_response, output_shape)
        json_version = str(operation_model.metadata.get("jsonVersion", "1.1"))
        return (
            {"Content-Type": f"application/x-amz-json-{json_version}"},
            json.dumps(value, separators=(",", ":")).encode(),
        )

    def _json_wire_value(self, value: Any, shape: Any) -> Any:
        if shape.type_name == "structure" and isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for member_name, member_value in value.items():
                member_shape = shape.members.get(member_name)
                if member_shape is None:
                    result[str(member_name)] = self._json_scalar(member_value)
                    continue
                wire_name = str(
                    member_shape.serialization.get("name", member_name)
                )
                result[wire_name] = self._json_wire_value(
                    member_value,
                    member_shape,
                )
            return result
        if shape.type_name == "list" and isinstance(value, list):
            return [
                self._json_wire_value(item, shape.member) for item in value
            ]
        if shape.type_name == "map" and isinstance(value, Mapping):
            return {
                str(key): self._json_wire_value(item, shape.value)
                for key, item in value.items()
            }
        if shape.type_name == "blob":
            if isinstance(value, str):
                return value
            return base64.b64encode(bytes(value)).decode()
        return self._json_scalar(value)

    def _json_scalar(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            if value == value.to_integral_value():
                return int(value)
            return float(value)
        if isinstance(value, datetime):
            return value.timestamp()
        if isinstance(value, bytes | bytearray | memoryview):
            return base64.b64encode(bytes(value)).decode()
        if isinstance(value, Mapping):
            return {
                str(key): self._json_scalar(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._json_scalar(item) for item in value]
        return value

    def _serialize_query_output(
        self,
        operation_model: Any,
        parsed_response: Mapping[str, Any],
    ) -> tuple[dict[str, str], bytes]:
        output_shape = operation_model.output_shape
        if output_shape is None:
            return {}, b""

        attributes: dict[str, str] = {}
        namespace = operation_model.metadata.get("xmlNamespace")
        if namespace is not None:
            attributes["xmlns"] = str(namespace)
        root = ElementTree.Element(
            f"{operation_model.name}Response",
            attributes,
        )
        wrapper_name = output_shape.serialization.get("resultWrapper")
        result = (
            ElementTree.SubElement(root, str(wrapper_name))
            if wrapper_name is not None
            else root
        )
        for member_name, member_shape in output_shape.members.items():
            value = parsed_response.get(member_name)
            if value is None:
                continue
            wire_name = str(
                member_shape.serialization.get("name", member_name)
            )
            self._append_xml_value(
                result,
                wire_name,
                member_shape,
                value,
            )

        if operation_model.service_model.resolved_protocol == "query":
            response_metadata = ElementTree.SubElement(
                root,
                "ResponseMetadata",
            )
            request_id = ElementTree.SubElement(
                response_metadata,
                "RequestId",
            )
            request_id.text = "awswire"
        return (
            {"Content-Type": "text/xml"},
            ElementTree.tostring(root, encoding="utf-8"),
        )

    def _append_xml_value(
        self,
        parent: Any,
        wire_name: str,
        shape: Any,
        value: Any,
    ) -> None:
        if shape.type_name == "list":
            self._append_xml_list(parent, wire_name, shape, value)
            return
        if shape.type_name == "map":
            self._append_xml_map(parent, wire_name, shape, value)
            return

        element = ElementTree.SubElement(parent, wire_name)
        if shape.type_name == "structure":
            if not isinstance(value, Mapping):
                element.text = str(value)
                return
            for member_name, member_shape in shape.members.items():
                if member_name not in value:
                    continue
                member_wire_name = str(
                    member_shape.serialization.get("name", member_name)
                )
                self._append_xml_value(
                    element,
                    member_wire_name,
                    member_shape,
                    value[member_name],
                )
            return
        element.text = self._xml_scalar(value, shape)

    def _append_xml_list(
        self,
        parent: Any,
        wire_name: str,
        shape: Any,
        value: Any,
    ) -> None:
        items = value if isinstance(value, list | tuple) else [value]
        item_name = str(shape.member.serialization.get("name", "member"))
        if shape.serialization.get("flattened"):
            for item in items:
                self._append_xml_value(
                    parent,
                    item_name or wire_name,
                    shape.member,
                    item,
                )
            return
        container = ElementTree.SubElement(parent, wire_name)
        for item in items:
            self._append_xml_value(
                container,
                item_name,
                shape.member,
                item,
            )

    def _append_xml_map(
        self,
        parent: Any,
        wire_name: str,
        shape: Any,
        value: Any,
    ) -> None:
        container = (
            parent
            if shape.serialization.get("flattened")
            else ElementTree.SubElement(parent, wire_name)
        )
        entry_name = wire_name if shape.serialization.get("flattened") else (
            "entry"
        )
        key_name = str(shape.key.serialization.get("name", "key"))
        value_name = str(shape.value.serialization.get("name", "value"))
        for key, item in value.items():
            entry = ElementTree.SubElement(container, entry_name)
            self._append_xml_value(entry, key_name, shape.key, key)
            self._append_xml_value(entry, value_name, shape.value, item)

    def _xml_scalar(self, value: Any, shape: Any) -> str:
        if shape.type_name == "boolean":
            return "true" if value else "false"
        if shape.type_name == "blob":
            raw = value.encode() if isinstance(value, str) else bytes(value)
            return base64.b64encode(raw).decode()
        if shape.type_name == "timestamp" and isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _fold_structured_payload(
        self,
        output_shape: Any,
        parsed_response: dict[str, Any],
    ) -> None:
        payload_name = output_shape.serialization.get("payload")
        if payload_name is None:
            return
        payload_shape = output_shape.members[payload_name]
        if payload_shape.type_name != "structure":
            return

        top_level_member_names = output_shape.members.keys() - {payload_name}
        payload_member_names = (
            payload_shape.members.keys() - top_level_member_names
        )
        flat_member_names = payload_member_names & parsed_response.keys()
        if not flat_member_names:
            return

        existing_payload = parsed_response.get(payload_name)
        if existing_payload is None:
            payload: dict[str, Any] = {}
        elif isinstance(existing_payload, Mapping):
            payload = dict(existing_payload)
        else:
            raise WireBridgeError(
                f"invalid structured payload for {payload_name}: "
                f"{type(existing_payload).__name__}"
            )

        for member_name in flat_member_names:
            value = parsed_response.pop(member_name)
            if member_name in payload and payload[member_name] != value:
                raise WireBridgeError(
                    f"conflicting values for {payload_name}.{member_name}"
                )
            payload[member_name] = value
        parsed_response[payload_name] = payload

    def _body_bytes(self, body: Any) -> bytes:
        if body is None:
            return b""
        if isinstance(body, bytes):
            return body
        if isinstance(body, str):
            return body.encode()
        if isinstance(body, io.BytesIO):
            return body.getvalue()
        read = getattr(body, "read", None)
        if callable(read):
            value = read()
            if isinstance(value, str):
                return value.encode()
            if isinstance(value, bytes):
                return value
            if isinstance(value, bytearray | memoryview):
                return bytes(value)
            raise TypeError(
                f"response body read returned {type(value).__name__}"
            )
        return bytes(body)

    def _fix_response(
        self,
        operation_name: str,
        status: int,
        headers: dict[str, str],
        body: bytes,
        request: RecordedHTTPRequest | None,
    ) -> HTTPResponse:
        if request is not None:
            byte_range = request.headers.get("range")
        else:
            byte_range = None
        if (
            operation_name == "GetObject"
            and byte_range is not None
            and 200 <= status < 300
        ):
            status = 206
            start, end = self._parse_range(byte_range, len(body))
            total = max(len(body), end + 1)
            headers["Content-Range"] = f"bytes {start}-{end}/{total}"
        if not (
            operation_name in ("HeadBucket", "HeadObject")
            and "Content-Length" in headers
        ):
            headers["Content-Length"] = str(len(body))
        return HTTPResponse.raw(body, status=status, headers=headers)

    def _parse_range(self, value: str, body_length: int) -> tuple[int, int]:
        prefix, separator, range_value = value.partition("=")
        if prefix.lower() != "bytes" or not separator:
            raise WireBridgeError(f"unsupported Range header: {value}")
        start_text, separator, end_text = range_value.partition("-")
        if not separator or not start_text:
            raise WireBridgeError(f"unsupported Range header: {value}")
        start = int(start_text)
        end = int(end_text) if end_text else start + body_length - 1
        return start, end

    def _error_response(
        self,
        operation_model: Any,
        error: Mapping[str, Any],
        status: int,
        headers: Mapping[str, str] | None,
    ) -> HTTPResponse:
        protocol_name = str(operation_model.service_model.resolved_protocol)
        if protocol_name in {"json", "rest-json"}:
            return self._json_error_response(error, status, headers)
        if protocol_name in {"query", "ec2"}:
            return self._query_error_response(
                operation_model,
                error,
                status,
                headers,
            )
        fields = [
            (name, error.get(name))
            for name in (
                "Code",
                "Message",
                "BucketName",
                "Key",
                "RequestId",
                "HostId",
            )
        ]
        body = (
            "<Error>"
            + "".join(
                f"<{name}>{escape(str(value))}</{name}>"
                for name, value in fields
                if value is not None
            )
            + "</Error>"
        )
        response_headers = {"Content-Type": "application/xml"}
        if headers is not None:
            response_headers.update(
                {str(name): str(value) for name, value in headers.items()}
            )
        return HTTPResponse.raw(
            body.encode(),
            status=status,
            headers=response_headers,
        )

    def _json_error_response(
        self,
        error: Mapping[str, Any],
        status: int,
        headers: Mapping[str, str] | None,
    ) -> HTTPResponse:
        code = str(error["Code"])
        message = str(error.get("Message", ""))
        body = json.dumps({"__type": code, "message": message}).encode()
        response_headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "x-amzn-errortype": code,
        }
        if headers is not None:
            response_headers.update(
                {str(name): str(value) for name, value in headers.items()}
            )
        return HTTPResponse.raw(
            body,
            status=status,
            headers=response_headers,
        )

    def _query_error_response(
        self,
        operation_model: Any,
        error: Mapping[str, Any],
        status: int,
        headers: Mapping[str, str] | None,
    ) -> HTTPResponse:
        attributes: dict[str, str] = {}
        namespace = operation_model.metadata.get("xmlNamespace")
        if namespace is not None:
            attributes["xmlns"] = str(namespace)
        root = ElementTree.Element("ErrorResponse", attributes)
        error_element = ElementTree.SubElement(root, "Error")
        for name in ("Type", "Code", "Message"):
            value = error.get(name)
            if value is None and name == "Type":
                value = "Sender"
            if value is not None:
                element = ElementTree.SubElement(error_element, name)
                element.text = str(value)
        request_id = ElementTree.SubElement(root, "RequestId")
        request_id.text = str(
            error.get("RequestId", "awswire")
        )
        response_headers = {"Content-Type": "text/xml"}
        if headers is not None:
            response_headers.update(
                {str(name): str(value) for name, value in headers.items()}
            )
        return HTTPResponse.raw(
            ElementTree.tostring(root, encoding="utf-8"),
            status=status,
            headers=response_headers,
        )


def create_aws_wire_protocol(
    service_names: Iterable[str] = _SERVICE_NAMES,
) -> AwsWireProtocol:
    """A protocol for `service_names`, every service the blackbox tests
    script unless a caller names fewer: each model loaded costs a parse of
    its botocore JSON."""
    session = botocore_session.get_session()
    service_models = {
        service_name: session.get_service_model(service_name)
        for service_name in service_names
    }
    return AwsWireProtocol(service_models, _COMMAND_SERVICE_NAMES)


def decode_aws_chunked(
    body: bytes,
    content_encoding: str | None,
) -> tuple[bytes, dict[str, str]]:
    if content_encoding is None or "aws-chunked" not in content_encoding:
        return body, {}

    decoded = bytearray()
    trailers: dict[str, str] = {}
    offset = 0
    while offset < len(body):
        match = _CHUNK_HEADER.match(body[offset:])
        if match is None:
            raise WireBridgeError("invalid aws-chunked request body")
        size = int(match.group(1), 16)
        offset += match.end()
        if size == 0:
            trailer_end = body.find(b"\r\n\r\n", offset)
            raw_trailers = (
                body[offset:]
                if trailer_end == -1
                else body[offset:trailer_end]
            )
            for line in raw_trailers.split(b"\r\n"):
                name, separator, value = line.partition(b":")
                if separator:
                    trailers[name.decode().lower()] = value.decode().strip()
            break
        end = offset + size
        if end + 2 > len(body) or body[end : end + 2] != b"\r\n":
            raise WireBridgeError("truncated aws-chunked request body")
        decoded.extend(body[offset:end])
        offset = end + 2
    return bytes(decoded), trailers
