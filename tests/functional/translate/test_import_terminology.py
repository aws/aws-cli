# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestImortTerminology(BaseAWSCommandParamsTest):

    prefix = 'translate import-terminology'

    def setUp(self):
        super(TestImortTerminology, self).setUp()
        self.files = FileCreator()
        self.temp_file = self.files.create_file(
            'foo', 'mycontents')
        with open(self.temp_file, 'rb') as f:
            self.temp_file_contents = f.read()

    def tearDown(self):
        super(TestImortTerminology, self).tearDown()
        self.files.remove_all()

    def test_import_terminology_with_file_and_csv(self):
        cmdline = self.prefix
        cmdline += ' --name myterminology --merge-strategy OVERWRITE'
        cmdline += ' --terminology-data Format=CSV'
        cmdline += ' --data-file fileb://%s' % self.temp_file
        result = {
            'Name': 'myterminology',
            'MergeStrategy': 'OVERWRITE',
            'TerminologyData': {
                'File': self.temp_file_contents,
                'Format': 'CSV',
            },
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_import_terminology_with_file_and_tmx(self):
        cmdline = self.prefix
        cmdline += ' --name myterminology --merge-strategy OVERWRITE'
        cmdline += ' --terminology-data Format=TMX'
        cmdline += ' --data-file fileb://%s' % self.temp_file
        result = {
            'Name': 'myterminology',
            'MergeStrategy': 'OVERWRITE',
            'TerminologyData': {
                'File': self.temp_file_contents,
                'Format': 'TMX',
            },
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_import_using_original_file_param(self):
        cmdline = self.prefix
        cmdline += ' --name myterminology --merge-strategy OVERWRITE'
        cmdline += ' --terminology-data File=fileb://wrong.csv,Format=TMX'
        cmdline += ' --data-file fileb://right.csv'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn(
            "File cannot be provided as part of the '--terminology-data' "
            "argument. Please use the '--data-file' option instead to specify "
            "a file.",
            stderr
        )

    def test_import_terminology_with_no_file(self):
        cmdline = self.prefix
        cmdline += ' --name myterminology --merge-strategy OVERWRITE'
        cmdline += ' --terminology-data Format=TMX'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=2)
        self.assertIn('--data-file', stderr)

    def test_import_terminology_with_no_format(self):
        cmdline = self.prefix
        cmdline += ' --name myterminology --merge-strategy OVERWRITE'
        cmdline += ' --data-file fileb://%s' % self.temp_file
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn(
            'Missing required parameter in TerminologyData: "Format"', stderr
        )
