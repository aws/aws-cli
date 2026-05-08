# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import threading

from botocore.hooks import HierarchicalEmitter
from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.customizations.s3.bucketlister import (
    BucketLister,
    ThreadedBucketLister,
)
from awscli.testutils import mock, unittest


class BaseBucketListTest:
    LISTER_CLS = None

    def setUp(self):
        self.client = mock.Mock()
        self.emitter = HierarchicalEmitter()
        self.client.meta.events = self.emitter
        self.date_parser = mock.Mock()
        self.date_parser.return_value = mock.sentinel.now
        self.responses = []
        self._response_index = 0
        self.client.get_paginator.return_value.paginate.side_effect = (
            self.fake_paginate
        )
        self.client.list_objects_v2.side_effect = self.fake_list_objects_v2

    def fake_paginate(self, *args, **kwargs):
        return self.responses

    def fake_list_objects_v2(self, **kwargs):
        del kwargs
        if self._response_index >= len(self.responses):
            raise AssertionError('No more ListObjectsV2 responses configured')
        response = self.responses[self._response_index]
        self._response_index += 1
        return response

    def create_lister(self):
        return self.LISTER_CLS(self.client, self.date_parser)

    def test_list_objects(self):
        now = mock.sentinel.now
        individual_response_elements = [
            {
                'LastModified': '2014-02-27T04:20:38.000Z',
                'Key': 'a',
                'Size': 1,
            },
            {
                'LastModified': '2014-02-27T04:20:38.000Z',
                'Key': 'b',
                'Size': 2,
            },
            {
                'LastModified': '2014-02-27T04:20:38.000Z',
                'Key': 'c',
                'Size': 3,
            },
        ]
        self.responses = [
            {'Contents': individual_response_elements[0:2]},
            {'Contents': [individual_response_elements[2]]},
        ]
        lister = self.create_lister()
        objects = list(lister.list_objects(bucket='foo'))
        self.assertEqual(
            objects,
            [
                ('foo/a', individual_response_elements[0]),
                ('foo/b', individual_response_elements[1]),
                ('foo/c', individual_response_elements[2]),
            ],
        )
        for individual_response in individual_response_elements:
            self.assertEqual(individual_response['LastModified'], now)

    def test_list_objects_passes_in_extra_args(self):
        self.responses = [
            {
                'Contents': [
                    {
                        'LastModified': '2014-02-27T04:20:38.000Z',
                        'Key': 'mykey',
                        'Size': 3,
                    }
                ]
            }
        ]
        lister = self.create_lister()
        list(
            lister.list_objects(
                bucket='mybucket', extra_args={'RequestPayer': 'requester'}
            )
        )
        self.client.get_paginator.return_value.paginate.assert_called_with(
            Bucket='mybucket',
            PaginationConfig={'PageSize': None},
            RequestPayer='requester',
        )

    def test_list_objects_uses_local_tz_aware_datetimes_by_default(self):
        timestamp = '2014-02-27T04:20:38.000Z'
        self.responses = [
            {
                'Contents': [
                    {
                        'LastModified': timestamp,
                        'Key': 'mykey',
                        'Size': 3,
                    }
                ]
            }
        ]
        lister = self.LISTER_CLS(self.client)

        objects = list(lister.list_objects(bucket='mybucket'))

        last_modified = objects[0][1]['LastModified']
        self.assertEqual(last_modified, parse(timestamp).astimezone(tzlocal()))
        self.assertIsNotNone(last_modified.tzinfo)


class TestBucketList(BaseBucketListTest, unittest.TestCase):
    LISTER_CLS = BucketLister


class TestThreadedBucketList(BaseBucketListTest, unittest.TestCase):
    LISTER_CLS = ThreadedBucketLister

    def _emit_before_parse(self, body):
        self.emitter.emit(
            'before-parse.s3.ListObjectsV2',
            operation_model=None,
            response_dict={
                'body': body,
                'headers': {},
                'status_code': 200,
            },
            customized_response_dict={},
        )

    def test_list_objects(self):
        now = mock.sentinel.now
        individual_response_elements = [
            {
                'LastModified': '2014-02-27T04:20:38.000Z',
                'Key': 'a',
                'Size': 1,
            },
            {
                'LastModified': '2014-02-27T04:20:38.000Z',
                'Key': 'b',
                'Size': 2,
            },
            {
                'LastModified': '2014-02-27T04:20:38.000Z',
                'Key': 'c',
                'Size': 3,
            },
        ]
        self.responses = [
            {
                'Contents': individual_response_elements[0:2],
                'IsTruncated': True,
                'NextContinuationToken': 'token-2',
            },
            {
                'Contents': [individual_response_elements[2]],
                'IsTruncated': False,
            },
        ]
        lister = self.create_lister()
        objects = list(lister.list_objects(bucket='foo'))
        self.assertEqual(
            objects,
            [
                ('foo/a', individual_response_elements[0]),
                ('foo/b', individual_response_elements[1]),
                ('foo/c', individual_response_elements[2]),
            ],
        )
        for individual_response in individual_response_elements:
            self.assertEqual(individual_response['LastModified'], now)

    def test_list_objects_passes_in_extra_args(self):
        self.responses = [
            {
                'Contents': [
                    {
                        'LastModified': '2014-02-27T04:20:38.000Z',
                        'Key': 'mykey',
                        'Size': 3,
                    }
                ]
            }
        ]
        lister = self.create_lister()
        list(
            lister.list_objects(
                bucket='mybucket', extra_args={'RequestPayer': 'requester'}
            )
        )
        self.client.list_objects_v2.assert_called_once_with(
            Bucket='mybucket', RequestPayer='requester'
        )

    def test_list_objects_uses_page_size_as_max_keys(self):
        self.responses = [
            {
                'Contents': [
                    {
                        'LastModified': '2014-02-27T04:20:38.000Z',
                        'Key': 'mykey',
                        'Size': 3,
                    }
                ]
            }
        ]
        lister = self.create_lister()
        list(lister.list_objects(bucket='mybucket', page_size=25))
        self.client.list_objects_v2.assert_called_once_with(
            Bucket='mybucket', MaxKeys=25
        )

    def test_list_objects_prefetches_pages_in_background(self):
        page_two_requested = threading.Event()

        def list_objects_v2(**kwargs):
            continuation_token = kwargs.get('ContinuationToken')
            if continuation_token is None:
                self._emit_before_parse(
                    (
                        b'<?xml version="1.0" encoding="UTF-8"?>'
                        b'<ListBucketResult>'
                        b'<NextContinuationToken>token-2'
                        b'</NextContinuationToken>'
                        b'<IsTruncated>true</IsTruncated>'
                        b'</ListBucketResult>'
                    )
                )
                self.assertTrue(page_two_requested.wait(timeout=1))
                return {
                    'Contents': [
                        {
                            'LastModified': '2014-02-27T04:20:38.000Z',
                            'Key': 'a',
                            'Size': 1,
                        },
                        {
                            'LastModified': '2014-02-27T04:20:38.000Z',
                            'Key': 'b',
                            'Size': 2,
                        },
                    ],
                    'IsTruncated': True,
                    'NextContinuationToken': 'token-2',
                }
            self.assertEqual(continuation_token, 'token-2')
            page_two_requested.set()
            return {
                'Contents': [
                    {
                        'LastModified': '2014-02-27T04:20:38.000Z',
                        'Key': 'c',
                        'Size': 3,
                    }
                ],
                'IsTruncated': False,
            }

        self.client.list_objects_v2.side_effect = list_objects_v2
        objects = list(
            ThreadedBucketLister(
                self.client, self.date_parser
            ).list_objects(bucket='foo')
        )

        self.assertTrue(page_two_requested.is_set())
        self.assertEqual(
            objects,
            [
                ('foo/a', mock.ANY),
                ('foo/b', mock.ANY),
                ('foo/c', mock.ANY),
            ],
        )

    def test_list_objects_prefetches_pages_from_parsed_page(self):
        page_two_requested = threading.Event()
        allow_page_two = threading.Event()

        def list_objects_v2(**kwargs):
            continuation_token = kwargs.get('ContinuationToken')
            if continuation_token is None:
                return {
                    'Contents': [
                        {
                            'LastModified': '2014-02-27T04:20:38.000Z',
                            'Key': 'a',
                            'Size': 1,
                        },
                        {
                            'LastModified': '2014-02-27T04:20:38.000Z',
                            'Key': 'b',
                            'Size': 2,
                        },
                    ],
                    'IsTruncated': True,
                    'NextContinuationToken': 'token-2',
                }
            self.assertEqual(continuation_token, 'token-2')
            page_two_requested.set()
            allow_page_two.wait(timeout=1)
            return {
                'Contents': [
                    {
                        'LastModified': '2014-02-27T04:20:38.000Z',
                        'Key': 'c',
                        'Size': 3,
                    }
                ],
                'IsTruncated': False,
            }

        self.client.list_objects_v2.side_effect = list_objects_v2
        objects = ThreadedBucketLister(
            self.client, self.date_parser
        ).list_objects(bucket='foo')

        try:
            self.assertEqual(next(objects), ('foo/a', mock.ANY))
            self.assertTrue(page_two_requested.wait(timeout=1))
            allow_page_two.set()
            self.assertEqual(
                list(objects),
                [
                    ('foo/b', mock.ANY),
                    ('foo/c', mock.ANY),
                ],
            )
        finally:
            allow_page_two.set()
            objects.close()

    def test_list_objects_propagates_background_exception(self):
        class BackgroundError(Exception):
            pass

        def list_objects_v2(**kwargs):
            if 'ContinuationToken' not in kwargs:
                return {
                    'Contents': [
                        {
                            'LastModified': '2014-02-27T04:20:38.000Z',
                            'Key': 'a',
                            'Size': 1,
                        }
                    ],
                    'IsTruncated': True,
                    'NextContinuationToken': 'token-2',
                }
            raise BackgroundError('background failure')

        self.client.list_objects_v2.side_effect = list_objects_v2
        objects = ThreadedBucketLister(
            self.client, self.date_parser
        ).list_objects(bucket='foo')

        self.assertEqual(next(objects), ('foo/a', mock.ANY))
        with self.assertRaises(BackgroundError):
            list(objects)

    def test_closing_lister_cleans_up_requester(self):
        page_two_requested = threading.Event()
        allow_page_two = threading.Event()

        def list_objects_v2(**kwargs):
            if 'ContinuationToken' not in kwargs:
                self._emit_before_parse(
                    (
                        b'<?xml version="1.0" encoding="UTF-8"?>'
                        b'<ListBucketResult>'
                        b'<NextContinuationToken>token-2'
                        b'</NextContinuationToken>'
                        b'<IsTruncated>true</IsTruncated>'
                        b'</ListBucketResult>'
                    )
                )
                return {
                    'Contents': [
                        {
                            'LastModified': '2014-02-27T04:20:38.000Z',
                            'Key': 'a',
                            'Size': 1,
                        }
                    ],
                    'IsTruncated': True,
                    'NextContinuationToken': 'token-2',
                }
            page_two_requested.set()
            allow_page_two.wait(timeout=1)
            return {
                'Contents': [
                    {
                        'LastModified': '2014-02-27T04:20:38.000Z',
                        'Key': 'b',
                        'Size': 2,
                    }
                ],
                'IsTruncated': False,
            }

        self.client.list_objects_v2.side_effect = list_objects_v2
        objects = ThreadedBucketLister(
            self.client, self.date_parser
        ).list_objects(bucket='foo')

        self.assertEqual(next(objects), ('foo/a', mock.ANY))
        self.assertTrue(page_two_requested.wait(timeout=1))
        allow_page_two.set()
        objects.close()
