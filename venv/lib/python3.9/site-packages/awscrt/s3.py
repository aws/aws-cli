"""
S3 client
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt
from concurrent.futures import Future
from awscrt import NativeResource
from awscrt.http import HttpRequest
from awscrt.io import ClientBootstrap, TlsConnectionOptions
from awscrt.auth import AwsCredentialsProvider, AwsSignatureType, AwsSignedBodyHeaderType, AwsSignedBodyValue, \
    AwsSigningAlgorithm, AwsSigningConfig
import awscrt.exceptions
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple, Sequence
from enum import IntEnum


class CrossProcessLock(NativeResource):
    """
    Class representing an exclusive cross-process lock, scoped by `lock_scope_name`

    Recommended usage is to either explicitly call acquire() followed by release() when the lock  is no longer required, or use this in a 'with' statement.

    acquire() will throw a RuntimeError with AWS_MUTEX_CALLER_NOT_OWNER as the error code, if the lock could not be acquired.

    If the lock has not been explicitly released when the process exits, it will be released by the operating system.

    Keyword Args:
        lock_scope_name (str): Unique string identifying the caller holding the lock.
    """

    def __init__(self, lock_scope_name):
        super().__init__()
        self._binding = _awscrt.s3_cross_process_lock_new(lock_scope_name)

    def acquire(self):
        _awscrt.s3_cross_process_lock_acquire(self._binding)

    def __enter__(self):
        self.acquire()

    def release(self):
        _awscrt.s3_cross_process_lock_release(self._binding)

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.release()


class S3RequestType(IntEnum):
    """The type of the AWS S3 request"""

    DEFAULT = 0
    """
    Default type, for all S3 request types other than
    :attr:`~S3RequestType.GET_OBJECT`/:attr:`~S3RequestType.PUT_OBJECT`.
    """

    GET_OBJECT = 1
    """
    Get Object S3 request
    """

    PUT_OBJECT = 2
    """
    Put Object S3 request
    """


class S3RequestTlsMode(IntEnum):
    """TLS mode for S3 request"""

    ENABLED = 0
    """
    Enable TLS for S3 request.
    """

    DISABLED = 1
    """
    Disable TLS for S3 request.
    """


class S3ChecksumAlgorithm(IntEnum):
    """
    Checksum algorithm used to verify object integrity.
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html
    """

    CRC32C = 1
    """CRC32C"""

    CRC32 = 2
    """CRC32"""

    SHA1 = 3
    """SHA-1"""

    SHA256 = 4
    """SHA-256"""

    CRC64NVME = 5
    """CRC64NVME"""


class S3ChecksumLocation(IntEnum):
    """Where to put the checksum."""

    HEADER = 1
    """
    Add checksum as a request header field.
    The checksum is calculated before any part of the request is sent to the server.
    """

    TRAILER = 2
    """
    Add checksum as a request trailer field.
    The checksum is calculated as the body is streamed to the server, then
    added as a trailer field. This may be more efficient than HEADER, but
    can only be used with "streaming" requests that support it.
    """


@dataclass
class S3ChecksumConfig:
    """Configures how the S3Client calculates and verifies checksums."""

    algorithm: Optional[S3ChecksumAlgorithm] = None
    """
    If set, the S3Client will calculate a checksum using this algorithm
    and add it to the request. If you set this, you must also set `location`.
    """

    location: Optional[S3ChecksumLocation] = None
    """Where to put the request checksum."""

    validate_response: bool = False
    """Whether to retrieve and validate response checksums."""


class S3Client(NativeResource):
    """S3 client

    Keyword Args:
        bootstrap (Optional [ClientBootstrap]): Client bootstrap to use when initiating socket connection.
            If None is provided, the default singleton is used.

        region (str): Region that the S3 bucket lives in.

        tls_mode (Optional[S3RequestTlsMode]):  How TLS should be used while performing the request

            If this is :attr:`S3RequestTlsMode.ENABLED`:
                If `tls_connection_options` is set, then those TLS options will be used
                If `tls_connection_options` is unset, then default TLS options will be used

            If this is :attr:`S3RequestTlsMode.DISABLED`:
                No TLS options will be used, regardless of `tls_connection_options` value.

        signing_config (Optional[AwsSigningConfig]): Configuration for signing of the client.
            Use :func:`create_default_s3_signing_config()` to create the default config.

            If not set, a default config will be used with anonymous credentials and skip signing the request.

            If set:
                Credentials provider is required. Other configs are all optional, and will be default to what
                    needs to sign the request for S3, only overrides when Non-zero/Not-empty is set.

                S3 Client will derive the right config for signing process based on this.

            Notes:

                1. For SIGV4_S3EXPRESS, S3 client will use the credentials in the config to derive the S3 Express
                    credentials that are used in the signing process.
                2. Client may make modifications to signing config before passing it on to signer.

        credential_provider (Optional[AwsCredentialsProvider]): Deprecated, prefer `signing_config` instead.
            Credentials providers source the :class:`~awscrt.auth.AwsCredentials` needed to sign an authenticated AWS request.
            If None is provided, the request will not be signed.

        tls_connection_options (Optional[TlsConnectionOptions]): Optional TLS Options to be used
            for each connection, unless `tls_mode` is :attr:`S3RequestTlsMode.DISABLED`

        part_size (Optional[int]): Size, in bytes, of parts that files will be downloaded or uploaded in.
            Note: for :attr:`S3RequestType.PUT_OBJECT` request, client will adjust the part size to meet the service limits.
            (max number of parts per upload is 10,000, minimum upload part size is 5 MiB)

        multipart_upload_threshold (Optional[int]): The size threshold in bytes, for when to use multipart uploads.
            This only affects :attr:`S3RequestType.PUT_OBJECT` request.
            Uploads over this size will use the multipart upload strategy.
            Uploads this size or less will use a single request.
            If not set, maximal of `part_size` and 5 MiB will be used.

        throughput_target_gbps (Optional[float]): Throughput target in
            Gigabits per second (Gbps) that we are trying to reach.
            You can also use `get_recommended_throughput_target_gbps()` to get recommended value for your system.
            10.0 Gbps by default (may change in future)

        enable_s3express (Optional[bool]): To enable S3 Express support for the client.
            The typical usage for a S3 Express request is to set this to true and let the request to be
            signed with `AwsSigningAlgorithm.V4_S3EXPRESS`, either from the client-level `signing_config`
            or the request-level override.

        memory_limit (Optional[int]): Memory limit, in bytes, of how much memory
            client can use for buffering data for requests.
            Default values scale with target throughput and are currently
            between 2GiB and 8GiB (may change in future)

        network_interface_names: (Optional[Sequence(str)])
            **THIS IS AN EXPERIMENTAL AND UNSTABLE API.**
            A sequence of network interface names. The client will distribute the
            connections across network interfaces. If any interface name is invalid, goes down,
            or has any issues like network access, you will see connection failures.
            This option is only supported on Linux, MacOS, and platforms that have either SO_BINDTODEVICE or IP_BOUND_IF. It
            is not supported on Windows. `AWS_ERROR_PLATFORM_NOT_SUPPORTED` will be raised on unsupported platforms. On
            Linux, SO_BINDTODEVICE is used and requires kernel version >= 5.7 or root privileges.
    """

    __slots__ = ('shutdown_event', '_region')

    def __init__(
            self,
            *,
            bootstrap=None,
            region,
            tls_mode=None,
            signing_config=None,
            credential_provider=None,
            tls_connection_options=None,
            part_size=None,
            multipart_upload_threshold=None,
            throughput_target_gbps=None,
            enable_s3express=False,
            memory_limit=None,
            network_interface_names: Optional[Sequence[str]] = None):
        assert isinstance(bootstrap, ClientBootstrap) or bootstrap is None
        assert isinstance(region, str)
        assert isinstance(signing_config, AwsSigningConfig) or signing_config is None
        assert isinstance(credential_provider, AwsCredentialsProvider) or credential_provider is None
        assert isinstance(tls_connection_options, TlsConnectionOptions) or tls_connection_options is None
        assert isinstance(part_size, int) or part_size is None
        assert isinstance(
            throughput_target_gbps,
            int) or isinstance(
            throughput_target_gbps,
            float) or throughput_target_gbps is None
        assert isinstance(enable_s3express, bool) or enable_s3express is None
        assert isinstance(network_interface_names, Sequence) or network_interface_names is None

        if credential_provider and signing_config:
            raise ValueError("'credential_provider' has been deprecated in favor of 'signing_config'.  "
                             "Both parameters may not be set.")

        super().__init__()

        shutdown_event = threading.Event()

        def on_shutdown():
            shutdown_event.set()

        self._region = region
        self.shutdown_event = shutdown_event

        if not bootstrap:
            bootstrap = ClientBootstrap.get_or_create_static_default()

        s3_client_core = _S3ClientCore(
            bootstrap,
            credential_provider,
            signing_config,
            tls_connection_options)

        # C layer uses 0 to indicate defaults
        if tls_mode is None:
            tls_mode = 0
        if part_size is None:
            part_size = 0
        if multipart_upload_threshold is None:
            multipart_upload_threshold = 0
        if throughput_target_gbps is None:
            throughput_target_gbps = 0
        if memory_limit is None:
            memory_limit = 0
        if network_interface_names is not None:
            # ensure this is a list, so it's simpler to process in C
            if not isinstance(network_interface_names, list):
                network_interface_names = list(network_interface_names)

        self._binding = _awscrt.s3_client_new(
            bootstrap,
            signing_config,
            credential_provider,
            tls_connection_options,
            on_shutdown,
            region,
            tls_mode,
            part_size,
            multipart_upload_threshold,
            throughput_target_gbps,
            enable_s3express,
            memory_limit,
            network_interface_names,
            s3_client_core)

    def make_request(
            self,
            *,
            type,
            request,
            operation_name=None,
            recv_filepath=None,
            send_filepath=None,
            signing_config=None,
            credential_provider=None,
            checksum_config=None,
            part_size=None,
            multipart_upload_threshold=None,
            on_headers=None,
            on_body=None,
            on_done=None,
            on_progress=None):
        """Create the Request to the the S3 server,
        :attr:`~S3RequestType.GET_OBJECT`/:attr:`~S3RequestType.PUT_OBJECT` requests are split it into multi-part
        requests under the hood for acceleration.

        Keyword Args:
            type (S3RequestType): The type of S3 request passed in,
                :attr:`~S3RequestType.GET_OBJECT`/:attr:`~S3RequestType.PUT_OBJECT` can be accelerated

            request (HttpRequest): The overall outgoing API request for S3 operation.
                If the request body is a file, set send_filepath for better performance.

            operation_name(Optional[str]): S3 operation name (e.g. "CreateBucket").
                This MUST be set when `type` is :attr:`~S3RequestType.DEFAULT`.
                It is ignored for other types, since the operation is implicitly known.
                See `S3 API documentation
                <https://docs.aws.amazon.com/AmazonS3/latest/API/API_Operations_Amazon_Simple_Storage_Service.html>`_
                for the canonical list of names.

                This name is used to fill out details in metrics and error reports.
                It also drives some operation-specific behavior.
                If you pass the wrong name, you risk getting the wrong behavior.

                For example, every operation except "GetObject" has its response checked
                for error, even if the HTTP status-code was 200 OK
                (see `knowledge center <https://repost.aws/knowledge-center/s3-resolve-200-internalerror>`_).
                If you used the :attr:`~S3RequestType.DEFAULT` type to do
                `GetObject <https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html>`_,
                but mis-named it "Download", and the object looked like XML with an error code,
                then the request would fail. You risk logging the full response body,
                and leaking sensitive data.

            recv_filepath (Optional[str]): Optional file path. If set, the
                response body is written directly to a file and the
                `on_body` callback is not invoked. This should give better
                performance than writing to file from the `on_body` callback.

            send_filepath (Optional[str]): Optional file path. If set, the
                request body is read directly from a file and the
                request's `body_stream` is ignored. This should give better
                performance than reading a file from a stream.

            signing_config (Optional[AwsSigningConfig]): Configuration for signing of the request to override the configuration from client.
                Use :func:`create_default_s3_signing_config()` to create the default config.

                If None is provided, the client configuration will be used.

                If set:
                    All fields are optional. The credentials will be resolve from client if not set.
                    S3 Client will derive the right config for signing process based on this.

                Notes:

                    1. For SIGV4_S3EXPRESS, S3 client will use the credentials in the config to derive the S3 Express
                        credentials that are used in the signing process.
                    2. Client may make modifications to signing config before passing it on to signer.

            credential_provider (Optional[AwsCredentialsProvider]):  Deprecated, prefer `signing_config` instead.
                Credentials providers source the :class:`~awscrt.auth.AwsCredentials` needed to sign an authenticated AWS request, for this request only.
                If None is provided, the client configuration will be used.

            checksum_config (Optional[S3ChecksumConfig]): Optional checksum settings.

            part_size (Optional[int]): Size, in bytes, of parts that files will be downloaded or uploaded in.
                If not set, the part size configured for the client will be used.
                Note: for :attr:`S3RequestType.PUT_OBJECT` request, client will adjust the part size to meet the service limits.
                (max number of parts per upload is 10,000, minimum upload part size is 5 MiB)

            multipart_upload_threshold (Optional[int]): The size threshold in bytes, for when to use multipart uploads.
                This only affects :attr:`S3RequestType.PUT_OBJECT` request.
                Uploads over this size will use the multipart upload strategy.
                Uploads this size or less will use a single request.
                If set, this should be at least `part_size`.
                If not set, `part_size` adjusted by client will be used as the threshold.
                If both `part_size` and `multipart_upload_threshold` are not set,
                the values from `aws_s3_client_config` are used.

            on_headers: Optional callback invoked as the response received, and even the API request
                has been split into multiple parts, this callback will only be invoked once as
                it's just making one API request to S3.
                The function should take the following arguments and return nothing:

                    *   `status_code` (int): Response status code.

                    *   `headers` (List[Tuple[str, str]]): Response headers as a
                        list of (name,value) pairs.

                    *   `**kwargs` (dict): Forward-compatibility kwargs.

            on_body: Optional callback invoked 0+ times as the response body received from S3 server.
                If simply writing to a file, use `recv_filepath` instead of `on_body` for better performance.
                The function should take the following arguments and return nothing:

                    *   `chunk` (buffer): Response body data (not necessarily
                        a whole "chunk" of chunked encoding).

                    *   `offset` (int): The offset of the chunk started in the whole body.

                    *   `**kwargs` (dict): Forward-compatibility kwargs.

            on_done: Optional callback invoked when the request has finished the job.
                The function should take the following arguments and return nothing:

                    *   `error` (Optional[Exception]): None if the request was
                        successfully sent and valid response received, or an Exception
                        if it failed.

                    *   `error_headers` (Optional[List[Tuple[str, str]]]): If request
                        failed because server side sent an unsuccessful response, the headers
                        of the response is provided here. Else None will be returned.

                    *   `error_body` (Optional[bytes]): If request failed because server
                        side sent an unsuccessful response, the body of the response is
                        provided here. Else None will be returned.

                    *   `error_operation_name` (Optional[str]): If request failed
                        because server side sent and unsuccessful response, this
                        is the name of the S3 operation it was responding to.
                        For example, if a :attr:`~S3RequestType.PUT_OBJECT` fails
                        this could be "PutObject", "CreateMultipartUpload", "UploadPart",
                        "CompleteMultipartUpload", or others. For :attr:`~S3RequestType.DEFAULT`,
                        this is the `operation_name` passed to :meth:`S3Client.make_request()`.
                        This will be None if the request failed for another reason,
                        or the S3 operation name is unknown.

                    *   `status_code` (Optional[int]): HTTP response status code (if available).
                        If request failed because server side sent an unsuccessful response,
                        this is its status code. If the operation was successful,
                        this is the final response's status code. If the operation
                        failed for another reason, None is returned.

                    *   `did_validate_checksum` (bool):
                            Was the server side checksum compared against a calculated checksum of the response body.
                            This may be false even if :attr:`S3ChecksumConfig.validate_response` was set because
                            the object was uploaded without a checksum, or downloaded differently from how it's uploaded.

                    *   `checksum_validation_algorithm` (Optional[S3ChecksumAlgorithm]): The checksum algorithm used to validate the response.

                    *   `**kwargs` (dict): Forward-compatibility kwargs.

            on_progress: Optional callback invoked when part of the transfer is done to report the progress.
                The function should take the following arguments and return nothing:

                    *   `progress` (int): Number of bytes of data that just get transferred

                    *   `**kwargs` (dict): Forward-compatibility kwargs.

        Returns:
            S3Request
        """
        return S3Request(
            client=self,
            type=type,
            request=request,
            operation_name=operation_name,
            recv_filepath=recv_filepath,
            send_filepath=send_filepath,
            signing_config=signing_config,
            credential_provider=credential_provider,
            checksum_config=checksum_config,
            part_size=part_size,
            multipart_upload_threshold=multipart_upload_threshold,
            on_headers=on_headers,
            on_body=on_body,
            on_done=on_done,
            on_progress=on_progress,
            region=self._region)


class S3Request(NativeResource):
    """S3 request
    Create a new S3Request with :meth:`S3Client.make_request()`

    Attributes:
        finished_future (concurrent.futures.Future): Future that will
            resolve when the s3 request has finished successfully.
            If the error happens, the Future will contain an exception
            indicating why it failed. Note: Future will set before on_done invoked

        shutdown_event (threading.Event): Signals when underlying threads and
            structures have all finished shutting down. Shutdown begins when the
            S3Request object is destroyed.
    """
    __slots__ = ('_finished_future', 'shutdown_event')

    def __init__(
            self,
            *,
            client,
            type,
            request,
            operation_name=None,
            recv_filepath=None,
            send_filepath=None,
            signing_config=None,
            credential_provider=None,
            checksum_config=None,
            part_size=None,
            multipart_upload_threshold=None,
            on_headers=None,
            on_body=None,
            on_done=None,
            on_progress=None,
            region=None):
        assert isinstance(client, S3Client)
        assert isinstance(request, HttpRequest)
        assert callable(on_headers) or on_headers is None
        assert callable(on_body) or on_body is None
        assert callable(on_done) or on_done is None
        assert isinstance(part_size, int) or part_size is None
        assert isinstance(multipart_upload_threshold, int) or multipart_upload_threshold is None

        if type == S3RequestType.DEFAULT and not operation_name:
            raise ValueError("'operation_name' must be set when using S3RequestType.DEFAULT")

        super().__init__()

        self._finished_future = Future()
        self.shutdown_event = threading.Event()

        # C layer uses 0 to indicate defaults
        if part_size is None:
            part_size = 0
        if multipart_upload_threshold is None:
            multipart_upload_threshold = 0
        checksum_algorithm = 0
        checksum_location = 0
        validate_response_checksum = False
        if checksum_config is not None:
            if checksum_config.algorithm is not None:
                checksum_algorithm = checksum_config.algorithm.value
            if checksum_config.location is not None:
                checksum_location = checksum_config.location.value
            validate_response_checksum = checksum_config.validate_response

        s3_request_core = _S3RequestCore(
            request,
            self._finished_future,
            self.shutdown_event,
            signing_config,
            credential_provider,
            on_headers,
            on_body,
            on_done,
            on_progress)

        self._binding = _awscrt.s3_client_make_meta_request(
            self,
            client,
            request,
            type,
            operation_name,
            signing_config,
            credential_provider,
            recv_filepath,
            send_filepath,
            region,
            checksum_algorithm,
            checksum_location,
            validate_response_checksum,
            part_size,
            multipart_upload_threshold,
            s3_request_core)

    @property
    def finished_future(self):
        return self._finished_future

    def cancel(self):
        _awscrt.s3_meta_request_cancel(self)


class S3ResponseError(awscrt.exceptions.AwsCrtError):
    '''
    An error response from S3.

    Subclasses :class:`awscrt.exceptions.AwsCrtError`.

    Attributes:
        status_code (int): HTTP response status code.
        headers (list[tuple[str, str]]): Headers from HTTP response.
        body (Optional[bytes]): Body of HTTP response (if any).
            This is usually XML. It may be None in the case of a HEAD response.
        operation_name: Name of the S3 operation that failed.
            For example, if a :attr:`~S3RequestType.PUT_OBJECT` fails
            this could be "PutObject", "CreateMultipartUpload", "UploadPart",
            "CompleteMultipartUpload", or others. For :attr:`~S3RequestType.DEFAULT`,
            this is the `operation_name` passed to :meth:`S3Client.make_request()`.
        code (int): CRT error code.
        name (str): CRT error name.
        message (str): CRT error message.
    '''

    def __init__(self, *,
                 code: int,
                 name: str,
                 message: str,
                 status_code: List[Tuple[str, str]] = None,
                 headers: List[Tuple[str, str]] = None,
                 body: Optional[bytes] = None,
                 operation_name: Optional[str] = None):
        super().__init__(code, name, message)
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.operation_name = operation_name


class _S3ClientCore:
    '''
    Private class to keep all the related Python object alive until C land clean up for S3Client
    '''

    def __init__(self, bootstrap,
                 credential_provider=None,
                 signing_config=None,
                 tls_connection_options=None):
        self._bootstrap = bootstrap
        self._credential_provider = credential_provider
        self._signing_config = signing_config
        self._tls_connection_options = tls_connection_options


class _S3RequestCore:
    '''
    Private class to keep all the related Python object alive until C land clean up for S3Request
    '''

    def __init__(
            self,
            request,
            finish_future,
            shutdown_event,
            signing_config=None,
            credential_provider=None,
            on_headers=None,
            on_body=None,
            on_done=None,
            on_progress=None):

        # Stores exception raised in on_headers or on_body callback so that we can rethrow it in the on_done callback
        self._python_callback_exception = None
        self._request = request
        self._signing_config = signing_config
        self._credential_provider = credential_provider

        self._on_headers_cb = on_headers
        self._on_body_cb = on_body
        self._on_done_cb = on_done
        self._on_progress_cb = on_progress

        self._finished_future = finish_future
        self._shutdown_event = shutdown_event

    def _on_headers(self, status_code, headers):
        if self._on_headers_cb:
            try:
                self._on_headers_cb(status_code=status_code, headers=headers)
                return True
            except BaseException as e:
                self._python_callback_exception = e
                return False

    def _on_body(self, chunk, offset):
        if self._on_body_cb:
            try:
                self._on_body_cb(chunk=chunk, offset=offset)
                return True
            except BaseException as e:
                self._python_callback_exception = e
                return False

    def _on_shutdown(self):
        self._shutdown_event.set()

    def _on_finish(
            self,
            error_code,
            status_code,
            error_headers,
            error_body,
            error_operation_name,
            did_validate_checksum,
            checksum_validation_algorithm):
        # If C layer gives status_code 0, that means "unknown"
        if status_code == 0:
            status_code = None

        error = None
        if error_code:
            error = awscrt.exceptions.from_code(error_code)
            if isinstance(error, awscrt.exceptions.AwsCrtError):
                if (error.name == "AWS_ERROR_CRT_CALLBACK_EXCEPTION"
                        and self._python_callback_exception is not None):
                    error = self._python_callback_exception
                # If the failure was due to a response, make it into an S3ResponseError.
                # When failure is due to a response, its headers are always included.
                elif status_code is not None \
                        and error_headers is not None:
                    error = S3ResponseError(
                        code=error.code,
                        name=error.name,
                        message=error.message,
                        status_code=status_code,
                        headers=error_headers,
                        body=error_body,
                        operation_name=error_operation_name)
            self._finished_future.set_exception(error)
        else:
            self._finished_future.set_result(None)

        if checksum_validation_algorithm:
            checksum_validation_algorithm = S3ChecksumAlgorithm(checksum_validation_algorithm)
        else:
            checksum_validation_algorithm = None

        if self._on_done_cb:
            self._on_done_cb(
                error=error,
                error_headers=error_headers,
                error_body=error_body,
                error_operation_name=error_operation_name,
                status_code=status_code,
                did_validate_checksum=did_validate_checksum,
                checksum_validation_algorithm=checksum_validation_algorithm)

    def _on_progress(self, progress):
        if self._on_progress_cb:
            self._on_progress_cb(progress)


def create_default_s3_signing_config(*, region: str, credential_provider: AwsCredentialsProvider, **kwargs):
    """Create a default `AwsSigningConfig` for S3 service.

        Attributes:
            region (str): The region to sign against.

            credential_provider (AwsCredentialsProvider): Credentials provider
                to fetch signing credentials with.

            `**kwargs`: Forward compatibility kwargs.

        Returns:
            AwsSigningConfig
    """
    return AwsSigningConfig(
        algorithm=AwsSigningAlgorithm.V4,
        signature_type=AwsSignatureType.HTTP_REQUEST_HEADERS,
        service="s3",
        signed_body_header_type=AwsSignedBodyHeaderType.X_AMZ_CONTENT_SHA_256,
        signed_body_value=AwsSignedBodyValue.UNSIGNED_PAYLOAD,
        region=region,
        credentials_provider=credential_provider,
        use_double_uri_encode=False,
        should_normalize_uri_path=False,
    )


def get_ec2_instance_type():
    """
        First this function will check it's running on EC2 via. attempting to read DMI info to avoid making IMDS calls.

        If the function detects it's on EC2, and it was able to detect the instance type without a call to IMDS
        it will return it.

        Finally, it will call IMDS and return the instance type from there.
        Note that in the case of the IMDS call, a new client stack is spun up using 1 background thread. The call is made
        synchronously with a 1 second timeout: It's not cheap. To make this easier, the underlying result is cached
        internally and will be freed when this module is unloaded is called.

        Returns:
           A string indicating the instance type or None if it could not be determined.
    """
    return _awscrt.s3_get_ec2_instance_type()


def is_optimized_for_system():
    """
        Returns:
            true if the current build of this module has an optimized configuration
            for the current system.
    """
    return _awscrt.s3_is_crt_s3_optimized_for_system()


def get_optimized_platforms():
    """
    Returns:
        A list[str] of platform identifiers, such as EC2 instance types, for which S3 client is pre-optimized
        and have a recommended throughput_target_gbps. You can use `get_recommended_throughput_target_gbps()`
        to obtain the recommended throughput_target_gbps for those platforms.
    """
    return _awscrt.s3_get_optimized_platforms()


def get_recommended_throughput_target_gbps() -> Optional[float]:
    """
    Returns:
        Recommended throughput, in gigabits per second, based on detected system configuration.
        If the best throughput configuration is unknown, returns None.
        Use this as the S3Client's `throughput_target_gbps`.
    """
    # Currently the CRT returns 0 if it was unable to make a good guess on configuration. Pre-known configs,
    # have this value set. Eventually, the CRT will make a full calculation based on NIC and CPU configuration,
    # but until then handle 0.
    max_value = _awscrt.s3_get_recommended_throughput_target_gbps()
    if max_value > 0:
        return max_value
    else:
        return None
