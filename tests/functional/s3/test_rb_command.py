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
from awscli.testutils import BaseCLIDriverTest, capture_output

from awscli.customizations.s3.subcommands import RbCommand


class FakeArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return hasattr(self, key)


class StatusCode(object):
    def __init__(self, status_code):
        self.status_code = status_code


class TestRbCommand(BaseCLIDriverTest):

    prefix = 's3 rb '

    def setUp(self):
        super(TestRbCommand, self).setUp()
        self.responses = {}
        self.method_calls = []

    def tearDown(self):
        super(TestRbCommand, self).tearDown()

    def handler(self, model, **kwargs):
        name = model.name
        if name in self.responses:
            self.method_calls.append(name)
            return self.responses[name].pop()
        raise RuntimeError("No response for: %s" % name)

    def test_rb_force_deletes_bucket_on_success(self):
        cmd = RbCommand(self.session)
        self.session.register('before-call', self.handler)

        self.responses['ListObjects'] = [
            (StatusCode(200), {'Contents': [
                {'Key': 'foo',
                 'Size': 100,
                 'LastModified': '2016-03-01T23:50:13.000Z'}]})
        ]
        self.responses['DeleteObject'] = [
            (StatusCode(200), {})
        ]
        self.responses['DeleteBucket'] = [
            (StatusCode(200), {})
        ]

        global_args = FakeArgs(endpoint_url=None,
                               region=None,
                               verify_ssl=None)
        rc = cmd(['s3://bucket/', '--force'], global_args)
        self.assertEqual(self.method_calls,
                         ['ListObjects', 'DeleteObject', 'DeleteBucket'])
        self.assertEqual(rc, 0)

    def test_rb_force_does_not_delete_bucket_on_failure(self):
        cmd = RbCommand(self.session)
        self.session.register('before-call', self.handler)
        self.responses['ListObjects'] = [
            (StatusCode(500), {})
        ]

        global_args = FakeArgs(endpoint_url=None,
                               region=None,
                               verify_ssl=None)
        with self.assertRaisesRegexp(
                RuntimeError, "Unable to delete all objects in the bucket"):
            with capture_output():
                cmd(['s3://bucket/', '--force'], global_args)
        # Note there's no DeleteObject nor DeleteBucket calls
        # because the ListOBjects call failed.
        self.assertEqual(self.method_calls, ['ListObjects'])
