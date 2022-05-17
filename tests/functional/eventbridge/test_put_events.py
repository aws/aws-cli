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

from awscli.testutils import BaseAWSCommandParamsTest


class TestPutEventsCommand(BaseAWSCommandParamsTest):

    def run_put_events(self, cmd):
        response, _, _ = self.run_cmd(cmd)
        return response

    def test_put_events_with_endpoint_id(self):
        """Verify SigV4a signer has been loaded for put-events with
        an endpoint-id provided.
        """
        self.patch_make_request()
        cmd = [
            "events",
            "put-events",
            "--entries",
            "[{}]",
            "--endpoint-id",
            "123abcdefg.abc",
        ]
        response = self.run_put_events(cmd)
        self.assertEqual(
            self.last_request_dict["url"],
            "https://123abcdefg.abc.endpoint.events.amazonaws.com/",
        )
        self.assertEqual(self.last_request_dict["context"]["auth_type"], "v4a")
