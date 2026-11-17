"""Parsed S3 replies and expected requests for the ports of upstream's S3
command tests (tests/functional/s3/__init__.py).

Each function returns what the base class method of the same name does,
for an `ApiSession` to serialize or a test to compare with the decoded
requests. A body is given as bytes, which the wire carries as the object.
"""

from collections.abc import Mapping
from typing import Any
from unittest import mock

type Params = dict[str, Any]
type Request = tuple[str, Params]


def head_object_response(**override: Any) -> Params:
    response: Params = {
        "ContentLength": 100,
        "LastModified": "00:00:00Z",
        "ETag": '"foo-1"',
    }
    response.update(override)
    return response


def list_objects_response(keys: list[str], **override: Any) -> Params:
    contents = []
    for key in keys:
        content: Params = {
            "Key": key,
            "LastModified": "00:00:00Z",
            "Size": 100,
            "ETag": '"foo-1"',
        }
        content.update(override)
        contents.append(content)
    return {"Contents": contents, "CommonPrefixes": []}


def get_object_response(body: bytes = b"foo") -> Params:
    return {"ETag": '"foo-1"', "Body": body}


def create_mpu_response(upload_id: str) -> Params:
    return {"UploadId": upload_id}


def upload_part_copy_response() -> Params:
    return {"CopyPartResult": {"ETag": '"etag"'}}


def get_object_tagging_response(tags: Mapping[str, str]) -> Params:
    return {"TagSet": [{"Key": k, "Value": v} for k, v in tags.items()]}


def list_object_annotations_response(names: list[str]) -> Params:
    return {"Annotations": [{"AnnotationName": name} for name in names]}


def get_object_annotation_response(payload: Any) -> Params:
    return {"AnnotationPayload": payload}


def no_such_key_error_response() -> Params:
    return {
        "Error": {
            "Code": "NoSuchKey",
            "Message": "The specified key does not exist",
        }
    }


def access_denied_error_response() -> Params:
    return {
        "Error": {
            "Code": "AccessDenied",
            "Message": "Operation not allowed",
        }
    }


def precondition_failed_error_response(
    condition: str = "If-None-Match",
) -> Params:
    return {
        "Error": {
            "Code": "PreconditionFailed",
            "Message": "At least one of the pre-conditions you "
            "specified did not hold",
            "Condition": condition,
        }
    }


def mp_copy_responses() -> list[Params]:
    return [
        create_mpu_response("upload_id"),
        upload_part_copy_response(),
        {},
    ]


def head_object_request(bucket: str, key: str, **override: Any) -> Request:
    params: Params = {"Bucket": bucket, "Key": key}
    params.update(override)
    return "HeadObject", params


def list_objects_request(
    bucket: str, prefix: str | None = None, **override: Any
) -> Request:
    params: Params = {"Bucket": bucket}
    if prefix is None:
        params["Prefix"] = ""
    params.update(override)
    return "ListObjectsV2", params


def put_object_request(bucket: str, key: str, **override: Any) -> Request:
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        "ChecksumAlgorithm": "CRC64NVME",
        "Body": mock.ANY,
    }
    params.update(override)
    return "PutObject", params


def get_object_request(bucket: str, key: str, **override: Any) -> Request:
    params: Params = {"Bucket": bucket, "Key": key}
    params.update(override)
    return "GetObject", params


def copy_object_request(
    source_bucket: str,
    source_key: str,
    bucket: str,
    key: str,
    **override: Any,
) -> Request:
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        "CopySource": {"Bucket": source_bucket, "Key": source_key},
    }
    override.setdefault("AnnotationDirective", "EXCLUDE")
    params.update(override)
    return "CopyObject", params


def delete_object_request(
    bucket: str, key: str, **override: Any
) -> Request:
    params: Params = {"Bucket": bucket, "Key": key}
    params.update(override)
    return "DeleteObject", params


def create_mpu_request(bucket: str, key: str, **override: Any) -> Request:
    params: Params = {"Bucket": bucket, "Key": key}
    params.update(override)
    return "CreateMultipartUpload", params


def upload_part_copy_request(
    source_bucket: str,
    source_key: str,
    bucket: str,
    key: str,
    upload_id: str,
    **override: Any,
) -> Request:
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        "CopySource": {"Bucket": source_bucket, "Key": source_key},
        "UploadId": upload_id,
    }
    params.update(override)
    return "UploadPartCopy", params


def complete_mpu_request(
    bucket: str, key: str, upload_id: str, num_parts: int, **override: Any
) -> Request:
    parts = [
        {"ETag": '"etag"', "PartNumber": number + 1}
        for number in range(num_parts)
    ]
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        "UploadId": upload_id,
        "MultipartUpload": {"Parts": parts},
    }
    params.update(override)
    return "CompleteMultipartUpload", params


def get_object_tagging_request(bucket: str, key: str) -> Request:
    return "GetObjectTagging", {"Bucket": bucket, "Key": key}


def put_object_tagging_request(
    bucket: str, key: str, tags: Mapping[str, str]
) -> Request:
    return "PutObjectTagging", {
        "Bucket": bucket,
        "Key": key,
        "Tagging": {
            "TagSet": [{"Key": k, "Value": v} for k, v in tags.items()],
        },
    }


def list_object_annotations_request(
    bucket: str, key: str, **override: Any
) -> Request:
    params: Params = {"Bucket": bucket, "Key": key}
    params.update(override)
    return "ListObjectAnnotations", params


def get_object_annotation_request(
    bucket: str, key: str, annotation_name: str, **override: Any
) -> Request:
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        "AnnotationName": annotation_name,
    }
    params.update(override)
    return "GetObjectAnnotation", params


def put_object_annotation_request(
    bucket: str,
    key: str,
    annotation_name: str,
    payload: Any,
    **override: Any,
) -> Request:
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        "AnnotationName": annotation_name,
        "AnnotationPayload": payload,
    }
    params.update(override)
    return "PutObjectAnnotation", params
