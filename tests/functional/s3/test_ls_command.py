#!/usr/bin/env python
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
from dateutil import parser, tz

from tests.functional.s3 import BaseS3TransferCommandTest

class TestLSCommand(BaseS3TransferCommandTest):

    def test_operations_used_in_recursive_list(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "foo/bar.txt", "Size": 100,
             "LastModified": time_utc}]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --recursive', expected_rc=0)
        call_args = self.operations_called[0][1]
        # We should not be calling the args with any delimiter because we
        # want a recursive listing.
        self.assertEqual(call_args['Prefix'], '')
        self.assertEqual(call_args['Bucket'], 'bucket')
        self.assertNotIn('delimiter', call_args)
        # Time is stored in UTC timezone, but the actual time displayed
        # is specific to your tzinfo, so shift the timezone to your local's.
        time_local = parser.parse(time_utc).astimezone(tz.tzlocal())
        self.assertEqual(
            stdout, '%s        100 foo/bar.txt\n'%time_local.strftime('%Y-%m-%d %H:%M:%S'))

    def test_errors_out_with_extra_arguments(self):
        stderr = self.run_cmd('s3 ls --extra-argument-foo', expected_rc=255)[1]
        self.assertIn('Unknown options', stderr)
        self.assertIn('--extra-argument-foo', stderr)

    def test_list_buckets_use_page_size(self):
        stdout, _, _ = self.run_cmd('s3 ls --page-size 8', expected_rc=0)
        call_args = self.operations_called[0][1]
        # The page size gets translated to ``MaxBuckets`` in the s3 model
        self.assertEqual(call_args['MaxBuckets'], 8)

    def test_operations_use_page_size(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "foo/bar.txt", "Size": 100,
             "LastModified": time_utc}]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --page-size 8', expected_rc=0)
        call_args = self.operations_called[0][1]
        # We should not be calling the args with any delimiter because we
        # want a recursive listing.
        self.assertEqual(call_args['Prefix'], '')
        self.assertEqual(call_args['Bucket'], 'bucket')
        # The page size gets translated to ``MaxKeys`` in the s3 model
        self.assertEqual(call_args['MaxKeys'], 8)

    def test_operations_use_page_size_recursive(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "foo/bar.txt", "Size": 100,
             "LastModified": time_utc}]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --page-size 8 --recursive', expected_rc=0)
        call_args = self.operations_called[0][1]
        # We should not be calling the args with any delimiter because we
        # want a recursive listing.
        self.assertEqual(call_args['Prefix'], '')
        self.assertEqual(call_args['Bucket'], 'bucket')
        # The page size gets translated to ``MaxKeys`` in the s3 model
        self.assertEqual(call_args['MaxKeys'], 8)
        self.assertNotIn('Delimiter', call_args)

    def test_success_rc_has_prefixes_and_objects(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [
            {"CommonPrefixes": [{"Prefix": "foo/"}],
             "Contents": [{"Key": "foo/bar.txt", "Size": 100,
                           "LastModified": time_utc}]}
        ]
        self.run_cmd('s3 ls s3://bucket/foo', expected_rc=0)

    def test_success_rc_has_only_prefixes(self):
        self.parsed_responses = [
            {"CommonPrefixes": [{"Prefix": "foo/"}]}
        ]
        self.run_cmd('s3 ls s3://bucket/foo', expected_rc=0)

    def test_success_rc_has_only_objects(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [
            {"Contents": [{"Key": "foo/bar.txt", "Size": 100,
             "LastModified": time_utc}]}
        ]
        self.run_cmd('s3 ls s3://bucket/foo', expected_rc=0)

    def test_success_rc_with_pagination(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        # Pagination should not affect a successful return code of zero, even
        # if there are no results on the second page because there were
        # results in previous pages.
        self.parsed_responses = [
            {"CommonPrefixes": [{"Prefix": "foo/"}],
             "Contents": [{"Key": "foo/bar.txt", "Size": 100,
                           "LastModified": time_utc}]},
            {}
        ]
        self.run_cmd('s3 ls s3://bucket/foo', expected_rc=0)

    def test_success_rc_empty_bucket_no_key_given(self):
        # If no key has been provided and the bucket is empty, it should
        # still return an rc of 0 since the user is not looking for an actual
        # object.
        self.parsed_responses = [{}]
        self.run_cmd('s3 ls s3://bucket', expected_rc=0)

    def test_fail_rc_no_objects_nor_prefixes(self):
        self.parsed_responses = [{}]
        self.run_cmd('s3 ls s3://bucket/foo', expected_rc=1)

    def test_human_readable_file_size(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
            {"Key": "onekilobyte.txt", "Size": 1024, "LastModified": time_utc},
            {"Key": "onemegabyte.txt", "Size": 1024 ** 2, "LastModified": time_utc},
            {"Key": "onegigabyte.txt", "Size": 1024 ** 3, "LastModified": time_utc},
            {"Key": "oneterabyte.txt", "Size": 1024 ** 4, "LastModified": time_utc},
            {"Key": "onepetabyte.txt", "Size": 1024 ** 5, "LastModified": time_utc} ]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --human-readable',
                                    expected_rc=0)
        call_args = self.operations_called[0][1]
        # Time is stored in UTC timezone, but the actual time displayed
        # is specific to your tzinfo, so shift the timezone to your local's.
        time_local = parser.parse(time_utc).astimezone(tz.tzlocal())
        time_fmt = time_local.strftime('%Y-%m-%d %H:%M:%S')
        self.assertIn('%s     1 Byte onebyte.txt\n' % time_fmt, stdout)
        self.assertIn('%s    1.0 KiB onekilobyte.txt\n' % time_fmt, stdout)
        self.assertIn('%s    1.0 MiB onemegabyte.txt\n' % time_fmt, stdout)
        self.assertIn('%s    1.0 GiB onegigabyte.txt\n' % time_fmt, stdout)
        self.assertIn('%s    1.0 TiB oneterabyte.txt\n' % time_fmt, stdout)
        self.assertIn('%s    1.0 PiB onepetabyte.txt\n' % time_fmt, stdout)

    def test_summarize(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
            {"Key": "onekilobyte.txt", "Size": 1024, "LastModified": time_utc},
            {"Key": "onemegabyte.txt", "Size": 1024 ** 2, "LastModified": time_utc},
            {"Key": "onegigabyte.txt", "Size": 1024 ** 3, "LastModified": time_utc},
            {"Key": "oneterabyte.txt", "Size": 1024 ** 4, "LastModified": time_utc},
            {"Key": "onepetabyte.txt", "Size": 1024 ** 5, "LastModified": time_utc} ]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --summarize', expected_rc=0)
        call_args = self.operations_called[0][1]
        # Time is stored in UTC timezone, but the actual time displayed
        # is specific to your tzinfo, so shift the timezone to your local's.
        time_local = parser.parse(time_utc).astimezone(tz.tzlocal())
        time_fmt = time_local.strftime('%Y-%m-%d %H:%M:%S')
        self.assertIn('Total Objects: 6\n', stdout)
        self.assertIn('Total Size: 1127000493261825\n', stdout)

    def test_summarize_with_human_readable(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
            {"Key": "onekilobyte.txt", "Size": 1024, "LastModified": time_utc},
            {"Key": "onemegabyte.txt", "Size": 1024 ** 2, "LastModified": time_utc},
            {"Key": "onegigabyte.txt", "Size": 1024 ** 3, "LastModified": time_utc},
            {"Key": "oneterabyte.txt", "Size": 1024 ** 4, "LastModified": time_utc},
            {"Key": "onepetabyte.txt", "Size": 1024 ** 5, "LastModified": time_utc} ]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --human-readable --summarize', expected_rc=0)
        call_args = self.operations_called[0][1]
        # Time is stored in UTC timezone, but the actual time displayed
        # is specific to your tzinfo, so shift the timezone to your local's.
        time_local = parser.parse(time_utc).astimezone(tz.tzlocal())
        time_fmt = time_local.strftime('%Y-%m-%d %H:%M:%S')
        self.assertIn('Total Objects: 6\n', stdout)
        self.assertIn('Total Size: 1.0 PiB\n', stdout)

    def test_requester_pays(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
        ]}]
        command = 's3 ls s3://mybucket/foo/ --request-payer requester'
        self.assert_params_for_cmd(command, {
            'Bucket': 'mybucket', 'Delimiter': '/',
            'RequestPayer': 'requester', 'EncodingType': 'url',
            'Prefix': 'foo/'
        })

    def test_requester_pays_with_no_args(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
        ]}]
        command = 's3 ls s3://mybucket/foo/ --request-payer'
        self.assert_params_for_cmd(command, {
            'Bucket': 'mybucket', 'Delimiter': '/',
            'RequestPayer': 'requester', 'EncodingType': 'url',
            'Prefix': 'foo/'
        })

    def test_accesspoint_arn(self):
        self.parsed_responses = [
            self.list_objects_response(['bar.txt'])
        ]
        arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint'
        )
        self.run_cmd('s3 ls s3://%s' % arn, expected_rc=0)
        call_args = self.operations_called[0][1]
        self.assertEqual(call_args['Bucket'], arn)

    def test_list_buckets_uses_bucket_name_prefix(self):
        stdout, _, _ = self.run_cmd('s3 ls --bucket-name-prefix myprefix', expected_rc=0)
        call_args = self.operations_called[0][1]
        self.assertEqual(call_args['Prefix'], 'myprefix')

    def test_list_buckets_uses_bucket_region(self):
        stdout, _, _ = self.run_cmd('s3 ls --bucket-region us-west-1', expected_rc=0)
        call_args = self.operations_called[0][1]
        self.assertEqual(call_args['BucketRegion'], 'us-west-1')

    def test_list_objects_ignores_bucket_name_prefix(self):
        stdout, _, _ = self.run_cmd('s3 ls s3://mybucket --bucket-name-prefix myprefix', expected_rc=0)
        call_args = self.operations_called[0][1]
        self.assertEqual(call_args['Prefix'], '')

    def test_list_objects_ignores_bucket_region(self):
        stdout, _, _ = self.run_cmd('s3 ls s3://mybucket --bucket-region us-west-1', expected_rc=0)
        call_args = self.operations_called[0][1]
        self.assertNotIn('BucketRegion', call_args)
