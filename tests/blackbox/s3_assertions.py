"""Per-operation S3 assertion helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse

# Known list wrapper elements in S3 XML request bodies.
_LIST_ELEMENTS = {"Tags", "TagSet", "Parts"}


def _check_bucket(request, bucket: str, addressing_style: str, op_name: str):
    """Assert Bucket is in the correct location based on addressing style."""
    parsed_url = urlparse(request.effective_path)
    host = request.headers.get("host", "")
    if bucket.startswith("arn:"):
        resource = bucket.split(":", 5)[-1]
        name = resource.split("/")[-1].split(":")[-1]
        assert (
            name in host
        ), f"{op_name}.Bucket: expected {name!r} (from ARN) in host, got {host!r}"
    elif addressing_style == "path":
        assert parsed_url.path.startswith(
            f"/{bucket}"
        ), f"{op_name}.Bucket: expected path-style /{bucket}/..., got {parsed_url.path!r}"
    else:
        assert (
            bucket in host
        ), f"{op_name}.Bucket: expected {bucket!r} in host, got {host!r}"


def _check_key(request, key: str, addressing_style: str, op_name: str):
    """Assert Key is in the correct path location based on addressing style."""
    parsed_url = urlparse(request.effective_path)
    if addressing_style == "path":
        assert parsed_url.path.endswith(
            f"/{key}"
        ), f"{op_name}.Key: expected path ending with /{key}, got {parsed_url.path!r}"
    else:
        assert (
            parsed_url.path == f"/{key}"
        ), f"{op_name}.Key: expected /{key}, got {parsed_url.path!r}"


def _check_params(request, params: dict, param_map: dict, op_name: str):
    """Check optional params against the wire using a lookup map.

    param_map maps param_name -> (location, wire_name) where location
    is "header", "headers", or "querystring".
    """
    parsed_url = urlparse(request.effective_path)
    actual_qs = parse_qs(parsed_url.query)
    for param_name, expected in params.items():
        if param_name not in param_map:
            raise ValueError(f"{op_name}: unknown param {param_name!r}")
        loc, wire = param_map[param_name]
        if loc == "header":
            actual = request.headers.get(wire) or request.headers.get(
                wire.lower()
            )
            assert (
                actual == expected
            ), f"{op_name}.{param_name}: expected {wire}={expected!r}, got {actual!r}"
        elif loc == "headers":
            prefix = wire.lower()
            assert isinstance(expected, dict)
            for k, v in expected.items():
                hdr = f"{prefix}{k.lower()}"
                actual = request.headers.get(hdr)
                assert (
                    actual == v
                ), f"{op_name}.{param_name}[{k}]: expected {hdr}={v!r}, got {actual!r}"
        elif loc == "querystring":
            actual_list = actual_qs.get(wire, [])
            actual = actual_list[0] if actual_list else None
            assert (
                actual == expected
            ), f"{op_name}.{param_name}: expected ?{wire}={expected!r}, got {actual!r}"
        elif loc == "payload":
            actual_body = _parse_xml_body(request.body, wire)
            _assert_subset(
                actual_body,
                expected,
                f"{op_name}.{param_name}",
                coerce_strings=True,
            )


def _assert_subset(actual, expected, path: str, coerce_strings: bool = False):
    """Assert expected is a subset of actual (recursive).

    When coerce_strings is True, leaf values are compared as strings.
    This is used for XML body comparisons where the parser returns all
    values as strings, but test authors may pass native types.
    """
    if isinstance(expected, dict):
        assert isinstance(
            actual, dict
        ), f"{path}: expected dict, got {type(actual)}"
        for k, v in expected.items():
            assert (
                k in actual
            ), f"{path}: missing key {k!r}, have {list(actual.keys())}"
            _assert_subset(actual[k], v, f"{path}.{k}", coerce_strings)
    elif isinstance(expected, list):
        assert isinstance(
            actual, list
        ), f"{path}: expected list, got {type(actual)}"
        for i, item in enumerate(expected):
            found = any(_matches(a, item, coerce_strings) for a in actual)
            assert found, f"{path}[{i}]: {item!r} not found in {actual!r}"
    else:
        if coerce_strings:
            assert str(actual) == str(
                expected
            ), f"{path}: expected {expected!r}, got {actual!r}"
        else:
            assert (
                actual == expected
            ), f"{path}: expected {expected!r}, got {actual!r}"


def _matches(actual, expected, coerce_strings: bool = False) -> bool:
    try:
        _assert_subset(actual, expected, "", coerce_strings)
        return True
    except AssertionError:
        return False


def _parse_xml_body(body: str | bytes, ns: str) -> dict | None:
    """Parse an XML request body into a dict, handling namespace."""
    if not body:
        return None
    root = ET.fromstring(
        body if isinstance(body, str) else body.decode("utf-8")
    )
    ns_prefix = f"{{{ns}}}" if ns else ""
    return _xml_to_dict(root, ns_prefix)


def _xml_to_dict(element, ns_prefix: str) -> dict | str | list:
    """Recursively convert XML element to dict."""
    children = list(element)
    if not children:
        return element.text
    own_tag = element.tag
    if own_tag.startswith(ns_prefix):
        own_tag = own_tag[len(ns_prefix) :]
    child_tags = set()
    for c in children:
        tag = c.tag
        if tag.startswith(ns_prefix):
            tag = tag[len(ns_prefix) :]
        child_tags.add(tag)
    is_list = (
        len(child_tags) == 1 and len(children) > 1
    ) or own_tag in _LIST_ELEMENTS
    if is_list:
        return [_xml_to_dict(c, ns_prefix) for c in children]
    result = {}
    for child in children:
        tag = child.tag
        if tag.startswith(ns_prefix):
            tag = tag[len(ns_prefix) :]
        child_value = _xml_to_dict(child, ns_prefix)
        if tag in result:
            existing = result[tag]
            if isinstance(existing, list):
                existing.append(child_value)
            else:
                result[tag] = [existing, child_value]
        else:
            result[tag] = child_value
    return result


# PutObject: PUT /{Bucket}/{Key+}
_PUT_OBJECT_PARAMS = {
    "ACL": ("header", "x-amz-acl"),
    "CacheControl": ("header", "Cache-Control"),
    "ContentDisposition": ("header", "Content-Disposition"),
    "ContentEncoding": ("header", "Content-Encoding"),
    "ContentLanguage": ("header", "Content-Language"),
    "ContentLength": ("header", "Content-Length"),
    "ContentMD5": ("header", "Content-MD5"),
    "ContentType": ("header", "Content-Type"),
    "ChecksumAlgorithm": ("header", "x-amz-sdk-checksum-algorithm"),
    "ChecksumCRC32": ("header", "x-amz-checksum-crc32"),
    "ChecksumCRC32C": ("header", "x-amz-checksum-crc32c"),
    "ChecksumCRC64NVME": ("header", "x-amz-checksum-crc64nvme"),
    "ChecksumSHA1": ("header", "x-amz-checksum-sha1"),
    "ChecksumSHA256": ("header", "x-amz-checksum-sha256"),
    "ChecksumSHA512": ("header", "x-amz-checksum-sha512"),
    "ChecksumMD5": ("header", "x-amz-checksum-md5"),
    "ChecksumXXHASH64": ("header", "x-amz-checksum-xxhash64"),
    "ChecksumXXHASH3": ("header", "x-amz-checksum-xxhash3"),
    "ChecksumXXHASH128": ("header", "x-amz-checksum-xxhash128"),
    "Expires": ("header", "Expires"),
    "IfMatch": ("header", "If-Match"),
    "IfNoneMatch": ("header", "If-None-Match"),
    "GrantFullControl": ("header", "x-amz-grant-full-control"),
    "GrantRead": ("header", "x-amz-grant-read"),
    "GrantReadACP": ("header", "x-amz-grant-read-acp"),
    "GrantWriteACP": ("header", "x-amz-grant-write-acp"),
    "WriteOffsetBytes": ("header", "x-amz-write-offset-bytes"),
    "ServerSideEncryption": ("header", "x-amz-server-side-encryption"),
    "StorageClass": ("header", "x-amz-storage-class"),
    "WebsiteRedirectLocation": ("header", "x-amz-website-redirect-location"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "SSEKMSKeyId": ("header", "x-amz-server-side-encryption-aws-kms-key-id"),
    "SSEKMSEncryptionContext": (
        "header",
        "x-amz-server-side-encryption-context",
    ),
    "BucketKeyEnabled": (
        "header",
        "x-amz-server-side-encryption-bucket-key-enabled",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "Tagging": ("header", "x-amz-tagging"),
    "ObjectLockMode": ("header", "x-amz-object-lock-mode"),
    "ObjectLockRetainUntilDate": (
        "header",
        "x-amz-object-lock-retain-until-date",
    ),
    "ObjectLockLegalHoldStatus": ("header", "x-amz-object-lock-legal-hold"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "Metadata": ("headers", "x-amz-meta-"),
}


def assert_put_object(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a PutObject (PUT /{Bucket}/{Key+})."""
    assert (
        request.method == "PUT"
    ), f"PutObject: expected PUT, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "PutObject")
    _check_key(request, Key, addressing_style, "PutObject")
    _check_params(request, params, _PUT_OBJECT_PARAMS, "PutObject")


# HeadObject: HEAD /{Bucket}/{Key+}
_HEAD_OBJECT_PARAMS = {
    "IfMatch": ("header", "If-Match"),
    "IfModifiedSince": ("header", "If-Modified-Since"),
    "IfNoneMatch": ("header", "If-None-Match"),
    "IfUnmodifiedSince": ("header", "If-Unmodified-Since"),
    "Range": ("header", "Range"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "ChecksumMode": ("header", "x-amz-checksum-mode"),
    "ResponseCacheControl": ("querystring", "response-cache-control"),
    "ResponseContentDisposition": (
        "querystring",
        "response-content-disposition",
    ),
    "ResponseContentEncoding": ("querystring", "response-content-encoding"),
    "ResponseContentLanguage": ("querystring", "response-content-language"),
    "ResponseContentType": ("querystring", "response-content-type"),
    "ResponseExpires": ("querystring", "response-expires"),
    "VersionId": ("querystring", "versionId"),
    "PartNumber": ("querystring", "partNumber"),
}


def assert_head_object(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a HeadObject (HEAD /{Bucket}/{Key+})."""
    assert (
        request.method == "HEAD"
    ), f"HeadObject: expected HEAD, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "HeadObject")
    _check_key(request, Key, addressing_style, "HeadObject")
    _check_params(request, params, _HEAD_OBJECT_PARAMS, "HeadObject")


# GetObject: GET /{Bucket}/{Key+}
_GET_OBJECT_PARAMS = {
    "IfMatch": ("header", "If-Match"),
    "IfModifiedSince": ("header", "If-Modified-Since"),
    "IfNoneMatch": ("header", "If-None-Match"),
    "IfUnmodifiedSince": ("header", "If-Unmodified-Since"),
    "Range": ("header", "Range"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "ChecksumMode": ("header", "x-amz-checksum-mode"),
    "ResponseCacheControl": ("querystring", "response-cache-control"),
    "ResponseContentDisposition": (
        "querystring",
        "response-content-disposition",
    ),
    "ResponseContentEncoding": ("querystring", "response-content-encoding"),
    "ResponseContentLanguage": ("querystring", "response-content-language"),
    "ResponseContentType": ("querystring", "response-content-type"),
    "ResponseExpires": ("querystring", "response-expires"),
    "VersionId": ("querystring", "versionId"),
    "PartNumber": ("querystring", "partNumber"),
}


def assert_get_object(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a GetObject (GET /{Bucket}/{Key+})."""
    assert (
        request.method == "GET"
    ), f"GetObject: expected GET, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "GetObject")
    _check_key(request, Key, addressing_style, "GetObject")
    _check_params(request, params, _GET_OBJECT_PARAMS, "GetObject")


# DeleteObject: DELETE /{Bucket}/{Key+}
_DELETE_OBJECT_PARAMS = {
    "MFA": ("header", "x-amz-mfa"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "BypassGovernanceRetention": (
        "header",
        "x-amz-bypass-governance-retention",
    ),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "IfMatch": ("header", "If-Match"),
    "IfMatchLastModifiedTime": ("header", "x-amz-if-match-last-modified-time"),
    "IfMatchSize": ("header", "x-amz-if-match-size"),
    "VersionId": ("querystring", "versionId"),
}


def assert_delete_object(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a DeleteObject (DELETE /{Bucket}/{Key+})."""
    assert (
        request.method == "DELETE"
    ), f"DeleteObject: expected DELETE, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "DeleteObject")
    _check_key(request, Key, addressing_style, "DeleteObject")
    _check_params(request, params, _DELETE_OBJECT_PARAMS, "DeleteObject")


# CopyObject: PUT /{Bucket}/{Key+}
_COPY_OBJECT_PARAMS = {
    "ACL": ("header", "x-amz-acl"),
    "CacheControl": ("header", "Cache-Control"),
    "ChecksumAlgorithm": ("header", "x-amz-checksum-algorithm"),
    "ContentDisposition": ("header", "Content-Disposition"),
    "ContentEncoding": ("header", "Content-Encoding"),
    "ContentLanguage": ("header", "Content-Language"),
    "ContentType": ("header", "Content-Type"),
    "CopySource": ("header", "x-amz-copy-source"),
    "CopySourceIfMatch": ("header", "x-amz-copy-source-if-match"),
    "CopySourceIfModifiedSince": (
        "header",
        "x-amz-copy-source-if-modified-since",
    ),
    "CopySourceIfNoneMatch": ("header", "x-amz-copy-source-if-none-match"),
    "CopySourceIfUnmodifiedSince": (
        "header",
        "x-amz-copy-source-if-unmodified-since",
    ),
    "Expires": ("header", "Expires"),
    "GrantFullControl": ("header", "x-amz-grant-full-control"),
    "GrantRead": ("header", "x-amz-grant-read"),
    "GrantReadACP": ("header", "x-amz-grant-read-acp"),
    "GrantWriteACP": ("header", "x-amz-grant-write-acp"),
    "IfMatch": ("header", "If-Match"),
    "IfNoneMatch": ("header", "If-None-Match"),
    "MetadataDirective": ("header", "x-amz-metadata-directive"),
    "TaggingDirective": ("header", "x-amz-tagging-directive"),
    "AnnotationDirective": ("header", "x-amz-object-annotation-directive"),
    "ServerSideEncryption": ("header", "x-amz-server-side-encryption"),
    "StorageClass": ("header", "x-amz-storage-class"),
    "WebsiteRedirectLocation": ("header", "x-amz-website-redirect-location"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "SSEKMSKeyId": ("header", "x-amz-server-side-encryption-aws-kms-key-id"),
    "SSEKMSEncryptionContext": (
        "header",
        "x-amz-server-side-encryption-context",
    ),
    "BucketKeyEnabled": (
        "header",
        "x-amz-server-side-encryption-bucket-key-enabled",
    ),
    "CopySourceSSECustomerAlgorithm": (
        "header",
        "x-amz-copy-source-server-side-encryption-customer-algorithm",
    ),
    "CopySourceSSECustomerKey": (
        "header",
        "x-amz-copy-source-server-side-encryption-customer-key",
    ),
    "CopySourceSSECustomerKeyMD5": (
        "header",
        "x-amz-copy-source-server-side-encryption-customer-key-MD5",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "Tagging": ("header", "x-amz-tagging"),
    "ObjectLockMode": ("header", "x-amz-object-lock-mode"),
    "ObjectLockRetainUntilDate": (
        "header",
        "x-amz-object-lock-retain-until-date",
    ),
    "ObjectLockLegalHoldStatus": ("header", "x-amz-object-lock-legal-hold"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "ExpectedSourceBucketOwner": (
        "header",
        "x-amz-source-expected-bucket-owner",
    ),
    "Metadata": ("headers", "x-amz-meta-"),
}


def assert_copy_object(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a CopyObject (PUT /{Bucket}/{Key+})."""
    assert (
        request.method == "PUT"
    ), f"CopyObject: expected PUT, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "CopyObject")
    _check_key(request, Key, addressing_style, "CopyObject")
    assert (
        request.headers.get("x-amz-copy-source") is not None
        or request.headers.get("x-amz-copy-source") is not None
    ), "CopyObject: required header x-amz-copy-source (CopySource) is missing"
    _check_params(request, params, _COPY_OBJECT_PARAMS, "CopyObject")


# ListObjectsV2: GET /{Bucket}?list-type=2
_LIST_OBJECTS_V2_PARAMS = {
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "OptionalObjectAttributes": ("header", "x-amz-optional-object-attributes"),
    "Delimiter": ("querystring", "delimiter"),
    "EncodingType": ("querystring", "encoding-type"),
    "MaxKeys": ("querystring", "max-keys"),
    "Prefix": ("querystring", "prefix"),
    "ContinuationToken": ("querystring", "continuation-token"),
    "FetchOwner": ("querystring", "fetch-owner"),
    "StartAfter": ("querystring", "start-after"),
}


def assert_list_objects_v2(
    request, Bucket: str, addressing_style: str = "virtual", **params
):
    """Assert request is a ListObjectsV2 (GET /{Bucket}?list-type=2)."""
    assert (
        request.method == "GET"
    ), f"ListObjectsV2: expected GET, got {request.method}"
    _qs = parse_qs(urlparse(request.effective_path).query)
    assert _qs.get("list-type") == [
        "2"
    ], "ListObjectsV2: expected ?list-type=2 in query"
    _check_bucket(request, Bucket, addressing_style, "ListObjectsV2")
    _check_params(request, params, _LIST_OBJECTS_V2_PARAMS, "ListObjectsV2")


# CreateMultipartUpload: POST /{Bucket}/{Key+}?uploads
_CREATE_MULTIPART_UPLOAD_PARAMS = {
    "ACL": ("header", "x-amz-acl"),
    "CacheControl": ("header", "Cache-Control"),
    "ContentDisposition": ("header", "Content-Disposition"),
    "ContentEncoding": ("header", "Content-Encoding"),
    "ContentLanguage": ("header", "Content-Language"),
    "ContentType": ("header", "Content-Type"),
    "Expires": ("header", "Expires"),
    "GrantFullControl": ("header", "x-amz-grant-full-control"),
    "GrantRead": ("header", "x-amz-grant-read"),
    "GrantReadACP": ("header", "x-amz-grant-read-acp"),
    "GrantWriteACP": ("header", "x-amz-grant-write-acp"),
    "ServerSideEncryption": ("header", "x-amz-server-side-encryption"),
    "StorageClass": ("header", "x-amz-storage-class"),
    "WebsiteRedirectLocation": ("header", "x-amz-website-redirect-location"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "SSEKMSKeyId": ("header", "x-amz-server-side-encryption-aws-kms-key-id"),
    "SSEKMSEncryptionContext": (
        "header",
        "x-amz-server-side-encryption-context",
    ),
    "BucketKeyEnabled": (
        "header",
        "x-amz-server-side-encryption-bucket-key-enabled",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "Tagging": ("header", "x-amz-tagging"),
    "ObjectLockMode": ("header", "x-amz-object-lock-mode"),
    "ObjectLockRetainUntilDate": (
        "header",
        "x-amz-object-lock-retain-until-date",
    ),
    "ObjectLockLegalHoldStatus": ("header", "x-amz-object-lock-legal-hold"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "ChecksumAlgorithm": ("header", "x-amz-checksum-algorithm"),
    "ChecksumType": ("header", "x-amz-checksum-type"),
    "Metadata": ("headers", "x-amz-meta-"),
}


def assert_create_multipart_upload(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a CreateMultipartUpload (POST /{Bucket}/{Key+}?uploads)."""
    assert (
        request.method == "POST"
    ), f"CreateMultipartUpload: expected POST, got {request.method}"
    _qs = parse_qs(urlparse(request.effective_path).query)
    assert (
        "uploads" in urlparse(request.effective_path).query
    ), f"CreateMultipartUpload: expected ?uploads in {request.effective_path}"
    _check_bucket(request, Bucket, addressing_style, "CreateMultipartUpload")
    _check_key(request, Key, addressing_style, "CreateMultipartUpload")
    _check_params(
        request,
        params,
        _CREATE_MULTIPART_UPLOAD_PARAMS,
        "CreateMultipartUpload",
    )


# UploadPart: PUT /{Bucket}/{Key+}
_UPLOAD_PART_PARAMS = {
    "ContentLength": ("header", "Content-Length"),
    "ContentMD5": ("header", "Content-MD5"),
    "ChecksumAlgorithm": ("header", "x-amz-sdk-checksum-algorithm"),
    "ChecksumCRC32": ("header", "x-amz-checksum-crc32"),
    "ChecksumCRC32C": ("header", "x-amz-checksum-crc32c"),
    "ChecksumCRC64NVME": ("header", "x-amz-checksum-crc64nvme"),
    "ChecksumSHA1": ("header", "x-amz-checksum-sha1"),
    "ChecksumSHA256": ("header", "x-amz-checksum-sha256"),
    "ChecksumSHA512": ("header", "x-amz-checksum-sha512"),
    "ChecksumMD5": ("header", "x-amz-checksum-md5"),
    "ChecksumXXHASH64": ("header", "x-amz-checksum-xxhash64"),
    "ChecksumXXHASH3": ("header", "x-amz-checksum-xxhash3"),
    "ChecksumXXHASH128": ("header", "x-amz-checksum-xxhash128"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "PartNumber": ("querystring", "partNumber"),
    "UploadId": ("querystring", "uploadId"),
}


def assert_upload_part(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a UploadPart (PUT /{Bucket}/{Key+})."""
    assert (
        request.method == "PUT"
    ), f"UploadPart: expected PUT, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "UploadPart")
    _check_key(request, Key, addressing_style, "UploadPart")
    assert "partNumber" in parse_qs(
        urlparse(request.effective_path).query
    ), "UploadPart: required query param partNumber (PartNumber) is missing"
    assert "uploadId" in parse_qs(
        urlparse(request.effective_path).query
    ), "UploadPart: required query param uploadId (UploadId) is missing"
    _check_params(request, params, _UPLOAD_PART_PARAMS, "UploadPart")


# UploadPartCopy: PUT /{Bucket}/{Key+}
_UPLOAD_PART_COPY_PARAMS = {
    "CopySource": ("header", "x-amz-copy-source"),
    "CopySourceIfMatch": ("header", "x-amz-copy-source-if-match"),
    "CopySourceIfModifiedSince": (
        "header",
        "x-amz-copy-source-if-modified-since",
    ),
    "CopySourceIfNoneMatch": ("header", "x-amz-copy-source-if-none-match"),
    "CopySourceIfUnmodifiedSince": (
        "header",
        "x-amz-copy-source-if-unmodified-since",
    ),
    "CopySourceRange": ("header", "x-amz-copy-source-range"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "CopySourceSSECustomerAlgorithm": (
        "header",
        "x-amz-copy-source-server-side-encryption-customer-algorithm",
    ),
    "CopySourceSSECustomerKey": (
        "header",
        "x-amz-copy-source-server-side-encryption-customer-key",
    ),
    "CopySourceSSECustomerKeyMD5": (
        "header",
        "x-amz-copy-source-server-side-encryption-customer-key-MD5",
    ),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "ExpectedSourceBucketOwner": (
        "header",
        "x-amz-source-expected-bucket-owner",
    ),
    "PartNumber": ("querystring", "partNumber"),
    "UploadId": ("querystring", "uploadId"),
}


def assert_upload_part_copy(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a UploadPartCopy (PUT /{Bucket}/{Key+})."""
    assert (
        request.method == "PUT"
    ), f"UploadPartCopy: expected PUT, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "UploadPartCopy")
    _check_key(request, Key, addressing_style, "UploadPartCopy")
    assert (
        "partNumber" in parse_qs(urlparse(request.effective_path).query)
    ), "UploadPartCopy: required query param partNumber (PartNumber) is missing"
    assert "uploadId" in parse_qs(
        urlparse(request.effective_path).query
    ), "UploadPartCopy: required query param uploadId (UploadId) is missing"
    assert (
        request.headers.get("x-amz-copy-source") is not None
        or request.headers.get("x-amz-copy-source") is not None
    ), "UploadPartCopy: required header x-amz-copy-source (CopySource) is missing"
    _check_params(request, params, _UPLOAD_PART_COPY_PARAMS, "UploadPartCopy")


# CompleteMultipartUpload: POST /{Bucket}/{Key+}
_COMPLETE_MULTIPART_UPLOAD_PARAMS = {
    "ChecksumCRC32": ("header", "x-amz-checksum-crc32"),
    "ChecksumCRC32C": ("header", "x-amz-checksum-crc32c"),
    "ChecksumCRC64NVME": ("header", "x-amz-checksum-crc64nvme"),
    "ChecksumSHA1": ("header", "x-amz-checksum-sha1"),
    "ChecksumSHA256": ("header", "x-amz-checksum-sha256"),
    "ChecksumSHA512": ("header", "x-amz-checksum-sha512"),
    "ChecksumMD5": ("header", "x-amz-checksum-md5"),
    "ChecksumXXHASH64": ("header", "x-amz-checksum-xxhash64"),
    "ChecksumXXHASH3": ("header", "x-amz-checksum-xxhash3"),
    "ChecksumXXHASH128": ("header", "x-amz-checksum-xxhash128"),
    "ChecksumType": ("header", "x-amz-checksum-type"),
    "MpuObjectSize": ("header", "x-amz-mp-object-size"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "IfMatch": ("header", "If-Match"),
    "IfNoneMatch": ("header", "If-None-Match"),
    "SSECustomerAlgorithm": (
        "header",
        "x-amz-server-side-encryption-customer-algorithm",
    ),
    "SSECustomerKey": ("header", "x-amz-server-side-encryption-customer-key"),
    "SSECustomerKeyMD5": (
        "header",
        "x-amz-server-side-encryption-customer-key-MD5",
    ),
    "UploadId": ("querystring", "uploadId"),
    "MultipartUpload": ("payload", "http://s3.amazonaws.com/doc/2006-03-01/"),
}


def assert_complete_multipart_upload(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a CompleteMultipartUpload (POST /{Bucket}/{Key+})."""
    assert (
        request.method == "POST"
    ), f"CompleteMultipartUpload: expected POST, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "CompleteMultipartUpload")
    _check_key(request, Key, addressing_style, "CompleteMultipartUpload")
    assert (
        "uploadId" in parse_qs(urlparse(request.effective_path).query)
    ), "CompleteMultipartUpload: required query param uploadId (UploadId) is missing"
    _check_params(
        request,
        params,
        _COMPLETE_MULTIPART_UPLOAD_PARAMS,
        "CompleteMultipartUpload",
    )


# AbortMultipartUpload: DELETE /{Bucket}/{Key+}
_ABORT_MULTIPART_UPLOAD_PARAMS = {
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "IfMatchInitiatedTime": ("header", "x-amz-if-match-initiated-time"),
    "UploadId": ("querystring", "uploadId"),
}


def assert_abort_multipart_upload(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a AbortMultipartUpload (DELETE /{Bucket}/{Key+})."""
    assert (
        request.method == "DELETE"
    ), f"AbortMultipartUpload: expected DELETE, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "AbortMultipartUpload")
    _check_key(request, Key, addressing_style, "AbortMultipartUpload")
    assert (
        "uploadId" in parse_qs(urlparse(request.effective_path).query)
    ), "AbortMultipartUpload: required query param uploadId (UploadId) is missing"
    _check_params(
        request, params, _ABORT_MULTIPART_UPLOAD_PARAMS, "AbortMultipartUpload"
    )


# CreateBucket: PUT /{Bucket}
_CREATE_BUCKET_PARAMS = {
    "ACL": ("header", "x-amz-acl"),
    "GrantFullControl": ("header", "x-amz-grant-full-control"),
    "GrantRead": ("header", "x-amz-grant-read"),
    "GrantReadACP": ("header", "x-amz-grant-read-acp"),
    "GrantWrite": ("header", "x-amz-grant-write"),
    "GrantWriteACP": ("header", "x-amz-grant-write-acp"),
    "ObjectLockEnabledForBucket": (
        "header",
        "x-amz-bucket-object-lock-enabled",
    ),
    "ObjectOwnership": ("header", "x-amz-object-ownership"),
    "BucketNamespace": ("header", "x-amz-bucket-namespace"),
    "CreateBucketConfiguration": (
        "payload",
        "http://s3.amazonaws.com/doc/2006-03-01/",
    ),
}


def assert_create_bucket(
    request, Bucket: str, addressing_style: str = "virtual", **params
):
    """Assert request is a CreateBucket (PUT /{Bucket})."""
    assert (
        request.method == "PUT"
    ), f"CreateBucket: expected PUT, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "CreateBucket")
    _check_params(request, params, _CREATE_BUCKET_PARAMS, "CreateBucket")


# DeleteBucket: DELETE /{Bucket}
_DELETE_BUCKET_PARAMS = {
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
}


def assert_delete_bucket(
    request, Bucket: str, addressing_style: str = "virtual", **params
):
    """Assert request is a DeleteBucket (DELETE /{Bucket})."""
    assert (
        request.method == "DELETE"
    ), f"DeleteBucket: expected DELETE, got {request.method}"
    _check_bucket(request, Bucket, addressing_style, "DeleteBucket")
    _check_params(request, params, _DELETE_BUCKET_PARAMS, "DeleteBucket")


# GetObjectTagging: GET /{Bucket}/{Key+}?tagging
_GET_OBJECT_TAGGING_PARAMS = {
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "VersionId": ("querystring", "versionId"),
}


def assert_get_object_tagging(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a GetObjectTagging (GET /{Bucket}/{Key+}?tagging)."""
    assert (
        request.method == "GET"
    ), f"GetObjectTagging: expected GET, got {request.method}"
    _qs = parse_qs(urlparse(request.effective_path).query)
    assert (
        "tagging" in urlparse(request.effective_path).query
    ), f"GetObjectTagging: expected ?tagging in {request.effective_path}"
    _check_bucket(request, Bucket, addressing_style, "GetObjectTagging")
    _check_key(request, Key, addressing_style, "GetObjectTagging")
    _check_params(
        request, params, _GET_OBJECT_TAGGING_PARAMS, "GetObjectTagging"
    )


# PutObjectTagging: PUT /{Bucket}/{Key+}?tagging
_PUT_OBJECT_TAGGING_PARAMS = {
    "ContentMD5": ("header", "Content-MD5"),
    "ChecksumAlgorithm": ("header", "x-amz-sdk-checksum-algorithm"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "VersionId": ("querystring", "versionId"),
    "Tagging": ("payload", "http://s3.amazonaws.com/doc/2006-03-01/"),
}


def assert_put_object_tagging(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a PutObjectTagging (PUT /{Bucket}/{Key+}?tagging)."""
    assert (
        request.method == "PUT"
    ), f"PutObjectTagging: expected PUT, got {request.method}"
    _qs = parse_qs(urlparse(request.effective_path).query)
    assert (
        "tagging" in urlparse(request.effective_path).query
    ), f"PutObjectTagging: expected ?tagging in {request.effective_path}"
    _check_bucket(request, Bucket, addressing_style, "PutObjectTagging")
    _check_key(request, Key, addressing_style, "PutObjectTagging")
    _check_params(
        request, params, _PUT_OBJECT_TAGGING_PARAMS, "PutObjectTagging"
    )


# ListBuckets: GET /
_LIST_BUCKETS_PARAMS = {
    "MaxBuckets": ("querystring", "max-buckets"),
    "ContinuationToken": ("querystring", "continuation-token"),
    "Prefix": ("querystring", "prefix"),
    "BucketRegion": ("querystring", "bucket-region"),
}


def assert_list_buckets(request, **params):
    """Assert request is a ListBuckets (GET /)."""
    assert (
        request.method == "GET"
    ), f"ListBuckets: expected GET, got {request.method}"
    _check_params(request, params, _LIST_BUCKETS_PARAMS, "ListBuckets")


# ListObjectAnnotations: GET /{Bucket}/{Key+}?annotation
_LIST_OBJECT_ANNOTATIONS_PARAMS = {
    "VersionId": ("querystring", "versionId"),
    "MaxAnnotationResults": ("querystring", "max-annotation-results"),
    "AnnotationPrefix": ("querystring", "annotation-prefix"),
    "ContinuationToken": ("querystring", "continuation-token"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
}


def assert_list_object_annotations(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a ListObjectAnnotations (GET /{Bucket}/{Key+}?annotation)."""
    assert (
        request.method == "GET"
    ), f"ListObjectAnnotations: expected GET, got {request.method}"
    assert (
        "annotation" in urlparse(request.effective_path).query
    ), f"ListObjectAnnotations: expected ?annotation in {request.effective_path}"
    _check_bucket(request, Bucket, addressing_style, "ListObjectAnnotations")
    _check_key(request, Key, addressing_style, "ListObjectAnnotations")
    _check_params(
        request,
        params,
        _LIST_OBJECT_ANNOTATIONS_PARAMS,
        "ListObjectAnnotations",
    )


# GetObjectAnnotation: GET /{Bucket}/{Key+}?annotation
_GET_OBJECT_ANNOTATION_PARAMS = {
    "AnnotationName": ("querystring", "annotationName"),
    "VersionId": ("querystring", "versionId"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
    "ChecksumMode": ("header", "x-amz-checksum-mode"),
}


def assert_get_object_annotation(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a GetObjectAnnotation (GET /{Bucket}/{Key+}?annotation&annotationName=...)."""
    assert (
        request.method == "GET"
    ), f"GetObjectAnnotation: expected GET, got {request.method}"
    _qs = parse_qs(urlparse(request.effective_path).query)
    assert (
        "annotationName" in _qs
    ), "GetObjectAnnotation: required query param annotationName is missing"
    _check_bucket(request, Bucket, addressing_style, "GetObjectAnnotation")
    _check_key(request, Key, addressing_style, "GetObjectAnnotation")
    _check_params(
        request, params, _GET_OBJECT_ANNOTATION_PARAMS, "GetObjectAnnotation"
    )


# PutObjectAnnotation: PUT /{Bucket}/{Key+}?annotation
_PUT_OBJECT_ANNOTATION_PARAMS = {
    "AnnotationName": ("querystring", "annotationName"),
    "VersionId": ("querystring", "versionId"),
    "ObjectIfMatch": ("header", "x-amz-object-if-match"),
    "ChecksumAlgorithm": ("header", "x-amz-sdk-checksum-algorithm"),
    "RequestPayer": ("header", "x-amz-request-payer"),
    "ExpectedBucketOwner": ("header", "x-amz-expected-bucket-owner"),
}


def assert_put_object_annotation(
    request, Bucket: str, Key: str, addressing_style: str = "virtual", **params
):
    """Assert request is a PutObjectAnnotation (PUT /{Bucket}/{Key+}?annotation)."""
    assert (
        request.method == "PUT"
    ), f"PutObjectAnnotation: expected PUT, got {request.method}"
    _qs = parse_qs(urlparse(request.effective_path).query)
    assert (
        "annotationName" in _qs
    ), "PutObjectAnnotation: required query param annotationName is missing"
    _check_bucket(request, Bucket, addressing_style, "PutObjectAnnotation")
    _check_key(request, Key, addressing_style, "PutObjectAnnotation")
    _check_params(
        request, params, _PUT_OBJECT_ANNOTATION_PARAMS, "PutObjectAnnotation"
    )


def assert_get_access_point(request):
    """Assert request is an S3 Control GetAccessPoint (GET /v20180820/accesspoint/{name})."""
    assert (
        request.method == "GET"
    ), f"GetAccessPoint: expected GET, got {request.method}"
    assert (
        "/v20180820/accesspoint/" in request.effective_path
    ), f"GetAccessPoint: expected /v20180820/accesspoint/ in {request.effective_path}"
    assert (
        request.headers.get("x-amz-account-id") is not None
    ), "GetAccessPoint: required header x-amz-account-id is missing"


def assert_get_caller_identity(request):
    """Assert request is an STS GetCallerIdentity (POST /)."""
    assert (
        request.method == "POST"
    ), f"GetCallerIdentity: expected POST, got {request.method}"
    body = (
        request.body.decode("utf-8")
        if isinstance(request.body, bytes)
        else (request.body or "")
    )
    assert "Action=GetCallerIdentity" in body, (
        f"GetCallerIdentity: expected Action=GetCallerIdentity in body, "
        f"got {body!r}"
    )
