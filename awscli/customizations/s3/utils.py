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
from datetime import datetime
import hashlib
import os
from six.moves import queue as Queue

from dateutil.tz import tzlocal

from awscli.customizations.s3.constants import QUEUE_TIMEOUT_WAIT


class MD5Error(Exception):
    """
    Exception for md5's that do not match.
    """
    pass


class NoBlockQueue(Queue.Queue):
    """
    This queue ensures that joining does not block interrupt signals.
    It also contains a threading event ``interrupt`` that breaks the
    while loop if signaled.  The ``interrupt`` signal is optional.
    If left out, this should act like a normal queue.
    """
    def __init__(self, interrupt=None):
        Queue.Queue.__init__(self)
        self.interrupt = interrupt

    def join(self):
        self.all_tasks_done.acquire()
        try:
            while self.unfinished_tasks:
                if self.interrupt and self.interrupt.isSet():
                    break
                self.all_tasks_done.wait(QUEUE_TIMEOUT_WAIT)
        finally:
            self.all_tasks_done.release()


def find_bucket_key(s3_path):
    """
    This is a helper function that given an s3 path such that the path is of
    the form: bucket/key
    It will return the bucket and the key represented by the s3 path
    """
    s3_components = s3_path.split('/')
    bucket = s3_components[0]
    s3_key = ""
    if len(s3_components) > 1:
        s3_key = '/'.join(s3_components[1:])
    return bucket, s3_key


def get_file_stat(path):
    """
    This is a helper function that given a local path return the size of
    the file in bytes and time of last modification.
    """
    stats = os.stat(path)
    update_time = datetime.fromtimestamp(stats.st_mtime, tzlocal())
    return stats.st_size, update_time


def retrieve_http_etag(http_response):
    """
    Retrieves etag from http response.
    """
    return http_response.headers['ETag'][1:-1]


def check_etag(etag, data):
    """
    This fucntion checks the etag and the md5 checksum to ensure no
    data was corrupted upon transfer.
    """
    m = hashlib.md5()
    m.update(data)
    if '-' not in etag:
        if etag != m.hexdigest():
            raise MD5Error


def check_error(response_data):
    """
    A helper function that prints out the error message recieved in the
    response_data and raises an error when there is an error.
    """
    if response_data:
        if 'Errors' in response_data:
            errors = response_data['Errors']
            for error in errors:
                raise Exception("Error: %s\n" % error['Message'])


def operate(service, cmd, kwargs):
    """
    A helper function that universally calls any command by taking in the
    service, name of the command, and any additional parameters required in
    the call.
    """
    operation = service.get_operation(cmd)
    http_response, response_data = operation.call(**kwargs)
    check_error(response_data)
    return response_data, http_response
