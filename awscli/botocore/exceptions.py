# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from botocore.vendored.requests.packages import urllib3


def _exception_from_packed_args(exception_cls, args=None, kwargs=None):
    # This is helpful for reducing Exceptions that only accept kwargs as
    # only positional arguments can be provided for __reduce__
    # Ideally, this would also be a class method on the BotoCoreError
    # but instance methods cannot be pickled.
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    return exception_cls(*args, **kwargs)


class BotoCoreError(Exception):
    """
    The base exception class for BotoCore exceptions.

    :ivar msg: The descriptive message associated with the error.
    """

    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs

    def __reduce__(self):
        return _exception_from_packed_args, (self.__class__, None, self.kwargs)


class DataNotFoundError(BotoCoreError):
    """
    The data associated with a particular path could not be loaded.

    :ivar data_path: The data path that the user attempted to load.
    """

    fmt = 'Unable to load data for: {data_path}'


class UnknownServiceError(DataNotFoundError):
    """Raised when trying to load data for an unknown service.

    :ivar service_name: The name of the unknown service.

    """

    fmt = (
        "Unknown service: '{service_name}'. Valid service names are: "
        "{known_service_names}"
    )


class UnknownRegionError(BotoCoreError):
    """Raised when trying to load data for an unknown region.
    :ivar region_name: The name of the unknown region.
    """

    fmt = "Unknown region: '{region_name}'. {error_msg}"


class ApiVersionNotFoundError(BotoCoreError):
    """
    The data associated with either the API version or a compatible one
    could not be loaded.

    :ivar data_path: The data path that the user attempted to load.
    :ivar api_version: The API version that the user attempted to load.
    """

    fmt = 'Unable to load data {data_path} for: {api_version}'


class HTTPClientError(BotoCoreError):
    fmt = 'An HTTP Client raised an unhandled exception: {error}'

    def __init__(self, request=None, response=None, **kwargs):
        self.request = request
        self.response = response
        super().__init__(**kwargs)

    def __reduce__(self):
        return _exception_from_packed_args, (
            self.__class__,
            (self.request, self.response),
            self.kwargs,
        )


class ConnectionError(BotoCoreError):
    fmt = 'An HTTP Client failed to establish a connection: {error}'


class InvalidIMDSEndpointError(BotoCoreError):
    fmt = 'Invalid endpoint EC2 Instance Metadata endpoint: {endpoint}'


class InvalidIMDSEndpointModeError(BotoCoreError):
    fmt = (
        'Invalid EC2 Instance Metadata endpoint mode: {mode}'
        ' Valid endpoint modes (case-insensitive): {valid_modes}.'
    )


class EndpointConnectionError(ConnectionError):
    fmt = 'Could not connect to the endpoint URL: "{endpoint_url}"'


class SSLError(ConnectionError):
    fmt = 'SSL validation failed for {endpoint_url} {error}'


class ConnectionClosedError(HTTPClientError):
    fmt = (
        'Connection was closed before we received a valid response '
        'from endpoint URL: "{endpoint_url}".'
    )


class ReadTimeoutError(HTTPClientError, urllib3.exceptions.ReadTimeoutError):
    fmt = 'Read timeout on endpoint URL: "{endpoint_url}"'


class ConnectTimeoutError(ConnectionError):
    fmt = 'Connect timeout on endpoint URL: "{endpoint_url}"'


class ProxyConnectionError(ConnectionError):
    fmt = 'Failed to connect to proxy URL: "{proxy_url}"'


class NoCredentialsError(BotoCoreError):
    """
    No credentials could be found.
    """

    fmt = 'Unable to locate credentials'


class NoAuthTokenError(BotoCoreError):
    """
    No authorization token could be found.
    """

    fmt = 'Unable to locate authorization token'


class TokenRetrievalError(BotoCoreError):
    """
    Error attempting to retrieve a token from a remote source.

    :ivar provider: The name of the token provider.
    :ivar error_msg: The msg explaining why the token could not be retrieved.

    """

    fmt = 'Error when retrieving token from {provider}: {error_msg}'


class PartialCredentialsError(BotoCoreError):
    """
    Only partial credentials were found.

    :ivar cred_var: The missing credential variable name.

    """

    fmt = 'Partial credentials found in {provider}, missing: {cred_var}'


class CredentialRetrievalError(BotoCoreError):
    """
    Error attempting to retrieve credentials from a remote source.

    :ivar provider: The name of the credential provider.
    :ivar error_msg: The msg explaining why credentials could not be
        retrieved.

    """

    fmt = 'Error when retrieving credentials from {provider}: {error_msg}'


class UnknownSignatureVersionError(BotoCoreError):
    """
    Requested Signature Version is not known.

    :ivar signature_version: The name of the requested signature version.
    """

    fmt = 'Unknown Signature Version: {signature_version}.'


class ServiceNotInRegionError(BotoCoreError):
    """
    The service is not available in requested region.

    :ivar service_name: The name of the service.
    :ivar region_name: The name of the region.
    """

    fmt = 'Service {service_name} not available in region {region_name}'


class BaseEndpointResolverError(BotoCoreError):
    """Base error for endpoint resolving errors.

    Should never be raised directly, but clients can catch
    this exception if they want to generically handle any errors
    during the endpoint resolution process.

    """


class NoRegionError(BaseEndpointResolverError):
    """No region was specified."""

    fmt = 'You must specify a region.'


class EndpointVariantError(BaseEndpointResolverError):
    """
    Could not construct modeled endpoint variant.

    :ivar error_msg: The message explaining why the modeled endpoint variant
        is unable to be constructed.

    """

    fmt = (
        'Unable to construct a modeled endpoint with the following '
        'variant(s) {tags}: '
    )


class UnknownEndpointError(BaseEndpointResolverError, ValueError):
    """
    Could not construct an endpoint.

    :ivar service_name: The name of the service.
    :ivar region_name: The name of the region.
    """

    fmt = (
        'Unable to construct an endpoint for '
        '{service_name} in region {region_name}'
    )


class UnknownFIPSEndpointError(BaseEndpointResolverError):
    """
    Could not construct a FIPS endpoint.

    :ivar service_name: The name of the service.
    :ivar region_name: The name of the region.
    """

    fmt = (
        'The provided FIPS pseudo-region "{region_name}" is not known for '
        'the service "{service_name}". A FIPS compliant endpoint cannot be '
        'constructed.'
    )


class ProfileNotFound(BotoCoreError):
    """
    The specified configuration profile was not found in the
    configuration file.

    :ivar profile: The name of the profile the user attempted to load.
    """

    fmt = 'The config profile ({profile}) could not be found'


class ConfigParseError(BotoCoreError):
    """
    The configuration file could not be parsed.

    :ivar path: The path to the configuration file.
    """

    fmt = 'Unable to parse config file: {path}'


class ConfigNotFound(BotoCoreError):
    """
    The specified configuration file could not be found.

    :ivar path: The path to the configuration file.
    """

    fmt = 'The specified config file ({path}) could not be found.'


class MissingParametersError(BotoCoreError):
    """
    One or more required parameters were not supplied.

    :ivar object: The object that has missing parameters.
        This can be an operation or a parameter (in the
        case of inner params).  The str() of this object
        will be used so it doesn't need to implement anything
        other than str().
    :ivar missing: The names of the missing parameters.
    """

    fmt = (
        'The following required parameters are missing for '
        '{object_name}: {missing}'
    )


class ValidationError(BotoCoreError):
    """
    An exception occurred validating parameters.

    Subclasses must accept a ``value`` and ``param``
    argument in their ``__init__``.

    :ivar value: The value that was being validated.
    :ivar param: The parameter that failed validation.
    :ivar type_name: The name of the underlying type.
    """

    fmt = "Invalid value ('{value}') for param {param} " "of type {type_name} "


class ParamValidationError(BotoCoreError):
    fmt = 'Parameter validation failed:\n{report}'


# These exceptions subclass from ValidationError so that code
# can just 'except ValidationError' to catch any possibly validation
# error.
class UnknownKeyError(ValidationError):
    """
    Unknown key in a struct parameter.

    :ivar value: The value that was being checked.
    :ivar param: The name of the parameter.
    :ivar choices: The valid choices the value can be.
    """

    fmt = (
        "Unknown key '{value}' for param '{param}'.  Must be one "
        "of: {choices}"
    )


class RangeError(ValidationError):
    """
    A parameter value was out of the valid range.

    :ivar value: The value that was being checked.
    :ivar param: The parameter that failed validation.
    :ivar min_value: The specified minimum value.
    :ivar max_value: The specified maximum value.
    """

    fmt = (
        'Value out of range for param {param}: '
        '{min_value} <= {value} <= {max_value}'
    )


class UnknownParameterError(ValidationError):
    """
    Unknown top level parameter.

    :ivar name: The name of the unknown parameter.
    :ivar operation: The name of the operation.
    :ivar choices: The valid choices the parameter name can be.
    """

    fmt = (
        "Unknown parameter '{name}' for operation {operation}.  Must be one "
        "of: {choices}"
    )


class InvalidRegionError(ValidationError, ValueError):
    """
    Invalid region_name provided to client or resource.

    :ivar region_name: region_name that was being validated.
    """

    fmt = "Provided region_name '{region_name}' doesn't match a supported format."


class AliasConflictParameterError(ValidationError):
    """
    Error when an alias is provided for a parameter as well as the original.

    :ivar original: The name of the original parameter.
    :ivar alias: The name of the alias
    :ivar operation: The name of the operation.
    """

    fmt = (
        "Parameter '{original}' and its alias '{alias}' were provided "
        "for operation {operation}.  Only one of them may be used."
    )


class UnknownServiceStyle(BotoCoreError):
    """
    Unknown style of service invocation.

    :ivar service_style: The style requested.
    """

    fmt = 'The service style ({service_style}) is not understood.'


class PaginationError(BotoCoreError):
    fmt = 'Error during pagination: {message}'


class OperationNotPageableError(BotoCoreError):
    fmt = 'Operation cannot be paginated: {operation_name}'


class ChecksumError(BotoCoreError):
    """The expected checksum did not match the calculated checksum."""

    fmt = (
        'Checksum {checksum_type} failed, expected checksum '
        '{expected_checksum} did not match calculated checksum '
        '{actual_checksum}.'
    )


class UnseekableStreamError(BotoCoreError):
    """Need to seek a stream, but stream does not support seeking."""

    fmt = (
        'Need to rewind the stream {stream_object}, but stream '
        'is not seekable.'
    )


class WaiterError(BotoCoreError):
    """Waiter failed to reach desired state."""

    fmt = 'Waiter {name} failed: {reason}'

    def __init__(self, name, reason, last_response):
        super().__init__(name=name, reason=reason)
        self.last_response = last_response


class IncompleteReadError(BotoCoreError):
    """HTTP response did not return expected number of bytes."""

    fmt = (
        '{actual_bytes} read, but total bytes ' 'expected is {expected_bytes}.'
    )


class InvalidExpressionError(BotoCoreError):
    """Expression is either invalid or too complex."""

    fmt = 'Invalid expression {expression}: Only dotted lookups are supported.'


class UnknownCredentialError(BotoCoreError):
    """Tried to insert before/after an unregistered credential type."""

    fmt = 'Credential named {name} not found.'


class WaiterConfigError(BotoCoreError):
    """Error when processing waiter configuration."""

    fmt = 'Error processing waiter config: {error_msg}'


class UnknownClientMethodError(BotoCoreError):
    """Error when trying to access a method on a client that does not exist."""

    fmt = 'Client does not have method: {method_name}'


class UnsupportedSignatureVersionError(BotoCoreError):
    """Error when trying to use an unsupported Signature Version."""

    fmt = 'Signature version(s) are not supported: {signature_version}'


class ClientError(Exception):
    MSG_TEMPLATE = (
        'An error occurred ({error_code}) when calling the {operation_name} '
        'operation{retry_info}: {error_message}'
    )

    def __init__(self, error_response, operation_name):
        retry_info = self._get_retry_info(error_response)
        error = error_response.get('Error', {})
        msg = self.MSG_TEMPLATE.format(
            error_code=error.get('Code', 'Unknown'),
            error_message=error.get('Message', 'Unknown'),
            operation_name=operation_name,
            retry_info=retry_info,
        )
        super().__init__(msg)
        self.response = error_response
        self.operation_name = operation_name
        self.modeled_fields = None

    def _get_retry_info(self, response):
        retry_info = ''
        if 'ResponseMetadata' in response:
            metadata = response['ResponseMetadata']
            if metadata.get('MaxAttemptsReached', False):
                if 'RetryAttempts' in metadata:
                    retry_info = ' (reached max retries: {})'.format(
                        metadata['RetryAttempts']
                    )
        return retry_info

    def __reduce__(self):
        # Subclasses of ClientError's are dynamically generated and
        # cannot be pickled unless they are attributes of a
        # module. So at the very least return a ClientError back.
        return ClientError, (self.response, self.operation_name)


class EventStreamError(ClientError):
    pass


class UnsupportedTLSVersionWarning(Warning):
    """Warn when an openssl version that uses TLS 1.2 is required"""

    pass


class ImminentRemovalWarning(Warning):
    pass


class InvalidDNSNameError(BotoCoreError):
    """Error when virtual host path is forced on a non-DNS compatible bucket"""

    fmt = (
        'Bucket named {bucket_name} is not DNS compatible. Virtual '
        'hosted-style addressing cannot be used. The addressing style '
        'can be configured by removing the addressing_style value '
        'or setting that value to \'path\' or \'auto\' in the AWS Config '
        'file or in the botocore.client.Config object.'
    )


class InvalidS3AddressingStyleError(BotoCoreError):
    """Error when an invalid path style is specified"""

    fmt = (
        'S3 addressing style {s3_addressing_style} is invalid. Valid options '
        'are: \'auto\', \'virtual\', and \'path\''
    )


class UnsupportedS3ArnError(BotoCoreError):
    """Error when S3 ARN provided to Bucket parameter is not supported"""

    fmt = (
        'S3 ARN {arn} provided to "Bucket" parameter is invalid. Only '
        'ARNs for S3 access-points are supported.'
    )


class UnsupportedS3ControlArnError(BotoCoreError):
    """Error when S3 ARN provided to S3 control parameter is not supported"""

    fmt = 'S3 ARN "{arn}" provided is invalid for this operation. {msg}'


class InvalidHostLabelError(BotoCoreError):
    """Error when an invalid host label would be bound to an endpoint"""

    fmt = (
        'Invalid host label to be bound to the hostname of the endpoint: '
        '"{label}".'
    )


class UnsupportedOutpostResourceError(BotoCoreError):
    """Error when S3 Outpost ARN provided to Bucket parameter is incomplete"""

    fmt = (
        'S3 Outpost ARN resource "{resource_name}" provided to "Bucket" '
        'parameter is invalid. Only ARNs for S3 Outpost arns with an '
        'access-point sub-resource are supported.'
    )


class UnsupportedS3ConfigurationError(BotoCoreError):
    """Error when an unsupported configuration is used with access-points"""

    fmt = 'Unsupported configuration when using S3: {msg}'


class UnsupportedS3AccesspointConfigurationError(BotoCoreError):
    """Error when an unsupported configuration is used with access-points"""

    fmt = 'Unsupported configuration when using S3 access-points: {msg}'


class InvalidEndpointDiscoveryConfigurationError(BotoCoreError):
    """Error when invalid value supplied for endpoint_discovery_enabled"""

    fmt = (
        'Unsupported configuration value for endpoint_discovery_enabled. '
        'Expected one of ("true", "false", "auto") but got {config_value}.'
    )


class UnsupportedS3ControlConfigurationError(BotoCoreError):
    """Error when an unsupported configuration is used with S3 Control"""

    fmt = 'Unsupported configuration when using S3 Control: {msg}'


class InvalidRetryConfigurationError(BotoCoreError):
    """Error when invalid retry configuration is specified"""

    fmt = (
        'Cannot provide retry configuration for "{retry_config_option}". '
        'Valid retry configuration options are: \'max_attempts\''
    )


class InvalidMaxRetryAttemptsError(InvalidRetryConfigurationError):
    """Error when invalid retry configuration is specified"""

    fmt = (
        'Value provided to "max_attempts": {provided_max_attempts} must '
        'be an integer greater than or equal to one.'
    )


class InvalidRetryModeError(InvalidRetryConfigurationError):
    """Error when invalid retry mode configuration is specified"""

    fmt = (
        'Invalid value provided to "mode": "{provided_retry_mode}" must '
        'be one of: "standard" or "adaptive"'
    )


class StubResponseError(BotoCoreError):
    fmt = (
        'Error getting response stub for operation {operation_name}: {reason}'
    )


class StubAssertionError(StubResponseError, AssertionError):
    pass


class UnStubbedResponseError(StubResponseError):
    pass


class InvalidConfigError(BotoCoreError):
    fmt = '{error_msg}'


class InfiniteLoopConfigError(InvalidConfigError):
    fmt = (
        'Infinite loop in credential configuration detected. Attempting to '
        'load from profile {source_profile} which has already been visited. '
        'Visited profiles: {visited_profiles}'
    )


class RefreshWithMFAUnsupportedError(BotoCoreError):
    fmt = 'Cannot refresh credentials: MFA token required.'


class MD5UnavailableError(BotoCoreError):
    fmt = "This system does not support MD5 generation."


class MetadataRetrievalError(BotoCoreError):
    fmt = "Error retrieving metadata: {error_msg}"


class UndefinedModelAttributeError(Exception):
    pass


class MissingServiceIdError(UndefinedModelAttributeError):
    fmt = (
        "The model being used for the service {service_name} is missing the "
        "serviceId metadata property, which is required."
    )

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs


class SSOError(BotoCoreError):
    fmt = (
        "An unspecified error happened when resolving AWS credentials or an "
        "access token from SSO."
    )


class PendingAuthorizationExpiredError(SSOError):
    fmt = (
        "The pending authorization to retrieve an SSO token has expired. The "
        "login flow to retrieve an SSO token must be restarted."
    )


class SSOTokenLoadError(SSOError):
    fmt = "Error loading SSO Token: {error_msg}"


class AuthorizationCodeLoadError(SSOError):
    fmt = "Error loading authorization code: {error_msg}"


class UnauthorizedSSOTokenError(SSOError):
    fmt = (
        "The SSO session associated with this profile has expired or is "
        "otherwise invalid. To refresh this SSO session run aws sso login "
        "with the corresponding profile."
    )


class AuthCodeFetcherError(SSOError):
    fmt = (
        "Unable to initialize the OAuth 2.0 authorization callback handler: "
        "{error_msg} \n You may use --use-device-code to fall back to the "
        "device code flow which does not require the callback handler."
    )


class LoginError(BotoCoreError):
    fmt = (
        "An unspecified error happened when resolving AWS credentials or "
        "refreshing a login session profile."
    )


class LoginRefreshTokenExpired(LoginError):
    fmt = "Your session has expired. Please reauthenticate using 'aws login'."


class LoginRefreshPasswordChanged(LoginError):
    fmt = (
        "Unable to refresh login credentials because of a change in your "
        "password. Please reauthenticate with your new password using 'aws login'."
    )


class LoginInsufficientPermissions(LoginError):
    fmt = (
        "Unable to create or refresh login credentials due to insufficient "
        "permissions. You may be missing permission for the 'signin:CreateOAuth2Token' action."
    )


class LoginTokenLoadError(LoginError):
    fmt = "Error loading login session token: {error_msg}"


class LoginAuthorizationCodeError(LoginError):
    fmt = "Error loading or redeeming a login authorization code: {error_msg} "


class CredentialDaemonError(BotoCoreError):
    """An error from the credential daemon.

    :ivar code: The credential daemon's error code, such as
        ``REAUTH_REQUIRED``, if any.
    :ivar data: Any other details the credential daemon sent with the error.
    :ivar daemon_message: The credential daemon's own message, control
        characters removed, if the error came from a credential daemon error
        reply.

    Raise it with ``error_msg``, the whole message, or, for a subclass whose
    ``fmt`` names fields, with those fields, such as ``credential_name``.
    ``error_msg`` wins over the subclass's ``fmt``. A message built from
    fields ends with what the credential daemon said, if anything
    (``{daemon_said}``).
    """

    fmt = '{error_msg}'

    def __init__(self, **kwargs):
        kwargs.setdefault('code', None)
        kwargs.setdefault('data', {})
        kwargs.setdefault('daemon_message', None)
        if 'error_msg' in kwargs:
            self.fmt = CredentialDaemonError.fmt
        super().__init__(**kwargs, daemon_said=self._daemon_said(kwargs))
        # The fields as passed, so the error pickles as raised.
        self.kwargs = kwargs
        self.code = kwargs['code']
        self.data = kwargs['data']
        self.daemon_message = kwargs['daemon_message']

    @staticmethod
    def _daemon_said(kwargs):
        # The SEP: an error from a daemon error reply shows the daemon's
        # message too, so the customer sees what the credential daemon said.
        if not kwargs['daemon_message']:
            return ''
        return f" The credential daemon said: {kwargs['daemon_message']}"


class CredentialDaemonConnectionError(CredentialDaemonError):
    """The CLI couldn't reach the credential daemon, or lost its connection to
    it."""


class CredentialDaemonUnsupportedPlatformError(
    CredentialDaemonConnectionError
):
    """The credential daemon doesn't run on this platform, such as Windows,
    so the CLI can't connect to it."""


class CredentialDaemonNotRunningError(CredentialDaemonConnectionError):
    """Nothing is listening on the credential daemon's socket.

    :ivar hint: What to tell the customer to do, if not how to start the
        credential daemon: the empty string when the message already says
        it, or None for the usual hint (``credential_daemon.start_hint``).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('hint', None)
        super().__init__(**kwargs)
        self.hint = kwargs['hint']


class CredentialDaemonTimeoutError(CredentialDaemonNotRunningError):
    """The credential daemon didn't accept the connection or answer before the
    timeout.

    The SEP counts a timeout as NOT_RUNNING.
    """


class CredentialDaemonUntrustedSocketError(CredentialDaemonConnectionError):
    """The CLI didn't trust what's on the credential daemon's socket, so it
    sent nothing (``UNTRUSTED_SOCKET``).

    Another user could own the socket, a folder above it, or the process
    serving it, or on macOS the process serving it isn't the signed
    credential daemon (or its signature couldn't be checked). Commands treat
    it as the credential daemon being unavailable, but never suggest
    starting it.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('code', 'UNTRUSTED_SOCKET')
        super().__init__(**kwargs)


class CredentialDaemonProtocolError(CredentialDaemonError):
    """The credential daemon sent something this version of the CLI doesn't
    understand.

    For a credential/get reply the CLI can't use, raise it with
    ``credential_name`` and ``problem``, which never holds a value from the
    reply.
    """

    fmt = (
        "The credential daemon sent a reply the CLI can't use for "
        "'{credential_name}': {problem}."
    )


class CredentialDaemonUnsupportedMaterialError(CredentialDaemonError):
    """The credential daemon sent a type of credential this version of the
    CLI can't use, such as a bearer token (the SEP's UNSUPPORTED_MATERIAL).

    ``material_type`` is shown as passed, so it has its control characters
    removed first.
    """

    fmt = (
        "This version of the AWS CLI doesn't support material type "
        "{material_type} from the credential daemon for '{credential_name}'. "
        "Update the AWS CLI."
    )


class CredentialDaemonReauthRequiredError(CredentialDaemonError):
    """The credential was signed out, or its session ended.

    ``advice`` says what ended and how to sign in again.
    """

    fmt = '{advice}{daemon_said}'


class CredentialDaemonCredentialNotFoundError(CredentialDaemonError):
    """The credential daemon has no credential with the name the CLI asked
    for.

    ``advice`` says how to create it again.
    """

    fmt = (
        "The credential daemon has no credential named '{credential_name}'. "
        "{advice}{daemon_said}"
    )


class CredentialDaemonProviderUnavailableError(CredentialDaemonError):
    """The credential daemon couldn't get credentials from AWS: it couldn't
    reach AWS, or AWS refused the request.

    The credential daemon uses this code for both, so the message doesn't
    say which. It runs as a service and calls AWS with its own settings,
    never the caller's, so the message says where proxy settings go.
    """

    fmt = (
        "The credential daemon couldn't get credentials from AWS."
        "{daemon_said} If you use a proxy, set HTTPS_PROXY (and "
        "AWS_CA_BUNDLE, if the proxy inspects TLS) in the credential "
        "daemon's service settings. Settings in your shell don't reach it."
    )

    @staticmethod
    def _daemon_said(kwargs):
        # The daemon's message ends its sentence here, as end_sentence in
        # botocore.credential_daemon.text does; that package imports this
        # module, so it can't be imported here.
        said = CredentialDaemonError._daemon_said(kwargs).rstrip()
        if said and not said.endswith(('.', '!', '?')):
            said += '.'
        return said


class CredentialDaemonCredentialUnusableError(CredentialDaemonError):
    """The credential daemon can't use the credential: its settings changed
    since they were approved, the caller's credential daemon configuration
    doesn't validate, or its stored data can't be checked
    (``CONFIG_DRIFTED``, ``CONFIG_INVALID``, ``INTEGRITY_UNVERIFIABLE`` or
    ``CUSTODY_BROKEN``).

    ``profile`` is shown as passed, so it has its control characters removed
    first.
    """

    fmt = (
        "The credential daemon can't use credential '{credential_name}' for "
        "profile '{profile}': its settings changed, or its stored data can't "
        "be checked.{daemon_said}"
    )


class CredentialDaemonIdentityMismatchError(CredentialDaemonError):
    """A sign-in to a credential the credential daemon holds signed in as
    another account or role than the credential records, or the credential
    has no record of one, so nothing was saved (``IDENTITY_MISMATCH``).
    Changing who a credential signs in as replaces it, which needs
    approval."""


class CredentialDaemonRequestRejectedError(CredentialDaemonError):
    """The credential daemon refused the request with an error the CLI has no
    name for (the SEP's REQUEST_REJECTED). ``code`` is the credential daemon's
    own code."""


class CredentialDaemonApprovalRequiredError(CredentialDaemonError):
    """The credential daemon needs approval first, for example to replace a
    credential another tool created."""


class CapacityNotAvailableError(BotoCoreError):
    fmt = 'Insufficient request capacity available.'


class InvalidProxiesConfigError(BotoCoreError):
    fmt = 'Invalid configuration value(s) provided for proxies_config.'


class AwsChunkedWrapperError(BotoCoreError):
    fmt = '{error_msg}'


class FlexibleChecksumError(BotoCoreError):
    fmt = '{error_msg}'


class InvalidEndpointConfigurationError(BotoCoreError):
    fmt = 'Invalid endpoint configuration: {msg}'


class EndpointProviderError(BotoCoreError):
    """Base error for the EndpointProvider class"""

    fmt = '{msg}'


class EndpointResolutionError(EndpointProviderError):
    """Error when input parameters resolve to an error rule"""

    fmt = '{msg}'


class UnknownEndpointResolutionBuiltInName(EndpointProviderError):
    fmt = 'Unknown builtin variable name: {name}'


class InvalidChecksumConfigError(BotoCoreError):
    """Error when an invalid checksum config value is supplied."""

    fmt = (
        'Unsupported configuration value for {config_key}. '
        'Expected one of {valid_options} but got {config_value}.'
    )


class UnsupportedServiceProtocolsError(BotoCoreError):
    """Error when a service does not use any protocol supported by botocore."""

    fmt = (
        'Botocore supports {botocore_supported_protocols}, but service {service} only '
        'supports {service_supported_protocols}.'
    )
