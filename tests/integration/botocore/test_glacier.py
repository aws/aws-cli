# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest

from botocore.exceptions import ClientError
from botocore.vendored import six
import botocore.session


class TestGlacier(unittest.TestCase):
    # We have to use a single vault for all the integration tests.
    # This is because if we create a vault and upload then delete
    # an archive, we cannot immediately clean up and delete the vault.
    # The compromise is that we'll use a single vault and use
    # get_or_create semantics for the integ tests.  This does mean you
    # need to be careful when writing tests.  Assume that other code
    # is also using this vault in parallel, so don't rely on things like
    # number of archives in a vault.

    VAULT_NAME = 'botocore-integ-test-vault'

    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('glacier', 'us-west-2')
        # There's no error if the vault already exists so we don't
        # need to catch any exceptions here.
        self.client.create_vault(vaultName=self.VAULT_NAME)

    def test_can_list_vaults_without_account_id(self):
        response = self.client.list_vaults()
        self.assertIn('VaultList', response)

    def test_can_handle_error_responses(self):
        with self.assertRaises(ClientError):
            self.client.list_vaults(accountId='asdf')

    def test_can_upload_archive(self):
        body = six.BytesIO(b"bytes content")
        response = self.client.upload_archive(vaultName=self.VAULT_NAME,
                                              archiveDescription='test upload',
                                              body=body)
        self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 201)
        archive_id = response['archiveId']
        response = self.client.delete_archive(vaultName=self.VAULT_NAME,
                                              archiveId=archive_id)
        self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 204)

    def test_can_upload_archive_from_bytes(self):
        response = self.client.upload_archive(vaultName=self.VAULT_NAME,
                                              archiveDescription='test upload',
                                              body=b'bytes body')
        self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 201)
        archive_id = response['archiveId']
        response = self.client.delete_archive(vaultName=self.VAULT_NAME,
                                              archiveId=archive_id)
        self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 204)


if __name__ == '__main__':
    unittest.main()

