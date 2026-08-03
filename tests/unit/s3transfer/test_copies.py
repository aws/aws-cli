# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import io
import unittest

from s3transfer.copies import (
    CopyCompleteMultipartUploadTask,
    CopyObjectTask,
    CopyPartTask,
)
from s3transfer.exceptions import S3CopyFailedError
from tests import BaseTaskTest, RecordingSubscriber


class RecordingClient:
    """Minimal stand-in for a boto3 client that records calls made to it."""

    def __init__(self, responses=None):
        self.calls = []
        self._responses = responses or {}

    def _record(self, method, **kwargs):
        self.calls.append((method, kwargs))
        return self._responses.get(method, {})

    def get_object_tagging(self, **kwargs):
        return self._record('get_object_tagging', **kwargs)

    def put_object_tagging(self, **kwargs):
        return self._record('put_object_tagging', **kwargs)

    def list_object_annotations(self, **kwargs):
        return self._record('list_object_annotations', **kwargs)

    def get_object_annotation(self, **kwargs):
        return self._record('get_object_annotation', **kwargs)

    def put_object_annotation(self, **kwargs):
        return self._record('put_object_annotation', **kwargs)


class FakeCallArgs:
    def __init__(
        self, copy_source, bucket, key, extra_args=None, source_client=None
    ):
        self.copy_source = copy_source
        self.bucket = bucket
        self.key = key
        self.extra_args = extra_args or {}
        self.source_client = source_client


class TestApplyTags(unittest.TestCase):
    def setUp(self):
        self.copy_source = {'Bucket': 'src-bucket', 'Key': 'src-key'}
        self.bucket = 'dest-bucket'
        self.key = 'dest-key'
        self.task = CopyCompleteMultipartUploadTask.__new__(
            CopyCompleteMultipartUploadTask
        )

    def _make_call_args(self, extra_args, source_client=None):
        return FakeCallArgs(
            self.copy_source,
            self.bucket,
            self.key,
            extra_args,
            source_client=source_client,
        )

    def _apply(
        self, client, call_args, source_version_id=None, dest_version_id=None
    ):
        # Default source_client to the same client unless test overrode it
        if call_args.source_client is None:
            call_args.source_client = client
        self.task._apply_tags(
            client, call_args, source_version_id, dest_version_id
        )

    def test_no_directive_no_tagging_makes_no_calls(self):
        client = RecordingClient()
        self._apply(client, self._make_call_args({}))
        self.assertEqual(client.calls, [])

    def test_replace_directive_with_tagging_applies_supplied_tags(self):
        client = RecordingClient()
        call_args = self._make_call_args(
            {'TaggingDirective': 'REPLACE', 'Tagging': 'env=prod&team=sdk'}
        )
        self._apply(client, call_args)
        self.assertEqual(
            client.calls,
            [
                (
                    'put_object_tagging',
                    {
                        'Bucket': self.bucket,
                        'Key': self.key,
                        'Tagging': {
                            'TagSet': [
                                {'Key': 'env', 'Value': 'prod'},
                                {'Key': 'team', 'Value': 'sdk'},
                            ]
                        },
                    },
                )
            ],
        )

    def test_copy_directive_fetches_and_applies_source_tags(self):
        source_tags = [{'Key': 'env', 'Value': 'prod'}]
        client = RecordingClient(
            responses={
                'get_object_tagging': {'TagSet': source_tags},
            }
        )
        call_args = self._make_call_args({'TaggingDirective': 'COPY'})
        self._apply(client, call_args)
        methods = [c[0] for c in client.calls]
        self.assertEqual(methods, ['get_object_tagging', 'put_object_tagging'])
        self.assertEqual(
            client.calls[1],
            (
                'put_object_tagging',
                {
                    'Bucket': self.bucket,
                    'Key': self.key,
                    'Tagging': {'TagSet': source_tags},
                },
            ),
        )

    def test_copy_directive_passes_version_id_to_get_object_tagging(self):
        source_tags = [{'Key': 'env', 'Value': 'prod'}]
        client = RecordingClient(
            responses={
                'get_object_tagging': {'TagSet': source_tags},
            }
        )
        call_args = self._make_call_args({'TaggingDirective': 'COPY'})
        self._apply(client, call_args, source_version_id='v123')
        _, kwargs = client.calls[0]
        self.assertEqual(kwargs.get('VersionId'), 'v123')

    def test_replace_directive_pins_dest_version_id_on_put(self):
        client = RecordingClient()
        call_args = self._make_call_args(
            {'TaggingDirective': 'REPLACE', 'Tagging': 'k=v'}
        )
        self._apply(client, call_args, dest_version_id='dest-v1')
        _, kwargs = client.calls[0]
        self.assertEqual(kwargs.get('VersionId'), 'dest-v1')

    def test_replace_directive_omits_dest_version_id_when_none(self):
        client = RecordingClient()
        call_args = self._make_call_args(
            {'TaggingDirective': 'REPLACE', 'Tagging': 'k=v'}
        )
        self._apply(client, call_args, dest_version_id=None)
        _, kwargs = client.calls[0]
        self.assertNotIn('VersionId', kwargs)

    def test_copy_directive_omits_version_id_when_none(self):
        client = RecordingClient(
            responses={
                'get_object_tagging': {'TagSet': []},
            }
        )
        call_args = self._make_call_args({'TaggingDirective': 'COPY'})
        self._apply(client, call_args, source_version_id=None)
        _, kwargs = client.calls[0]
        self.assertNotIn('VersionId', kwargs)

    def test_tagging_supplied_without_directive_makes_no_calls(self):
        # Per spec, multipart copy with no TaggingDirective is "do not copy",
        # even when Tagging is supplied. Caller-side warning surfaces this.
        client = RecordingClient()
        self._apply(client, self._make_call_args({'Tagging': 'key=val'}))
        self.assertEqual(client.calls, [])


class TestApplyAnnotations(unittest.TestCase):
    def setUp(self):
        self.copy_source = {'Bucket': 'src-bucket', 'Key': 'src-key'}
        self.bucket = 'dest-bucket'
        self.key = 'dest-key'
        self.task = CopyCompleteMultipartUploadTask.__new__(
            CopyCompleteMultipartUploadTask
        )

        class AnnotationListClient(RecordingClient):
            """RecordingClient whose list_object_annotations returns a single 'note' annotation."""

            def list_object_annotations(self, **kwargs):
                self.calls.append(('list_object_annotations', kwargs))
                return {'Annotations': [{'AnnotationName': 'note'}]}

        self.AnnotationListClient = AnnotationListClient

    def _make_call_args(self, extra_args, source_client=None):
        return FakeCallArgs(
            self.copy_source,
            self.bucket,
            self.key,
            extra_args,
            source_client=source_client,
        )

    def _apply(
        self,
        client,
        call_args,
        source_version_id=None,
        dest_version_id=None,
        dest_etag=None,
    ):
        if call_args.source_client is None:
            call_args.source_client = client
        self.task._apply_annotations(
            client, call_args, source_version_id, dest_version_id, dest_etag
        )

    def test_no_directive_makes_no_calls(self):
        client = RecordingClient()
        self._apply(client, self._make_call_args({}))
        self.assertEqual(client.calls, [])

    def test_exclude_directive_makes_no_calls(self):
        client = RecordingClient()
        self._apply(
            client, self._make_call_args({'AnnotationDirective': 'EXCLUDE'})
        )
        self.assertEqual(client.calls, [])

    def test_copy_directive_copies_annotations(self):
        annotation_payload = b'hello annotation'
        client = RecordingClient(
            responses={
                'list_object_annotations': {
                    'Annotations': [{'AnnotationName': 'my-note'}]
                },
                'get_object_annotation': {
                    'AnnotationPayload': io.BytesIO(annotation_payload)
                },
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(client, call_args)
        methods = [c[0] for c in client.calls]
        self.assertEqual(
            methods,
            [
                'list_object_annotations',
                'get_object_annotation',
                'put_object_annotation',
            ],
        )
        _, put_kwargs = client.calls[2]
        self.assertEqual(put_kwargs['Bucket'], self.bucket)
        self.assertEqual(put_kwargs['Key'], self.key)
        self.assertEqual(put_kwargs['AnnotationName'], 'my-note')
        self.assertEqual(put_kwargs['AnnotationPayload'], annotation_payload)

    def test_copy_directive_with_no_source_annotations_skips_put(self):
        client = RecordingClient(
            responses={
                'list_object_annotations': {'Annotations': []},
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(client, call_args)
        methods = [c[0] for c in client.calls]
        self.assertIn('list_object_annotations', methods)
        self.assertNotIn('put_object_annotation', methods)

    def test_copy_directive_pins_dest_version_and_etag_on_put(self):
        client = self.AnnotationListClient(
            responses={
                'get_object_annotation': {
                    'AnnotationPayload': io.BytesIO(b'data')
                },
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(
            client,
            call_args,
            dest_version_id='dest-v1',
            dest_etag='"destetag"',
        )
        _, put_kwargs = next(
            (m, k) for m, k in client.calls if m == 'put_object_annotation'
        )
        self.assertEqual(put_kwargs.get('VersionId'), 'dest-v1')
        self.assertEqual(put_kwargs.get('ObjectIfMatch'), '"destetag"')

    def test_copy_directive_omits_dest_pins_when_not_in_result(self):
        client = self.AnnotationListClient(
            responses={
                'get_object_annotation': {
                    'AnnotationPayload': io.BytesIO(b'data')
                },
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(client, call_args)
        _, put_kwargs = next(
            (m, k) for m, k in client.calls if m == 'put_object_annotation'
        )
        self.assertNotIn('VersionId', put_kwargs)
        self.assertNotIn('ObjectIfMatch', put_kwargs)

    def test_copy_directive_passes_version_id_to_annotation_reads(self):
        annotation_payload = b'data'
        client = self.AnnotationListClient(
            responses={
                'get_object_annotation': {
                    'AnnotationPayload': io.BytesIO(annotation_payload)
                },
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(client, call_args, source_version_id='v456')
        list_kwargs = next(
            k for m, k in client.calls if m == 'list_object_annotations'
        )
        get_kwargs = next(
            k for m, k in client.calls if m == 'get_object_annotation'
        )
        self.assertEqual(list_kwargs.get('VersionId'), 'v456')
        self.assertEqual(get_kwargs.get('VersionId'), 'v456')

    def test_copy_directive_omits_version_id_from_annotations_when_none(self):
        annotation_payload = b'data'
        client = self.AnnotationListClient(
            responses={
                'get_object_annotation': {
                    'AnnotationPayload': io.BytesIO(annotation_payload)
                },
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(client, call_args, source_version_id=None)
        list_kwargs = next(
            k for m, k in client.calls if m == 'list_object_annotations'
        )
        get_kwargs = next(
            k for m, k in client.calls if m == 'get_object_annotation'
        )
        self.assertNotIn('VersionId', list_kwargs)
        self.assertNotIn('VersionId', get_kwargs)

    def test_partial_annotation_failure_raises_s3_copy_failed_error(self):
        payloads = {'note-a': b'payload-a', 'note-b': b'payload-b'}

        class FailingPutClient(RecordingClient):
            def list_object_annotations(self, **kwargs):
                self.calls.append(('list_object_annotations', kwargs))
                return {
                    'Annotations': [
                        {'AnnotationName': 'note-a'},
                        {'AnnotationName': 'note-b'},
                    ]
                }

            def get_object_annotation(self, **kwargs):
                self.calls.append(('get_object_annotation', kwargs))
                return {
                    'AnnotationPayload': io.BytesIO(
                        payloads[kwargs['AnnotationName']]
                    )
                }

            def put_object_annotation(self, **kwargs):
                self.calls.append(('put_object_annotation', kwargs))
                if kwargs['AnnotationName'] == 'note-b':
                    raise Exception('Service error on note-b')

        client = FailingPutClient()
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        with self.assertRaises(S3CopyFailedError) as cm:
            self._apply(client, call_args)
        msg = str(cm.exception)
        self.assertIn('note-b', msg)
        self.assertIn('note-a', msg)
        self.assertIn('Succeeded', msg)
        self.assertIn('Failed', msg)

    def test_copy_directive_copies_multiple_annotations(self):
        payloads = {
            'note-a': b'payload-a',
            'note-b': b'payload-b',
        }

        class MultiAnnotationClient(RecordingClient):
            def get_object_annotation(self, **kwargs):
                self.calls.append(('get_object_annotation', kwargs))
                return {
                    'AnnotationPayload': io.BytesIO(
                        payloads[kwargs['AnnotationName']]
                    )
                }

        client = MultiAnnotationClient(
            responses={
                'list_object_annotations': {
                    'Annotations': [
                        {'AnnotationName': 'note-a'},
                        {'AnnotationName': 'note-b'},
                    ]
                },
            }
        )
        call_args = self._make_call_args({'AnnotationDirective': 'COPY'})
        self._apply(client, call_args)
        put_calls = [
            (c[1]['AnnotationName'], c[1]['AnnotationPayload'])
            for c in client.calls
            if c[0] == 'put_object_annotation'
        ]
        self.assertEqual(
            put_calls,
            [
                ('note-a', b'payload-a'),
                ('note-b', b'payload-b'),
            ],
        )


class BaseCopyTaskTest(BaseTaskTest):
    def setUp(self):
        super().setUp()
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.copy_source = {'Bucket': 'mysourcebucket', 'Key': 'mysourcekey'}
        self.extra_args = {}
        self.callbacks = []
        self.size = 5


class TestCopyObjectTask(BaseCopyTaskTest):
    def get_copy_task(self, **kwargs):
        default_kwargs = {
            'client': self.client,
            'copy_source': self.copy_source,
            'bucket': self.bucket,
            'key': self.key,
            'extra_args': self.extra_args,
            'callbacks': self.callbacks,
            'size': self.size,
        }
        default_kwargs.update(kwargs)
        return self.get_task(CopyObjectTask, main_kwargs=default_kwargs)

    def test_main(self):
        self.stubber.add_response(
            'copy_object',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
            },
        )
        task = self.get_copy_task()
        task()

        self.stubber.assert_no_pending_responses()

    def test_extra_args(self):
        self.extra_args['ACL'] = 'private'
        self.stubber.add_response(
            'copy_object',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
                'ACL': 'private',
            },
        )
        task = self.get_copy_task()
        task()

        self.stubber.assert_no_pending_responses()

    def test_callbacks_invoked(self):
        subscriber = RecordingSubscriber()
        self.callbacks.append(subscriber.on_progress)
        self.stubber.add_response(
            'copy_object',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
            },
        )
        task = self.get_copy_task()
        task()

        self.stubber.assert_no_pending_responses()
        self.assertEqual(subscriber.calculate_bytes_seen(), self.size)


class TestCopyPartTask(BaseCopyTaskTest):
    def setUp(self):
        super().setUp()
        self.copy_source_range = 'bytes=5-9'
        self.extra_args['CopySourceRange'] = self.copy_source_range
        self.upload_id = 'myuploadid'
        self.part_number = 1
        self.result_etag = 'my-etag'
        self.checksum_sha1 = 'my-checksum_sha1'

    def get_copy_task(self, **kwargs):
        default_kwargs = {
            'client': self.client,
            'copy_source': self.copy_source,
            'bucket': self.bucket,
            'key': self.key,
            'upload_id': self.upload_id,
            'part_number': self.part_number,
            'extra_args': self.extra_args,
            'callbacks': self.callbacks,
            'size': self.size,
        }
        default_kwargs.update(kwargs)
        return self.get_task(CopyPartTask, main_kwargs=default_kwargs)

    def test_main(self):
        self.stubber.add_response(
            'upload_part_copy',
            service_response={'CopyPartResult': {'ETag': self.result_etag}},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
                'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range,
            },
        )
        task = self.get_copy_task()
        self.assertEqual(
            task(), {'PartNumber': self.part_number, 'ETag': self.result_etag}
        )
        self.stubber.assert_no_pending_responses()

    def test_main_with_checksum(self):
        self.stubber.add_response(
            'upload_part_copy',
            service_response={
                'CopyPartResult': {
                    'ETag': self.result_etag,
                    'ChecksumSHA1': self.checksum_sha1,
                }
            },
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
                'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range,
            },
        )
        task = self.get_copy_task(checksum_algorithm="sha1")
        self.assertEqual(
            task(),
            {
                'PartNumber': self.part_number,
                'ETag': self.result_etag,
                'ChecksumSHA1': self.checksum_sha1,
            },
        )
        self.stubber.assert_no_pending_responses()

    def test_extra_args(self):
        self.extra_args['RequestPayer'] = 'requester'
        self.stubber.add_response(
            'upload_part_copy',
            service_response={'CopyPartResult': {'ETag': self.result_etag}},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
                'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range,
                'RequestPayer': 'requester',
            },
        )
        task = self.get_copy_task()
        self.assertEqual(
            task(), {'PartNumber': self.part_number, 'ETag': self.result_etag}
        )
        self.stubber.assert_no_pending_responses()

    def test_callbacks_invoked(self):
        subscriber = RecordingSubscriber()
        self.callbacks.append(subscriber.on_progress)
        self.stubber.add_response(
            'upload_part_copy',
            service_response={'CopyPartResult': {'ETag': self.result_etag}},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
                'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range,
            },
        )
        task = self.get_copy_task()
        self.assertEqual(
            task(), {'PartNumber': self.part_number, 'ETag': self.result_etag}
        )
        self.stubber.assert_no_pending_responses()
        self.assertEqual(subscriber.calculate_bytes_seen(), self.size)
