# -*- coding: utf-8 -*-
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

# The following tests are performed to ensure that the commands work.
# It does not check every possible parameter that can be thrown as
# those are checked by tests in other classes
import datetime
import os
import platform
import contextlib
import time
import re
import stat
import signal
import socket
import tempfile
import copy

from awscli.compat import six, urlopen
import botocore.session
from botocore.exceptions import ClientError
from botocore.exceptions import WaiterError
from dateutil.tz import tzutc
import pytest

from awscli.testutils import unittest, get_stdout_encoding
from awscli.testutils import skip_if_windows
from awscli.testutils import aws as _aws
from awscli.testutils import random_chars, random_bucket_name, create_bucket
from awscli.testutils import FileCreator, ConsistencyWaiter
from awscli.customizations.s3.transferconfig import DEFAULTS


@pytest.fixture(scope='module')
def region():
    return 'us-west-2'


@pytest.fixture(scope='module')
def session():
    return botocore.session.Session()


@pytest.fixture(scope='module')
def s3_utils(session, region):
    return S3Utils(session, region)


@pytest.fixture(scope='module')
def shared_bucket(s3_utils):
    bucket_name = s3_utils.create_bucket()
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


# Bucket for cross-S3 copies
@pytest.fixture(scope='module')
def shared_copy_bucket(s3_utils):
    bucket_name = s3_utils.create_bucket()
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


# Bucket for cross-region, cross-S3 copies
@pytest.fixture(scope='module')
def shared_cross_region_bucket(s3_utils):
    bucket_name = s3_utils.create_bucket(region='eu-central-1')
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


@pytest.fixture(scope='module')
def shared_non_dns_compatible_bucket(s3_utils):
    bucket_name = _generate_non_dns_compatible_bucket_name()
    s3_utils.create_bucket(name=bucket_name)
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


@pytest.fixture(scope='module')
def shared_non_dns_compatible_us_east_1_bucket(s3_utils):
    bucket_name = _generate_non_dns_compatible_bucket_name()
    s3_utils.create_bucket(name=bucket_name, region='us-east-1')
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


@pytest.fixture
def clean_shared_buckets(s3_utils, shared_bucket, shared_copy_bucket,
                         shared_cross_region_bucket,
                         shared_non_dns_compatible_bucket,
                         shared_non_dns_compatible_us_east_1_bucket):
    s3_utils.remove_all_objects(shared_bucket)
    s3_utils.remove_all_objects(shared_copy_bucket)
    s3_utils.remove_all_objects(shared_cross_region_bucket)
    s3_utils.remove_all_objects(shared_non_dns_compatible_bucket)
    s3_utils.remove_all_objects(shared_non_dns_compatible_us_east_1_bucket)


@pytest.fixture
def files():
    files = FileCreator()
    yield files
    files.remove_all()


@pytest.fixture
def symlink_files(files):
    nested_dir = os.path.join(files.rootdir, 'realfiles')
    os.mkdir(nested_dir)
    sample_file = files.create_file(
        os.path.join(nested_dir, 'foo.txt'),
        contents='foo.txt contents'
    )
    # Create a symlink to foo.txt.
    os.symlink(sample_file, os.path.join(files.rootdir, 'a-goodsymlink'))
    # Create a bad symlink.
    os.symlink(
        'non-existent-file', os.path.join(files.rootdir, 'b-badsymlink'))
    # Create a symlink to directory where foo.txt is.
    os.symlink(nested_dir, os.path.join(files.rootdir, 'c-goodsymlink'))


@pytest.fixture
def config_with_profile(session, files):
    config_file = os.path.join(files.rootdir, 'tmpconfig')
    with open(config_file, 'w') as f:
        creds = session.get_credentials()
        f.write(
            "[profile testprofile]\n"
            "aws_access_key_id=%s\n"
            "aws_secret_access_key=%s\n" % (
                creds.access_key,
                creds.secret_key)
        )
        if creds.token is not None:
            f.write("aws_session_token=%s\n" % creds.token)
        f.flush()
    yield config_file


@pytest.fixture
def encrypt_key():
    return 'a' * 32


@pytest.fixture
def other_encrypt_key():
    return 'b' * 32


@contextlib.contextmanager
def cd(directory):
    original = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(original)


def aws(command, collect_memory=False, env_vars=None, wait_for_finish=True,
        input_data=None, input_file=None):
    if not env_vars:
        env_vars = os.environ.copy()
        env_vars['AWS_DEFAULT_REGION'] = "us-west-2"
    return _aws(command, collect_memory=collect_memory, env_vars=env_vars,
                wait_for_finish=wait_for_finish, input_data=input_data,
                input_file=input_file)


def wait_for_process_exit(process, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc = process.poll()
        if rc is not None:
            break
        time.sleep(1)
    else:
        process.kill()
        raise AssertionError("CLI did not exist within %s seconds of "
                             "receiving a Ctrl+C" % timeout)


def _generate_non_dns_compatible_bucket_name():
    name_comp = []
    # This creates a non DNS compatible bucket name by making two random
    # sequences of characters and joining them with a period and
    # adding a .com at the end.
    for i in range(2):
        name_comp.append(random_chars(10))
    return '.'.join(name_comp + ['com'])


def _running_on_rhel():
    return (
        hasattr(platform, 'linux_distribution') and
        platform.linux_distribution()[0] == 'Red Hat Enterprise Linux Server')


class S3Utils:
    _PUT_HEAD_SHARED_EXTRAS = [
        'SSECustomerAlgorithm',
        'SSECustomerKey',
        'SSECustomerKeyMD5',
        'RequestPayer',
    ]

    def __init__(self, session, region=None):
        self._session = session
        self._region = region
        self._bucket_to_region = {}
        self._client = self._session.create_client(
            's3', region_name=self._region)

    def _create_client_for_bucket(self, bucket_name):
        region = self._bucket_to_region.get(bucket_name, self._region)
        client = self._session.create_client('s3', region_name=region)
        return client

    def assert_key_contents_equal(self, bucket, key, expected_contents):
        self.wait_until_key_exists(bucket, key)
        if isinstance(expected_contents, six.BytesIO):
            expected_contents = expected_contents.getvalue().decode('utf-8')
        actual_contents = self.get_key_contents(bucket, key)
        # The contents can be huge so we try to give helpful error messages
        # without necessarily printing the actual contents.
        assert len(actual_contents) == len(expected_contents)
        assert actual_contents == expected_contents, (
            f"Contents for {bucket}/{key} do not match (but they "
            f"have the same length)"
        )

    def create_bucket(self, name=None, region=None):
        if not region:
            region = self._region
        bucket_name = create_bucket(self._session, name, region)
        self._bucket_to_region[bucket_name] = region
        # Wait for the bucket to exist before letting it be used.
        self.wait_bucket_exists(bucket_name)
        return bucket_name

    def put_object(self, bucket_name, key_name, contents='', extra_args=None):
        client = self._create_client_for_bucket(bucket_name)
        call_args = {
            'Bucket': bucket_name,
            'Key': key_name, 'Body': contents
        }
        if extra_args is not None:
            call_args.update(extra_args)
        response = client.put_object(**call_args)
        extra_head_params = {}
        if extra_args:
            extra_head_params = dict(
                (k, v) for (k, v) in extra_args.items()
                if k in self._PUT_HEAD_SHARED_EXTRAS
            )
        self.wait_until_key_exists(
            bucket_name,
            key_name,
            extra_params=extra_head_params,
        )
        return response

    def delete_bucket(self, bucket_name, attempts=5, delay=5):
        self.remove_all_objects(bucket_name)
        client = self._create_client_for_bucket(bucket_name)

        # There's a chance that, even though the bucket has been used
        # several times, the delete will fail due to eventual consistency
        # issues.
        attempts_remaining = attempts
        while True:
            attempts_remaining -= 1
            try:
                client.delete_bucket(Bucket=bucket_name)
                break
            except client.exceptions.NoSuchBucket:
                if self.bucket_not_exists(bucket_name):
                    # Fast fail when the NoSuchBucket error is real.
                    break
                if attempts_remaining <= 0:
                    raise
                time.sleep(delay)

        self._bucket_to_region.pop(bucket_name, None)

    def remove_all_objects(self, bucket_name):
        client = self._create_client_for_bucket(bucket_name)
        paginator = client.get_paginator('list_objects')
        pages = paginator.paginate(Bucket=bucket_name)
        key_names = []
        for page in pages:
            key_names += [obj['Key'] for obj in page.get('Contents', [])]
        for key_name in key_names:
            self.delete_key(bucket_name, key_name)

    def delete_key(self, bucket_name, key_name):
        client = self._create_client_for_bucket(bucket_name)
        client.delete_object(Bucket=bucket_name, Key=key_name)

    def get_key_contents(self, bucket_name, key_name):
        self.wait_until_key_exists(bucket_name, key_name)
        client = self._create_client_for_bucket(bucket_name)
        response = client.get_object(Bucket=bucket_name, Key=key_name)
        return response['Body'].read().decode('utf-8')

    def wait_bucket_exists(self, bucket_name, min_successes=3):
        client = self._create_client_for_bucket(bucket_name)
        waiter = client.get_waiter('bucket_exists')
        consistency_waiter = ConsistencyWaiter(
            min_successes=min_successes, delay_initial_poll=True)
        consistency_waiter.wait(
            lambda: waiter.wait(Bucket=bucket_name) is None
        )

    def bucket_not_exists(self, bucket_name):
        client = self._create_client_for_bucket(bucket_name)
        try:
            client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as error:
            if error.response.get('Code') == '404':
                return False
            raise

    def key_exists(self, bucket_name, key_name, min_successes=3):
        try:
            self.wait_until_key_exists(
                    bucket_name, key_name, min_successes=min_successes)
            return True
        except (ClientError, WaiterError):
            return False

    def key_not_exists(self, bucket_name, key_name, min_successes=3):
        try:
            self.wait_until_key_not_exists(
                    bucket_name, key_name, min_successes=min_successes)
            return True
        except (ClientError, WaiterError):
            return False

    def list_multipart_uploads(self, bucket_name):
        client = self._create_client_for_bucket(bucket_name)
        return client.list_multipart_uploads(
            Bucket=bucket_name).get('Uploads', [])

    def list_buckets(self):
        response = self._client.list_buckets()
        return response['Buckets']

    def get_bucket_website(self, bucket_name):
        client = self._create_client_for_bucket(bucket_name)
        return client.get_bucket_website(Bucket=bucket_name)

    def content_type_for_key(self, bucket_name, key_name):
        parsed = self.head_object(bucket_name, key_name)
        return parsed['ContentType']

    def head_object(self, bucket_name, key_name):
        client = self._create_client_for_bucket(bucket_name)
        response = client.head_object(Bucket=bucket_name, Key=key_name)
        return response

    def wait_until_key_exists(self, bucket_name, key_name, extra_params=None,
                              min_successes=3):
        self._wait_for_key(bucket_name, key_name, extra_params,
                           min_successes, exists=True)

    def wait_until_key_not_exists(self, bucket_name, key_name,
                                  extra_params=None, min_successes=3):
        self._wait_for_key(bucket_name, key_name, extra_params,
                           min_successes, exists=False)

    def _wait_for_key(self, bucket_name, key_name, extra_params=None,
                      min_successes=3, exists=True):
        client = self._create_client_for_bucket(bucket_name)
        if exists:
            waiter = client.get_waiter('object_exists')
        else:
            waiter = client.get_waiter('object_not_exists')
        params = {'Bucket': bucket_name, 'Key': key_name}
        if extra_params is not None:
            params.update(extra_params)
        for _ in range(min_successes):
            waiter.wait(**params)


@pytest.mark.usefixtures('clean_shared_buckets')
class BaseS3IntegrationTest:
    def assert_no_errors(self, p):
        assert p.rc == 0, (
            f'Non zero rc ({p.rc}) received: {p.stdout + p.stderr}'
        )
        assert 'Error:' not in p.stderr
        assert 'failed:' not in p.stderr
        assert 'client error' not in p.stderr
        assert 'server error' not in p.stderr


class TestMoveCommand(BaseS3IntegrationTest):
    def test_mv_local_to_s3(self, files, s3_utils, shared_bucket):
        full_path = files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 mv %s s3://%s/foo.txt' % (full_path,
                                              shared_bucket))
        self.assert_no_errors(p)
        # When we move an object, the local file is gone:
        assert not os.path.exists(full_path)
        # And now resides in s3.
        s3_utils.assert_key_contents_equal(
            shared_bucket, 'foo.txt', 'this is foo.txt')

    def test_mv_s3_to_local(self, files, s3_utils, shared_bucket):
        s3_utils.put_object(shared_bucket, 'foo.txt', 'this is foo.txt')
        full_path = files.full_path('foo.txt')
        assert s3_utils.key_exists(shared_bucket, key_name='foo.txt')
        p = aws('s3 mv s3://%s/foo.txt %s' % (shared_bucket, full_path))
        self.assert_no_errors(p)
        assert os.path.exists(full_path)
        with open(full_path, 'r') as f:
            assert f.read() == 'this is foo.txt'
        # The s3 file should not be there anymore.
        assert s3_utils.key_not_exists(shared_bucket, key_name='foo.txt')

    def test_mv_s3_to_s3(self, s3_utils, shared_bucket, shared_copy_bucket):
        from_bucket = shared_bucket
        to_bucket = shared_copy_bucket
        s3_utils.put_object(from_bucket, 'foo.txt', 'this is foo.txt')

        p = aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket,
                                                           to_bucket))
        self.assert_no_errors(p)
        contents = s3_utils.get_key_contents(to_bucket, 'foo.txt')
        assert contents == 'this is foo.txt'
        # And verify that the object no longer exists in the from_bucket.
        assert s3_utils.key_not_exists(from_bucket, key_name='foo.txt')

    def test_mv_s3_to_s3_multipart(self, s3_utils, shared_bucket,
                                   shared_copy_bucket):
        from_bucket = shared_bucket
        to_bucket = shared_copy_bucket
        file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        s3_utils.put_object(from_bucket, 'foo.txt', file_contents)

        p = aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket,
                                                           to_bucket))
        self.assert_no_errors(p)
        s3_utils.assert_key_contents_equal(to_bucket, 'foo.txt', file_contents)
        # And verify that the object no longer exists in the from_bucket.
        assert s3_utils.key_not_exists(from_bucket, key_name='foo.txt')

    def test_mv_s3_to_s3_multipart_recursive(self, s3_utils, shared_bucket,
                                             shared_copy_bucket):
        from_bucket = shared_bucket
        to_bucket = shared_copy_bucket

        large_file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        small_file_contents = 'small file contents'
        s3_utils.put_object(from_bucket, 'largefile', large_file_contents)
        s3_utils.put_object(from_bucket, 'smallfile', small_file_contents)

        p = aws('s3 mv s3://%s/ s3://%s/ --recursive' % (from_bucket,
                                                         to_bucket))
        self.assert_no_errors(p)
        # Nothing's in the from_bucket.
        assert s3_utils.key_not_exists(from_bucket, key_name='largefile')
        assert s3_utils.key_not_exists(from_bucket, key_name='smallfile')

        # And both files are in the to_bucket.
        assert s3_utils.key_exists(to_bucket, key_name='largefile')
        assert s3_utils.key_exists(to_bucket, key_name='smallfile')

        # And the contents are what we expect.
        s3_utils.assert_key_contents_equal(to_bucket, 'smallfile',
                                           small_file_contents)
        s3_utils.assert_key_contents_equal(to_bucket, 'largefile',
                                           large_file_contents)

    def test_mv_s3_to_s3_with_sig4(self, s3_utils, shared_bucket,
                                   shared_cross_region_bucket):
        to_region = 'eu-central-1'
        from_region = 'us-west-2'

        from_bucket = shared_bucket
        to_bucket = shared_cross_region_bucket

        file_name = 'hello.txt'
        file_contents = 'hello'
        s3_utils.put_object(from_bucket, file_name, file_contents)

        p = aws('s3 mv s3://{0}/{4} s3://{1}/{4} '
                '--source-region {2} --region {3}'
                .format(from_bucket, to_bucket, from_region, to_region,
                        file_name))
        self.assert_no_errors(p)

        assert s3_utils.key_not_exists(from_bucket, file_name)
        assert s3_utils.key_exists(to_bucket, file_name)

    def test_mv_with_large_file(self, files, s3_utils, shared_bucket):
        # 40MB will force a multipart upload.
        file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        foo_txt = files.create_file(
            'foo.txt', file_contents.getvalue().decode('utf-8'))
        p = aws('s3 mv %s s3://%s/foo.txt' % (foo_txt, shared_bucket))
        self.assert_no_errors(p)
        # When we move an object, the local file is gone:
        assert not os.path.exists(foo_txt)
        # And now resides in s3.
        s3_utils.assert_key_contents_equal(
            shared_bucket, 'foo.txt', file_contents)

        # Now verify we can download this file.
        p = aws('s3 mv s3://%s/foo.txt %s' % (shared_bucket, foo_txt))
        self.assert_no_errors(p)
        assert os.path.exists(foo_txt)
        assert os.path.getsize(foo_txt) == len(file_contents.getvalue())

    def test_mv_to_nonexistent_bucket(self, files):
        full_path = files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 mv %s s3://bad-noexist-13143242/foo.txt' % (full_path,))
        assert p.rc == 1

    def test_cant_move_file_onto_itself_small_file(self, s3_utils,
                                                   shared_bucket):
        # We don't even need a remote file in this case.  We can
        # immediately validate that we can't move a file onto itself.
        s3_utils.put_object(shared_bucket, key_name='key.txt', contents='foo')
        p = aws('s3 mv s3://%s/key.txt s3://%s/key.txt' %
                (shared_bucket, shared_bucket))
        assert p.rc == 252
        assert 'Cannot mv a file onto itself' in p.stderr

    def test_cant_move_large_file_onto_itself(self, s3_utils,
                                              shared_bucket):
        # At the API level, you can multipart copy an object onto itself,
        # but a mv command doesn't make sense because a mv is just a
        # cp + an rm of the src file.  We should be consistent and
        # not allow large files to be mv'd onto themselves.
        file_contents = six.BytesIO(b'a' * (1024 * 1024 * 10))
        s3_utils.put_object(shared_bucket, key_name='key.txt',
                            contents=file_contents)
        p = aws('s3 mv s3://%s/key.txt s3://%s/key.txt' %
                (shared_bucket, shared_bucket))
        assert p.rc == 252
        assert 'Cannot mv a file onto itself' in p.stderr


class TestRm(BaseS3IntegrationTest):
    @skip_if_windows('Newline in filename test not valid on windows.')
    # Windows won't let you do this.  You'll get:
    # [Errno 22] invalid mode ('w') or filename:
    # 'c:\\windows\\temp\\tmp0fv8uu\\foo\r.txt'
    def test_rm_with_newlines(self, files, s3_utils, shared_bucket):
        # Note the carriage return in the key name.
        foo_txt = files.create_file('foo\r.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/foo\r.txt' % (foo_txt, shared_bucket))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        assert s3_utils.key_exists(shared_bucket, key_name='foo\r.txt')

        # Then delete the file.
        aws('s3 rm s3://%s/ --recursive' % (shared_bucket,))

        # And verify it's gone.
        assert s3_utils.key_not_exists(shared_bucket, key_name='foo\r.txt')

    def test_rm_with_page_size(self, s3_utils, shared_bucket):
        s3_utils.put_object(shared_bucket, 'foo.txt', contents='hello world')
        s3_utils.put_object(shared_bucket, 'bar.txt', contents='hello world2')
        p = aws('s3 rm s3://%s/ --recursive --page-size 1' % shared_bucket)
        self.assert_no_errors(p)

        assert s3_utils.key_not_exists(shared_bucket, key_name='foo.txt')
        assert s3_utils.key_not_exists(shared_bucket, key_name='bar.txt')


class TestCp(BaseS3IntegrationTest):
    def test_cp_to_and_from_s3(self, files, s3_utils, shared_bucket):
        # This tests the ability to put a single file in s3
        # move it to a different bucket.
        # and download the file locally

        # copy file into bucket.
        foo_txt = files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/foo.txt' % (foo_txt, shared_bucket))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        assert s3_utils.key_exists(shared_bucket, key_name='foo.txt')
        contents = s3_utils.get_key_contents(shared_bucket, key_name='foo.txt')
        assert contents == 'this is foo.txt'
        content_type = s3_utils.content_type_for_key(
            shared_bucket, key_name='foo.txt')
        assert content_type == 'text/plain'

        # Make a new name for the file and copy it locally.
        full_path = files.full_path('bar.txt')
        p = aws('s3 cp s3://%s/foo.txt %s' % (shared_bucket, full_path))
        self.assert_no_errors(p)

        with open(full_path, 'r') as f:
            assert f.read() == 'this is foo.txt'

    def test_cp_without_trailing_slash(self, files, s3_utils, shared_bucket):
        # There's a unit test for this, but we still want to verify this
        # with an integration test.

        # copy file into bucket.
        foo_txt = files.create_file('foo.txt', 'this is foo.txt')
        # Note that the destination has no trailing slash.
        p = aws('s3 cp %s s3://%s' % (foo_txt, shared_bucket))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        assert s3_utils.key_exists(shared_bucket, key_name='foo.txt')
        contents = s3_utils.get_key_contents(shared_bucket, key_name='foo.txt')
        assert contents == 'this is foo.txt'

    def test_cp_s3_s3_multipart(self, s3_utils, shared_bucket,
                                shared_copy_bucket):
        from_bucket = shared_bucket
        to_bucket = shared_copy_bucket
        file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        s3_utils.put_object(from_bucket, 'foo.txt', file_contents)

        p = aws('s3 cp s3://%s/foo.txt s3://%s/foo.txt' %
                (from_bucket, to_bucket))
        self.assert_no_errors(p)
        s3_utils.assert_key_contents_equal(to_bucket, 'foo.txt', file_contents)
        assert s3_utils.key_exists(from_bucket, key_name='foo.txt')

    def test_guess_mime_type(self, files, s3_utils, shared_bucket):
        bar_png = files.create_file('bar.jpeg', 'fake png image')
        p = aws('s3 cp %s s3://%s/bar.jpeg' % (bar_png, shared_bucket))
        self.assert_no_errors(p)

        # We should have correctly guessed the content type based on the
        # filename extension.
        content_type = s3_utils.content_type_for_key(
            shared_bucket, key_name='bar.jpeg')
        assert content_type == 'image/jpeg'

    def test_download_large_file(self, files, s3_utils, shared_bucket):
        # This will force a multipart download.
        foo_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        s3_utils.put_object(shared_bucket, key_name='foo.txt',
                            contents=foo_contents)
        local_foo_txt = files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/foo.txt %s' % (shared_bucket, local_foo_txt))
        self.assert_no_errors(p)
        assert os.path.getsize(local_foo_txt) == len(foo_contents.getvalue())

    @skip_if_windows('SIGINT not supported on Windows.')
    def test_download_ctrl_c_does_not_hang(self, files, s3_utils,
                                           shared_bucket):
        foo_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 40))
        s3_utils.put_object(shared_bucket, key_name='foo.txt',
                            contents=foo_contents)
        local_foo_txt = files.full_path('foo.txt')
        # --quiet is added to make sure too much output is not communicated
        # to the PIPE, causing a deadlock when not consumed.
        process = aws('s3 cp s3://%s/foo.txt %s --quiet' %
                      (shared_bucket, local_foo_txt), wait_for_finish=False)
        # Give it some time to start up and enter it's main task loop.
        time.sleep(3)
        # The process has 60 seconds to finish after being sent a Ctrl+C,
        # otherwise the test fails.
        process.send_signal(signal.SIGINT)
        wait_for_process_exit(process, timeout=60)
        # A Ctrl+C should have a non-zero RC.
        # We either caught the process in
        # its main polling loop (rc=1), or it was successfully terminated by
        # the SIGINT (rc=-2).
        #
        # There is also the chance the interrupt happened before the transfer
        # process started or even after transfer process finished. So the
        # signal may have never been encountered, resulting in an rc of 0.
        # Therefore, it is acceptable to have an rc of 0 as the important part
        # about this test is that it does not hang.
        assert process.returncode in [0, 1, -2]

    @skip_if_windows('SIGINT not supported on Windows.')
    def test_cleans_up_aborted_uploads(self, files, s3_utils, shared_bucket):
        foo_txt = files.create_file('foo.txt', '')
        with open(foo_txt, 'wb') as f:
            for i in range(20):
                f.write(b'a' * 1024 * 1024)
        # --quiet is added to make sure too much output is not communicated
        # to the PIPE, causing a deadlock when not consumed.
        process = aws('s3 cp %s s3://%s/ --quiet' % (foo_txt, shared_bucket),
                      wait_for_finish=False)
        time.sleep(3)
        # The process has 60 seconds to finish after being sent a Ctrl+C,
        # otherwise the test fails.
        process.send_signal(signal.SIGINT)
        wait_for_process_exit(process, timeout=60)
        uploads_after = s3_utils.list_multipart_uploads(shared_bucket)
        assert uploads_after == [], (
            f"Not all multipart uploads were properly "
            f"aborted after receiving Ctrl-C: {uploads_after}"
        )

    def test_cp_to_nonexistent_bucket(self, files):
        foo_txt = files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://noexist-bucket-foo-bar123/foo.txt' % (foo_txt,))
        assert p.rc == 1

    def test_cp_empty_file(self, files, s3_utils, shared_bucket):
        foo_txt = files.create_file('foo.txt', contents='')
        p = aws('s3 cp %s s3://%s/' % (foo_txt, shared_bucket))
        assert p.rc == 0
        assert 'failed' not in p.stderr
        assert s3_utils.key_exists(shared_bucket, 'foo.txt')

    def test_download_non_existent_key(self):
        p = aws('s3 cp s3://jasoidfjasdjfasdofijasdf/foo.txt foo.txt')
        assert p.rc == 1
        expected_err_msg = (
            'An error occurred (404) when calling the '
            'HeadObject operation: Key "foo.txt" does not exist')
        assert expected_err_msg in p.stderr

    def test_download_encrypted_kms_object(self, s3_utils, files,
                                           shared_cross_region_bucket):
        bucket_name = shared_cross_region_bucket
        extra_args = {
            'ServerSideEncryption': 'aws:kms',
            'SSEKMSKeyId': 'alias/aws/s3'
        }
        object_name = 'foo.txt'
        contents = 'this is foo.txt'
        s3_utils.put_object(bucket_name, object_name, contents,
                            extra_args=extra_args)
        local_filename = files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/%s %s --region eu-central-1' %
                (bucket_name, object_name, local_filename))
        assert p.rc == 0
        # Assert that the file was downloaded properly.
        with open(local_filename, 'r') as f:
            assert f.read() == contents

    def test_download_empty_object(self, files, s3_utils, shared_bucket):
        object_name = 'empty-object'
        s3_utils.put_object(shared_bucket, object_name, '')
        local_filename = files.full_path('empty.txt')
        p = aws('s3 cp s3://%s/%s %s' % (
            shared_bucket, object_name, local_filename))
        assert p.rc == 0
        # Assert that the file was downloaded and has no content.
        with open(local_filename, 'r') as f:
            assert f.read() == ''

    def test_website_redirect_ignore_paramfile(self, files, s3_utils,
                                               shared_bucket):
        foo_txt = files.create_file('foo.txt', 'bar')
        website_redirect = 'http://someserver'
        p = aws('s3 cp %s s3://%s/foo.txt --website-redirect %s' %
                (foo_txt, shared_bucket, website_redirect))
        self.assert_no_errors(p)

        # Ensure that the web address is used as opposed to the contents
        # of the web address. We can check via a head object.
        response = s3_utils.head_object(shared_bucket, 'foo.txt')
        assert response['WebsiteRedirectLocation'] == website_redirect

    def test_copy_large_file_signature_v4(self, s3_utils, files,
                                          shared_cross_region_bucket):
        # Just verify that we can upload a large file to a region
        # that uses signature version 4.
        bucket_name = shared_cross_region_bucket
        num_mb = 200
        foo_txt = files.create_file('foo.txt', '')
        with open(foo_txt, 'wb') as f:
            for i in range(num_mb):
                f.write(b'a' * 1024 * 1024)

        p = aws('s3 cp %s s3://%s/ --region eu-central-1' % (
            foo_txt, bucket_name))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(bucket_name, key_name='foo.txt')

    def test_copy_metadata(self, s3_utils, files, shared_bucket):
        # Copy the same style of parsing as the CLI session. This is needed
        # For comparing expires timestamp.
        key = random_chars(6)
        filename = files.create_file(key, contents='')
        p = aws('s3 cp %s s3://%s/%s --metadata keyname=value' %
                (filename, shared_bucket, key))
        self.assert_no_errors(p)
        response = s3_utils.head_object(shared_bucket, key)
        # These values should have the metadata of the source object
        assert response['Metadata'].get('keyname') == 'value'

    def test_copy_metadata_directive(self, s3_utils, shared_bucket):
        # Copy the same style of parsing as the CLI session. This is needed
        # For comparing expires timestamp.
        original_key = '%s-a' % random_chars(6)
        new_key = '%s-b' % random_chars(6)
        metadata = {
            'ContentType': 'foo',
            'ContentDisposition': 'foo',
            'ContentEncoding': 'foo',
            'ContentLanguage': 'foo',
            'CacheControl': '90',
            'Expires': '0'
        }
        s3_utils.put_object(shared_bucket, original_key, contents='foo',
                            extra_args=metadata)
        p = aws('s3 cp s3://%s/%s s3://%s/%s' %
                (shared_bucket, original_key, shared_bucket, new_key))
        self.assert_no_errors(p)
        response = s3_utils.head_object(shared_bucket, new_key)
        # These values should have the metadata of the source object
        metadata_ref = copy.copy(metadata)
        expires_datetime = datetime.datetime.utcfromtimestamp(0)
        expires_datetime = expires_datetime.replace(tzinfo=tzutc())
        metadata_ref['Expires'] = expires_datetime
        for name, value in metadata_ref.items():
            assert response[name] == value

        # Use REPLACE to wipe out all of the metadata when copying to a new
        # key.
        new_key = '%s-c' % random_chars(6)
        p = aws('s3 cp s3://%s/%s s3://%s/%s --metadata-directive REPLACE' %
                (shared_bucket, original_key, shared_bucket, new_key))
        self.assert_no_errors(p)
        response = s3_utils.head_object(shared_bucket, new_key)
        # Make sure all of the original metadata is gone.
        for name, value in metadata_ref.items():
            assert response.get(name) != value

        # Use REPLACE to wipe out all of the metadata but include a new
        # metadata value.
        new_key = '%s-d' % random_chars(6)
        p = aws('s3 cp s3://%s/%s s3://%s/%s --metadata-directive REPLACE '
                '--content-type bar' %
                (shared_bucket, original_key, shared_bucket, new_key))
        self.assert_no_errors(p)
        response = s3_utils.head_object(shared_bucket, new_key)
        # Make sure the content type metadata is included
        assert response['ContentType'] == 'bar'
        # Make sure all of the original metadata is gone.
        for name, value in metadata_ref.items():
            assert response.get(name) != value

    def test_cp_with_request_payer(self, files, s3_utils, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/mykey --request-payer' % (
                foo_txt, shared_bucket))

        # From the S3 API, the only way to for sure know that request payer is
        # working is to set up a bucket with request payer and have another
        # account with permissions make a request to that bucket. If they
        # do not include request payer, they will get an access denied error.
        # Setting this up for an integration test would be tricky as it
        # requires having/creating another account outside of the one running
        # the integration tests. So instead at the very least we want to
        # make sure we can use the parameter, have the command run
        # successfully, and correctly upload the key to S3.
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, key_name='mykey')
        contents = s3_utils.get_key_contents(shared_bucket, key_name='mykey')
        assert contents == 'this is foo.txt'


class TestSync(BaseS3IntegrationTest):
    def test_sync_with_plus_chars_paginate(self, files, shared_bucket):
        # This test ensures pagination tokens are url decoded.
        # 1. Create > 2 files with '+' in the filename.
        # 2. Sync up to s3 while the page size is 2.
        # 3. Sync up to s3 while the page size is 2.
        # 4. Verify nothing was synced up down from s3 in step 3.
        filenames = []
        for i in range(4):
            # Create a file with a space char and a '+' char in the filename.
            # We're interested in testing the filename comparisons, not the
            # mtime comparisons so we're setting the mtime to some time
            # in the past to avoid mtime comparisons interfering with
            # test results.
            mtime = time.time() - 300
            filenames.append(
                files.create_file('foo +%06d' % i, contents='', mtime=mtime)
            )
        p = aws('s3 sync %s s3://%s/ --page-size 2' %
                (files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        time.sleep(1)
        p2 = aws('s3 sync %s s3://%s/ --page-size 2'
                 % (files.rootdir, shared_bucket))
        assert 'upload:' not in p2.stdout
        assert '' == p2.stdout

    def test_s3_to_s3_sync_with_plus_char_paginate(self, files, s3_utils,
                                                   shared_bucket,
                                                   shared_copy_bucket):
        keynames = []
        for i in range(4):
            keyname = 'foo+%d' % i
            keynames.append(keyname)
            files.create_file(keyname, contents='')

        bucket_name = shared_bucket
        bucket_name_2 = shared_copy_bucket

        p = aws('s3 sync %s s3://%s' % (files.rootdir, bucket_name))
        self.assert_no_errors(p)
        for key in keynames:
            assert s3_utils.key_exists(bucket_name, key)

        p = aws('s3 sync s3://%s/ s3://%s/ --page-size 2' %
                (bucket_name, bucket_name_2))
        self.assert_no_errors(p)
        for key in keynames:
            assert s3_utils.key_exists(bucket_name_2, key)

        p2 = aws('s3 sync s3://%s/ s3://%s/ --page-size 2' %
                 (bucket_name, bucket_name_2))
        assert 'copy:' not in p2.stdout
        assert '' == p2.stdout

    def test_sync_no_resync(self, files, s3_utils, shared_bucket):
        files.create_file('xyz123456789', contents='test1')
        files.create_file(os.path.join('xyz1', 'test'), contents='test2')
        files.create_file(os.path.join('xyz', 'test'), contents='test3')

        p = aws('s3 sync %s s3://%s' % (files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        time.sleep(2)
        assert s3_utils.key_exists(shared_bucket, 'xyz123456789')
        assert s3_utils.key_exists(shared_bucket, 'xyz1/test')
        assert s3_utils.key_exists(shared_bucket, 'xyz/test')

        p2 = aws('s3 sync %s s3://%s/' % (files.rootdir, shared_bucket))
        assert 'upload:' not in p2.stdout
        assert '' == p2.stdout

    def test_sync_to_from_s3(self, files, s3_utils, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'foo contents')
        bar_txt = files.create_file('bar.txt', 'bar contents')

        # Sync the directory and the bucket.
        p = aws('s3 sync %s s3://%s' % (files.rootdir, shared_bucket))
        self.assert_no_errors(p)

        # Ensure both files are in the bucket.
        assert s3_utils.key_exists(shared_bucket, 'foo.txt')
        assert s3_utils.key_exists(shared_bucket, 'bar.txt')

        # Sync back down.  First remote the local files.
        os.remove(foo_txt)
        os.remove(bar_txt)
        p = aws('s3 sync s3://%s %s' % (shared_bucket, files.rootdir))
        # The files should be back now.
        assert os.path.isfile(foo_txt)
        assert os.path.isfile(bar_txt)
        with open(foo_txt, 'r') as f:
            assert f.read() == 'foo contents'
        with open(bar_txt, 'r') as f:
            assert f.read() == 'bar contents'

    def test_sync_to_nonexistent_bucket(self, files):
        files.create_file('foo.txt', 'foo contents')
        files.create_file('bar.txt', 'bar contents')

        # Sync the directory and the bucket.
        p = aws('s3 sync %s s3://noexist-bkt-nme-1412' % (files.rootdir,))
        assert p.rc == 1

    def test_sync_with_empty_files(self, files, s3_utils, shared_bucket):
        files.create_file('foo.txt', 'foo contents')
        files.create_file('bar.txt', contents='')
        p = aws('s3 sync %s s3://%s/' % (files.rootdir, shared_bucket))
        assert p.rc == 0
        assert 'failed' not in p.stderr
        assert s3_utils.key_exists(shared_bucket, 'bar.txt')

    def test_sync_with_delete_option_with_same_prefix(self, files,
                                                      shared_bucket):
        # Test for issue 440 (https://github.com/aws/aws-cli/issues/440)
        # First, we need to create a directory structure that has a dir with
        # the same prefix as some of the files:
        #
        #  test/foo.txt
        #  test-123.txt
        #  test-321.txt
        #  test.txt
        # create test/foo.txt
        nested_dir = os.path.join(files.rootdir, 'test')
        os.mkdir(nested_dir)
        files.create_file(os.path.join(nested_dir, 'foo.txt'),
                          contents='foo.txt contents')
        # Then create test-123.txt, test-321.txt, test.txt.
        files.create_file('test-123.txt', 'test-123.txt contents')
        files.create_file('test-321.txt', 'test-321.txt contents')
        files.create_file('test.txt', 'test.txt contents')

        # Now sync this content up to s3.
        # Allow settling time so that we have a different time between
        # source and destination.
        time.sleep(2)
        p = aws('s3 sync %s s3://%s/' % (files.rootdir, shared_bucket))
        self.assert_no_errors(p)

        # Now here's the issue.  If we try to sync the contents down
        # with the --delete flag we should *not* see any output, the
        # sync operation should determine that nothing is different and
        # therefore do nothing.  We can just use --dryrun to show the issue.
        p = aws('s3 sync s3://%s/ %s --dryrun --delete' % (
            shared_bucket, files.rootdir))
        self.assert_no_errors(p)
        # These assertion methods will give better error messages than just
        # checking if the output is empty.
        assert 'download:' not in p.stdout
        assert 'delete:' not in p.stdout
        assert '' == p.stdout

    def test_sync_with_delete_across_sig4_regions(self, files, s3_utils,
                                                  shared_bucket,
                                                  shared_cross_region_bucket):
        src_region = 'us-west-2'
        dst_region = 'eu-central-1'

        src_bucket = shared_bucket
        dst_bucket = shared_cross_region_bucket

        src_key_name = 'hello.txt'
        files.create_file(src_key_name, contents='hello')

        p = aws('s3 sync %s s3://%s --region %s' %
                (files.rootdir, src_bucket, src_region))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(src_bucket, src_key_name)

        files.remove_all()

        dst_key_name = 'goodbye.txt'
        files.create_file(dst_key_name, contents='goodbye')

        p = aws('s3 sync %s s3://%s --region %s' %
                (files.rootdir, dst_bucket, dst_region))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(dst_bucket, dst_key_name)
        assert s3_utils.key_not_exists(dst_bucket, src_key_name)

        p = aws('s3 sync --delete s3://%s s3://%s '
                '--source-region %s --region %s' %
                (src_bucket, dst_bucket, src_region, dst_region))
        self.assert_no_errors(p)

        assert s3_utils.key_exists(src_bucket, src_key_name)
        assert s3_utils.key_exists(dst_bucket, src_key_name)
        assert s3_utils.key_not_exists(src_bucket, dst_key_name)
        assert s3_utils.key_not_exists(dst_bucket, dst_key_name)

    def test_sync_delete_locally(self, files, s3_utils, shared_bucket):
        file_to_delete = files.create_file(
            'foo.txt', contents='foo contents')
        s3_utils.put_object(shared_bucket, 'bar.txt', contents='bar contents')

        p = aws('s3 sync s3://%s/ %s --delete' % (
            shared_bucket, files.rootdir))
        self.assert_no_errors(p)

        # Make sure the uploaded file got downloaded and the previously
        # existing local file got deleted
        assert os.path.exists(
            os.path.join(files.rootdir, 'bar.txt'))
        assert not os.path.exists(file_to_delete)


class TestSourceRegion(BaseS3IntegrationTest):
    def test_cp_region(self, files, s3_utils, shared_non_dns_compatible_bucket,
                       shared_non_dns_compatible_us_east_1_bucket):
        src_region = 'us-west-2'
        src_bucket = shared_non_dns_compatible_bucket
        dest_region = 'us-east-1'
        dest_bucket = shared_non_dns_compatible_us_east_1_bucket
        files.create_file('foo.txt', 'foo')
        p = aws('s3 sync %s s3://%s/ --region %s' %
                (files.rootdir, src_bucket, src_region))
        self.assert_no_errors(p)
        p2 = aws('s3 cp s3://%s/ s3://%s/ --region %s --source-region %s '
                 '--recursive' %
                 (src_bucket, dest_bucket, dest_region,
                  src_region))
        assert p2.rc == 0, p2.stdout
        assert s3_utils.key_exists(dest_bucket, 'foo.txt')

    def test_sync_region(self, files, s3_utils,
                         shared_non_dns_compatible_bucket,
                         shared_non_dns_compatible_us_east_1_bucket):
        src_region = 'us-west-2'
        src_bucket = shared_non_dns_compatible_bucket
        dest_region = 'us-east-1'
        dest_bucket = shared_non_dns_compatible_us_east_1_bucket
        files.create_file('foo.txt', 'foo')
        p = aws('s3 sync %s s3://%s/ --region %s' %
                (files.rootdir, src_bucket, src_region))
        self.assert_no_errors(p)
        p2 = aws('s3 sync s3://%s/ s3://%s/ --region %s --source-region %s ' %
                 (src_bucket, dest_bucket, dest_region,
                  src_region))
        assert p2.rc == 0, p2.stdout
        assert s3_utils.key_exists(dest_bucket, 'foo.txt')

    def test_mv_region(self, files, s3_utils, shared_non_dns_compatible_bucket,
                       shared_non_dns_compatible_us_east_1_bucket):
        src_region = 'us-west-2'
        src_bucket = shared_non_dns_compatible_bucket
        dest_region = 'us-east-1'
        dest_bucket = shared_non_dns_compatible_us_east_1_bucket
        files.create_file('foo.txt', 'foo')
        p = aws('s3 sync %s s3://%s/ --region %s' %
                (files.rootdir, src_bucket, src_region))
        self.assert_no_errors(p)
        p2 = aws('s3 mv s3://%s/ s3://%s/ --region %s --source-region %s '
                 '--recursive' %
                 (src_bucket, dest_bucket, dest_region,
                  src_region))
        assert p2.rc == 0, p2.stdout
        assert s3_utils.key_exists(dest_bucket, 'foo.txt')
        assert s3_utils.key_not_exists(src_bucket, 'foo.txt')

    def test_mv_large_file_region(self, files, s3_utils,
                                  shared_non_dns_compatible_bucket,
                                  shared_non_dns_compatible_us_east_1_bucket):
        src_region = 'us-west-2'
        src_bucket = shared_non_dns_compatible_bucket
        dest_region = 'us-east-1'
        dest_bucket = shared_non_dns_compatible_us_east_1_bucket
        foo_txt = files.create_file('foo.txt', 'a' * 1024 * 1024 * 10)
        p = aws('s3 cp %s s3://%s/foo.txt --region %s' %
                (foo_txt, src_bucket, src_region))
        self.assert_no_errors(p)

        p2 = aws(
            's3 mv s3://%s/foo.txt s3://%s/ --region %s --source-region %s ' %
            (src_bucket, dest_bucket, dest_region,
             src_region)
        )
        self.assert_no_errors(p2)
        assert s3_utils.key_exists(dest_bucket, 'foo.txt')
        assert s3_utils.key_not_exists(src_bucket, 'foo.txt')


class TestWarnings(BaseS3IntegrationTest):
    def test_no_exist(self, files, shared_bucket):
        filename = os.path.join(files.rootdir, "no-exists-file")
        p = aws('s3 cp %s s3://%s/' % (filename, shared_bucket))
        # If the local path provided by the user is nonexistant for an
        # upload, this should error out.
        assert p.rc == 255, p.stderr
        assert f'The user-provided path {filename} does not exist.' in p.stderr

    @skip_if_windows('Read permissions tests only supported on mac/linux')
    def test_no_read_access(self, files, shared_bucket):
        if os.geteuid() == 0:
            pytest.skip('Cannot completely remove read access as root user.')
        files.create_file('foo.txt', 'foo')
        filename = os.path.join(files.rootdir, 'foo.txt')
        permissions = stat.S_IMODE(os.stat(filename).st_mode)
        # Remove read permissions
        permissions = permissions ^ stat.S_IREAD
        os.chmod(filename, permissions)
        p = aws('s3 cp %s s3://%s/' % (filename, shared_bucket))
        assert p.rc == 2, p.stderr
        warning_msg = (
            f'warning: Skipping file {filename}. File/Directory is '
            f'not readable.'
        )
        assert warning_msg in p.stderr

    @skip_if_windows('Special files only supported on mac/linux')
    def test_is_special_file(self, files, shared_bucket):
        file_path = os.path.join(files.rootdir, 'foo')
        # Use socket for special file.
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(file_path)
        p = aws('s3 cp %s s3://%s/' % (file_path, shared_bucket))
        assert p.rc == 2, p.stderr
        warning_msg = (
            f"warning: Skipping file {file_path}. File is character "
            f"special device, block special device, FIFO, or "
            f"socket."
        )
        assert warning_msg in p.stderr


class TestUnableToWriteToFile(BaseS3IntegrationTest):
    @skip_if_windows('Write permissions tests only supported on mac/linux')
    def test_no_write_access_small_file(self, files, s3_utils, shared_bucket):
        if os.geteuid() == 0:
            pytest.skip('Cannot completely remove write access as root user.')
        os.chmod(files.rootdir, 0o444)
        s3_utils.put_object(shared_bucket, 'foo.txt',
                            contents='Hello world')
        p = aws('s3 cp s3://%s/foo.txt %s' % (
            shared_bucket, os.path.join(files.rootdir, 'foo.txt')))
        assert p.rc == 1
        assert 'download failed' in p.stderr

    @skip_if_windows('Write permissions tests only supported on mac/linux')
    def test_no_write_access_large_file(self, files, s3_utils, shared_bucket):
        if os.geteuid() == 0:
            pytest.skip('Cannot completely remove write access as root user.')
        # We have to use a file like object because using a string
        # would result in the header + body sent as a single packet
        # which effectively disables the expect 100 continue logic.
        # This will result in a test error because we won't follow
        # the temporary redirect for the newly created bucket.
        contents = six.BytesIO(b'a' * 10 * 1024 * 1024)
        s3_utils.put_object(shared_bucket, 'foo.txt',
                            contents=contents)
        os.chmod(files.rootdir, 0o444)
        p = aws('s3 cp s3://%s/foo.txt %s' % (
            shared_bucket, os.path.join(files.rootdir, 'foo.txt')))
        assert p.rc == 1
        assert 'download failed' in p.stderr


@skip_if_windows('Symlink tests only supported on mac/linux')
class TestSymlinks(BaseS3IntegrationTest):
    """
    This class test the ability to follow or not follow symlinks.
    """
    def test_no_follow_symlinks(self, files, s3_utils, symlink_files,
                                shared_bucket):
        p = aws('s3 sync %s s3://%s/ --no-follow-symlinks' % (
            files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        assert s3_utils.key_not_exists(shared_bucket, 'a-goodsymlink')
        assert s3_utils.key_not_exists(shared_bucket, 'b-badsymlink')
        assert s3_utils.key_not_exists(shared_bucket, 'c-goodsymlink/foo.txt')
        contents = s3_utils.get_key_contents(
            shared_bucket, 'realfiles/foo.txt')
        assert contents == 'foo.txt contents'

    def test_follow_symlinks(self, files, s3_utils, symlink_files,
                             shared_bucket):
        # Get rid of the bad symlink first.
        os.remove(os.path.join(files.rootdir, 'b-badsymlink'))
        p = aws('s3 sync %s s3://%s/ --follow-symlinks' %
                (files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        contents = s3_utils.get_key_contents(shared_bucket, 'a-goodsymlink')
        assert contents == 'foo.txt contents'
        assert s3_utils.key_not_exists(shared_bucket, 'b-badsymlink')
        contents = s3_utils.get_key_contents(
            shared_bucket, 'c-goodsymlink/foo.txt')
        assert contents == 'foo.txt contents'
        contents = s3_utils.get_key_contents(
            shared_bucket, 'realfiles/foo.txt')
        assert contents == 'foo.txt contents'

    def test_follow_symlinks_default(self, files, s3_utils, symlink_files,
                                     shared_bucket):
        # Get rid of the bad symlink first.
        os.remove(os.path.join(files.rootdir, 'b-badsymlink'))
        p = aws('s3 sync %s s3://%s/' %
                (files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        contents = s3_utils.get_key_contents(shared_bucket, 'a-goodsymlink')
        assert contents == 'foo.txt contents'
        assert s3_utils.key_not_exists(shared_bucket, 'b-badsymlink')
        contents = s3_utils.get_key_contents(
            shared_bucket, 'c-goodsymlink/foo.txt')
        assert contents == 'foo.txt contents'
        contents = s3_utils.get_key_contents(
            shared_bucket, 'realfiles/foo.txt')
        assert contents == 'foo.txt contents'

    def test_bad_symlink(self, files, symlink_files, shared_bucket):
        p = aws('s3 sync %s s3://%s/' % (files.rootdir, shared_bucket))
        assert p.rc == 2, p.stderr
        warning_msg = (
            'warning: Skipping file %s. File does not exist.' %
            os.path.join(files.rootdir, 'b-badsymlink')
        )
        assert warning_msg in p.stderr


class TestUnicode(BaseS3IntegrationTest):
    """
    The purpose of these tests are to ensure that the commands can handle
    unicode characters in both keyname and from those generated for both
    uploading and downloading files.
    """
    def test_cp(self, files, shared_bucket):
        local_example1_txt = files.create_file(
            u'\u00e9xample.txt', 'example1 contents')
        s3_example1_txt = 's3://%s/%s' % (shared_bucket,
                                          os.path.basename(local_example1_txt))
        local_example2_txt = files.full_path(u'\u00e9xample2.txt')

        p = aws('s3 cp %s %s' % (local_example1_txt, s3_example1_txt))
        self.assert_no_errors(p)

        # Download the file to the second example2.txt filename.
        p = aws('s3 cp %s %s --quiet' % (s3_example1_txt, local_example2_txt))
        self.assert_no_errors(p)
        with open(local_example2_txt, 'rb') as f:
            assert f.read() == b'example1 contents'

    def test_recursive_cp(self, files, shared_bucket):
        local_example1_txt = files.create_file(u'\u00e9xample.txt',
                                               'example1 contents')
        local_example2_txt = files.create_file(u'\u00e9xample2.txt',
                                               'example2 contents')
        p = aws('s3 cp %s s3://%s --recursive --quiet' % (
            files.rootdir, shared_bucket))
        self.assert_no_errors(p)

        os.remove(local_example1_txt)
        os.remove(local_example2_txt)

        p = aws('s3 cp s3://%s %s --recursive --quiet' % (
            shared_bucket, files.rootdir))
        self.assert_no_errors(p)
        assert open(local_example1_txt).read() == 'example1 contents'
        assert open(local_example2_txt).read() == 'example2 contents'


class TestLs(BaseS3IntegrationTest):
    """
    This tests using the ``ls`` command.
    """

    def test_ls_bucket(self):
        p = aws('s3 ls')
        self.assert_no_errors(p)

    def test_ls_with_no_env_vars(self):
        # By default, the aws() function injects
        # an AWS_DEFAULT_REGION into the env var of the
        # process.  We're verifying that a region does *not*
        # need to be set anywhere.  If we provide our
        # own environ dict, then the aws() function won't
        # inject a region.
        env = os.environ.copy()
        p = aws('s3 ls', env_vars=env)
        self.assert_no_errors(p)

    def test_ls_bucket_with_s3_prefix(self):
        p = aws('s3 ls s3://')
        self.assert_no_errors(p)

    def test_ls_non_existent_bucket(self):
        p = aws('s3 ls s3://foobara99842u4wbts829381')
        assert p.rc == 254
        error_msg = (
            'An error occurred (NoSuchBucket) when calling the '
            'ListObjectsV2 operation: The specified bucket does not exist'
        )
        assert error_msg in p.stderr
        # There should be no stdout if we can't find the bucket.
        assert p.stdout == ''

    def test_ls_with_prefix(self, s3_utils, shared_bucket):
        s3_utils.put_object(shared_bucket, 'foo.txt', 'contents')
        s3_utils.put_object(shared_bucket, 'foo', 'contents')
        s3_utils.put_object(shared_bucket, 'bar.txt', 'contents')
        s3_utils.put_object(shared_bucket, 'subdir/foo.txt', 'contents')
        p = aws('s3 ls s3://%s' % shared_bucket)
        assert 'PRE subdir/' in p.stdout
        assert '8 foo.txt' in p.stdout
        assert '8 foo' in p.stdout
        assert '8 bar.txt' in p.stdout

    def test_ls_recursive(self, s3_utils, shared_bucket):
        s3_utils.put_object(shared_bucket, 'foo.txt', 'contents')
        s3_utils.put_object(shared_bucket, 'foo', 'contents')
        s3_utils.put_object(shared_bucket, 'bar.txt', 'contents')
        s3_utils.put_object(shared_bucket, 'subdir/foo.txt', 'contents')
        p = aws('s3 ls s3://%s --recursive' % shared_bucket)
        assert '8 foo.txt' in p.stdout
        assert '8 foo' in p.stdout
        assert '8 bar.txt' in p.stdout
        assert '8 subdir/foo.txt' in p.stdout

    def test_ls_without_prefix(self, s3_utils, shared_bucket):
        # The ls command does not require an s3:// prefix,
        # we're always listing s3 contents.
        s3_utils.put_object(shared_bucket, 'foo.txt', 'contents')
        p = aws('s3 ls %s' % shared_bucket)
        assert p.rc == 0
        assert 'foo.txt' in p.stdout

    def test_only_prefix(self, s3_utils, shared_bucket):
        s3_utils.put_object(shared_bucket, 'temp/foo.txt', 'contents')
        p = aws('s3 ls s3://%s/temp/foo.txt' % shared_bucket)
        assert p.rc == 0
        assert 'foo.txt' in p.stdout

    def test_ls_empty_bucket(self, shared_bucket):
        p = aws('s3 ls %s' % shared_bucket)
        # There should not be an error thrown for checking the contents of
        # an empty bucket because no key was specified.
        assert p.rc == 0

    def test_ls_fail(self, shared_bucket):
        p = aws('s3 ls s3://%s/foo' % shared_bucket)
        assert p.rc == 1

    def test_ls_fail_recursive(self, shared_bucket):
        p = aws('s3 ls s3://%s/bar --recursive' % shared_bucket)
        assert p.rc == 1


class TestMbRb(BaseS3IntegrationTest):
    """
    Tests primarily using ``rb`` and ``mb`` command.
    """
    def test_mb_rb(self, s3_utils):
        bucket_name = random_bucket_name()
        p = aws('s3 mb s3://%s' % bucket_name)
        self.assert_no_errors(p)

        # Give the bucket time to form.
        time.sleep(1)
        response = s3_utils.list_buckets()
        assert bucket_name in [b['Name'] for b in response]

        p = aws('s3 rb s3://%s' % bucket_name)
        self.assert_no_errors(p)

    def test_fail_mb_rb(self):
        # Choose a bucket name that already exists.
        p = aws('s3 mb s3://mybucket')
        assert "BucketAlreadyExists" in p.stderr
        assert p.rc == 1


class TestOutput(BaseS3IntegrationTest):
    """
    This ensures that arguments that affect output i.e. ``--quiet`` and
    ``--only-show-errors`` behave as expected.
    """
    def test_normal_output(self, files, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/' % (foo_txt, shared_bucket))
        assert p.rc == 0
        # Check that there were no errors and that parts of the expected
        # progress message are written to stdout.
        self.assert_no_errors(p)
        assert 'upload' in p.stdout
        assert 's3://%s/foo.txt' % shared_bucket in p.stdout

    def test_normal_output_quiet(self, files, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --quiet' % (foo_txt, shared_bucket))
        assert p.rc == 0
        # Check that nothing was printed to stdout.
        assert '' == p.stdout

    def test_normal_output_only_show_errors(self, files, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --only-show-errors' % (foo_txt,
                                                          shared_bucket))
        assert p.rc == 0
        # Check that nothing was printed to stdout.
        assert '' == p.stdout

    def test_normal_output_no_progress(self, files, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --no-progress' % (foo_txt, shared_bucket))
        assert p.rc == 0
        # Ensure success message was printed
        assert 'upload' in p.stdout
        assert 's3://%s/foo.txt' % shared_bucket in p.stdout
        assert 'Completed ' not in p.stdout
        assert 'calculating' not in p.stdout

    def test_error_output(self, files):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://non-existant-bucket/' % foo_txt)
        # Check that there were errors and that the error was print to stderr.
        assert p.rc == 1
        assert 'upload failed' in p.stderr

    def test_error_ouput_quiet(self, files):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://non-existant-bucket/ --quiet' % foo_txt)
        # Check that there were errors and that the error was not
        # print to stderr.
        assert p.rc == 1
        assert '' == p.stderr

    def test_error_output_only_show_errors(self, files):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://non-existant-bucket/ --only-show-errors'
                % foo_txt)
        # Check that there were errors and that the error was print to stderr.
        assert p.rc == 1
        assert 'upload failed' in p.stderr

    def test_error_and_success_output_only_show_errors(self, files, s3_utils,
                                                       shared_bucket):
        # Create one file.
        files.create_file('f', 'foo contents')

        # Create another file that has a slightly longer name than the first.
        files.create_file('bar.txt', 'bar contents')

        # Create a prefix that will cause the second created file to have a key
        # longer than 1024 bytes which is not allowed in s3.
        long_prefix = 'd' * 1022

        p = aws('s3 cp %s s3://%s/%s/ --only-show-errors --recursive'
                % (files.rootdir, shared_bucket, long_prefix))

        # Check that there was at least one error.
        assert p.rc == 1

        # Check that there was nothing written to stdout for successful upload.
        assert '' == p.stdout

        # Check that the failed message showed up in stderr.
        assert 'upload failed' in p.stderr

        # Ensure the expected successful key exists in the bucket.
        assert s3_utils.key_exists(shared_bucket, long_prefix + '/f')


class TestDryrun(BaseS3IntegrationTest):
    """
    This ensures that dryrun works.
    """
    def test_dryrun(self, files, s3_utils, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --dryrun' % (foo_txt, shared_bucket))
        assert p.rc == 0
        self.assert_no_errors(p)
        assert s3_utils.key_not_exists(shared_bucket, 'foo.txt')

    def test_dryrun_large_files(self, files, s3_utils, shared_bucket):
        foo_txt = files.create_file('foo.txt', 'a' * 1024 * 1024 * 10)

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --dryrun' % (foo_txt, shared_bucket))
        assert p.rc == 0
        self.assert_no_errors(p)
        assert s3_utils.key_not_exists(shared_bucket, 'foo.txt'), (
            "The key 'foo.txt' exists in S3. It looks like the --dryrun "
            "argument was not obeyed."
        )

    def test_dryrun_download_large_file(self, files, s3_utils, shared_bucket):
        full_path = files.create_file('largefile', 'a' * 1024 * 1024 * 10)
        with open(full_path, 'rb') as body:
            s3_utils.put_object(shared_bucket, 'foo.txt', body)

        foo_txt = files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/foo.txt %s --dryrun' % (shared_bucket, foo_txt))
        assert p.rc == 0
        self.assert_no_errors(p)
        assert not os.path.exists(foo_txt), (
            "The file 'foo.txt' exists locally. It looks like the --dryrun "
            "argument was not obeyed."
        )


@skip_if_windows('Memory tests only supported on mac/linux')
class TestMemoryUtilization(BaseS3IntegrationTest):
    # These tests verify the memory utilization and growth are what we expect.
    num_threads = DEFAULTS['max_concurrent_requests']
    chunk_size = DEFAULTS['multipart_chunksize']
    expected_memory_usage = num_threads * chunk_size
    # margin for things like python VM overhead, botocore service
    # objects, etc.  1.5 is really generous, perhaps over time this can be
    # lowered.
    runtime_margin = 1.5
    max_mem_allowed = runtime_margin * expected_memory_usage

    def assert_max_memory_used(self, process, max_mem_allowed, full_command):
        peak_memory = max(process.memory_usage)
        if peak_memory > max_mem_allowed:
            failure_message = (
                'Exceeded max memory allowed (%s MB) for command '
                '"%s": %s MB' % (self.max_mem_allowed / 1024.0 / 1024.0,
                                 full_command,
                                 peak_memory / 1024.0 / 1024.0))
            self.fail(failure_message)

    def test_transfer_single_large_file(self, files, shared_bucket):
        # 40MB will force a multipart upload.
        file_contents = 'abcdabcd' * (1024 * 1024 * 10)
        foo_txt = files.create_file('foo.txt', file_contents)
        full_command = 's3 mv %s s3://%s/foo.txt' % (foo_txt, shared_bucket)
        p = aws(full_command, collect_memory=True)
        self.assert_no_errors(p)
        self.assert_max_memory_used(p, self.max_mem_allowed, full_command)

        # Verify downloading it back down obeys memory utilization.
        download_full_command = 's3 mv s3://%s/foo.txt %s' % (
            shared_bucket, foo_txt)
        p = aws(download_full_command, collect_memory=True)
        self.assert_no_errors(p)
        self.assert_max_memory_used(p, self.max_mem_allowed,
                                    download_full_command)

    # Some versions of RHEL allocate memory in a way where free'd memory isn't
    # given back to the OS.  We haven't seen behavior as bad as RHEL's to the
    # point where this test fails on other distros, so for now we're disabling
    # the test on RHEL until we come up with a better way to collect
    # memory usage.
    @unittest.skipIf(_running_on_rhel(),
                     'Streaming memory tests no supported on RHEL.')
    def test_stream_large_file(self, files, shared_bucket):
        """
        This tests to ensure that streaming files for both uploads and
        downloads do not use too much memory.  Note that streaming uploads
        will use slightly more memory than usual but should not put the
        entire file into memory.
        """
        # Create a 200 MB file that will be streamed
        num_mb = 200
        foo_txt = files.create_file('foo.txt', '')
        with open(foo_txt, 'wb') as f:
            for i in range(num_mb):
                f.write(b'a' * 1024 * 1024)

        # The current memory threshold is set at about the peak amount for
        # performing a streaming upload of a file larger than 100 MB. So
        # this maximum needs to be bumped up.  The maximum memory allowance
        # is increased by two chunksizes because that is the maximum
        # amount of chunks that will be queued while not being operated on
        # by a thread when performing a streaming multipart upload.
        max_mem_allowed = self.max_mem_allowed + 2 * self.chunk_size

        full_command = 's3 cp - s3://%s/foo.txt' % shared_bucket
        with open(foo_txt, 'rb') as f:
            p = aws(full_command, input_file=f, collect_memory=True)
            self.assert_no_errors(p)
            self.assert_max_memory_used(p, max_mem_allowed, full_command)

        # Now perform a streaming download of the file.
        full_command = 's3 cp s3://%s/foo.txt - > %s' % (
            shared_bucket, foo_txt)
        p = aws(full_command, collect_memory=True)
        self.assert_no_errors(p)
        # Use the usual bar for maximum memory usage since a streaming
        # download's memory usage should be comparable to non-streaming
        # transfers.
        self.assert_max_memory_used(p, self.max_mem_allowed, full_command)


class TestWebsiteConfiguration(BaseS3IntegrationTest):
    def test_create_website_index_configuration(self, s3_utils, shared_bucket):
        # Supply only --index-document argument.
        full_command = 's3 website %s --index-document index.html' % (
            shared_bucket)
        p = aws(full_command)
        assert p.rc == 0
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        parsed = s3_utils.get_bucket_website(shared_bucket)
        assert parsed['IndexDocument']['Suffix'] == 'index.html'
        assert 'ErrorDocument' not in parsed
        assert 'RoutingRules' not in parsed
        assert 'RedirectAllRequestsTo' not in parsed

    def test_create_website_index_and_error_configuration(self, s3_utils,
                                                          shared_bucket):
        # Supply both --index-document and --error-document arguments.
        p = aws('s3 website %s --index-document index.html '
                '--error-document error.html' % shared_bucket)
        assert p.rc == 0
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        parsed = s3_utils.get_bucket_website(shared_bucket)
        assert parsed['IndexDocument']['Suffix'] == 'index.html'
        assert parsed['ErrorDocument']['Key'] == 'error.html'
        assert 'RoutingRules' not in parsed
        assert 'RedirectAllRequestsTo' not in parsed


class TestIncludeExcludeFilters(BaseS3IntegrationTest):
    def assert_no_files_would_be_uploaded(self, p):
        self.assert_no_errors(p)
        # There should be no output.
        assert p.stdout == ''
        assert p.stderr == ''

    def test_basic_exclude_filter_for_single_file(self, files):
        full_path = files.create_file('foo.txt', 'this is foo.txt')
        # With no exclude we should upload the file.
        p = aws('s3 cp %s s3://random-bucket-name/ --dryrun' % full_path)
        self.assert_no_errors(p)
        assert '(dryrun) upload:' in p.stdout

        p2 = aws("s3 cp %s s3://random-bucket-name/ --dryrun --exclude '*'"
                 % full_path)
        self.assert_no_files_would_be_uploaded(p2)

    def test_explicitly_exclude_single_file(self, files):
        full_path = files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://random-bucket-name/'
                ' --dryrun --exclude foo.txt'
                % full_path)
        self.assert_no_files_would_be_uploaded(p)

    def test_cwd_doesnt_matter(self, files):
        full_path = files.create_file('foo.txt', 'this is foo.txt')
        with tempfile.TemporaryDirectory() as tempdir:
            with cd(tempdir):
                p = aws(
                    "s3 cp %s s3://random-bucket-name/ --dryrun --exclude '*'"
                    % full_path
                )
        self.assert_no_files_would_be_uploaded(p)

    def test_recursive_exclude(self, files):
        # create test/foo.txt
        nested_dir = os.path.join(files.rootdir, 'test')
        os.mkdir(nested_dir)
        files.create_file(os.path.join(nested_dir, 'foo.txt'),
                          contents='foo.txt contents')
        # Then create test-123.txt, test-321.txt, test.txt.
        files.create_file('test-123.txt', 'test-123.txt contents')
        files.create_file('test-321.txt', 'test-321.txt contents')
        files.create_file('test.txt', 'test.txt contents')
        # An --exclude test* should exclude everything here.
        p = aws("s3 cp %s s3://random-bucket-name/ --dryrun --exclude '*' "
                "--recursive" % files.rootdir)
        self.assert_no_files_would_be_uploaded(p)

        # We can include the test directory though.
        p = aws("s3 cp %s s3://random-bucket-name/ --dryrun "
                "--exclude '*' --include 'test/*' --recursive"
                % files.rootdir)
        self.assert_no_errors(p)
        assert re.search(r'\(dryrun\) upload:.*test/foo.txt.*', p.stdout)

    def test_s3_filtering(self, s3_utils, shared_bucket):
        # Should behave the same as local file filtering.
        s3_utils.put_object(shared_bucket, key_name='foo.txt')
        s3_utils.put_object(shared_bucket, key_name='bar.txt')
        s3_utils.put_object(shared_bucket, key_name='baz.jpg')
        p = aws("s3 rm s3://%s/ --dryrun --exclude '*' --recursive"
                % shared_bucket)
        self.assert_no_files_would_be_uploaded(p)

        p = aws(
            "s3 rm s3://%s/ --dryrun --exclude '*.jpg' --exclude '*.txt' "
            "--recursive" % shared_bucket)
        self.assert_no_files_would_be_uploaded(p)

        p = aws("s3 rm s3://%s/ --dryrun --exclude '*.txt' --recursive"
                % shared_bucket)
        self.assert_no_errors(p)
        assert re.search(r'\(dryrun\) delete:.*baz.jpg.*', p.stdout)
        assert 'bar.txt' not in p.stdout
        assert 'foo.txt' not in p.stdout

    def test_exclude_filter_with_delete(self, files, s3_utils, shared_bucket):
        # Test for: https://github.com/aws/aws-cli/issues/778
        files.create_file('foo.txt', 'contents')
        second = files.create_file('bar.py', 'contents')
        p = aws("s3 sync %s s3://%s/" % (files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, key_name='bar.py')
        os.remove(second)
        # We now have the same state as specified in the bug:
        # local           remote
        # -----           ------
        #
        # foo.txt         foo.txt
        #                 bar.py
        #
        # If we now run --exclude '*.py' --delete, then we should *not*
        # delete bar.py and the remote side.
        p = aws("s3 sync %s s3://%s/ --exclude '*.py' --delete" % (
            files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, key_name='bar.py'), (
            "The --delete flag was not applied to the receiving "
            "end, the 'bar.py' file was deleted even though it"
            " was excluded."
        )

    def test_exclude_filter_with_relative_path(self, files, s3_utils,
                                               shared_bucket):
        # Same test as test_exclude_filter_with_delete, except we don't
        # use an absolute path on the source dir.
        files.create_file('foo.txt', 'contents')
        second = files.create_file('bar.py', 'contents')
        p = aws("s3 sync %s s3://%s/" % (files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, key_name='bar.py')
        os.remove(second)
        cwd = os.getcwd()
        try:
            os.chdir(files.rootdir)
            # Note how we're using "." for the source directory.
            p = aws("s3 sync . s3://%s/ --exclude '*.py' --delete"
                    % shared_bucket)
        finally:
            os.chdir(cwd)
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, key_name='bar.py'), (
            "The --delete flag was not applied to the receiving "
            "end, the 'bar.py' file was deleted even though it"
            " was excluded."
        )

    def test_filter_s3_with_prefix(self, files, s3_utils, shared_bucket):
        s3_utils.put_object(shared_bucket, key_name='temp/test')
        p = aws('s3 cp s3://%s/temp/ %s --recursive --exclude test --dryrun'
                % (shared_bucket, files.rootdir))
        self.assert_no_files_would_be_uploaded(p)

    def test_filter_no_resync(self, files, s3_utils, shared_bucket):
        # This specifically tests for the issue described here:
        # https://github.com/aws/aws-cli/issues/794
        dir_name = os.path.join(files.rootdir, 'temp')
        files.create_file(os.path.join(dir_name, 'test.txt'),
                          contents='foo')
        # Sync a local directory to an s3 prefix.
        p = aws('s3 sync %s s3://%s/temp' % (dir_name, shared_bucket))
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, key_name='temp/test.txt')

        # Nothing should be synced down if filters are used.
        p = aws("s3 sync s3://%s/temp %s --exclude '*' --include test.txt"
                % (shared_bucket, dir_name))
        self.assert_no_files_would_be_uploaded(p)


class TestFileWithSpaces(BaseS3IntegrationTest):
    def test_upload_download_file_with_spaces(self, files, shared_bucket):
        filename = files.create_file('with space.txt', 'contents')
        p = aws('s3 cp %s s3://%s/ --recursive' % (files.rootdir,
                                                   shared_bucket))
        self.assert_no_errors(p)
        os.remove(filename)
        # Now download the file back down locally.
        p = aws('s3 cp s3://%s/ %s --recursive' % (shared_bucket,
                                                   files.rootdir))
        self.assert_no_errors(p)
        assert os.listdir(files.rootdir)[0] == 'with space.txt'

    def test_sync_file_with_spaces(self, files, shared_bucket):
        files.create_file('with space.txt',
                          'contents', mtime=time.time() - 300)
        p = aws('s3 sync %s s3://%s/' % (files.rootdir,
                                         shared_bucket))
        self.assert_no_errors(p)
        time.sleep(1)
        # Now syncing again should *not* trigger any uploads (i.e we should
        # get nothing on stdout).
        p2 = aws('s3 sync %s s3://%s/' % (files.rootdir,
                                          shared_bucket))
        assert p2.stdout == ''
        assert p2.stderr == ''
        assert p2.rc == 0


class TestStreams(BaseS3IntegrationTest):
    def test_upload(self, s3_utils, shared_bucket):
        """
        This tests uploading a small stream from stdin.
        """
        p = aws('s3 cp - s3://%s/stream' % shared_bucket,
                input_data=b'This is a test')
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, 'stream')
        contents = s3_utils.get_key_contents(shared_bucket, 'stream')
        assert contents == 'This is a test'

    def test_unicode_upload(self, s3_utils, shared_bucket):
        """
        This tests being able to upload unicode from stdin.
        """
        unicode_str = u'\u00e9 This is a test'
        byte_str = unicode_str.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % shared_bucket,
                input_data=byte_str)
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, 'stream')
        contents = s3_utils.get_key_contents(shared_bucket, 'stream')
        assert contents == unicode_str

    def test_multipart_upload(self, s3_utils, shared_bucket):
        """
        This tests the ability to multipart upload streams from stdin.
        The data has some unicode in it to avoid having to do a separate
        multipart upload test just for unicode.
        """
        data = u'\u00e9bcd' * (1024 * 1024 * 10)
        data_encoded = data.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % shared_bucket,
                input_data=data_encoded)
        self.assert_no_errors(p)
        assert s3_utils.key_exists(shared_bucket, 'stream')
        contents = s3_utils.get_key_contents(shared_bucket, 'stream')
        assert contents == data

    def test_download(self, shared_bucket):
        """
        This tests downloading a small stream from stdout.
        """
        p = aws('s3 cp - s3://%s/stream' % shared_bucket,
                input_data=b'This is a test')
        self.assert_no_errors(p)

        p = aws('s3 cp s3://%s/stream -' % shared_bucket)
        self.assert_no_errors(p)
        assert p.stdout == 'This is a test'

    def test_unicode_download(self, shared_bucket):
        """
        This tests downloading a small unicode stream from stdout.
        """
        data = u'\u00e9 This is a test'
        data_encoded = data.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % shared_bucket,
                input_data=data_encoded)
        self.assert_no_errors(p)

        # Downloading the unicode stream to standard out.
        p = aws('s3 cp s3://%s/stream -' % shared_bucket)
        self.assert_no_errors(p)
        assert p.stdout == data_encoded.decode(get_stdout_encoding())

    def test_multipart_download(self, shared_bucket):
        """
        This tests the ability to multipart download streams to stdout.
        The data has some unicode in it to avoid having to do a seperate
        multipart download test just for unicode.
        """
        # First lets upload some data via streaming since
        # its faster and we do not have to write to a file!
        data = u'\u00e9bcd' * (1024 * 1024 * 10)
        data_encoded = data.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % shared_bucket,
                input_data=data_encoded)

        # Download the unicode stream to standard out.
        p = aws('s3 cp s3://%s/stream -' % shared_bucket)
        self.assert_no_errors(p)
        assert p.stdout == data_encoded.decode(get_stdout_encoding())


class TestLSWithProfile(BaseS3IntegrationTest):
    def test_can_ls_with_profile(self, config_with_profile):
        env_vars = os.environ.copy()
        env_vars['AWS_CONFIG_FILE'] = config_with_profile
        p = aws('s3 ls s3:// --profile testprofile', env_vars=env_vars)
        self.assert_no_errors(p)


class TestNoSignRequests(BaseS3IntegrationTest):
    def test_no_sign_request(self, files, s3_utils, shared_bucket, region):
        s3_utils.put_object(shared_bucket, 'foo', contents='bar',
                            extra_args={'ACL': 'public-read-write'})
        env_vars = os.environ.copy()
        env_vars['AWS_ACCESS_KEY_ID'] = 'foo'
        env_vars['AWS_SECRET_ACCESS_KEY'] = 'bar'
        p = aws('s3 cp s3://%s/foo %s/ --region %s' %
                (shared_bucket, files.rootdir, region),
                env_vars=env_vars)
        # Should have credential issues
        assert p.rc == 1

        p = aws('s3 cp s3://%s/foo %s/ --region %s --no-sign-request' %
                (shared_bucket, files.rootdir, region),
                env_vars=env_vars)
        # Should be able to download the file when not signing the request.
        self.assert_no_errors(p)


class TestHonorsEndpointUrl(BaseS3IntegrationTest):
    def test_verify_endpoint_url_is_used(self):
        # We're going to verify this indirectly by looking at the
        # debug logs.  The endpoint url we specify should be in the
        # debug logs, and the endpoint url that botocore would have
        # used if we didn't provide the endpoint-url should not
        # be in the debug logs.  The other alternative is to actually
        # watch what connections are made in the process, which is not
        # easy.
        p = aws('s3 ls s3://dnscompat/ '
                '--endpoint-url http://localhost:51515 '
                '--debug')
        debug_logs = p.stderr
        original_hostname = 'dnscompat.s3.amazonaws.com'
        expected = 'localhost'
        assert original_hostname not in debug_logs, (
            '--endpoint-url is being ignored in s3 commands.')
        assert expected in debug_logs


class TestSSERelatedParams(BaseS3IntegrationTest):
    def download_and_assert_kms_object_integrity(self, bucket, key, contents,
                                                 files, s3_utils):
        s3_utils.wait_until_key_exists(bucket, key)
        # Ensure the kms object can be download it by downloading it
        # with --sse aws:kms is enabled to ensure sigv4 is used on the
        # download, as it is required for kms.
        download_filename = os.path.join(files.rootdir, 'tmp', key)
        p = aws('s3 cp s3://%s/%s %s --sse aws:kms' % (
            bucket, key, download_filename))
        self.assert_no_errors(p)

        assert os.path.isfile(download_filename)
        with open(download_filename, 'r') as f:
            assert f.read() == contents

    def test_sse_upload(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload the file using AES256
        p = aws('s3 cp %s s3://%s/%s --sse AES256' % (
            file_name, shared_bucket, key))
        self.assert_no_errors(p)

        # Ensure the file was uploaded correctly
        s3_utils.assert_key_contents_equal(shared_bucket, key, contents)

    def test_large_file_sse_upload(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = files.create_file(key, contents)

        # Upload the file using AES256
        p = aws('s3 cp %s s3://%s/%s --sse AES256' % (
            file_name, shared_bucket, key))
        self.assert_no_errors(p)

        # Ensure the file was uploaded correctly
        s3_utils.assert_key_contents_equal(shared_bucket, key, contents)

    def test_sse_with_kms_upload(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload the file using KMS
        p = aws('s3 cp %s s3://%s/%s --sse aws:kms' % (
            file_name, shared_bucket, key))
        self.assert_no_errors(p)

        self.download_and_assert_kms_object_integrity(
            shared_bucket, key, contents, files, s3_utils)

    def test_large_file_sse_kms_upload(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = files.create_file(key, contents)

        # Upload the file using KMS
        p = aws('s3 cp %s s3://%s/%s --sse aws:kms' % (
            file_name, shared_bucket, key))
        self.assert_no_errors(p)
        self.download_and_assert_kms_object_integrity(
            shared_bucket, key, contents, files, s3_utils)

    def test_sse_copy(self, s3_utils, shared_bucket):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'contents'
        s3_utils.put_object(shared_bucket, key, contents)

        # Copy the file using AES256
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse AES256' % (
            shared_bucket, key, shared_bucket, new_key))
        self.assert_no_errors(p)

        # Ensure the file was copied correctly
        s3_utils.assert_key_contents_equal(shared_bucket, new_key, contents)

    def test_large_file_sse_copy(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'a' * (10 * (1024 * 1024))

        # This is a little faster and more efficient than
        # calling self.put_object()
        file_name = files.create_file(key, contents)
        p = aws('s3 cp %s s3://%s/%s' % (file_name, shared_bucket, key))
        self.assert_no_errors(p)

        # Copy the file using AES256
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse AES256' % (
            shared_bucket, key, shared_bucket, new_key))
        self.assert_no_errors(p)

        # Ensure the file was copied correctly
        s3_utils.assert_key_contents_equal(shared_bucket, new_key, contents)

    def test_sse_kms_copy(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'contents'
        s3_utils.put_object(shared_bucket, key, contents)

        # Copy the file using KMS
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse aws:kms' % (
            shared_bucket, key, shared_bucket, new_key))
        self.assert_no_errors(p)
        self.download_and_assert_kms_object_integrity(
            shared_bucket, key, contents, files, s3_utils)

    def test_large_file_sse_kms_copy(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'a' * (10 * (1024 * 1024))

        # This is a little faster and more efficient than
        # calling self.put_object()
        file_name = files.create_file(key, contents)
        p = aws('s3 cp %s s3://%s/%s' % (file_name, shared_bucket, key))
        self.assert_no_errors(p)

        # Copy the file using KMS
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse aws:kms' % (
            shared_bucket, key, shared_bucket, new_key))
        self.assert_no_errors(p)
        self.download_and_assert_kms_object_integrity(
            shared_bucket, key, contents, files, s3_utils)

    def test_smoke_sync_sse(self, files, s3_utils, shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload sync
        p = aws('s3 sync %s s3://%s/foo/ --sse AES256' % (
            files.rootdir, shared_bucket))
        self.assert_no_errors(p)
        s3_utils.wait_until_key_exists(shared_bucket, 'foo/foo.txt')

        # Copy sync
        p = aws('s3 sync s3://%s/foo/ s3://%s/bar/ --sse AES256' % (
            shared_bucket, shared_bucket))
        self.assert_no_errors(p)
        s3_utils.wait_until_key_exists(shared_bucket, 'bar/foo.txt')

        # Remove the original file
        os.remove(file_name)

        # Download sync
        p = aws('s3 sync s3://%s/bar/ %s --sse AES256' % (
            shared_bucket, files.rootdir))
        self.assert_no_errors(p)

        assert os.path.isfile(file_name)
        with open(file_name, 'r') as f:
            assert f.read() == contents

    def test_smoke_sync_sse_kms(self, files, shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload sync
        p = aws('s3 sync %s s3://%s/foo/ --sse aws:kms' % (
            files.rootdir, shared_bucket))
        self.assert_no_errors(p)

        # Copy sync
        p = aws('s3 sync s3://%s/foo/ s3://%s/bar/ --sse aws:kms' % (
            shared_bucket, shared_bucket))
        self.assert_no_errors(p)

        # Remove the original file
        os.remove(file_name)

        # Download sync
        p = aws('s3 sync s3://%s/bar/ %s --sse aws:kms' % (
            shared_bucket, files.rootdir))
        self.assert_no_errors(p)

        assert os.path.isfile(file_name)
        with open(file_name, 'r') as f:
            assert f.read() == contents


class TestSSECRelatedParams(BaseS3IntegrationTest):
    def download_and_assert_sse_c_object_integrity(
            self, bucket, key, encrypt_key, contents, files, s3_utils):
        s3_utils.wait_until_key_exists(bucket, key,
                                       {'SSECustomerKey': encrypt_key,
                                        'SSECustomerAlgorithm': 'AES256'})
        download_filename = os.path.join(files.rootdir, 'tmp', key)
        p = aws('s3 cp s3://%s/%s %s --sse-c AES256 --sse-c-key %s' % (
            bucket, key, download_filename, encrypt_key))
        self.assert_no_errors(p)

        assert os.path.isfile(download_filename)
        with open(download_filename, 'r') as f:
            assert f.read() == contents

    def test_sse_c_upload_and_download(self, files, s3_utils, encrypt_key,
                                       shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, shared_bucket, encrypt_key))
        self.assert_no_errors(p)

        self.download_and_assert_sse_c_object_integrity(
            shared_bucket, key, encrypt_key, contents, files, s3_utils)

    def test_can_delete_single_sse_c_object(self, s3_utils, encrypt_key,
                                            shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        s3_utils.put_object(
            shared_bucket, key, contents,
            extra_args={
                'SSECustomerKey': encrypt_key,
                'SSECustomerAlgorithm': 'AES256'
            }
        )
        p = aws('s3 rm s3://%s/%s' % (shared_bucket, key))
        self.assert_no_errors(p)
        assert not s3_utils.key_exists(shared_bucket, key)

    def test_sse_c_upload_and_download_large_file(self, files, s3_utils,
                                                  encrypt_key, shared_bucket):
        key = 'foo.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, shared_bucket, encrypt_key))
        self.assert_no_errors(p)

        self.download_and_assert_sse_c_object_integrity(
            shared_bucket, key, encrypt_key, contents, files, s3_utils)

    def test_sse_c_copy(self, files, s3_utils, encrypt_key, other_encrypt_key,
                        shared_bucket):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, shared_bucket, encrypt_key))
        self.assert_no_errors(p)

        # Copy the file using SSE-C and a new encryption key
        p = aws(
            's3 cp s3://%s/%s s3://%s/%s --sse-c AES256 --sse-c-key %s '
            '--sse-c-copy-source AES256 --sse-c-copy-source-key %s' % (
                shared_bucket, key, shared_bucket, new_key, other_encrypt_key,
                encrypt_key))
        self.assert_no_errors(p)
        self.download_and_assert_sse_c_object_integrity(
            shared_bucket, new_key, other_encrypt_key, contents, files,
            s3_utils)

    def test_sse_c_copy_large_file(self, files, s3_utils, encrypt_key,
                                   other_encrypt_key, shared_bucket):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, shared_bucket, encrypt_key))
        self.assert_no_errors(p)

        # Copy the file using SSE-C and a new encryption key
        p = aws(
            's3 cp s3://%s/%s s3://%s/%s --sse-c AES256 --sse-c-key %s '
            '--sse-c-copy-source AES256 --sse-c-copy-source-key %s' % (
                shared_bucket, key, shared_bucket, new_key, other_encrypt_key,
                encrypt_key))
        self.assert_no_errors(p)
        self.download_and_assert_sse_c_object_integrity(
            shared_bucket, new_key, other_encrypt_key, contents, files,
            s3_utils)

    def test_smoke_sync_sse_c(self, files, encrypt_key, other_encrypt_key,
                              shared_bucket):
        key = 'foo.txt'
        contents = 'contents'
        file_name = files.create_file(key, contents)

        # Upload sync
        p = aws('s3 sync %s s3://%s/foo/ --sse-c AES256 --sse-c-key %s' % (
            files.rootdir, shared_bucket, encrypt_key))
        self.assert_no_errors(p)

        # Copy sync
        p = aws('s3 sync s3://%s/foo/ s3://%s/bar/ --sse-c AES256 '
                '--sse-c-key %s --sse-c-copy-source AES256 '
                '--sse-c-copy-source-key %s' % (
                    shared_bucket, shared_bucket, other_encrypt_key,
                    encrypt_key))
        self.assert_no_errors(p)

        # Remove the original file
        os.remove(file_name)

        # Download sync
        p = aws('s3 sync s3://%s/bar/ %s --sse-c AES256 --sse-c-key %s' % (
            shared_bucket, files.rootdir, other_encrypt_key))
        self.assert_no_errors(p)

        assert os.path.isfile(file_name)
        with open(file_name, 'r') as f:
            assert f.read() == contents


class TestPresignCommand(BaseS3IntegrationTest):

    def test_can_retrieve_presigned_url(self, s3_utils, shared_bucket):
        original_contents = b'this is foo.txt'
        s3_utils.put_object(shared_bucket, 'foo.txt', original_contents)
        p = aws('s3 presign s3://%s/foo.txt' % (shared_bucket,))
        self.assert_no_errors(p)
        url = p.stdout.strip()
        contents = urlopen(url).read()
        assert contents == original_contents
