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
from awscli.testutils import FileCreator


class TestTranslateDocument(BaseAWSCommandParamsTest):
    prefix = "translate translate-document"

    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        self.temp_file = self.files.create_file("foo", "mycontents")
        with open(self.temp_file, "rb") as f:
            self.temp_file_contents = f.read()

    def tearDown(self):
        super().tearDown()
        self.files.remove_all()

    def test_translate_document_with_file(self):
        cmdline = self.prefix
        cmdline += " --source-language-code FOO"
        cmdline += " --target-language-code BAR"
        cmdline += " --document ContentType=datatype"
        cmdline += " --document-content fileb://%s" % self.temp_file
        result = {
            "Document": {"Content": self.temp_file_contents, "ContentType": "datatype"},
            "SourceLanguageCode": "FOO",
            "TargetLanguageCode": "BAR",
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_translate_document_with_orignal_argument(self):
        cmdline = self.prefix
        cmdline += " --source-language-code FOO"
        cmdline += " --target-language-code BAR"
        cmdline += " --document Content=data,ContentType=datatype"

        stdout, stderr, rc = self.assert_params_for_cmd(cmdline, expected_rc=2)
        self.assertIn(
            "the following arguments are required: --document-content", stderr
        )

    def test_translate_document_with_file_and_orignal_argument(self):
        cmdline = self.prefix
        cmdline += " --source-language-code FOO"
        cmdline += " --target-language-code BAR"
        cmdline += " --document Content=data,ContentType=datatype"
        cmdline += " --document-content fileb://%s" % self.temp_file

        stdout, stderr, rc = self.assert_params_for_cmd(cmdline, expected_rc=255)
        self.assertIn(
            "Content cannot be provided as a part of the '--document' "
            "argument. Please use the '--document-content' option instead to "
            "specify a file.",
            stderr,
        )
