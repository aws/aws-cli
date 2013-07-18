#!/usr/bin/env python
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import unittest
import botocore.session
from botocore.compat import json


class TestElasticTranscoderOperations(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.session = botocore.session.get_session()
        self.dc = self.session.get_service('elastictranscoder')

    def test_create_connection(self):
        op = self.dc.get_operation('CreatePipeline')
        params = op.build_parameters(name='testpipeline',
                                     input_bucket='etc-input',
                                     output_bucket='etc-output',
                                     role='etc-role',
                                     notifications={'completed': 'etc-topic',
                                                    'progressing': 'etc-topic',
                                                    'warning': 'etc-topic',
                                                    'error': 'etc-topic'})
        result = {"OutputBucket": "etc-output",
                  "Notifications": {"Completed": "etc-topic",
                                    "Warning": "etc-topic",
                                    "Progressing": "etc-topic",
                                    "Error": "etc-topic"},
                  "Role": "etc-role",
                  "Name": "testpipeline",
                  "InputBucket": "etc-input"}
        json_body = json.loads(params['payload'].getvalue())
        self.assertEqual(json_body, result)


if __name__ == "__main__":
    unittest.main()
