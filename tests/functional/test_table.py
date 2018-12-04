# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestColor(BaseAWSCommandParamsTest):

    def test_pipe_color(self):
        command = "s3api list-buckets --output table --color on"
        self.parsed_response = {
            "Owner": {
                "DisplayName": "foo",
                "ID": "bar"
            },
            "Buckets": [
                {
                    "CreationDate": "2016-06-15T16:49:44.000Z",
                    "Name": "foo-bucket"
                }
            ]
        }
        stdout, stderr, rc = self.run_cmd(command, 0)
        # `\x1b` is the ANSI color prefix character.
        self.assertIn('\x1b', stdout)

