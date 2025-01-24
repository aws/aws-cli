"""
AWS client-side authentication: standard credentials providers and signing.
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt
from awscrt import NativeResource
import awscrt.exceptions
from awscrt.http import HttpRequest, HttpProxyOptions
from awscrt.io import ClientBootstrap, ClientTlsContext
from concurrent.futures import Future
import datetime
from enum import IntEnum
from typing import Optional, Sequence, Tuple


class AwsCredentials(NativeResource):
    """
    AwsCredentials are the public/private data needed to sign an authenticated AWS request.

    AwsCredentials are immutable.

    Args:
        access_key_id (str): Access key ID
        secret_access_key (str): Secret access key
        session_token (Optional[str]): Optional security token associated with
            the credentials.
        expiration (Optional[datetime.datetime]): Optional expiration datetime,
            that the credentials will no longer be valid past.
            Converted to UTC timezone and rounded down to nearest second.
            If not set, then credentials do not expire.

    Attributes:
        access_key_id (str): Access key ID
        secret_access_key (str): Secret access key
        session_token (Optional[str]): Security token associated with
            the credentials. None if not set.
        expiration (Optional[datetime.datetime]): Expiration datetime,
            that the credentials will no longer be valid past.
            None if credentials do not expire.
            Timezone is always UTC.
    """
    __slots__ = ()

    # C layer uses UINT64_MAX as timestamp for non-expiring credentials
    _NONEXPIRING_TIMESTAMP = 0xFFFFFFFFFFFFFFFF

    def __init__(self, access_key_id, secret_access_key, session_token=None, expiration=None):
        assert isinstance(access_key_id, str)
        assert isinstance(secret_access_key, str)
        assert isinstance(session_token, str) or session_token is None

        # C layer uses large int as timestamp for non-expiring credentials
        if expiration is None:
            expiration_timestamp = self._NONEXPIRING_TIMESTAMP
        else:
            expiration_timestamp = int(expiration.timestamp())
            if expiration_timestamp < 0 or expiration_timestamp >= self._NONEXPIRING_TIMESTAMP:
                raise OverflowError("expiration datetime out of range")

        super().__init__()
        self._binding = _awscrt.credentials_new(
            access_key_id,
            secret_access_key,
            session_token,
            expiration_timestamp)

    @classmethod
    def _from_binding(cls, binding):
        """Construct from a pre-existing native object"""
        credentials = cls.__new__(cls)  # avoid class's default constructor
        super(cls, credentials).__init__()  # just invoke parent class's __init__()
        credentials._binding = binding
        return credentials

    @property
    def access_key_id(self):
        return _awscrt.credentials_access_key_id(self._binding)

    @property
    def secret_access_key(self):
        return _awscrt.credentials_secret_access_key(self._binding)

    @property
    def session_token(self):
        return _awscrt.credentials_session_token(self._binding)

    @property
    def expiration(self):
        timestamp = _awscrt.credentials_expiration_timestamp_seconds(self._binding)
        # C layer uses large int as timestamp for non-expiring credentials
        if timestamp == self._NONEXPIRING_TIMESTAMP:
            return None
        else:
            return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

    def __deepcopy__(self, memo):
        # AwsCredentials is immutable, so just return self.
        return self


class AwsCredentialsProviderBase(NativeResource):
    # Pointless base class, kept for backwards compatibility.
    # AwsCredentialsProvider is (and always will be) the only subclass.
    #
    # Originally created with the thought that, when we supported
    # custom python providers, they would inherit from this class.
    # We ended up supporting custom python providers via
    # AwsCredentialsProvider.new_delegate() instead.
    pass


class AwsCredentialsProvider(AwsCredentialsProviderBase):
    """
    Credentials providers source the AwsCredentials needed to sign an authenticated AWS request.

    This class provides `new_X()` functions for several built-in provider types.
    To define a custom provider, use the :meth:`new_delegate()` function.
    """
    __slots__ = ()

    def __init__(self, binding):
        super().__init__()
        self._binding = binding

    @classmethod
    def new_default_chain(cls, client_bootstrap=None):
        """
        Create the default provider chain used by most AWS SDKs.

        Generally:

        1.  Environment
        2.  Profile
        3.  (conditional, off by default) ECS
        4.  (conditional, on by default) EC2 Instance Metadata

        Args:
            client_bootstrap (Optional[ClientBootstrap]): Client bootstrap to use when initiating socket connection.
                If not set, uses the default static ClientBootstrap instead.

        Returns:
            AwsCredentialsProvider:
        """
        assert isinstance(client_bootstrap, ClientBootstrap) or client_bootstrap is None

        if client_bootstrap is None:
            client_bootstrap = ClientBootstrap.get_or_create_static_default()

        binding = _awscrt.credentials_provider_new_chain_default(client_bootstrap)
        return cls(binding)

    @classmethod
    def new_static(cls, access_key_id, secret_access_key, session_token=None):
        """
        Create a simple provider that just returns a fixed set of credentials.

        Args:
            access_key_id (str): Access key ID
            secret_access_key (str): Secret access key
            session_token (Optional[str]): Optional session token

        Returns:
            AwsCredentialsProvider:
        """
        assert isinstance(access_key_id, str)
        assert isinstance(secret_access_key, str)
        assert isinstance(session_token, str) or session_token is None

        binding = _awscrt.credentials_provider_new_static(access_key_id, secret_access_key, session_token)
        return cls(binding)

    @classmethod
    def new_profile(
            cls,
            client_bootstrap=None,
            profile_name=None,
            config_filepath=None,
            credentials_filepath=None):
        """
        Creates a provider that sources credentials from key-value profiles
        loaded from the aws credentials file.

        Args:
            client_bootstrap (Optional[ClientBootstrap]): Client bootstrap to use when initiating socket connection.
                If not set, uses the static default ClientBootstrap instead.

            profile_name (Optional[str]): Name of profile to use.
                If not set, uses value from AWS_PROFILE environment variable.
                If that is not set, uses value of "default"

            config_filepath (Optional[str]): Path to profile config file.
                If not set, uses value from AWS_CONFIG_FILE environment variable.
                If that is not set, uses value of "~/.aws/config"

            credentials_filepath (Optional[str]): Path to profile credentials file.
                If not set, uses value from AWS_SHARED_CREDENTIALS_FILE environment variable.
                If that is not set, uses value of "~/.aws/credentials"

        Returns:
            AwsCredentialsProvider:
        """
        assert isinstance(client_bootstrap, ClientBootstrap) or client_bootstrap is None
        assert isinstance(profile_name, str) or profile_name is None
        assert isinstance(config_filepath, str) or config_filepath is None
        assert isinstance(credentials_filepath, str) or credentials_filepath is None

        if client_bootstrap is None:
            client_bootstrap = ClientBootstrap.get_or_create_static_default()

        binding = _awscrt.credentials_provider_new_profile(
            client_bootstrap, profile_name, config_filepath, credentials_filepath)
        return cls(binding)

    @classmethod
    def new_process(cls, profile_to_use=None):
        """
        Creates a provider that sources credentials from running an external command or process.

        The command to run is sourced from a profile in the AWS config file, using the standard
        profile selection rules. The profile key the command is read from is "credential_process."
        Example::

            [default]
            credential_process=/opt/amazon/bin/my-credential-fetcher --argsA=abc

        On successfully running the command, the output should be a json data with the following
        format::

            {
                "Version": 1,
                "AccessKeyId": "accesskey",
                "SecretAccessKey": "secretAccessKey"
                "SessionToken": "....",
                "Expiration": "2019-05-29T00:21:43Z"
            }

        Version here identifies the command output format version.
        This provider is not part of the default provider chain.

        Args:
            profile_to_use (Optional[str]): Name of profile in which to look for credential_process.
                If not set, uses value from AWS_PROFILE environment variable.
                If that is not set, uses value of "default"

        Returns:
            AwsCredentialsProvider:
        """

        binding = _awscrt.credentials_provider_new_process(profile_to_use)
        return cls(binding)

    @classmethod
    def new_environment(cls):
        """
        Creates a provider that returns credentials sourced from environment variables.

        * AWS_ACCESS_KEY_ID
        * AWS_SECRET_ACCESS_KEY
        * AWS_SESSION_TOKEN

        Returns:
            AwsCredentialsProvider:
        """

        binding = _awscrt.credentials_provider_new_environment()
        return cls(binding)

    @classmethod
    def new_chain(cls, providers):
        """
        Creates a provider that sources credentials from an ordered sequence of providers.

        This provider uses the first set of credentials successfully queried.
        Providers are queried one at a time; a provider is not queried until the
        preceding provider has failed to source credentials.

        Args:
            providers (List[AwsCredentialsProvider]): List of credentials providers.

        Returns:
            AwsCredentialsProvider:
        """

        binding = _awscrt.credentials_provider_new_chain(providers)
        return cls(binding)

    @classmethod
    def new_delegate(cls, get_credentials):
        """
        Creates a provider that sources credentials from a custom
        synchronous callback.

        Args:
            get_credentials: Callable which takes no arguments and returns
                :class:`AwsCredentials`.

        Returns:
            AwsCredentialsProvider:
        """
        # TODO: support async delegates

        assert callable(get_credentials)

        binding = _awscrt.credentials_provider_new_delegate(get_credentials)
        return cls(binding)

    @classmethod
    def new_cognito(
            cls,
            *,
            endpoint: str,
            identity: str,
            tls_ctx: awscrt.io.ClientTlsContext,
            logins: Optional[Sequence[Tuple[str, str]]] = None,
            custom_role_arn: Optional[str] = None,
            client_bootstrap: Optional[ClientBootstrap] = None,
            http_proxy_options: Optional[HttpProxyOptions] = None):
        """
        Creates a provider that sources credentials from the AWS Cognito Identity service.

        Args:
            endpoint (str): Cognito Identity service regional endpoint to source credentials from.

            identity (str): Cognito identity to fetch credentials relative to.

            tls_ctx (ClientTlsContext): Client TLS context to use when querying cognito credentials by HTTP.

            logins (Optional[Sequence[tuple[str, str]]]): Sequence of tuples specifying pairs of identity provider name
                and token values, representing established login contexts for identity authentication purposes.

            custom_role_arn (Optional[str]): ARN of the role to be assumed when multiple roles were received in the
                token from the identity provider.

            client_bootstrap (Optional[ClientBootstrap]): Client bootstrap to use when initiating a socket connection.
                If not set, uses the static default ClientBootstrap instead.

            http_proxy_options (Optional[HttpProxyOptions]): Optional HTTP proxy options.
                If None is provided then an HTTP proxy is not used.

        Returns:
            AwsCredentialsProvider:
        """

        assert isinstance(endpoint, str)
        assert isinstance(identity, str)
        assert isinstance(tls_ctx, ClientTlsContext)
        assert isinstance(custom_role_arn, str) or custom_role_arn is None
        assert isinstance(http_proxy_options, HttpProxyOptions) or http_proxy_options is None

        if client_bootstrap is None:
            client_bootstrap = ClientBootstrap.get_or_create_static_default()
        assert isinstance(client_bootstrap, ClientBootstrap)

        binding = _awscrt.credentials_provider_new_cognito(
            endpoint,
            identity,
            tls_ctx,
            client_bootstrap,
            logins,
            custom_role_arn,
            http_proxy_options)
        return cls(binding)

    @classmethod
    def new_x509(
            cls,
            *,
            endpoint: str,
            thing_name: str,
            role_alias: str,
            tls_ctx: awscrt.io.ClientTlsContext,
            client_bootstrap: Optional[ClientBootstrap] = None,
            http_proxy_options: Optional[HttpProxyOptions] = None):
        """
        Creates a provider that sources credentials from IoT's X509 credentials service.

        Args:
            endpoint (str): X509 service regional endpoint to source credentials from.
                            This is a per-account value that can be determined via the CLI:
                            `aws iot describe-endpoint --endpoint-type iot:CredentialProvider`

            thing_name (str): The name of the IoT thing to use to fetch credentials.

            role_alias (str): The name of the role alias to fetch credentials through.

            tls_ctx (ClientTlsContext): The client TLS context to use when establishing the http connection to IoT's X509 credentials service.

            client_bootstrap (Optional[ClientBootstrap]): Client bootstrap to use when initiating a socket connection.
                If not set, uses the static default ClientBootstrap instead.

            http_proxy_options (Optional[HttpProxyOptions]): Optional HTTP proxy options.
                If None is provided then an HTTP proxy is not used.

        Returns:
            AwsCredentialsProvider:
        """

        assert isinstance(endpoint, str)
        assert isinstance(thing_name, str)
        assert isinstance(role_alias, str)
        assert isinstance(tls_ctx, ClientTlsContext)
        assert isinstance(http_proxy_options, HttpProxyOptions) or http_proxy_options is None
        if client_bootstrap is None:
            client_bootstrap = ClientBootstrap.get_or_create_static_default()
        assert isinstance(client_bootstrap, ClientBootstrap)

        binding = _awscrt.credentials_provider_new_x509(
            endpoint,
            thing_name,
            role_alias,
            tls_ctx,
            client_bootstrap,
            http_proxy_options)
        return cls(binding)

    def get_credentials(self):
        """
        Asynchronously fetch AwsCredentials.

        Returns:
            concurrent.futures.Future: A Future which will contain
            :class:`AwsCredentials` (or an exception) when the operation completes.
            The operation may complete on a different thread.
        """
        future = Future()

        def _on_complete(error_code, binding):
            try:
                if error_code:
                    future.set_exception(awscrt.exceptions.from_code(error_code))
                else:
                    credentials = AwsCredentials._from_binding(binding)
                    future.set_result(credentials)

            except Exception as e:
                future.set_exception(e)

        try:
            _awscrt.credentials_provider_get_credentials(self._binding, _on_complete)
        except Exception as e:
            future.set_exception(e)

        return future


class AwsSigningAlgorithm(IntEnum):
    """AWS signing algorithm enumeration."""

    V4 = 0
    """Signature Version 4"""

    V4_ASYMMETRIC = 1
    """Signature Version 4 - Asymmetric"""

    V4_S3EXPRESS = 2
    """Signature Version 4 - S3 Express"""


class AwsSignatureType(IntEnum):
    """Which sort of signature should be computed from the signable."""

    HTTP_REQUEST_HEADERS = 0
    """
    A signature for a full HTTP request should be computed,
    with header updates applied to the signing result.
    """

    HTTP_REQUEST_QUERY_PARAMS = 1
    """
    A signature for a full HTTP request should be computed,
    with query param updates applied to the signing result.
    """


class AwsSignedBodyValue:
    """
    Values for use with :attr:`AwsSigningConfig.signed_body_value`.

    Some services use special values (e.g. "UNSIGNED-PAYLOAD") when the body
    is not being signed in the usual way.
    """

    EMPTY_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """The SHA-256 of the empty string."""

    UNSIGNED_PAYLOAD = 'UNSIGNED-PAYLOAD'
    """Unsigned payload option (not accepted by all services)"""

    STREAMING_AWS4_HMAC_SHA256_PAYLOAD = 'STREAMING-AWS4-HMAC-SHA256-PAYLOAD'
    """Each payload chunk will be signed (not accepted by all services)"""

    STREAMING_AWS4_HMAC_SHA256_EVENTS = 'STREAMING-AWS4-HMAC-SHA256-EVENTS'
    """Each event will be signed (not accepted by all services)"""


class AwsSignedBodyHeaderType(IntEnum):
    """
    Controls if signing adds a header containing the canonical request's signed body value.

    See :attr:`AwsSigningConfig.signed_body_value`.
    """

    NONE = 0
    """Do not add a header."""

    X_AMZ_CONTENT_SHA_256 = 1
    """Add the "x-amz-content-sha256" header with the canonical request's signed body value"""


class AwsSigningConfig(NativeResource):
    """
    Configuration for use in AWS-related signing.

    AwsSigningConfig is immutable.

    It is good practice to use a new config for each signature, or the date might get too old.

    Args:
        algorithm (AwsSigningAlgorithm): Which signing algorithm to use.

        signature_type (AwsSignatureType): Which sort of signature should be
            computed from the signable.

        credentials_provider (AwsCredentialsProvider): Credentials provider
            to fetch signing credentials with. If the algorithm is
            :attr:`AwsSigningAlgorithm.V4_ASYMMETRIC`, ECC-based credentials will be derived from the
            fetched credentials.

        region (str): If the algorithm is :attr:`AwsSigningAlgorithm.V4`, the region to sign against.
            If the algorithm is :attr:`AwsSigningAlgorithm.V4_ASYMMETRIC`, the value of the
            "X-amzn-region-set" header (added in signing).

        service (str): Name of service to sign a request for.

        date (Optional[datetime.datetime]): Date and time to use during the
            signing process. If None is provided then
            `datetime.datetime.now(datetime.timezone.utc)` is used.
            Naive dates (lacking timezone info) are assumed to be in local time.

        should_sign_header (Optional[Callable[[str], bool]]):
            Optional function to control which headers are
            a part of the canonical request.

            Skipping auth-required headers will result in an unusable signature.
            Headers injected by the signing process are not skippable.
            This function does not override the internal check function
            (x-amzn-trace-id, user-agent), but rather supplements it.
            In particular, a header will get signed if and only if it returns
            true to both the internal check (skips x-amzn-trace-id, user-agent)
            and this function (if defined).

        use_double_uri_encode (bool): Whether to double-encode the resource path
            when constructing the canonical request (assuming the path is already
            encoded). Default is True. All services except S3 use double encoding.

        should_normalize_uri_path (bool): Whether the resource paths are
            normalized when building the canonical request. Default is True.

        signed_body_value (Optional[str]): If set, this value is used as the
            canonical request's body value. Typically, this is the SHA-256
            of the payload, written as lowercase hex. If this has been
            precalculated, it can be set here. Special values used by certain
            services can also be set (see :class:`AwsSignedBodyValue`). If `None`
            is passed (the default), the typical value will be calculated from
            the payload during signing.

        signed_body_header_type (AwsSignedBodyHeaderType): Controls if signing
            adds a header containing the canonical request's signed body value.
            Default is to not add a header.

        expiration_in_seconds (Optional[int]): If set, and signature_type is
            :attr:`AwsSignatureType.HTTP_REQUEST_QUERY_PARAMS`, then signing will add "X-Amz-Expires"
            to the query string, equal to the value specified here.

        omit_session_token (bool): If set True, the "X-Amz-Security-Token"
            query param is omitted from the canonical request.
            The default False should be used for most services.
    """
    __slots__ = ('_priv_should_sign_cb')

    _attributes = (
        'algorithm',
        'signature_type',
        'credentials_provider',
        'region',
        'service',
        'date',
        'should_sign_header',
        'use_double_uri_encode',
        'should_normalize_uri_path',
        'signed_body_value',
        'signed_body_header_type',
        'expiration_in_seconds',
        'omit_session_token',
    )

    def __init__(self,
                 algorithm=AwsSigningAlgorithm.V4,
                 signature_type=AwsSignatureType.HTTP_REQUEST_HEADERS,
                 credentials_provider=None,
                 region="",
                 service="",
                 date=None,
                 should_sign_header=None,
                 use_double_uri_encode=True,
                 should_normalize_uri_path=True,
                 signed_body_value=None,
                 signed_body_header_type=AwsSignedBodyHeaderType.NONE,
                 expiration_in_seconds=None,
                 omit_session_token=False,
                 ):

        assert isinstance(algorithm, AwsSigningAlgorithm)
        assert isinstance(signature_type, AwsSignatureType)
        assert isinstance(credentials_provider, AwsCredentialsProvider) or credentials_provider is None
        assert isinstance(region, str)
        assert isinstance(service, str)
        assert callable(should_sign_header) or should_sign_header is None
        assert signed_body_value is None or (isinstance(signed_body_value, str) and len(signed_body_value) > 0)
        assert isinstance(signed_body_header_type, AwsSignedBodyHeaderType)
        assert expiration_in_seconds is None or expiration_in_seconds > 0

        super().__init__()

        if date is None:
            date = datetime.datetime.now(datetime.timezone.utc)

        timestamp = date.timestamp()

        self._priv_should_sign_cb = should_sign_header

        if should_sign_header is not None:
            def should_sign_header_wrapper(name):
                return should_sign_header(name=name)
        else:
            should_sign_header_wrapper = None

        if expiration_in_seconds is None:
            # C layer uses 0 to indicate None
            expiration_in_seconds = 0

        self._binding = _awscrt.signing_config_new(
            algorithm,
            signature_type,
            credentials_provider,
            region,
            service,
            date,
            timestamp,
            should_sign_header_wrapper,
            use_double_uri_encode,
            should_normalize_uri_path,
            signed_body_value,
            signed_body_header_type,
            expiration_in_seconds,
            omit_session_token)

    def replace(self, **kwargs):
        """
        Return an AwsSigningConfig with the same attributes, except for those
        attributes given new values by whichever keyword arguments are specified.
        """
        args = {x: kwargs.get(x, getattr(self, x)) for x in AwsSigningConfig._attributes}
        return AwsSigningConfig(**args)

    @property
    def algorithm(self):
        """AwsSigningAlgorithm: Which signing algorithm to use"""
        return AwsSigningAlgorithm(_awscrt.signing_config_get_algorithm(self._binding))

    @property
    def signature_type(self):
        """AwsSignatureType: Which sort of signature should be computed from the signable."""
        return AwsSignatureType(_awscrt.signing_config_get_signature_type(self._binding))

    @property
    def credentials_provider(self):
        """
        AwsCredentialsProvider: Credentials provider to fetch signing credentials with.
        If the algorithm is :attr:`AwsSigningAlgorithm.V4_ASYMMETRIC`, ECC-based credentials will be derived
        from the fetched credentials.
        """
        return _awscrt.signing_config_get_credentials_provider(self._binding)

    @property
    def region(self):
        """
        str: If signing algorithm is :attr:`AwsSigningAlgorithm.V4`, the region to sign against.
        If the algorithm is :attr:`AwsSigningAlgorithm.V4_ASYMMETRIC`, the value of the
        "X-amzn-region-set header" (added in signing).
        """
        return _awscrt.signing_config_get_region(self._binding)

    @property
    def service(self):
        """str: Name of service to sign a request for"""
        return _awscrt.signing_config_get_service(self._binding)

    @property
    def date(self):
        """
        datetime.datetime: Date and time to use during the signing process.

        If None is provided, then `datetime.datetime.now(datetime.timezone.utc)`
        at time of object construction is used.

        It is good practice to use a new config for each signature, or the date might get too old.
        """
        return _awscrt.signing_config_get_date(self._binding)

    @property
    def should_sign_header(self):
        """
        Optional[Callable[[str], bool]]: Optional function to control which
        headers are a part of the canonical request.

        Skipping auth-required headers will result in an unusable signature.
        Headers injected by the signing process are not skippable.
        This function does not override the internal check function
        (x-amzn-trace-id, user-agent), but rather supplements it. In particular,
        a header will get signed if and only if it returns true to both
        the internal check (skips x-amzn-trace-id, user-agent) and this function (if defined).
        """
        return self._priv_should_sign_cb

    @property
    def use_double_uri_encode(self):
        """
        bool: Whether to double-encode the resource path when constructing
        the canonical request (assuming the path is already encoded).

        By default, all services except S3 use double encoding.
        """
        return _awscrt.signing_config_get_use_double_uri_encode(self._binding)

    @property
    def should_normalize_uri_path(self):
        """
        bool: Whether the resource paths are normalized when building the
        canonical request.
        """
        return _awscrt.signing_config_get_should_normalize_uri_path(self._binding)

    @property
    def signed_body_value(self):
        """
        Optional[str]: What to use as the canonical request's body value.
        If `None` is set (the default), a value will be calculated from
        the payload during signing. Typically, this is the SHA-256 of the
        payload, written as lowercase hex. If this has been precalculated,
        it can be set here. Special values used by certain services can also
        be set (see :class:`AwsSignedBodyValue`).
        """
        return _awscrt.signing_config_get_signed_body_value(self._binding)

    @property
    def signed_body_header_type(self):
        """
        AwsSignedBodyHeaderType: Controls if signing adds a header containing
        the canonical request's signed body value.
        """
        return AwsSignedBodyHeaderType(_awscrt.signing_config_get_signed_body_header_type(self._binding))

    @property
    def expiration_in_seconds(self):
        """
        Optional[int]: If set, and signature_type is :attr:`AwsSignatureType.HTTP_REQUEST_QUERY_PARAMS`,
        then signing will add "X-Amz-Expires" to the query string, equal to the
        value specified here. Otherwise, this is None has no effect.
        """
        expiration = _awscrt.signing_config_get_expiration_in_seconds(self._binding)
        # C layer uses 0 to indicate None
        return None if expiration == 0 else expiration

    @property
    def omit_session_token(self):
        """
        bool: Whether the "X-Amz-Security-Token" query param is omitted
        from the canonical request. This should be False for most services.
        """
        return _awscrt.signing_config_get_omit_session_token(self._binding)


def aws_sign_request(http_request, signing_config):
    """
    Perform AWS HTTP request signing.

    The :class:`awscrt.http.HttpRequest` is transformed asynchronously,
    according to the :class:`AwsSigningConfig`.

    When signing:

    1.  It is good practice to use a new config for each signature,
        or the date might get too old.

    2.  Do not add the following headers to requests before signing, they may be added by the signer:
        x-amz-content-sha256,
        X-Amz-Date,
        Authorization

    3.  Do not add the following query params to requests before signing, they may be added by the signer:
        X-Amz-Signature,
        X-Amz-Date,
        X-Amz-Credential,
        X-Amz-Algorithm,
        X-Amz-SignedHeaders

    Args:
        http_request (awscrt.http.HttpRequest): The HTTP request to sign.
        signing_config (AwsSigningConfig): Configuration for signing.

    Returns:
        concurrent.futures.Future: A Future whose result will be the signed
        :class:`awscrt.http.HttpRequest`. The future will contain an exception
        if the signing process fails.
    """

    assert isinstance(http_request, HttpRequest)
    assert isinstance(signing_config, AwsSigningConfig)

    future = Future()

    def _on_complete(error_code):
        try:
            if error_code:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                future.set_result(http_request)
        except Exception as e:
            future.set_exception(e)

    _awscrt.sign_request_aws(http_request, signing_config, _on_complete)
    return future
