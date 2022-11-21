# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from tests import BaseSessionTest, ClientHTTPStubber


class TestImportexport(BaseSessionTest):
    def create_client_and_stubber(self, service_name, region_name=None):
        if region_name is None:
            region_name = 'us-west-2'

        client = self.session.create_client(service_name, region_name)
        http_stubber = ClientHTTPStubber(client)

        return client, http_stubber

    def test_importexport_signature_version(self):
        """The importexport service has sigv2 registered as its "signature_version"
        in the service model. While this was historically true, they migrated to
        sigv4 with the introduction of endpoints.json.

        This test ensures we always choose sigv4 regardless of what the model states.
        """
        client, stubber = self.create_client_and_stubber('importexport')
        importexport_response = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n\n'
            b"<CancelJobOutput>"
            b"<CancelJobResult></CancelJobResult>"
            b"</CancelJobOutput>"
        )

        # Confirm we've ignored the model signatureVersion and chosen v4
        assert client.meta.config.signature_version == "v4"
        with stubber:
            stubber.add_response(body=importexport_response)
            client.cancel_job(JobId="12345")

        # Validate we actually signed with sigv4
        auth_header = stubber.requests[0].headers.get('Authorization', '')
        assert auth_header.startswith(b"AWS4-HMAC-SHA256")
        assert b"aws4_request" in auth_header
