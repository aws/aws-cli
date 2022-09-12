# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import base64
import botocore
import json
import os
import sys

from datetime import datetime, timedelta
from botocore.signers import RequestSigner
from botocore.model import ServiceId

from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print
from awscli.customizations.utils import validate_mutually_exclusive

AUTH_SERVICE = "sts"
AUTH_COMMAND = "GetCallerIdentity"
AUTH_API_VERSION = "2011-06-15"
AUTH_SIGNING_VERSION = "v4"

ALPHA_API = "client.authentication.k8s.io/v1alpha1"
BETA_API = "client.authentication.k8s.io/v1beta1"
V1_API = "client.authentication.k8s.io/v1"

FULLY_SUPPORTED_API_VERSIONS = [
    V1_API,
    BETA_API,
]
DEPRECATED_API_VERSIONS = [
    ALPHA_API,
]

ERROR_MSG_TPL = (
    "{0} KUBERNETES_EXEC_INFO, defaulting to {1}. This is likely a "
    "bug in your Kubernetes client. Please update your Kubernetes "
    "client."
)
UNRECOGNIZED_MSG_TPL = (
    "Unrecognized API version in KUBERNETES_EXEC_INFO, defaulting to "
    "{0}. This is likely due to an outdated AWS "
    "CLI. Please update your AWS CLI."
)
DEPRECATION_MSG_TPL = (
    "Kubeconfig user entry is using deprecated API version {0}. Run "
    "'aws eks update-kubeconfig' to update."
)

# Presigned url timeout in seconds
URL_TIMEOUT = 60

TOKEN_EXPIRATION_MINS = 14

TOKEN_PREFIX = 'k8s-aws-v1.'

K8S_AWS_ID_HEADER = 'x-k8s-aws-id'


class GetTokenCommand(BasicCommand):
    NAME = 'get-token'

    DESCRIPTION = (
        "Get a token for authentication with an Amazon EKS cluster. "
        "This can be used as an alternative to the "
        "aws-iam-authenticator."
    )

    ARG_TABLE = [
        {
            'name': 'cluster-name',
            'help_text': (
                "Specify the name of the Amazon EKS cluster to create a token for. (Note: for local clusters on AWS Outposts, please use --cluster-id parameter)"
            ),
            'required': False,
        },
        {
            'name': 'role-arn',
            'help_text': (
                "Assume this role for credentials when signing the token. "
                "Use this optional parameter when the credentials for signing "
                "the token differ from that of the current role session. "
                "Using this parameter results in new role session credentials "
                "that are used to sign the token."
            ),
            'required': False,
        },
        {
            'name': 'cluster-id',
            # When EKS in-region cluster supports cluster-id, we will need to update this help text
            'help_text': (
                "Specify the id of the Amazon EKS cluster to create a token for. (Note: for local clusters on AWS Outposts only)"
            ),
            'required': False,
        },
    ]

    def get_expiration_time(self):
        token_expiration = datetime.utcnow() + timedelta(
            minutes=TOKEN_EXPIRATION_MINS
        )
        return token_expiration.strftime('%Y-%m-%dT%H:%M:%SZ')

    def _run_main(self, parsed_args, parsed_globals):
        client_factory = STSClientFactory(self._session)
        sts_client = client_factory.get_sts_client(
            region_name=parsed_globals.region, role_arn=parsed_args.role_arn
        )
        
        validate_mutually_exclusive(parsed_args, ['cluster_name'], ['cluster_id'])

        if parsed_args.cluster_id:
            identifier = parsed_args.cluster_id
        elif parsed_args.cluster_name:
            identifier = parsed_args.cluster_name
        else:
            return ValueError("Either parameter --cluster-name or --cluster-id must be specified.")

        token = TokenGenerator(sts_client).get_token(identifier)

        # By default STS signs the url for 15 minutes so we are creating a
        # rfc3339 timestamp with expiration in 14 minutes as part of the token, which
        # is used by some clients (client-go) who will refresh the token after 14 mins
        token_expiration = self.get_expiration_time()

        full_object = {
            "kind": "ExecCredential",
            "apiVersion": self.discover_api_version(),
            "spec": {},
            "status": {
                "expirationTimestamp": token_expiration,
                "token": token,
            },
        }

        uni_print(json.dumps(full_object))
        uni_print('\n')
        return 0

    def discover_api_version(self):
        """
        Parses the KUBERNETES_EXEC_INFO environment variable and returns the
        API version. If the environment variable is malformed or invalid,
        return the v1beta1 response and print a message to stderr.

        If the v1alpha1 API is specified explicitly, a message is printed to
        stderr with instructions to update.

        :return: The client authentication API version
        :rtype: string
        """
        # At the time Kubernetes v1.29 is released upstream (approx Dec 2023),
        # "v1beta1" will be removed. At or around that time, EKS will likely
        # support v1.22 through v1.28, in which client API version "v1beta1"
        # will be supported by all EKS versions.
        fallback_api_version = BETA_API

        error_prefixes = {
            "error": "Error parsing",
            "empty": "Empty",
        }

        exec_info_raw = os.environ.get("KUBERNETES_EXEC_INFO", "")
        if not exec_info_raw:
            # All kube clients should be setting this, but client-go clients
            # (kubectl, kubelet, etc) < 1.20 were not setting this if the API
            # version defined in the kubeconfig was not v1alpha1.
            #
            # This was changed in kubernetes/kubernetes#95489 so that
            # KUBERNETES_EXEC_INFO is always provided
            return fallback_api_version
        try:
            exec_info = json.loads(exec_info_raw)
        except json.JSONDecodeError:
            # The environment variable was malformed
            uni_print(
                ERROR_MSG_TPL.format(
                    error_prefixes["error"],
                    fallback_api_version,
                ),
                sys.stderr,
            )
            uni_print("\n", sys.stderr)
            return fallback_api_version

        api_version_raw = exec_info.get("apiVersion")
        if api_version_raw in FULLY_SUPPORTED_API_VERSIONS:
            return api_version_raw
        elif api_version_raw in DEPRECATED_API_VERSIONS:
            uni_print(DEPRECATION_MSG_TPL.format(api_version_raw), sys.stderr)
            uni_print("\n", sys.stderr)
            return api_version_raw
        else:
            uni_print(
                UNRECOGNIZED_MSG_TPL.format(fallback_api_version),
                sys.stderr,
            )
            uni_print("\n", sys.stderr)
            return fallback_api_version


class TokenGenerator(object):
    def __init__(self, sts_client):
        self._sts_client = sts_client

    def get_token(self, k8s_aws_id):
        """Generate a presigned url token to pass to kubectl."""
        url = self._get_presigned_url(k8s_aws_id)
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(
            url.encode('utf-8')
        ).decode('utf-8').rstrip('=')
        return token

    def _get_presigned_url(self, k8s_aws_id):
        return self._sts_client.generate_presigned_url(
            'get_caller_identity',
            Params={K8S_AWS_ID_HEADER: k8s_aws_id},
            ExpiresIn=URL_TIMEOUT,
            HttpMethod='GET',
        )


class STSClientFactory(object):
    def __init__(self, session):
        self._session = session

    def get_sts_client(self, region_name=None, role_arn=None):
        client_kwargs = {'region_name': region_name}
        if role_arn is not None:
            creds = self._get_role_credentials(region_name, role_arn)
            client_kwargs['aws_access_key_id'] = creds['AccessKeyId']
            client_kwargs['aws_secret_access_key'] = creds['SecretAccessKey']
            client_kwargs['aws_session_token'] = creds['SessionToken']
        sts = self._session.create_client('sts', **client_kwargs)
        self._register_k8s_aws_id_handlers(sts)
        return sts

    def _get_role_credentials(self, region_name, role_arn):
        sts = self._session.create_client('sts', region_name)
        return sts.assume_role(
            RoleArn=role_arn, RoleSessionName='EKSGetTokenAuth'
        )['Credentials']

    def _register_k8s_aws_id_handlers(self, sts_client):
        sts_client.meta.events.register(
            'provide-client-params.sts.GetCallerIdentity',
            self._retrieve_k8s_aws_id,
        )
        sts_client.meta.events.register(
            'before-sign.sts.GetCallerIdentity',
            self._inject_k8s_aws_id_header,
        )

    def _retrieve_k8s_aws_id(self, params, context, **kwargs):
        if K8S_AWS_ID_HEADER in params:
            context[K8S_AWS_ID_HEADER] = params.pop(K8S_AWS_ID_HEADER)

    def _inject_k8s_aws_id_header(self, request, **kwargs):
        if K8S_AWS_ID_HEADER in request.context:
            request.headers[K8S_AWS_ID_HEADER] = request.context[K8S_AWS_ID_HEADER]
