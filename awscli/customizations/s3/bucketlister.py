# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import io
import logging
import threading
import xml.sax.handler
from typing import Optional
from collections import namedtuple
from dataclasses import dataclass
from xml.sax.handler import ContentHandler

from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.compat import queue


LOGGER = logging.getLogger(__name__)


_THREADED_BUCKET_LISTER_COMPLETE = object()
_ThreadedBucketListerError = namedtuple(
    '_ThreadedBucketListerError', ['exception']
)
_ThreadedBucketPage = namedtuple('_ThreadedBucketPage', ['contents'])


def _date_parser(date_string, tzinfo):
    return parse(date_string).astimezone(tzinfo)


class _StopParsing(Exception):
    pass


class BucketLister:
    """List keys in a bucket."""

    def __init__(self, client, date_parser=_date_parser):
        self._client = client
        self._date_parser = date_parser
        self._local_tz = tzlocal()

    def _get_list_objects_kwargs(
        self, bucket, prefix=None, page_size=None, extra_args=None
    ):
        kwargs = {
            'Bucket': bucket,
            'PaginationConfig': {'PageSize': page_size},
        }
        if prefix is not None:
            kwargs['Prefix'] = prefix
        if extra_args is not None:
            kwargs.update(extra_args)
        return kwargs

    def _get_list_objects_v2_request_kwargs(
        self, bucket, prefix=None, page_size=None, extra_args=None
    ):
        kwargs = {'Bucket': bucket}
        if prefix is not None:
            kwargs['Prefix'] = prefix
        if page_size is not None:
            kwargs['MaxKeys'] = page_size
        if extra_args is not None:
            kwargs.update(extra_args)
        return kwargs

    def _yield_page_contents(self, bucket, contents):
        if not contents:
            return
        local_tz = self._local_tz
        for content in contents:
            source_path = bucket + '/' + content['Key']
            content['LastModified'] = self._date_parser(
                content['LastModified'],
                local_tz,
            )
            yield source_path, content

    def list_objects(
        self, bucket, prefix=None, page_size=None, extra_args=None
    ):
        kwargs = self._get_list_objects_kwargs(
            bucket=bucket,
            prefix=prefix,
            page_size=page_size,
            extra_args=extra_args,
        )
        paginator = self._client.get_paginator('list_objects_v2')
        pages = paginator.paginate(**kwargs)
        for page in pages:
            for item in self._yield_page_contents(
                bucket=bucket,
                contents=page.get('Contents', []),
            ):
                yield item


class ThreadedBucketLister(BucketLister):
    """List keys in a bucket using a background producer thread."""

    _BUFFER_WAIT_SECONDS = 0.1
    _MAX_PAGES_BUFFER = 10

    def list_objects(
        self, bucket, prefix=None, page_size=None, extra_args=None
    ):
        request_kwargs = self._get_list_objects_v2_request_kwargs(
            bucket=bucket,
            prefix=prefix,
            page_size=page_size,
            extra_args=extra_args,
        )
        page_queue = queue.Queue(maxsize=self._MAX_PAGES_BUFFER)
        stop_event = threading.Event()
        producer = threading.Thread(
            target=self._run_producer,
            kwargs={
                'request_kwargs': request_kwargs,
                'page_queue': page_queue,
                'stop_event': stop_event,
            },
            name='ThreadedBucketLister',
            daemon=True,
        )
        producer.start()
        try:
            while True:
                next_item = page_queue.get(True)
                if next_item is _THREADED_BUCKET_LISTER_COMPLETE:
                    break
                if isinstance(next_item, _ThreadedBucketListerError):
                    raise next_item.exception
                for item in self._yield_page_contents(
                    bucket=bucket,
                    contents=next_item.contents,
                ):
                    yield item
        finally:
            stop_event.set()
            producer.join()

    def _put_page_queue_item(self, page_queue, stop_event, item):
        # In Python 3.13, we have queue.shutdown() to avoid having to poll
        # with a timeout like we do below.  Until that's the min version
        # supported, we need to handle this ourselves and avoid non-timeout
        # put() calls.
        while not stop_event.is_set():
            try:
                page_queue.put(item, timeout=self._BUFFER_WAIT_SECONDS)
                return True
            except queue.Full:
                continue
        return False

    def _run_producer(self, request_kwargs, page_queue, stop_event):
        quick_pager = _QuickPageListObjectsV2(
            self._client,
            stop_event=stop_event,
        )
        unprocessed_pages = {}
        next_page_number = 1
        try:
            quick_pager.start_pagination(request_kwargs)
            while not stop_event.is_set():
                available_page = quick_pager.next_completed_page(
                    timeout=self._BUFFER_WAIT_SECONDS
                )
                if available_page is None:
                    continue
                unprocessed_pages[available_page.page_number] = (
                    available_page
                )
                while next_page_number in unprocessed_pages:
                    next_page = unprocessed_pages.pop(next_page_number)
                    if next_page.exception is not None:
                        raise next_page.exception
                    page = next_page.page_response
                    if stop_event.is_set():
                        return
                    contents = page.get('Contents', [])
                    next_page_number += 1
                    if contents:
                        if not self._put_page_queue_item(
                            page_queue,
                            stop_event,
                            _ThreadedBucketPage(contents=contents),
                        ):
                            return
                    is_last_page = not page.get(
                        'IsTruncated'
                    ) or not page.get('NextContinuationToken')
                    if is_last_page:
                        self._put_page_queue_item(
                            page_queue,
                            stop_event,
                            _THREADED_BUCKET_LISTER_COMPLETE,
                        )
                        return
        except Exception as e:
            if not stop_event.is_set():
                self._put_page_queue_item(
                    page_queue,
                    stop_event,
                    _ThreadedBucketListerError(exception=e),
                )
        finally:
            quick_pager.shutdown()


@dataclass
class ListObjectsV2PageTask:
    page_number: int
    request_kwargs: dict
    task_queue: queue.Queue
    next_task_queue: queue.Queue
    quick_page_scheduled: bool = False

    def create_next_page_request(self, next_request_kwargs):
        return ListObjectsV2PageTask(
            page_number=self.page_number + 1,
            request_kwargs=next_request_kwargs,
            task_queue=self.next_task_queue,
            next_task_queue=self.task_queue,
            quick_page_scheduled=False,
        )


@dataclass
class ListObjectsV2PageResponse:
    page_number: int
    page_response: dict
    exception: Optional[Exception] = None


class _QuickPageListObjectsV2:
    _BEFORE_PARSE_EVENT = 'before-parse.s3.ListObjectsV2'
    _REQUEST_WORKER_COMPLETE = object()
    _BUFFER_WAIT_SECONDS = 0.1
    _MAX_PAGES_BUFFER = 10

    def __init__(self, client, stop_event):
        self._client = client
        self._stop_event = stop_event
        self._task_queues = [queue.Queue(), queue.Queue()]
        self._complete_page_queue = queue.Queue(maxsize=self._MAX_PAGES_BUFFER)
        self._shutdown_triggered = False
        self._thread_local = threading.local()
        self._before_parse_unique_id = (
            'awscli-threaded-bucket-lister-prefetch-before-parse-%s'
            % id(self)
        )
        self._threads = [
            threading.Thread(
                target=self._thread_task_handler,
                args=(self._task_queues[0],),
                name='ThreadedBucketListerRequestA',
                daemon=True,
            ),
            threading.Thread(
                target=self._thread_task_handler,
                args=(self._task_queues[1],),
                name='ThreadedBucketListerRequestB',
                daemon=True,
            ),
        ]

    def start_pagination(self, request_kwargs):
        self._client.meta.events.register(
            self._BEFORE_PARSE_EVENT,
            self._on_before_parse,
            unique_id=self._before_parse_unique_id,
        )
        for thread in self._threads:
            thread.start()
        self._task_queues[0].put(
            ListObjectsV2PageTask(
                page_number=1,
                request_kwargs=request_kwargs,
                task_queue=self._task_queues[0],
                next_task_queue=self._task_queues[1],
            )
        )

    def next_completed_page(self, timeout=None):
        try:
            return self._complete_page_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _put_completed_page(self, completed_page):
        while not self._stop_event.is_set():
            try:
                self._complete_page_queue.put(
                    completed_page,
                    timeout=self._BUFFER_WAIT_SECONDS,
                )
                return True
            except queue.Full:
                continue
        return False

    def _thread_task_handler(self, task_queue):
        while True:
            task = task_queue.get()
            if task is self._REQUEST_WORKER_COMPLETE:
                return
            if self._stop_event.is_set():
                return
            self._process_list_objects_task(task)

    def _process_list_objects_task(self, task):
        self._thread_local.current_task = task
        try:
            page = self._client.list_objects_v2(**task.request_kwargs)
        except Exception as e:
            self._put_completed_page(
                ListObjectsV2PageResponse(
                    page_number=task.page_number,
                    page_response=None,
                    exception=e,
                )
            )
            return
        if not self._put_completed_page(
            ListObjectsV2PageResponse(
                page_number=task.page_number,
                page_response=page,
            )
        ):
            return
        if not task.quick_page_scheduled:
            if not page.get('IsTruncated'):
                return
            next_continuation_token = page.get('NextContinuationToken')
            if next_continuation_token is None:
                return
            next_request_kwargs = task.request_kwargs.copy()
            next_request_kwargs['ContinuationToken'] = next_continuation_token
            next_page_task = task.create_next_page_request(next_request_kwargs)
            task.next_task_queue.put(next_page_task)

    def _on_before_parse(self, response_dict, **kwargs):
        if self._shutdown_triggered or self._stop_event.is_set():
            return
        task = getattr(self._thread_local, 'current_task', None)
        if task is None:
            return
        if response_dict.get('status_code', 0) >= 300:
            return
        body = response_dict.get('body')
        if not isinstance(body, bytes):
            return
        try:
            next_token, is_truncated = _extract_next_continuation_token(body)
        except Exception:
            LOGGER.debug(
                'Unable to extract NextContinuationToken for background '
                'prefetch.',
                exc_info=True,
            )
            return
        if not is_truncated or next_token is None:
            return
        next_request_kwargs = task.request_kwargs.copy()
        next_request_kwargs['ContinuationToken'] = next_token
        next_page_task = task.create_next_page_request(next_request_kwargs)
        task.next_task_queue.put(next_page_task)
        task.quick_page_scheduled = True

    def _queue_completion_tasks(self):
        for task_queue in self._task_queues:
            task_queue.put(self._REQUEST_WORKER_COMPLETE)

    def shutdown(self):
        if not self._shutdown_triggered:
            self._shutdown_triggered = True
            self._stop_event.set()
            self._client.meta.events.unregister(
                self._BEFORE_PARSE_EVENT,
                self._on_before_parse,
                unique_id=self._before_parse_unique_id,
            )
            self._queue_completion_tasks()
            for thread in self._threads:
                thread.join()


class _NextContinuationTokenHandler(ContentHandler):
    def __init__(self):
        self.next_continuation_token = None
        self.is_truncated = None
        self._current_element = None
        self._text_parts = []

    def startElement(self, name, attrs):
        del attrs
        if name in ('NextContinuationToken', 'IsTruncated'):
            self._current_element = name
            self._text_parts = []

    def characters(self, content):
        if self._current_element is not None:
            self._text_parts.append(content)

    def endElement(self, name):
        if name != self._current_element:
            return

        text = ''.join(self._text_parts)
        self._current_element = None
        self._text_parts = []

        if name == 'NextContinuationToken':
            self.next_continuation_token = text
            self.is_truncated = True
            raise _StopParsing()

        if name == 'IsTruncated':
            self.is_truncated = text.lower() == 'true'
            if self.is_truncated is False:
                raise _StopParsing()


def _extract_next_continuation_token(body):
    handler = _NextContinuationTokenHandler()
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, False)
    parser.setContentHandler(handler)
    try:
        parser.parse(io.BytesIO(body))
    except _StopParsing:
        pass
    return handler.next_continuation_token, handler.is_truncated is True
