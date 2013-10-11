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
from tests.unit import BaseAWSCommandParamsTest
import os
import re

from six.moves import cStringIO
import mock


class TestCreateVirtualMFADevice(BaseAWSCommandParamsTest):

    prefix = 'iam create-virtual-mfa-device'

    def setUp(self):
        super(TestCreateVirtualMFADevice, self).setUp()
        self.parsed_response = {
            "VirtualMFADevice": {
                "Base32StringSeed": "VFpYTVc2V1lIUFlFRFczSVhLUlpRUTJRVFdUSFRNRDNTQ0c3TkZDUVdQWDVETlNWM0IyUENaQVpWTEpQTlBOTA==",
                "SerialNumber": "arn:aws:iam::419278470775:mfa/fiebaz",
                "QRCodePNG": "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6CAIAAAAHjs1qAAAFiElEQVR42u3bQW7jMBAEwPz/07vHvS0QeLpnZFVf7cgyWRTgJvPzR+Q1+TEEgrsI7iK4i+AugrsI7iK4i+AugrsI7iK4C+4iuIvgLoK7CO4iuIvgLoK7CO4iBe4/rfz/c391k7lLffK5v/r6tZu8Ofu444477rjjjjvuuOOOO+6xwcoZ/WTl5D53cNXlZqG2VPpXxh133HHHHXfccccdd9xxD09/rU7ZylZdVnvo5BY/7rjjjjvuuOOOO+64447713H/RFIOZW0944477rjjjjvuuOOOO+64417ZVM8ZPbLHXiOLO+6444477rjjjjvuuOP+fO5bC2lwMeQKoiN/ew0l7rjjjjvuuOOOO+644457uCLYGmivHuxeBmcfd6/ijrtXccfdq7jj7lXcH5han3Bkeedana9SgTvuuOOOO+6444477ri/hXttc7umMLc2tm5ycI4GnzJfWETijjvuuOOOO+6444477s9oZnKDlZvvGp2tnf/BNx8/NYA77rjjjjvuuOOOO+64v5V7rZkZHKzalXOwcg3J1qorFGK444477rjjjjvuuOOO+1u5fwLrSG9T6zEGxyr3FWqPwkeemcEdd9xxxx133HHHHXfcj3Kv4chNUo17rU7ZmtDjaxJ33HHHHXfccccdd9xxfw33rWYm12McOY/wBQupZgN33HHHHXfccccdd9xxx/2DwTpy0Pzm2sh9oyOgc+sZd9xxxx133HHHHXfcccc9liOVSE3SkYIot2KPFES444477rjjjjvuuOOO+/u4DzYzgxoGpyH35q3R2Nrb758awB133HHHHXfccccdd9zfyj23NmpX3jomkBuc3N7+4DIr+MYdd9xxxx133HHHHXfc38q91gkcUZi7jcGd/9xIHnkG4Y477rjjjjvuuOOOO+6430gOR20hbVUTW4cIrg0O7rjjjjvuuOOOO+644/4a7keKi8G+6At273Nv3vpc3HHHHXfccccdd9xxxx332LjXyocanUfgqJ0pqNU4uOOOO+6444477rjjjjvuS13E1l53jc5Ndjf144477rjjjjvuuOOOO+64x77Skf352mZ+7VhEbo62DiBE6jvccccdd9xxxx133HHHHffs9A8WNbnprz0atv7rYPDrP/IQAe6444477rjjjjvuuON+lPvguK//ci+TrS3RwZ7q5nMEd9xxxx133HHHHXfccce9VSDkippcY5A7nrBVaxyp2nDHHXfccccdd9xxxx133FuTVFs5tUttlVq5pZJ7cCy0arjjjjvuuOOOO+6444477tmd8K0SIDdnNXZHirj+YwV33HHHHXfccccdd9xxfw33mu+bHUiObK4By7E7jgF33HHHHXfccccdd9xxfw33Whcx+Kt/a1Zyn5tbZltkcccdd9xxxx133HHHHXfcb4DOnRp4YgeSQ/l9jRDuuOOOO+6444477rjjjntM4WCBMGhlcHByt1GrcbZOSeCOO+6444477rjjjjvuuD8htUMENcFbN1mrcXIfhDvuuOOOO+6444477rjjvvSrP3cbg3NWG7pcMTV4OuPtRSTuuOOOO+6444477rjjfoV7rXvZWjlbVr6+5CkUNbjjjjvuuOOOO+6444477qsacn+7VeMcaYRyVdsjDxHgjjvuuOOOO+6444477rinNNR6myfexlbXpJnBHXfccccdd9xxxx133J/PvbAFPT5nN4upLQy444477rjjjjvuuOOOO+4t7rWx27pybY/9iLMjvQ3uuOOOO+6444477rjjjvvSfB/Zr86t58H53qpxBpdoYZxxxx133HHHHXfccccd99dwF3lKcBfcRXAXwV0EdxHcRXAXwV0EdxHcRXAXwV1wF8FdBHcR3EVwF8FdBHcR3EVwF8Fd5F/+AgASajf850wfAAAAAElFTkSuQmCC",
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
        cmdline += ' --outfile %s --bootstrap-method Base32StringSeed' % outfile
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
        captured = cStringIO()
        outfile = '/some/bad/filename.png'
        self.addCleanup(self.remove_file_if_exists, outfile)
        cmdline = self.prefix
        cmdline += ' --virtual-mfa-device-name fiebaz'
        cmdline += ' --outfile %s --bootstrap-method QRCodePNG' % outfile
        result = {}
        with mock.patch('sys.stderr', captured):
            self.assert_params_for_cmd(cmdline, result, expected_rc=255)
