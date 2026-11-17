# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest


class TestResponseMetadata(BaseAWSCommandParamsTest):
    def test_excludes_response_metadata_when_errors_key_present(self):
        # The ResponseMetadata key should never be present in output. For this
        # test case, we are using an arbitrary command, s3api delete-objects,
        # to ensure generally that the ResponseMetadata does not appear in the
        # output even if the parsed response contains an Errors key.
        self.parsed_response = {
            "ResponseMetadata": {
                "RequestId": "REQUEST-ID",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amz-id-2": "REQUEST-ID-2",
                    "x-amz-request-id": "REQUEST-ID",
                    "date": "Thu, 13 Apr 2023 15:31:52 GMT",
                    "content-type": "application/xml",
                    "transfer-encoding": "chunked",
                    "server": "AmazonS3",
                    "connection": "close",
                },
                "RetryAttempts": 0,
            },
            "Errors": [
                {
                    "Key": "key",
                    "VersionId": "version-id",
                    "Code": "NoSuchVersion",
                    "Message": "The specified version does not exist.",
                }
            ],
        }
        stdout, _, _ = self.run_cmd(
            [
                "s3api",
                "delete-objects",
                "--bucket",
                "bucket",
                "--delete",
                "Objects=[{Key=key,VersionId=version-id}]",
            ]
        )
        self.assertNotIn("ResponseMetadata", stdout)
