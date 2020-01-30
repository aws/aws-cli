#!/usr/bin/env python
# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
import os


class TestOutFileQueryArguments(BaseAWSCommandParamsTest):
    def setUp(self):
        self.files = FileCreator()
        super(TestOutFileQueryArguments, self).setUp()

    def tearDown(self):
        self.files.remove_all()
        super(TestOutFileQueryArguments, self).tearDown()

    def test_saves_cert_to_file_for_create_certificate_from_csr(self):
        self.parsed_response = {
            'certificatePem': 'cert...',
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': 'request-id'
            }
        }
        outfile = self.files.full_path('cert.pem')
        cmdline = 'iot create-certificate-from-csr'
        cmdline += ' --certificate-signing-request "abc"'
        cmdline += ' --certificate-pem-outfile ' + outfile
        self.run_cmd(cmdline, 0)
        self.assertTrue(os.path.exists(outfile))
        with open(outfile) as fp:
            self.assertEquals('cert...', fp.read())

    def test_saves_files_for_create_keys_and_cert(self):
        self.parsed_response = {
            'certificatePem': 'cert...',
            'keyPair': {
                'PublicKey': 'public',
                'PrivateKey': 'private'
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': 'request-id'
            }
        }
        out_cert = self.files.full_path('cert.pem')
        out_pub = self.files.full_path('key_rsa.pub')
        out_priv = self.files.full_path('key_rsa')
        cmdline = 'iot create-keys-and-certificate'
        cmdline += ' --certificate-pem-outfile ' + out_cert
        cmdline += ' --public-key-outfile ' + out_pub
        cmdline += ' --private-key-outfile ' + out_priv
        self.run_cmd(cmdline, 0)
        self.assertTrue(os.path.exists(out_cert))
        self.assertTrue(os.path.exists(out_pub))
        self.assertTrue(os.path.exists(out_priv))
        with open(out_cert) as fp:
            self.assertEquals('cert...', fp.read())
        with open(out_pub) as fp:
            self.assertEquals('public', fp.read())
        with open(out_priv) as fp:
            self.assertEquals('private', fp.read())

    def test_bad_response(self):
        outfile = self.files.full_path('cert.pem')
        self.parsed_response = {
            'Error': {'Code': 'v1', 'Message': 'v2', 'Type': 'v3'},
            'ResponseMetadata': {
                'HTTPStatusCode': 403,
                'RequestId': 'request-id'
            }
        }
        self.http_response.status_code = 403
        cmdline = 'iot create-certificate-from-csr'
        cmdline += ' --certificate-signing-request "abc"'
        cmdline += ' --certificate-pem-outfile ' + outfile
        # The error message should be in the stderr.
        self.assert_params_for_cmd(
            cmdline,
            stderr_contains=self.parsed_response['Error']['Message'],
            expected_rc=254)

    def test_ensures_file_is_writable_before_sending(self):
        outfile = os.sep.join(['', 'does', 'not', 'exist_', 'file.txt'])
        self.parsed_response = {}
        cmdline = 'iot create-certificate-from-csr'
        cmdline += ' --certificate-signing-request "abc"'
        cmdline += ' --certificate-pem-outfile ' + outfile
        self.assert_params_for_cmd(
            cmdline,
            stderr_contains='Unable to write to file: ',
            expected_rc=252)
