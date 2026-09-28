# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import base64
import hashlib
import ipaddress
import re
import sys

from awscrt.crypto import EC, RSA, RSASignatureAlgorithm
from botocore.compat import parse_qsl, urlsplit
from botocore.signers import CloudFrontSigner
from botocore.utils import datetime2timestamp, parse_to_aware_datetime

from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError
from awscli.formatter import get_formatter

_HASH_ALGORITHMS = ('SHA1', 'SHA256')
_UNSAFE_POLICY_CHARS = re.compile(r'["\\\x00-\x1f\x7f]')
_IPV4_FORMAT = re.compile(r'\d{1,3}(\.\d{1,3}){3}(/\d{1,2})?', re.ASCII)
_SIGNING_QUERY_PARAMS = frozenset(
    ['Expires', 'Policy', 'Signature', 'Key-Pair-Id', 'Hash-Algorithm']
)
_KEY_PAIR_ID_FORMAT = re.compile(r'[A-Za-z0-9]+', re.ASCII)


class BaseSignCommand(BasicCommand):
    """Shared implementation of the CloudFront signing commands.

    Subclasses provide the resource argument(s) and decide how the signing
    result is written out (a signed URL or signed cookies).
    """

    DATE_FORMAT = """Supported formats include:
        YYYY-MM-DD (which means 0AM UTC of that day),
        YYYY-MM-DDThh:mm:ss (with default timezone as UTC),
        YYYY-MM-DDThh:mm:ss+hh:mm or YYYY-MM-DDThh:mm:ss-hh:mm (with offset),
        or EpochTime (which always means UTC).
        Do NOT use YYYYMMDD, because it will be treated as EpochTime."""
    SIGNING_ARGS = [
        {
            'name': 'key-pair-id',
            'required': True,
            'help_text': (
                "The active CloudFront key pair Id for the key pair "
                "that you're using to generate the signature."
            ),
        },
        {
            'name': 'private-key',
            'required': True,
            'cli_type_name': 'blob',
            'help_text': (
                'file://path/to/your/private-key.pem or '
                'fileb://path/to/your/private-key.pem. Both RSA and ECDSA '
                '(P-256) keys are supported in PEM format (PKCS#1, PKCS#8, '
                'or SEC1); the key type is detected automatically.'
            ),
        },
        {
            'name': 'date-less-than',
            'required': True,
            'help_text': 'The expiration date and time. ' + DATE_FORMAT,
        },
        {
            'name': 'date-greater-than',
            'help_text': (
                'An optional start date and time. It must be before '
                '--date-less-than. ' + DATE_FORMAT
            ),
        },
        {
            'name': 'ip-address',
            'help_text': (
                'An optional IPv4 address or IPv4 address range to allow '
                'client making the GET request from. Format: x.x.x.x/x or '
                'x.x.x.x'
            ),
        },
        {
            'name': 'hash-algorithm',
            'choices': list(_HASH_ALGORITHMS),
            'help_text': (
                'The hash algorithm used to sign, either ``SHA1`` or '
                '``SHA256``. ``SHA256`` is recommended for its stronger '
                'security posture. RSA keys default to ``SHA1``. ECDSA keys '
                'always use ``SHA256`` and cannot be used with ``SHA1``.'
            ),
        },
    ]

    def _run_main(self, args, parsed_globals):
        resource = self._get_policy_resource(args)
        date_less_than, date_greater_than = self._get_dates(args)
        self._validate_signing_args(args)
        signer = self._create_signer(args)
        if self._requires_custom_policy(args, resource):
            policy = signer.build_policy(
                resource,
                date_less_than,
                date_greater_than=date_greater_than,
                ip_address=args.ip_address,
            )
            signing_kwargs = {'policy': policy}
        else:
            signing_kwargs = {'date_less_than': date_less_than}
        return self._write_signed_output(
            signer, args, parsed_globals, signing_kwargs
        )

    def _get_policy_resource(self, args):
        """Validate and return the ``Resource`` of the signed policy."""
        raise NotImplementedError('_get_policy_resource')

    def _get_dates(self, args):
        date_less_than = self._parse_date(
            args.date_less_than, 'date-less-than'
        )
        date_greater_than = None
        if args.date_greater_than is not None:
            date_greater_than = self._parse_date(
                args.date_greater_than, 'date-greater-than'
            )
            _validate_date_range(date_less_than, date_greater_than)
        return date_less_than, date_greater_than

    def _parse_date(self, value, arg_name):
        try:
            return parse_to_aware_datetime(value)
        except (ValueError, TypeError, OverflowError, RuntimeError):
            raise ParamValidationError(
                f'Invalid value for --{arg_name}: "{value}" is not a valid '
                f'date. {self.DATE_FORMAT}'
            )

    def _validate_signing_args(self, args):
        if not _KEY_PAIR_ID_FORMAT.fullmatch(args.key_pair_id):
            raise ParamValidationError(
                f'Invalid value for --key-pair-id: "{args.key_pair_id}". The '
                'CloudFront key pair ID must only contain letters and '
                'digits, for example K2JCJMDEHXQW5F.'
            )
        ip_address = args.ip_address
        if ip_address is None:
            return
        _reject_ipv6_address(ip_address)
        try:
            if not _IPV4_FORMAT.fullmatch(ip_address):
                raise ValueError(ip_address)
            ipaddress.IPv4Network(ip_address, strict=False)
        except ValueError:
            raise ParamValidationError(
                f'Invalid value for --ip-address: "{ip_address}" is not a '
                'valid IPv4 address or CIDR range. Format: x.x.x.x/x or '
                'x.x.x.x'
            )

    def _create_signer(self, args):
        key_signer = _build_signer(args.private_key, args.hash_algorithm)
        hash_algorithm_param = None
        if key_signer.hash_algorithm != 'SHA1':
            hash_algorithm_param = key_signer.hash_algorithm
        return CloudFrontSigner(
            args.key_pair_id,
            key_signer.sign,
            hash_algorithm=hash_algorithm_param,
        )

    def _requires_custom_policy(self, args, resource):
        return (
            args.date_greater_than is not None
            or args.ip_address is not None
            or '*' in resource
        )

    def _write_signed_output(self, signer, args, parsed_globals, kwargs):
        raise NotImplementedError('_write_signed_output')


class SignCommand(BaseSignCommand):
    """Signs a URL."""

    NAME = 'sign'
    DESCRIPTION = (
        'Sign a given url. Supports RSA and ECDSA private keys. '
        'The key type is auto-detected from the PEM header. A custom '
        'policy is used when --date-greater-than or --ip-address is '
        'provided, or when --policy-resource differs from --url; otherwise '
        'a canned policy is used. To sign a URL with wildcards, provide '
        'the wildcard resource with --policy-resource.'
    )
    ARG_TABLE = [
        {
            'name': 'url',
            'no_paramfile': True,
            'required': True,
            'help_text': 'The URL to be signed',
        },
        {
            'name': 'policy-resource',
            'no_paramfile': True,
            'help_text': (
                'An optional resource for the signed policy, which may '
                'contain ``*`` and ``?`` wildcards (for example '
                '``https://d111111abcdef8.cloudfront.net/videos/*``). The '
                'signature is then valid for every URL matching the '
                'resource, and --url is the URL it is applied to. Defaults '
                'to --url.'
            ),
        },
    ] + BaseSignCommand.SIGNING_ARGS

    def _get_policy_resource(self, args):
        if args.policy_resource is None:
            # For backward compatibility --url is signed as it always was,
            # except for URLs that CloudFront could never accept.
            if '#' in args.url:
                raise ParamValidationError(
                    'Invalid value for --url: the URL must not contain a URL '
                    'fragment ("#"), which is never sent to CloudFront.'
                )
            return args.url
        _validate_resource(args.url, 'url', allow_wildcards=False)
        signing_params = _SIGNING_QUERY_PARAMS.intersection(
            name for name, _ in parse_qsl(urlsplit(args.url).query)
        )
        if signing_params:
            raise ParamValidationError(
                'Invalid value for --url: the URL already contains the '
                'CloudFront signing parameters '
                f'{", ".join(sorted(signing_params))}. Remove them before '
                'signing the URL.'
            )
        _validate_resource(args.policy_resource, 'policy-resource')
        # In CloudFront policies ``*`` matches zero or more characters and
        # ``?`` matches exactly one character.
        pattern = ''.join(
            {'*': '.*', '?': '.'}.get(char, re.escape(char))
            for char in args.policy_resource
        )
        if not re.fullmatch(pattern, args.url, re.DOTALL):
            raise ParamValidationError(
                f'Invalid value for --url: "{args.url}" does not match '
                f'--policy-resource "{args.policy_resource}", so CloudFront '
                'would reject the signature.'
            )
        return args.policy_resource

    def _get_dates(self, args):
        date_less_than = parse_to_aware_datetime(args.date_less_than)
        date_greater_than = args.date_greater_than
        if date_greater_than is not None:
            date_greater_than = parse_to_aware_datetime(date_greater_than)
            _validate_date_range(date_less_than, date_greater_than)
        return date_less_than, date_greater_than

    def _validate_signing_args(self, args):
        # For backward compatibility only input that CloudFront could never
        # accept is rejected, so every URL that could be used still signs.
        if args.ip_address is not None:
            _reject_ipv6_address(args.ip_address)

    def _requires_custom_policy(self, args, resource):
        return (
            args.date_greater_than is not None
            or args.ip_address is not None
            or resource != args.url
        )

    def _write_signed_output(self, signer, args, parsed_globals, kwargs):
        sys.stdout.write(signer.generate_presigned_url(args.url, **kwargs))
        return 0


def _validate_date_range(date_less_than, date_greater_than):
    # Compare at the epoch-second precision written into the policy.
    if int(datetime2timestamp(date_greater_than)) >= int(
        datetime2timestamp(date_less_than)
    ):
        raise ParamValidationError(
            'Invalid date range: --date-greater-than (the active date) must '
            'be before --date-less-than (the expiration date).'
        )


def _reject_ipv6_address(ip_address):
    try:
        is_ipv6 = ipaddress.ip_network(ip_address, strict=False).version == 6
    except ValueError:
        is_ipv6 = False
    if is_ipv6:
        raise ParamValidationError(
            f'Invalid value for --ip-address: "{ip_address}" is an IPv6 '
            'address. CloudFront only supports IPv4 addresses and ranges.'
        )


def _validate_resource(resource, arg_name, allow_wildcards=True):
    """Validate a resource that is written into the signed policy.

    Wildcards may appear anywhere in a resource (e.g. ``http*://``), so only
    resources without them are required to be well-formed URLs.
    """
    if not resource:
        error = 'the resource must not be empty.'
    elif _UNSAFE_POLICY_CHARS.search(resource):
        error = (
            'the resource must not contain double quotes, backslashes, or '
            'control characters.'
        )
    elif not resource.isascii() or ' ' in resource:
        error = (
            'the resource must only contain ASCII characters without '
            'spaces. Percent-encode other characters in the path and use the '
            'punycode (xn--) form of internationalized domain names.'
        )
    elif '#' in resource:
        error = (
            'the resource must not contain a URL fragment ("#"), which is '
            'never sent to CloudFront.'
        )
    elif (allow_wildcards and '*' in resource) or _is_http_url(resource):
        return
    else:
        error = (
            f'"{resource}" is not a valid URL. The URL must be an absolute '
            'http:// or https:// URL, for example '
            'https://d111111abcdef8.cloudfront.net/image.jpg'
        )
    raise ParamValidationError(f'Invalid value for --{arg_name}: {error}')


def _is_http_url(url):
    try:
        parsed = urlsplit(url)
        # Accessing the port validates it, raising ValueError if invalid.
        parsed.port
    except ValueError:
        return False
    return parsed.scheme in ('http', 'https') and bool(parsed.hostname)


def _build_signer(private_key, hash_algorithm=None):
    """Return the appropriate signer based on the private key type."""
    if isinstance(private_key, bytes):
        try:
            private_key = private_key.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError(
                'Unsupported private key. The private key must be an RSA or '
                'ECDSA (P-256) private key in PEM format.'
            )
    if (
        'BEGIN ENCRYPTED PRIVATE KEY' in private_key
        or 'Proc-Type: 4,ENCRYPTED' in private_key
    ):
        raise ValueError(
            'Encrypted private keys are not supported. Provide an '
            'unencrypted RSA or ECDSA (P-256) private key in PEM format.'
        )
    if 'BEGIN RSA PRIVATE KEY' in private_key:
        signer_classes = [RSASigner]
    elif 'BEGIN EC PRIVATE KEY' in private_key:
        signer_classes = [ECDSASigner]
    elif 'BEGIN PRIVATE KEY' in private_key:
        # PKCS#8 uses the same PEM header for both RSA and EC keys.
        signer_classes = [RSASigner, ECDSASigner]
    else:
        signer_classes = []
    for signer_class in signer_classes:
        signer = signer_class.from_pem(private_key, hash_algorithm)
        if signer is not None:
            return signer
    raise ValueError(
        'Unsupported key type or invalid private key. CloudFront signing '
        'supports RSA and ECDSA (P-256) private keys in PEM format '
        '(PKCS#1, PKCS#8, or SEC1).'
    )


def _pem_block(pem, *labels):
    """Return the first PEM block, including its armor, with one of labels.

    Only the requested block is returned, so PEM files that contain other
    blocks (e.g. the ``EC PARAMETERS`` written by ``openssl ecparam``) are
    supported.
    """
    for label in labels:
        match = re.search(
            rf'-----BEGIN {label}-----.*?-----END {label}-----',
            pem,
            re.DOTALL,
        )
        if match is not None:
            return match.group(0)
    raise ValueError(f'No {" or ".join(labels)} PEM block found')


class _KeySigner:
    def sign(self, message):
        try:
            return self._sign(message)
        except RuntimeError as e:
            # The CRT error only describes the failure, never the key.
            raise ValueError(
                f'Failed to sign the CloudFront policy with the private key: '
                f'{e}'
            )

    def _sign(self, message):
        raise NotImplementedError('_sign')


class RSASigner(_KeySigner):
    _SIGNATURE_ALGORITHMS = {
        'SHA1': (RSASignatureAlgorithm.PKCS1_5_SHA1, hashlib.sha1),
        'SHA256': (RSASignatureAlgorithm.PKCS1_5_SHA256, hashlib.sha256),
    }

    def __init__(self, priv_key, hash_algorithm=None):
        if hash_algorithm is None:
            # SHA-1 is CloudFront's default
            hash_algorithm = 'SHA1'
        if hash_algorithm not in self._SIGNATURE_ALGORITHMS:
            raise ParamValidationError(
                f'Unsupported hash algorithm "{hash_algorithm}". Supported '
                f'hash algorithms: {", ".join(_HASH_ALGORITHMS)}'
            )
        self.priv_key = priv_key
        self.hash_algorithm = hash_algorithm
        self._signature_algorithm, self._hash = self._SIGNATURE_ALGORITHMS[
            hash_algorithm
        ]

    @classmethod
    def from_pem(cls, private_key, hash_algorithm=None):
        """Return a signer for the RSA key in the PEM, or None if not RSA."""
        try:
            pem_block = _pem_block(
                private_key, 'RSA PRIVATE KEY', 'PRIVATE KEY'
            )
            key = RSA.new_private_key_from_pem_data(pem_block.encode('ascii'))
        except (RuntimeError, ValueError):
            return None
        return cls(key, hash_algorithm)

    def _sign(self, message):
        return self.priv_key.sign(
            self._signature_algorithm, self._hash(message).digest()
        )


class ECDSASigner(_KeySigner):
    _P256_COORDINATE_LENGTH = 32
    _SUPPORTED_HASH_ALGORITHMS = (None, 'SHA256')

    def __init__(self, priv_key, hash_algorithm=None):
        coords = priv_key.get_public_coords()
        if not coords.x:
            raise ValueError(
                'The EC private key does not include its public key, which '
                'is required for signing. Export the key again with its '
                'public key included.'
            )
        if len(coords.x) != self._P256_COORDINATE_LENGTH:
            raise ValueError(
                "Only P-256 EC keys are supported for CloudFront signing. "
                "The provided key appears to use a different curve."
            )
        if hash_algorithm not in self._SUPPORTED_HASH_ALGORITHMS:
            raise ParamValidationError(
                f'The {hash_algorithm} hash algorithm cannot be used with '
                'ECDSA keys, which only support SHA256. Remove '
                '--hash-algorithm or set it to SHA256.'
            )
        self.priv_key = priv_key
        self.hash_algorithm = 'SHA256'

    @classmethod
    def from_pem(cls, private_key, hash_algorithm=None):
        """Return a signer for the EC key in the PEM, or None if not EC."""
        try:
            pem_block = _pem_block(
                private_key, 'EC PRIVATE KEY', 'PRIVATE KEY'
            )
            body = ''.join(pem_block.splitlines()[1:-1])
            der = base64.b64decode(''.join(body.split()), validate=True)
            key = EC.new_key_from_der_data(der)
        except (RuntimeError, ValueError):
            return None
        return cls(key, hash_algorithm)

    def _sign(self, message):
        # The CRT returns the DER encoded signature that CloudFront expects.
        return self.priv_key.sign(hashlib.sha256(message).digest())
