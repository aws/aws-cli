# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import io

from tests import ClientHTTPStubber


def create_glacier_client(patched_session):
    return patched_session.create_client('glacier', 'us-west-2')


def test_can_list_vaults_without_account_id(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.list_vaults()
        assert '/-/vaults' in http_stubber.requests[0].url


def test_can_list_vaults_with_account_id(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.list_vaults(accountId='foo')
        assert '/foo/vaults' in http_stubber.requests[0].url


def test_can_upload_archive(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response(status=201)
        client.upload_archive(
            vaultName='test-vault',
            body=io.BytesIO(b'bytes content'),
        )
        headers = http_stubber.requests[0].headers
        assert 'x-amz-content-sha256' in headers
        assert 'x-amz-sha256-tree-hash' in headers


def test_can_upload_archive_from_bytes(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response(status=201)
        client.upload_archive(vaultName='test-vault', body=b'bytes content')
        headers = http_stubber.requests[0].headers
        assert 'x-amz-content-sha256' in headers
        assert 'x-amz-sha256-tree-hash' in headers


def test_can_upload_multipart_part(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response(status=204)
        client.upload_multipart_part(
            vaultName='test-vault',
            uploadId='upload-id',
            body=io.BytesIO(b'bytes content'),
        )
        headers = http_stubber.requests[0].headers
        assert 'x-amz-content-sha256' in headers
        assert 'x-amz-sha256-tree-hash' in headers


def test_can_upload_multipart_part_from_bytes(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response(status=204)
        client.upload_multipart_part(
            vaultName='test-vault',
            uploadId='upload-id',
            body=b'bytes content',
        )
        headers = http_stubber.requests[0].headers
        assert 'x-amz-content-sha256' in headers
        assert 'x-amz-sha256-tree-hash' in headers


def test_glacier_version_header_added(patched_session):
    client = create_glacier_client(patched_session)
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.list_vaults()
        assert 'x-amz-glacier-version' in http_stubber.requests[0].headers
