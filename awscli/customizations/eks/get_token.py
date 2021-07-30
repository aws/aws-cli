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

from datetime import datetime, timedelta
from botocore.signers import RequestSigner
from botocore.model import ServiceId

from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print

AUTH_SERVICE = "sts"
AUTH_COMMAND = "GetCallerIdentity"
AUTH_API_VERSION = "2011-06-15"
AUTH_SIGNING_VERSION = "v4"

# Presigned url timeout in seconds
URL_TIMEOUT = 60

TOKEN_EXPIRATION_MINS = 14

TOKEN_PREFIX = 'k8s-aws-v1.'

CLUSTER_NAME_HEADER = 'x-k8s-aws-id'


class GetTokenCommand(BasicCommand):
    NAME = 'get-token'

    DESCRIPTION = ("Get a token for authentication with an Amazon EKS cluster. "
                   "This can be used as an alternative to the "
                   "aws-iam-authenticator.")

    ARG_TABLE = [
        {
            'name': 'cluster-name',
            'help_text': ("Specify the name of the Amazon EKS cluster to create a token for."),
            'required': True
        },
        {
            'name': 'role-arn',
            'help_text': ("Assume this role for credentials when signing the token."),
            'required': False
        }
    ]

    def get_expiration_time(self):
        token_expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRATION_MINS)
        return token_expiration.strftime('%Y-%m-%dT%H:%M:%SZ')

    def _run_main(self, parsed_args, parsed_globals):
        client_factory = STSClientFactory(self._session)
        sts_client = client_factory.get_sts_client(
            region_name=parsed_globals.region,
            role_arn=parsed_args.role_arn)
        token = TokenGenerator(sts_client).get_token(parsed_args.cluster_name)

        # By default STS signs the url for 15 minutes so we are creating a
        # rfc3339 timestamp with expiration in 14 minutes as part of the token, which
        # is used by some clients (client-go) who will refresh the token after 14 mins
        token_expiration = self.get_expiration_time()

        full_object = {
            "kind": "ExecCredential",
            "apiVersion": "client.authentication.k8s.io/v1alpha1",
            "spec": {},
            "status": {
                "expirationTimestamp": token_expiration,
                "token": token
            }
        }

        uni_print(json.dumps(full_object))
        uni_print('\n')
        return 0


class TokenGenerator(object):
    def __init__(self, sts_client):
        self._sts_client = sts_client

    def get_token(self, cluster_name):
        """ Generate a presigned url token to pass to kubectl. """
        url = self._get_presigned_url(cluster_name)
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(
            url.encode('utf-8')).decode('utf-8').rstrip('=')
        return token

    def _get_presigned_url(self, cluster_name):
        return self._sts_client.generate_presigned_url(
            'get_caller_identity',
            Params={'ClusterName': cluster_name},
            ExpiresIn=URL_TIMEOUT,
            HttpMethod='GET',
        )


class STSClientFactory(object):
    def __init__(self, session):
        self._session = session

    def get_sts_client(self, region_name=None, role_arn=None):
        client_kwargs = {
            'region_name': region_name
        }
        if role_arn is not None:
            creds = self._get_role_credentials(region_name, role_arn)
            client_kwargs['aws_access_key_id'] = creds['AccessKeyId']
            client_kwargs['aws_secret_access_key'] = creds['SecretAccessKey']
            client_kwargs['aws_session_token'] = creds['SessionToken']
        sts = self._session.create_client('sts', **client_kwargs)
        self._register_cluster_name_handlers(sts)
        return sts

    def _get_role_credentials(self, region_name, role_arn):
        sts = self._session.create_client('sts', region_name)
        return sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName='EKSGetTokenAuth'
        )['Credentials']

    def _register_cluster_name_handlers(self, sts_client):
        sts_client.meta.events.register(
            'provide-client-params.sts.GetCallerIdentity',
            self._retrieve_cluster_name
        )
        sts_client.meta.events.register(
            'before-sign.sts.GetCallerIdentity',
            self._inject_cluster_name_header
        )

    def _retrieve_cluster_name(self, params, context, **kwargs):
        if 'ClusterName' in params:
            context['eks_cluster'] = params.pop('ClusterName')

    def _inject_cluster_name_header(self, request, **kwargs):
        if 'eks_cluster' in request.context:
            request.headers[
                CLUSTER_NAME_HEADER] = request.context['eks_cluster']
