# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import contextlib
import logging
import re
import threading
from concurrent.futures import CancelledError, Future
from io import BytesIO

import awscrt.http
import botocore.awsrequest
import botocore.session
from awscrt.auth import (
    AwsCredentials,
    AwsCredentialsProvider,
    AwsSigningAlgorithm,
    AwsSigningConfig,
)
from awscrt.io import (
    ClientBootstrap,
    ClientTlsContext,
    DefaultHostResolver,
    EventLoopGroup,
    TlsContextOptions,
)
from awscrt.s3 import (
    S3Client,
    S3FileIoOptions,
    S3RequestTlsMode,
    S3RequestType,
    S3ResponseError,
    get_recommended_throughput_target_gbps,
)
from botocore import UNSIGNED
from botocore.compat import urlsplit
from botocore.config import Config
from botocore.exceptions import InvalidConfigError, NoCredentialsError
from botocore.useragent import register_feature_id
from botocore.utils import (
    ArnParser,
    InvalidArnException,
    S3RegionRedirectorv2,
    is_s3express_bucket,
)
from s3transfer.compat import seekable
from s3transfer.constants import FULL_OBJECT_CHECKSUM_ARGS, MB
from s3transfer.exceptions import TransferNotDoneError
from s3transfer.futures import BaseTransferFuture, BaseTransferMeta
from s3transfer.utils import CallArgs, OSUtils, get_callbacks

logger = logging.getLogger(__name__)

CRT_S3_PROCESS_LOCK = None


def acquire_crt_s3_process_lock(name):
    # Currently, the CRT S3 client performs best when there is only one
    # instance of it running on a host. This lock allows an application to
    # signal across processes whether there is another process of the same
    # application using the CRT S3 client and prevent spawning more than one
    # CRT S3 clients running on the system for that application.
    #
    # NOTE: When acquiring the CRT process lock, the lock automatically is
    # released when the lock object is garbage collected. So, the CRT process
    # lock is set as a global so that it is not unintentionally garbage
    # collected/released if reference of the lock is lost.
    global CRT_S3_PROCESS_LOCK
    if CRT_S3_PROCESS_LOCK is None:
        crt_lock = awscrt.s3.CrossProcessLock(name)
        try:
            crt_lock.acquire()
        except RuntimeError:
            # If there is another process that is holding the lock, the CRT
            # returns a RuntimeError. We return None here to signal that our
            # current process was not able to acquire the lock.
            return None
        CRT_S3_PROCESS_LOCK = crt_lock
    return CRT_S3_PROCESS_LOCK


def create_s3_crt_client(
    region,
    crt_credentials_provider=None,
    num_threads=None,
    target_throughput=None,
    part_size=8 * MB,
    use_ssl=True,
    verify=None,
    fio_options=None,
    bootstrap=None,
):
    """
    :type region: str
    :param region: The region used for signing

    :type crt_credentials_provider:
        Optional[awscrt.auth.AwsCredentialsProvider]
    :param crt_credentials_provider: CRT AWS credentials provider
        to use to sign requests. If not set, requests will not be signed.

    :type num_threads: Optional[int]
    :param num_threads: Number of worker threads generated. Default
        is the number of processors in the machine.

    :type target_throughput: Optional[int]
    :param target_throughput: Throughput target in bytes per second.
        By default, CRT will automatically attempt to choose a target
        throughput that matches the system's maximum network throughput.
        Currently, if CRT is unable to determine the maximum network
        throughput, a fallback target throughput of ``1_250_000_000`` bytes
        per second (which translates to 10 gigabits per second, or 1.16
        gibibytes per second) is used. To set a specific target
        throughput, set a value for this parameter.

    :type part_size: Optional[int]
    :param part_size: Size, in Bytes, of parts that files will be downloaded
        or uploaded in.

    :type use_ssl: boolean
    :param use_ssl: Whether or not to use SSL.  By default, SSL is used.
        Note that not all services support non-ssl connections.

    :type verify: Optional[boolean/string]
    :param verify: Whether or not to verify SSL certificates.
        By default SSL certificates are verified.  You can provide the
        following values:

        * False - do not validate SSL certificates.  SSL will still be
            used (unless use_ssl is False), but SSL certificates
            will not be verified.
        * path/to/cert/bundle.pem - A filename of the CA cert bundle to
            use. Specify this argument if you want to use a custom CA cert
            bundle instead of the default one on your system.

    :type fio_options: Optional[dict]
    :param fio_options: Kwargs to use to build an `awscrt.s3.S3FileIoOptions`.

    :type bootstrap: Optional[awscrt.io.ClientBootstrap]
    :param bootstrap: Shared I/O bootstrap to use for the client. If not
        provided, a new bootstrap is created.
    """

    if bootstrap is None:
        bootstrap = create_crt_client_bootstrap(num_threads)
    tls_connection_options = None

    tls_mode = (
        S3RequestTlsMode.ENABLED if use_ssl else S3RequestTlsMode.DISABLED
    )
    if verify is not None:
        if isinstance(verify, str) and not verify.strip():
            raise InvalidConfigError(
                error_msg=(
                    'Invalid CA bundle: the configured value (ca_bundle, '
                    'AWS_CA_BUNDLE, REQUESTS_CA_BUNDLE, or verify) resolved '
                    'to an empty or whitespace-only string. Provide a valid '
                    'path to a CA bundle file.'
                )
            )
        tls_ctx_options = TlsContextOptions()
        if verify:
            tls_ctx_options.override_default_trust_store_from_path(
                ca_filepath=verify
            )
        else:
            tls_ctx_options.verify_peer = False
        client_tls_option = ClientTlsContext(tls_ctx_options)
        tls_connection_options = client_tls_option.new_connection_options()
    target_gbps = _get_crt_throughput_target_gbps(
        provided_throughput_target_bytes=target_throughput
    )
    crt_fio_options = None
    if fio_options:
        crt_fio_options = S3FileIoOptions(**fio_options)
    return S3Client(
        bootstrap=bootstrap,
        region=region,
        credential_provider=crt_credentials_provider,
        part_size=part_size,
        tls_mode=tls_mode,
        tls_connection_options=tls_connection_options,
        throughput_target_gbps=target_gbps,
        enable_s3express=True,
        fio_options=crt_fio_options,
    )


def create_crt_client_bootstrap(num_threads=None):
    event_loop_group = EventLoopGroup(num_threads)
    host_resolver = DefaultHostResolver(event_loop_group)
    return ClientBootstrap(event_loop_group, host_resolver)


def _get_crt_throughput_target_gbps(provided_throughput_target_bytes=None):
    if provided_throughput_target_bytes is None:
        target_gbps = get_recommended_throughput_target_gbps()
        logger.debug(
            'Recommended CRT throughput target in gbps: %s', target_gbps
        )
        if target_gbps is None:
            target_gbps = 10.0
    else:
        # NOTE: The GB constant in s3transfer is technically a gibibyte. The
        # GB constant is not used here because the CRT interprets gigabits
        # for networking as a base power of 10
        # (i.e. 1000 ** 3 instead of 1024 ** 3).
        target_gbps = provided_throughput_target_bytes * 8 / 1_000_000_000
    logger.debug('Using CRT throughput target in gbps: %s', target_gbps)
    return target_gbps


class CRTS3RegionRedirectPolicy:
    """Decides which region a CRT transfer to a bucket should use.

    Region discovery is delegated to the request serializer, which reuses
    botocore's ``S3RegionRedirectorv2`` classification. This class owns only
    the conditions under which a redirect may be attempted at all.
    """

    def __init__(self, crt_request_serializer):
        self._crt_request_serializer = crt_request_serializer
        # Bucket regions are held under one lock so that a burst of transfers
        # failing at once shares a single lookup instead of each paying for
        # its own, potentially a HeadBucket request each, and so that a
        # request cannot be built for a region that changes while it is built.
        # One lock covers every bucket because a command generally transfers
        # to or from a single one.
        self._region_lock = threading.Lock()

    def get_cached_bucket_region(self, bucket):
        """Return a region already discovered for a bucket, if any."""
        return self._crt_request_serializer.get_cached_bucket_region(bucket)

    @contextlib.contextmanager
    def locked_bucket_region(self, bucket):
        """Hold a bucket's region steady while a request is built for it.

        Serializing a request resolves its endpoint from the region cached for
        its bucket. The caller has to select a client for that same region, so
        the region must not change in between.
        """
        with self._region_lock:
            yield self.get_cached_bucket_region(bucket)

    def is_error_redirect_candidate(
        self,
        bucket,
        is_region_redirect,
        bytes_transferred,
        cancelled,
        is_replayable,
    ):
        """Return whether a failed request may be worth redirecting.

        Callers only ask this about a request that failed, so this inspects
        the state of the transfer rather than the error itself. These checks
        are cheap and never do I/O, so a caller running on a CRT completion
        thread can use them to decide whether discovering a region is worth
        handing off to another thread.
        """
        if is_region_redirect:
            logger.debug(
                'Transfer for bucket %s was already redirected, not '
                'redirecting again.',
                bucket,
            )
            return False
        if cancelled:
            return False
        if not is_replayable:
            logger.debug(
                'Not redirecting transfer for bucket %s because its stream '
                'cannot be replayed.',
                bucket,
            )
            return False
        if bytes_transferred:
            # Replaying a request that moved data would either duplicate
            # bytes or double-count progress.
            logger.debug(
                'Not redirecting transfer for bucket %s because it already '
                'transferred %s bytes.',
                bucket,
                bytes_transferred,
            )
            return False
        if is_s3express_bucket(bucket):
            return False
        return True

    def get_retry_region(
        self, bucket, transfer_type, error, request_region=None
    ):
        """Return the region to retry a failed request in, or ``None``.

        A returned region has been cached, so both the retried request and
        later transfers to the same bucket use it. This discovers the region
        of a bucket, which may require an additional ``HeadBucket`` request,
        so it must not be called from a CRT completion thread.

        :type request_region: Optional[str]
        :param request_region: The region the failed request was made in, or
            ``None`` if it used the configured region.
        """
        retry_region = self._get_cached_retry_region(bucket, request_region)
        if retry_region is not None:
            return retry_region
        with self._region_lock:
            # Another transfer may have discovered the region while this one
            # waited for the lock.
            retry_region = self._get_cached_retry_region(
                bucket, request_region
            )
            if retry_region is not None:
                return retry_region
            return self._discover_bucket_region(
                bucket, transfer_type, error, request_region
            )

    def _get_cached_retry_region(self, bucket, request_region):
        """Return an already discovered region the failed request did not use.

        A region another transfer discovered is worth retrying in, but the one
        the request just failed in is not.
        """
        cached_region = self.get_cached_bucket_region(bucket)
        if cached_region is None:
            return None
        if cached_region == request_region:
            # The failed request already used this region, so the cached
            # region is stale and retrying there would fail the same way.
            return None
        return cached_region

    def _discover_bucket_region(
        self, bucket, transfer_type, error, request_region=None
    ):
        try:
            new_region = self._crt_request_serializer.get_bucket_region(
                bucket, transfer_type, error
            )
        except Exception as redirect_error:
            logger.debug(
                'Unable to determine S3 redirect region.',
                exc_info=redirect_error,
            )
            return None
        if new_region is None:
            return None
        if new_region == (
            request_region
            or self._crt_request_serializer.get_configured_region()
        ):
            # The failed request was already made in this region, so retrying
            # it there would fail the same way. Leaving it out of the cache
            # also keeps later transfers on the client they already use.
            logger.debug(
                'Not redirecting transfer for bucket %s because it was '
                'already made in region %s.',
                bucket,
                new_region,
            )
            return None
        logger.debug(
            'Redirecting CRT S3 transfer for bucket %s to region %s',
            bucket,
            new_region,
        )
        self._crt_request_serializer.cache_bucket_region(bucket, new_region)
        return new_region


class CRTTransferManager:
    def __init__(
        self, crt_client_factory, crt_request_serializer, osutil=None
    ):
        """A transfer manager interface for Amazon S3 on CRT s3 client.

        :type crt_client_factory:
            Callable[[Optional[str]], awscrt.s3.S3Client]
        :param crt_client_factory: Creates a CRT client. ``None`` selects the
            configured region; a region string selects a redirected region.

        :type crt_request_serializer: s3transfer.crt.BaseCRTRequestSerializer
        :param crt_request_serializer: Serializer, generates unsigned CRT HTTP
            requests.

        :type osutil: s3transfer.utils.OSUtils
        :param osutil: OSUtils object to use for os-related behavior when
            using with transfer manager.
        """
        if osutil is None:
            self._osutil = OSUtils()
        self._s3_args_creator = S3ClientArgsCreator(
            crt_request_serializer, self._osutil
        )
        self._crt_exception_translator = (
            crt_request_serializer.translate_crt_exception
        )
        self._crt_client_factory = crt_client_factory
        self._crt_clients = {}
        self._crt_client_lock = threading.Lock()
        self._region_redirect_policy = CRTS3RegionRedirectPolicy(
            crt_request_serializer
        )
        self._future_coordinators = []
        self._semaphore = threading.Semaphore(128)  # not configurable
        # A counter to create unique id's for each transfer submitted.
        self._id_counter = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, *args):
        cancel = False
        if exc_type:
            cancel = True
        self._shutdown(cancel)

    def download(
        self, bucket, key, fileobj, extra_args=None, subscribers=None
    ):
        if extra_args is None:
            extra_args = {}
        if subscribers is None:
            subscribers = {}
        callargs = CallArgs(
            bucket=bucket,
            key=key,
            fileobj=fileobj,
            extra_args=extra_args,
            subscribers=subscribers,
        )
        return self._submit_transfer("get_object", callargs)

    def upload(self, fileobj, bucket, key, extra_args=None, subscribers=None):
        if extra_args is None:
            extra_args = {}
        if subscribers is None:
            subscribers = {}
        self._validate_checksum_algorithm_supported(extra_args)
        callargs = CallArgs(
            bucket=bucket,
            key=key,
            fileobj=fileobj,
            extra_args=extra_args,
            subscribers=subscribers,
        )
        return self._submit_transfer("put_object", callargs)

    def delete(self, bucket, key, extra_args=None, subscribers=None):
        if extra_args is None:
            extra_args = {}
        if subscribers is None:
            subscribers = {}
        callargs = CallArgs(
            bucket=bucket,
            key=key,
            extra_args=extra_args,
            subscribers=subscribers,
        )
        return self._submit_transfer("delete_object", callargs)

    def shutdown(self, cancel=False):
        self._shutdown(cancel)

    def _validate_checksum_algorithm_supported(self, extra_args):
        checksum_algorithm = extra_args.get('ChecksumAlgorithm')
        if checksum_algorithm is None:
            return
        supported_algorithms = list(awscrt.s3.S3ChecksumAlgorithm.__members__)
        if checksum_algorithm.upper() not in supported_algorithms:
            raise ValueError(
                f'ChecksumAlgorithm: {checksum_algorithm} not supported. '
                f'Supported algorithms are: {supported_algorithms}'
            )

    def _cancel_transfers(self):
        for coordinator in self._future_coordinators:
            if not coordinator.done():
                coordinator.cancel()

    def _finish_transfers(self):
        for coordinator in self._future_coordinators:
            coordinator.result()

    def _wait_transfers_done(self):
        for coordinator in self._future_coordinators:
            coordinator.wait_until_on_done_callbacks_complete()

    def _shutdown(self, cancel=False):
        if cancel:
            self._cancel_transfers()
        try:
            self._finish_transfers()

        except KeyboardInterrupt:
            self._cancel_transfers()
        except Exception:
            pass
        finally:
            self._wait_transfers_done()

    def _release_semaphore(self, **kwargs):
        self._semaphore.release()

    def get_crt_client(self, region=None):
        with self._crt_client_lock:
            crt_client = self._crt_clients.get(region)
            if crt_client is None:
                logger.debug(
                    'Creating CRT S3 client for region %s',
                    region if region is not None else 'default',
                )
                crt_client = self._crt_client_factory(region)
                self._crt_clients[region] = crt_client
            return crt_client

    def _submit_transfer(self, request_type, call_args):
        register_feature_id('S3_TRANSFER')
        on_done_after_calls = [self._release_semaphore]
        coordinator = CRTTransferCoordinator(
            transfer_id=self._id_counter,
            exception_translator=self._crt_exception_translator,
            completion_future=Future(),
        )
        components = {
            'meta': CRTTransferMeta(self._id_counter, call_args),
            'coordinator': coordinator,
        }
        future = CRTTransferFuture(**components)
        afterdone = AfterDoneHandler(coordinator)
        on_done_after_calls.append(afterdone)
        # Serialization can rewrite an ARN in call_args, so retain the
        # caller-provided bucket for redirect eligibility and caching.
        bucket = call_args.bucket
        # Record the current stream position and if its replayable,
        # in the event of a region redirect, we need to reset first
        is_replayable = True
        upload_stream_position = None
        if request_type == 'put_object' and not isinstance(
            call_args.fileobj, str
        ):
            try:
                is_replayable = seekable(call_args.fileobj)
                if is_replayable:
                    upload_stream_position = call_args.fileobj.tell()
            except (AttributeError, OSError, ValueError):
                is_replayable = False

        try:
            self._semaphore.acquire()
            on_queued = self._s3_args_creator.get_crt_callback(
                future, 'queued'
            )
            on_queued()

            def create_request(is_region_redirect):
                # Reset the stream if we're redirecting due to bucket region
                if is_region_redirect and upload_stream_position is not None:
                    call_args.fileobj.seek(upload_stream_position)
                policy = self._region_redirect_policy
                with policy.locked_bucket_region(bucket) as region:
                    if region is not None:
                        logger.debug(
                            'Using cached region %s for S3 bucket %s',
                            region,
                            bucket,
                        )
                    crt_callargs = (
                        self._s3_args_creator.get_make_request_args(
                            request_type,
                            call_args,
                            coordinator,
                            future,
                            on_done_after_calls,
                        )
                    )
                    crt_client = self.get_crt_client(region)
                return crt_client, crt_callargs, region

            coordinator.submit(
                create_request,
                self._region_redirect_policy,
                bucket,
                request_type,
                is_replayable=is_replayable,
            )
        except Exception as e:
            coordinator.set_exception(e, True)
            on_done = self._s3_args_creator.get_crt_callback(
                future, 'done', after_subscribers=on_done_after_calls
            )
            coordinator.complete(e)
            on_done(error=e)
        self._future_coordinators.append(coordinator)

        self._id_counter += 1
        return future


class CRTTransferMeta(BaseTransferMeta):
    """Holds metadata about the CRTTransferFuture"""

    def __init__(self, transfer_id=None, call_args=None):
        self._transfer_id = transfer_id
        self._call_args = call_args
        self._user_context = {}

    @property
    def call_args(self):
        return self._call_args

    @property
    def transfer_id(self):
        return self._transfer_id

    @property
    def user_context(self):
        return self._user_context


class CRTTransferFuture(BaseTransferFuture):
    def __init__(self, meta=None, coordinator=None):
        """The future associated to a submitted transfer request via CRT S3 client

        :type meta: s3transfer.crt.CRTTransferMeta
        :param meta: The metadata associated to the transfer future.

        :type coordinator: s3transfer.crt.CRTTransferCoordinator
        :param coordinator: The coordinator associated to the transfer future.
        """
        self._meta = meta
        if meta is None:
            self._meta = CRTTransferMeta()
        self._coordinator = coordinator

    @property
    def meta(self):
        return self._meta

    def done(self):
        return self._coordinator.done()

    def result(self, timeout=None):
        self._coordinator.result(timeout)

    def cancel(self):
        self._coordinator.cancel()

    def set_exception(self, exception):
        """Sets the exception on the future."""
        if not self.done():
            raise TransferNotDoneError(
                'set_exception can only be called once the transfer is '
                'complete.'
            )
        self._coordinator.set_exception(exception, override=True)


class BaseCRTRequestSerializer:
    def serialize_http_request(self, transfer_type, future):
        """Serialize CRT HTTP requests.

        :type transfer_type: string
        :param transfer_type: the type of transfer made,
            e.g 'put_object', 'get_object', 'delete_object'

        :type future: s3transfer.crt.CRTTransferFuture

        :rtype: awscrt.http.HttpRequest
        :returns: An unsigned HTTP request to be used for the CRT S3 client
        """
        raise NotImplementedError('serialize_http_request()')

    def translate_crt_exception(self, exception):
        raise NotImplementedError('translate_crt_exception()')

    def get_cached_bucket_region(self, bucket):
        """Return the region already discovered for a bucket, if any.

        Serializers that do not support bucket region redirects never have a
        region to report, which keeps their transfers in the configured
        region.
        """
        return None

    def cache_bucket_region(self, bucket, region):
        """Remember the region a bucket was found in."""

    def get_bucket_region(self, bucket, transfer_type, error):
        """Return the region a failed request should be retried in, if any."""
        return None

    def get_configured_region(self):
        """Return the region requests are serialized for by default."""
        return None


class LazyHeadBucketClient:
    """
    A boto client that is lazily initialized when needing to call head_bucket.
    The existing region redirect logic supports falling back to this when the
    region cannot be parsed from the S3 exception. We use this boto client even
    when CRT is being used for transfers
    """

    def __init__(self, client_factory):
        self._client_factory = client_factory
        self._client = None
        self._lock = threading.Lock()

    def head_bucket(self, **kwargs):
        with self._lock:
            if self._client is None:
                self._client = self._client_factory()
            client = self._client
        return client.head_bucket(**kwargs)


class BotocoreCRTRequestSerializer(BaseCRTRequestSerializer):
    def __init__(
        self,
        session,
        client_kwargs=None,
        region_redirect_client_factory=None,
    ):
        """Serialize CRT HTTP request using botocore logic
        It also takes into account configuration from both the session
        and any keyword arguments that could be passed to
        `Session.create_client()` when serializing the request.

        :type session: botocore.session.Session

        :type client_kwargs: Optional[Dict[str, str]])
        :param client_kwargs: The kwargs for the botocore
            s3 client initialization.

        :type region_redirect_client_factory: Optional[Callable]
        :param region_redirect_client_factory: Creates a real botocore S3
            client if a CRT redirect response requires a HeadBucket fallback.
        """
        self._session = session
        if client_kwargs is None:
            client_kwargs = {}
        client_kwargs = client_kwargs.copy()

        # Preserve the caller's client configuration for the real botocore
        # client used only by the HeadBucket fallback. The serializer client
        # below is reconfigured as unsigned and never sends its request.
        if region_redirect_client_factory is None:
            redirect_client_kwargs = client_kwargs.copy()
            redirect_client_kwargs['service_name'] = 's3'
            region_redirect_client_factory = lambda: session.create_client(
                **redirect_client_kwargs
            )

        # Build the botocore client that converts API arguments into the
        # unsigned HTTP requests consumed by CRT.
        self._resolve_client_config(session, client_kwargs)
        self._client = session.create_client(**client_kwargs)

        # Share the bucket-region cache between redirect discovery and later
        # request serialization. The real fallback client remains lazy.
        self._region_redirect_client = LazyHeadBucketClient(
            region_redirect_client_factory
        )
        self._region_cache = {}
        self._region_redirector = S3RegionRedirectorv2(
            None, self._region_redirect_client, cache=self._region_cache
        )

        # Convert normal botocore calls into serialized requests without
        # allowing the serializer client to perform network I/O.
        self._client.meta.events.register(
            'request-created.s3.*', self._capture_http_request
        )
        self._client.meta.events.register(
            'after-call.s3.*', self._change_response_to_serialized_http_request
        )
        self._client.meta.events.register(
            'before-send.s3.*', self._make_fake_http_response
        )
        self._client.meta.events.register(
            'before-call.s3.*', self._remove_checksum_context
        )
        self._client.meta.events.register(
            'before-endpoint-resolution.s3',
            self._region_redirector.redirect_from_cache,
        )

    def _resolve_client_config(self, session, client_kwargs):
        user_provided_config = None
        if session.get_default_client_config():
            user_provided_config = session.get_default_client_config()
        if 'config' in client_kwargs:
            user_provided_config = client_kwargs['config']

        client_config = Config(signature_version=UNSIGNED)
        if user_provided_config:
            client_config = user_provided_config.merge(client_config)
        client_kwargs['config'] = client_config
        client_kwargs["service_name"] = "s3"

    def _crt_request_from_aws_request(self, aws_request):
        url_parts = urlsplit(aws_request.url)
        crt_path = url_parts.path
        if url_parts.query:
            crt_path = f'{crt_path}?{url_parts.query}'
        headers_list = []
        for name, value in aws_request.headers.items():
            if isinstance(value, str):
                headers_list.append((name, value))
            else:
                headers_list.append((name, str(value, 'utf-8')))

        crt_headers = awscrt.http.HttpHeaders(headers_list)

        crt_request = awscrt.http.HttpRequest(
            method=aws_request.method,
            path=crt_path,
            headers=crt_headers,
            body_stream=aws_request.body,
        )
        return crt_request

    def _convert_to_crt_http_request(self, botocore_http_request):
        # Logic that does CRTUtils.crt_request_from_aws_request
        crt_request = self._crt_request_from_aws_request(botocore_http_request)
        if crt_request.headers.get("host") is None:
            # If host is not set, set it for the request before using CRT s3
            url_parts = urlsplit(botocore_http_request.url)
            crt_request.headers.set("host", url_parts.netloc)
        if crt_request.headers.get('Content-MD5') is not None:
            crt_request.headers.remove("Content-MD5")

        # In general, the CRT S3 client expects a content length header. It
        # only expects a missing content length header if the body is not
        # seekable. However, botocore does not set the content length header
        # for GetObject API requests and so we set the content length to zero
        # to meet the CRT S3 client's expectation that the content length
        # header is set even if there is no body.
        if crt_request.headers.get('Content-Length') is None:
            if botocore_http_request.body is None:
                crt_request.headers.add('Content-Length', "0")

        # Botocore sets the Transfer-Encoding header when it cannot determine
        # the content length of the request body (e.g. it's not seekable).
        # However, CRT does not support this header, but it supports
        # non-seekable bodies. So we remove this header to not cause issues
        # in the downstream CRT S3 request.
        if crt_request.headers.get('Transfer-Encoding') is not None:
            crt_request.headers.remove('Transfer-Encoding')

        return crt_request

    def _capture_http_request(self, request, **kwargs):
        request.context['http_request'] = request

    def _change_response_to_serialized_http_request(
        self, context, parsed, **kwargs
    ):
        request = context['http_request']
        parsed['HTTPRequest'] = request.prepare()

    def _make_fake_http_response(self, request, **kwargs):
        return botocore.awsrequest.AWSResponse(
            None,
            200,
            {},
            FakeRawResponse(b""),
        )

    def _get_botocore_http_request(self, client_method, call_args):
        return getattr(self._client, client_method)(
            Bucket=call_args.bucket, Key=call_args.key, **call_args.extra_args
        )['HTTPRequest']

    def serialize_http_request(self, transfer_type, future):
        botocore_http_request = self._get_botocore_http_request(
            transfer_type, future.meta.call_args
        )
        crt_request = self._convert_to_crt_http_request(botocore_http_request)
        return crt_request

    def translate_crt_exception(self, exception):
        if isinstance(exception, S3ResponseError):
            return self._translate_crt_s3_response_error(exception)
        else:
            return None

    def _translate_crt_s3_response_error(self, s3_response_error):
        status_code = s3_response_error.status_code
        if status_code < 301:
            # Botocore's exception parsing only
            # runs on status codes >= 301
            return None

        headers = {k: v for k, v in s3_response_error.headers}
        operation_name = s3_response_error.operation_name
        if operation_name is not None:
            service_model = self._client.meta.service_model
            shape = service_model.operation_model(operation_name).output_shape
        else:
            shape = None

        response_dict = {
            'headers': botocore.awsrequest.HeadersDict(headers),
            'status_code': status_code,
            'body': s3_response_error.body,
        }
        parsed_response = self._client._response_parser.parse(
            response_dict, shape=shape
        )

        error_code = parsed_response.get("Error", {}).get("Code")
        error_class = self._client.exceptions.from_code(error_code)
        return error_class(parsed_response, operation_name=operation_name)

    def _remove_checksum_context(self, params, **kwargs):
        request_context = params.get("context", {})
        if "checksum" in request_context:
            del request_context["checksum"]

    def cache_bucket_region(self, bucket, region):
        self._region_cache[bucket] = region

    def get_cached_bucket_region(self, bucket):
        return self._region_cache.get(bucket)

    def get_configured_region(self):
        return self._client.meta.region_name

    def get_bucket_region(self, bucket, transfer_type, error):
        """Extract a redirect region from a CRT response error.
        This adapts the CRT error for S3RegionRedirectorv2.
        """
        if not isinstance(error, S3ResponseError):
            return None
        translated_error = self._translate_crt_s3_response_error(error)
        if translated_error is None:
            return None

        operation_name = (
            translated_error.operation_name
            or self._client.meta.method_to_api_mapping[transfer_type]
        )
        operation = self._client.meta.service_model.operation_model(
            operation_name
        )
        http_response = botocore.awsrequest.AWSResponse(
            None,
            error.status_code,
            dict(error.headers or []),
            FakeRawResponse(error.body or b''),
        )
        response = (http_response, translated_error.response)
        # The redirector checks the CRT response first. It only uses this
        # serializer's real botocore client for HeadBucket when the response
        # identifies a redirect but omits the target region.
        return self._region_redirector.get_redirect_region(
            bucket,
            response,
            operation,
        )


class FakeRawResponse(BytesIO):
    def stream(self, amt=1024, decode_content=None):
        while True:
            chunk = self.read(amt)
            if not chunk:
                break
            yield chunk


class BotocoreCRTCredentialsWrapper:
    def __init__(self, resolved_botocore_credentials):
        self._resolved_credentials = resolved_botocore_credentials

    def __call__(self):
        credentials = self._get_credentials().get_frozen_credentials()
        return AwsCredentials(
            credentials.access_key, credentials.secret_key, credentials.token
        )

    def to_crt_credentials_provider(self):
        return AwsCredentialsProvider.new_delegate(self)

    def _get_credentials(self):
        if self._resolved_credentials is None:
            raise NoCredentialsError()
        return self._resolved_credentials


class CRTTransferCoordinator:
    """
    Coordinates one logical transfer across its native CRT request(s), which
    can make two if following a bucket region redirect
    """

    def __init__(
        self,
        transfer_id=None,
        s3_request=None,
        exception_translator=None,
        completion_future=None,
    ):
        self.transfer_id = transfer_id
        self._exception_translator = exception_translator
        self._s3_request = s3_request
        self._lock = threading.Lock()
        self._exception = None
        # This future represents the entire transfer,
        # which could include a retry for a region redirect.
        self._completion_future = completion_future or Future()
        self._completion_started = False
        self._done_event = threading.Event()
        self._cancelled = False
        self._redirect_retry_started = False
        # Set by submit(), and the same for every request the transfer makes.
        self._request_factory = None
        self._region_redirect_policy = None
        self._bucket = None
        self._transfer_type = None
        self._is_replayable = True

    @property
    def s3_request(self):
        return self._s3_request

    def set_done_callbacks_complete(self):
        self._done_event.set()

    def wait_until_on_done_callbacks_complete(self, timeout=None):
        self._done_event.wait(timeout)

    def set_exception(self, exception, override=False):
        with self._lock:
            if not self.done() or override:
                self._exception = exception

    def cancel(self):
        with self._lock:
            self._cancelled = True
            s3_request = self._s3_request
        if s3_request:
            s3_request.cancel()

    @property
    def cancelled(self):
        with self._lock:
            return self._cancelled

    def result(self, timeout=None):
        if self._exception:
            raise self._exception
        try:
            self._completion_future.result(timeout)
        except KeyboardInterrupt:
            self.cancel()
            self._completion_future.result(timeout)
            raise
        except Exception as e:
            self.handle_exception(e)
        finally:
            if self._s3_request:
                self._s3_request = None

    def handle_exception(self, exc):
        translated_exc = None
        if self._exception_translator:
            try:
                translated_exc = self._exception_translator(exc)
            except Exception as e:
                # Bail out if we hit an issue translating
                # and raise the original error.
                logger.debug("Unable to translate exception.", exc_info=e)
                pass
        if translated_exc is not None:
            raise translated_exc from exc
        else:
            raise exc

    def done(self):
        return self._completion_future.done()

    def submit(
        self,
        request_factory,
        region_redirect_policy,
        bucket,
        transfer_type,
        is_replayable=True,
    ):
        """Submit the transfer's CRT request.

        A request that failed because it was made in the wrong region for its
        bucket is resubmitted in the bucket's region, which makes a second
        request for the same transfer.
        """
        self._request_factory = request_factory
        self._region_redirect_policy = region_redirect_policy
        self._bucket = bucket
        self._transfer_type = transfer_type
        self._is_replayable = is_replayable
        self._start_request(is_region_redirect=False)

    def _start_request(self, is_region_redirect):
        with self._lock:
            if self._cancelled:
                raise CancelledError()
            if is_region_redirect:
                self._redirect_retry_started = True
        crt_client, crt_callargs, request_region = self._request_factory(
            is_region_redirect
        )
        on_done = crt_callargs['on_done']
        on_progress = crt_callargs['on_progress']
        bytes_transferred = 0

        def track_progress(transferred):
            nonlocal bytes_transferred
            bytes_transferred += transferred
            on_progress(transferred)

        def finish(error, kwargs):
            self.complete(error)
            on_done(error=error, **kwargs)

        def redirect_and_finish(error, kwargs):
            # Any failure deciding on or starting a redirect must still
            # complete the transfer. Otherwise the transfer is never marked
            # done and anything waiting on its result blocks forever.
            try:
                new_region = self._region_redirect_policy.get_retry_region(
                    self._bucket,
                    self._transfer_type,
                    error,
                    request_region,
                )
                if new_region is not None:
                    try:
                        self._start_request(is_region_redirect=True)
                        return
                    except Exception as retry_error:
                        retry_error.__cause__ = error
                        error = retry_error
                        self.set_exception(retry_error, True)
            except Exception as redirect_error:
                logger.debug(
                    'Unable to determine whether to redirect transfer for '
                    'bucket %s.',
                    self._bucket,
                    exc_info=redirect_error,
                )
                if error is None:
                    error = redirect_error
                    self.set_exception(redirect_error, True)
            finish(error, kwargs)

        def request_done(error=None, **kwargs):
            if error is not None and self._can_redirect(
                is_region_redirect, bytes_transferred
            ):
                # Discovering a region and serializing the retry can both
                # block, and this runs on a CRT completion thread, where
                # blocking stalls every other transfer sharing the event loop.
                self._dispatch_redirect(redirect_and_finish, error, kwargs)
                return
            # Nothing to discover, so finish on this thread rather than paying
            # for a handoff on every completed transfer.
            finish(error, kwargs)

        crt_callargs['on_done'] = request_done
        crt_callargs['on_progress'] = track_progress
        s3_request = crt_client.make_request(**crt_callargs)
        self.set_s3_request(s3_request, is_region_redirect=is_region_redirect)

    def _can_redirect(self, is_region_redirect, bytes_transferred):
        try:
            return self._region_redirect_policy.is_error_redirect_candidate(
                bucket=self._bucket,
                is_region_redirect=is_region_redirect,
                bytes_transferred=bytes_transferred,
                cancelled=self.cancelled,
                is_replayable=self._is_replayable,
            )
        except Exception as redirect_error:
            logger.debug(
                'Unable to determine whether transfer for bucket %s can be '
                'redirected.',
                self._bucket,
                exc_info=redirect_error,
            )
            return False

    def _dispatch_redirect(self, fn, *args):
        """Run a region redirect off of the CRT completion thread.

        Discovering a region and serializing the retry can both block, which
        would stall the event loop shared by every in-flight transfer. A
        transfer is redirected at most once and only when it fails, so these
        threads are few and short lived.
        """
        try:
            threading.Thread(
                target=fn, args=args, name='crt-s3-region-redirect'
            ).start()
        except RuntimeError as thread_error:
            # The OS refused a new thread. Blocking this thread is still
            # better than stranding the transfer.
            logger.debug(
                'Unable to hand off S3 region redirect, handling it inline.',
                exc_info=thread_error,
            )
            fn(*args)

    def set_s3_request(self, s3_request, is_region_redirect=False):
        """Make a CRT request the one the transfer acts on."""
        with self._lock:
            if not is_region_redirect and self._redirect_retry_started:
                # The redirect is already active. The original request
                # completed and redirected before make_request() returned.
                return
            if is_region_redirect:
                self._redirect_retry_started = True
            self._s3_request = s3_request
            cancelled = self._cancelled
        if cancelled:
            s3_request.cancel()

    def complete(self, error=None):
        """Complete the logical transfer after the original or retry request.

        This is separate from the native CRT request completion callbacks.
        """
        with self._lock:
            if self._completion_started or self._completion_future.done():
                return
            self._completion_started = True
            completion_future = self._completion_future
        if error is None:
            completion_future.set_result(None)
        else:
            completion_future.set_exception(error)


class S3ClientArgsCreator:
    _DOWNLOAD_TEMP_FILENAME = '_crt_download_temp_filename'

    def __init__(self, crt_request_serializer, os_utils):
        self._request_serializer = crt_request_serializer
        self._os_utils = os_utils

    def get_make_request_args(
        self, request_type, call_args, coordinator, future, on_done_after_calls
    ):
        request_args_handler = getattr(
            self,
            f'_get_make_request_args_{request_type}',
            self._default_get_make_request_args,
        )
        return request_args_handler(
            request_type=request_type,
            call_args=call_args,
            coordinator=coordinator,
            future=future,
            on_done_before_calls=[],
            on_done_after_calls=on_done_after_calls,
        )

    def get_crt_callback(
        self,
        future,
        callback_type,
        before_subscribers=None,
        after_subscribers=None,
    ):
        def invoke_all_callbacks(*args, **kwargs):
            callbacks_list = []
            if before_subscribers is not None:
                callbacks_list += before_subscribers
            callbacks_list += get_callbacks(future, callback_type)
            if after_subscribers is not None:
                callbacks_list += after_subscribers
            for callback in callbacks_list:
                # The get_callbacks helper will set the first augment
                # by keyword, the other augments need to be set by keyword
                # as well
                if callback_type == "progress":
                    callback(bytes_transferred=args[0])
                else:
                    callback(*args, **kwargs)

        return invoke_all_callbacks

    def _get_make_request_args_put_object(
        self,
        request_type,
        call_args,
        coordinator,
        future,
        on_done_before_calls,
        on_done_after_calls,
    ):
        send_filepath = None
        if isinstance(call_args.fileobj, str):
            send_filepath = call_args.fileobj
            data_len = self._os_utils.get_file_size(send_filepath)
            call_args.extra_args["ContentLength"] = data_len
        else:
            call_args.extra_args["Body"] = call_args.fileobj

        checksum_config = None
        provided_checksum_algorithm = None
        if not any(
            checksum_arg in call_args.extra_args
            for checksum_arg in FULL_OBJECT_CHECKSUM_ARGS
        ):
            # CRT applies this checksum itself, so we hide it from botocore
            # while serializing but store it for a possible redirected attempt
            provided_checksum_algorithm = call_args.extra_args.pop(
                'ChecksumAlgorithm', None
            )
            applied_checksum_algorithm = (
                provided_checksum_algorithm or 'CRC64NVME'
            ).upper()
            checksum_config = awscrt.s3.S3ChecksumConfig(
                algorithm=awscrt.s3.S3ChecksumAlgorithm[
                    applied_checksum_algorithm
                ],
                location=awscrt.s3.S3ChecksumLocation.TRAILER,
            )
        # Suppress botocore's automatic MD5 calculation by setting an override
        # value that will get deleted in the BotocoreCRTRequestSerializer.
        # As part of the CRT S3 request, we request the CRT S3 client to
        # automatically add trailing checksums to its uploads.
        call_args.extra_args["ContentMD5"] = "override-to-be-removed"

        try:
            make_request_args = self._default_get_make_request_args(
                request_type=request_type,
                call_args=call_args,
                coordinator=coordinator,
                future=future,
                on_done_before_calls=on_done_before_calls,
                on_done_after_calls=on_done_after_calls,
            )
        finally:
            if provided_checksum_algorithm is not None:
                call_args.extra_args['ChecksumAlgorithm'] = (
                    provided_checksum_algorithm
                )
        make_request_args['send_filepath'] = send_filepath
        make_request_args['checksum_config'] = checksum_config
        return make_request_args

    def _get_make_request_args_get_object(
        self,
        request_type,
        call_args,
        coordinator,
        future,
        on_done_before_calls,
        on_done_after_calls,
    ):
        recv_filepath = None
        on_body = None
        checksum_config = awscrt.s3.S3ChecksumConfig(validate_response=True)
        if isinstance(call_args.fileobj, str):
            final_filepath = call_args.fileobj
            # A redirected download creates more than one CRT request for the
            # same logical transfer. Keep one temp path so the final done
            # callback handles the file used by every attempt.
            recv_filepath = future.meta.user_context.get(
                self._DOWNLOAD_TEMP_FILENAME
            )
            if recv_filepath is None:
                # Store the path before the first request so a redirected
                # attempt reuses it.
                recv_filepath = self._os_utils.get_temp_filename(
                    final_filepath
                )
                future.meta.user_context[self._DOWNLOAD_TEMP_FILENAME] = (
                    recv_filepath
                )
            on_done_before_calls.append(
                RenameTempFileHandler(
                    coordinator, final_filepath, recv_filepath, self._os_utils
                )
            )
        else:
            on_body = OnBodyFileObjWriter(call_args.fileobj)

        make_request_args = self._default_get_make_request_args(
            request_type=request_type,
            call_args=call_args,
            coordinator=coordinator,
            future=future,
            on_done_before_calls=on_done_before_calls,
            on_done_after_calls=on_done_after_calls,
        )
        make_request_args['recv_filepath'] = recv_filepath
        make_request_args['on_body'] = on_body
        make_request_args['checksum_config'] = checksum_config
        return make_request_args

    def _default_get_make_request_args(
        self,
        request_type,
        call_args,
        coordinator,
        future,
        on_done_before_calls,
        on_done_after_calls,
    ):
        make_request_args = {
            'request': self._request_serializer.serialize_http_request(
                request_type, future
            ),
            'type': getattr(
                S3RequestType, request_type.upper(), S3RequestType.DEFAULT
            ),
            'on_done': self.get_crt_callback(
                future, 'done', on_done_before_calls, on_done_after_calls
            ),
            'on_progress': self.get_crt_callback(future, 'progress'),
        }

        # For DEFAULT requests, CRT requires the official S3 operation name.
        # So transform string like "delete_object" -> "DeleteObject".
        if make_request_args['type'] == S3RequestType.DEFAULT:
            make_request_args['operation_name'] = ''.join(
                x.title() for x in request_type.split('_')
            )

        arn_handler = _S3ArnParamHandler()
        if (
            accesspoint_arn_details := arn_handler.handle_arn(call_args.bucket)
        ) and accesspoint_arn_details['region'] == "":
            # Configure our region to `*` to propogate in `x-amz-region-set`
            # for multi-region support in MRAP accesspoints.
            # use_double_uri_encode and should_normalize_uri_path are defaulted to be True
            # But SDK already encoded the URI, and it's for S3, so set both to False
            make_request_args['signing_config'] = AwsSigningConfig(
                algorithm=AwsSigningAlgorithm.V4_ASYMMETRIC,
                region="*",
                use_double_uri_encode=False,
                should_normalize_uri_path=False,
            )
            call_args.bucket = accesspoint_arn_details['resource_name']
        elif is_s3express_bucket(call_args.bucket):
            # use_double_uri_encode and should_normalize_uri_path are defaulted to be True
            # But SDK already encoded the URI, and it's for S3, so set both to False
            make_request_args['signing_config'] = AwsSigningConfig(
                algorithm=AwsSigningAlgorithm.V4_S3EXPRESS,
                use_double_uri_encode=False,
                should_normalize_uri_path=False,
            )
        return make_request_args


class RenameTempFileHandler:
    def __init__(self, coordinator, final_filename, temp_filename, osutil):
        self._coordinator = coordinator
        self._final_filename = final_filename
        self._temp_filename = temp_filename
        self._osutil = osutil

    def __call__(self, **kwargs):
        error = kwargs['error']
        if error:
            self._osutil.remove_file(self._temp_filename)
        else:
            try:
                self._osutil.rename_file(
                    self._temp_filename, self._final_filename
                )
            except Exception as e:
                self._osutil.remove_file(self._temp_filename)
                # the CRT future has done already at this point
                self._coordinator.set_exception(e)


class AfterDoneHandler:
    def __init__(self, coordinator):
        self._coordinator = coordinator

    def __call__(self, **kwargs):
        self._coordinator.set_done_callbacks_complete()


class OnBodyFileObjWriter:
    def __init__(self, fileobj):
        self._fileobj = fileobj

    def __call__(self, chunk, **kwargs):
        self._fileobj.write(chunk)


class _S3ArnParamHandler:
    """Partial port of S3ArnParamHandler from botocore.

    This is used to make a determination on MRAP accesspoints for signing
    purposes. This should be safe to remove once we properly integrate auth
    resolution from Botocore into the CRT transfer integration.
    """

    _RESOURCE_REGEX = re.compile(
        r'^(?P<resource_type>accesspoint|outpost)[/:](?P<resource_name>.+)$'
    )

    def __init__(self):
        self._arn_parser = ArnParser()

    def handle_arn(self, bucket):
        arn_details = self._get_arn_details_from_bucket(bucket)
        if arn_details is None:
            return
        if arn_details['resource_type'] == 'accesspoint':
            return arn_details

    def _get_arn_details_from_bucket(self, bucket):
        try:
            arn_details = self._arn_parser.parse_arn(bucket)
            self._add_resource_type_and_name(arn_details)
            return arn_details
        except InvalidArnException:
            pass
        return None

    def _add_resource_type_and_name(self, arn_details):
        match = self._RESOURCE_REGEX.match(arn_details['resource'])
        if match:
            arn_details['resource_type'] = match.group('resource_type')
            arn_details['resource_name'] = match.group('resource_name')
