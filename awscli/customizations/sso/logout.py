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
import json
import logging
import os

from botocore.exceptions import ClientError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.sso.utils import SSO_TOKEN_DIR
from awscli.customizations.sso.utils import AWS_CREDS_CACHE_DIR


LOG = logging.getLogger(__name__)


class LogoutCommand(BasicCommand):
    NAME = 'logout'
    DESCRIPTION = (
        'Removes all cached AWS SSO access tokens and any cached temporary '
        'AWS credentials retrieved with SSO access tokens across all '
        'profiles. To use these profiles again, run: ``aws sso login``'
    )
    ARG_TABLE = []

    def _run_main(self, parsed_args, parsed_globals):
        SSOTokenSweeper(self._session).delete_credentials(SSO_TOKEN_DIR)
        SSOCredentialSweeper().delete_credentials(AWS_CREDS_CACHE_DIR)
        return 0


class BaseCredentialSweeper(object):
    def delete_credentials(self, creds_dir):
        if not os.path.isdir(creds_dir):
            return
        filenames = os.listdir(creds_dir)
        for filename in filenames:
            filepath = os.path.join(creds_dir, filename)
            contents = self._get_json_contents(filepath)
            if contents is None:
                continue
            if self._should_delete(contents):
                self._before_deletion(contents)
                os.remove(filepath)

    def _should_delete(self, filename):
        raise NotImplementedError('_should_delete')

    def _get_json_contents(self, filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception:
            # We do not want to include the traceback in the exception
            # so that we do not accidentally log sensitive contents because
            # of the exception or its Traceback.
            LOG.debug('Failed to load: %s', filename)
            return None

    def _before_deletion(self, contents):
        pass


class SSOTokenSweeper(BaseCredentialSweeper):
    def __init__(self, session):
        self._session = session

    def _should_delete(self, contents):
        return 'accessToken' in contents

    def _before_deletion(self, contents):
        # If the sso region is present in the cached token, construct a client
        # and invoke the logout api to invalidate the token before deleting it.
        sso_region = contents.get('region')
        if sso_region:
            sso = self._session.create_client('sso', region_name=sso_region)
            try:
                sso.logout(accessToken=contents['accessToken'])
            except ClientError:
                # The token may alread be expired or otherwise invalid. If we
                # get a client error on logout just log and continue on
                LOG.debug('Failed to call logout API:', exc_info=True)


class SSOCredentialSweeper(BaseCredentialSweeper):
    def _should_delete(self, contents):
        return contents.get('ProviderType') == 'sso'
