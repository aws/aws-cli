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

from botocore import session
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

    def _run_main(self, parsed_args, parsed_globals):
        token_generator = TokenGenerator(parsed_globals.region)
        token = token_generator.get_token(
            parsed_args.cluster_name,
            parsed_args.role_arn
        )

        full_object = {
            "kind": "ExecCredential",
            "apiVersion": "client.authentication.k8s.io/v1alpha1",
            "spec": {},
            "status": {
                "token": token
            }
        }

        uni_print(json.dumps(full_object))
        uni_print('\n')

class TokenGenerator(object):
    def __init__(self, region_name, session_handler=None):
        if session_handler is None:
            session_handler = SessionHandler()
        self._session_handler = session_handler
        self._region_name = region_name

    def get_token(self, cluster_name, role_arn):
        """ Generate a presigned url token to pass to kubectl. """
        url = self._get_presigned_url(cluster_name, role_arn)
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(url.encode('utf-8')).decode('utf-8').rstrip('=')
        return token

    def _get_presigned_url(self, cluster_name, role_arn):
        session = self._session_handler.get_session(
            self._region_name,
            role_arn
        )

        if self._region_name is None:
            self._region_name = session.get_config_variable('region')

        loader = botocore.loaders.create_loader()
        data = loader.load_data("endpoints")
        endpoint_resolver = botocore.regions.EndpointResolver(data)
        endpoint = endpoint_resolver.construct_endpoint(
            AUTH_SERVICE,
            self._region_name
        )
        signer = RequestSigner(
            ServiceId(AUTH_SERVICE),
            self._region_name,
            AUTH_SERVICE,
            AUTH_SIGNING_VERSION,
            session.get_credentials(),
            session.get_component('event_emitter')
        )
        action_params='Action=' + AUTH_COMMAND + '&Version=' + AUTH_API_VERSION
        params = {
            'method': 'GET',
            'url': 'https://' + endpoint["hostname"] + '/?' + action_params,
            'body': {},
            'headers': {CLUSTER_NAME_HEADER: cluster_name},
            'context': {}
        }

        url=signer.generate_presigned_url(
            params,
            region_name=endpoint["credentialScope"]["region"],
            operation_name='',
            expires_in=URL_TIMEOUT
        )
        return url

class SessionHandler(object):
    def get_session(self, region_name, role_arn):
        """
        Assumes the given role and returns a session object assuming said role.
        """
        session = botocore.session.get_session()
        if region_name is not None:
            session.set_config_variable('region', region_name)

        if role_arn is not None:
            sts = session.create_client(AUTH_SERVICE, region_name=region_name)
            credentials_dict = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName='EKSGetTokenAuth'
            )['Credentials']

            session.set_credentials(credentials_dict['AccessKeyId'],
                                    credentials_dict['SecretAccessKey'],
                                    credentials_dict['SessionToken'])
            return session
        else:
            return session
