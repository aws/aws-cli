#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os


class TestCreateVirtualMFADevice(BaseAWSCommandParamsTest):

    prefix = 'iam create-virtual-mfa-device'

    def setUp(self):
        super(TestCreateVirtualMFADevice, self).setUp()
        self.parsed_response = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': 'requset-id'
            },
            "VirtualMFADevice": {
                "Base32StringSeed": (
                    "VFpYTVc2V1lIUFlFRFczSVhLUlpRUTJRVFdUSFRNRDNTQ0c3"
                    "TkZDUVdQWDVETlNWM0IyUENaQVpWTEpQTlBOTA=="),
                "SerialNumber": "arn:aws:iam::419278470775:mfa/fiebaz",
                "QRCodePNG": (
                    "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6CAIAAAAHjs1qAAAFi"
                    "ElEQVR42u3bQW7jMBAEwPz/07vHvS0QeLpnZFVf7cgyWRTgJv"
                    "PzR+Q1+TEEgrsI7iK4i+AugrsI7iK4i+AugrsI7iK4C+4iuIv"
                    "gLoK7CO4iuIvgLoK7CO4iBe4/rfz/c391k7lLffK5v/r6tZu8"
                    "Ofu444477rjjjjvuuOOOO+6xwcoZ/WTl5D53cNXlZqG2VPpXx"
                    "h133HHHHXfccccdd9xxD09/rU7ZylZdVnvo5BY/7rjjjjvuuO"
                    "OOO+64447713H/RFIOZW0944477rjjjjvuuOOOO+64417ZVM8"
                    "ZPbLHXiOLO+6444477rjjjjvuuOP+fO5bC2lwMeQKoiN/ew0l"
                    "7rjjjjvuuOOOO+644457uCLYGmivHuxeBmcfd6/ijrtXccfdq"
                    "7jj7lXcH5han3Bkeedana9SgTvuuOOOO+6444477ri/hXttc7"
                    "umMLc2tm5ycI4GnzJfWETijjvuuOOOO+6444477s9oZnKDlZv"
                    "vGp2tnf/BNx8/NYA77rjjjjvuuOOOO+64v5V7rZkZHKzalXOw"
                    "cg3J1qorFGK444477rjjjjvuuOOO+1u5fwLrSG9T6zEGxyr3F"
                    "WqPwkeemcEdd9xxxx133HHHHXfcj3Kv4chNUo17rU7ZmtDjax"
                    "J33HHHHXfccccdd9xxfw33rWYm12McOY/wBQupZgN33HHHHXf"
                    "ccccdd9xxx/2DwTpy0Pzm2sh9oyOgc+sZd9xxxx133HHHHXfc"
                    "ccc9liOVSE3SkYIot2KPFES444477rjjjjvuuOOO+/u4DzYzg"
                    "xoGpyH35q3R2Nrb758awB133HHHHXfccccdd9zfyj23NmpX3j"
                    "omkBuc3N7+4DIr+MYdd9xxxx133HHHHXfc38q91gkcUZi7jcG"
                    "d/9xIHnkG4Y477rjjjjvuuOOOO+6430gOR20hbVUTW4cIrg0O"
                    "7rjjjjvuuOOOO+644/4a7keKi8G+6At273Nv3vpc3HHHHXfcc"
                    "ccdd9xxxx332LjXyocanUfgqJ0pqNU4uOOOO+6444477rjjjj"
                    "vuS13E1l53jc5Ndjf144477rjjjjvuuOOOO+64x77Skf352mZ"
                    "+7VhEbo62DiBE6jvccccdd9xxxx133HHHHffs9A8WNbnprz0a"
                    "tv7rYPDrP/IQAe6444477rjjjjvuuON+lPvguK//ci+TrS3Rw"
                    "Z7q5nMEd9xxxx133HHHHXfccce9VSDkippcY5A7nrBVaxyp2n"
                    "DHHXfccccdd9xxxx133FuTVFs5tUttlVq5pZJ7cCy0arjjjjv"
                    "uuOOOO+6444477tmd8K0SIDdnNXZHirj+YwV33HHHHXfccccd"
                    "d9xxfw33mu+bHUiObK4By7E7jgF33HHHHXfccccdd9xxfw33W"
                    "hcx+Kt/a1Zyn5tbZltkcccdd9xxxx133HHHHXfcb4DOnRp4Yg"
                    "eSQ/l9jRDuuOOOO+6444477rjjjntM4WCBMGhlcHByt1GrcbZ"
                    "OSeCOO+6444477rjjjjvuuD8htUMENcFbN1mrcXIfhDvuuOOO"
                    "O+6444477rjjvvSrP3cbg3NWG7pcMTV4OuPtRSTuuOOOO+644"
                    "4477rjjfoV7rXvZWjlbVr6+5CkUNbjjjjvuuOOOO+6444477q"
                    "sacn+7VeMcaYRyVdsjDxHgjjvuuOOOO+6444477rinNNR6myf"
                    "exlbXpJnBHXfccccdd9xxxx133J/PvbAFPT5nN4upLQy44447"
                    "7rjjjjvuuOOOO+4t7rWx27pybY/9iLMjvQ3uuOOOO+6444477"
                    "rjjjvvSfB/Zr86t58H53qpxBpdoYZxxxx133HHHHXfccccd99"
                    "dwF3lKcBfcRXAXwV0EdxHcRXAXwV0EdxHcRXAXwV1wF8FdBHc"
                    "R3EVwF8FdBHcR3EVwF8Fd5F/+AgASajf850wfAAAAAElFTkSu"
                    "QmCC"
                ),
            }
        }

    def getpath(self, filename):
        return os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            filename)

    def remove_file_if_exists(self, filename):
        if os.path.isfile(filename):
            os.remove(filename)

    def test_base32(self):
        outfile = self.getpath('fiebaz.b32')
        self.addCleanup(self.remove_file_if_exists, outfile)
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += (
            ' --outfile %s --bootstrap-method Base32StringSeed' % outfile)
        result = {"VirtualMFADeviceName": 'fiebaz'}
        self.assert_params_for_cmd(cmdline, result)
        self.assertTrue(os.path.exists(outfile))

    def test_qrcode(self):
        outfile = self.getpath('fiebaz.png')
        self.addCleanup(self.remove_file_if_exists, outfile)
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += ' --outfile %s --bootstrap-method QRCodePNG' % outfile
        result = {"VirtualMFADeviceName": 'fiebaz'}
        self.assert_params_for_cmd(cmdline, result)
        self.assertTrue(os.path.exists(outfile))

    def test_bad_filename(self):
        outfile = '/some/bad/filename.png'
        self.addCleanup(self.remove_file_if_exists, outfile)
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += ' --outfile %s --bootstrap-method QRCodePNG' % outfile
        self.assert_params_for_cmd(cmdline, expected_rc=252)

    def test_relative_filename(self):
        outfile = 'filename.png'
        self.addCleanup(self.remove_file_if_exists, outfile)
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += ' --outfile %s --bootstrap-method QRCodePNG' % outfile
        result = {"VirtualMFADeviceName": 'fiebaz'}
        self.assert_params_for_cmd(cmdline, result)
        self.assertTrue(os.path.exists(outfile))

    def test_bad_relative_filename(self):
        outfile = 'some/bad/filename.png'
        self.addCleanup(self.remove_file_if_exists, outfile)
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += ' --outfile %s --bootstrap-method QRCodePNG' % outfile
        self.assert_params_for_cmd(cmdline, expected_rc=252)

    def test_bad_response(self):
        # This can happen if you run the create-virtual-mfa-device
        # command multiple times with the same name.  You'll get
        # an "already exists" error and we should handle that case
        # gracefully.
        self.parsed_response = {
            'Error': {
                'Code': 'EntityAlreadyExists',
                'Message': 'MFADevice entity at the and name already exists.',
                'Type': 'Sender',
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 409,
                'RequestId': 'requset-id'}
        }
        self.http_response.status_code = 409
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += ' --outfile foo --bootstrap-method QRCodePNG'
        # The error message should be in the stderr.
        self.assert_params_for_cmd(
            cmdline,
            stderr_contains=self.parsed_response['Error']['Message'],
            expected_rc=254)
