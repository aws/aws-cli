# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest, aws


class TestIntegGenerateCliSkeleton(unittest.TestCase):
    """This tests various services to see if the generated skeleton is correct

    The operations and services selected are arbitrary. Tried to pick
    operations that do not have many input options for the sake of readablity
    and maintenance. These are essentially smoke tests. It is not trying to
    test the different types of input shapes that can be generated in the
    skeleton. It is only testing wheter the skeleton generator argument works
    for various services.
    """
    def test_generate_cli_skeleton_s3api(self):
        p = aws('s3api delete-object --generate-cli-skeleton')
        self.assertEqual(p.rc, 0)
        self.assertEqual(
            p.stdout,
            '{\n    "Bucket": "", \n    "Key": "", \n    "MFA": "", \n    '
            '"VersionId": ""\n}\n'
        )

    def test_generate_cli_skeleton_sqs(self):
        p = aws('sqs change-message-visibility --generate-cli-skeleton')
        self.assertEqual(p.rc, 0)
        self.assertEqual(
            p.stdout,
            '{\n    "QueueUrl": "", \n    "ReceiptHandle": "", \n    '
            '"VisibilityTimeout": 0\n}\n'
        )

    def test_generate_cli_skeleton_iam(self):
        p = aws('iam create-group --generate-cli-skeleton')
        self.assertEqual(p.rc, 0)
        self.assertEqual(
            p.stdout,
            '{\n    "Path": "", \n    "GroupName": ""\n}\n'
        )
