# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# Both nose and py.test will add the first parent directory it
# encounters that does not have a __init__.py to the sys.path. In
# our case, this is the root of the repository. This means that Python
# will import the botocore package from source instead of any installed
# distribution. This environment variable provides the option to remove the
# repository root from sys.path to be able to rely on the installed
# distribution when running the tests.
import os
import sys
import mock
import time
import random
import shutil
import contextlib
import tempfile
import binascii
import platform
import select
import datetime
from io import BytesIO
from subprocess import Popen, PIPE

from dateutil.tz import tzlocal
import unittest

import botocore.loaders
import botocore.session
from botocore.awsrequest import AWSResponse
from botocore.compat import six
from botocore.compat import urlparse
from botocore.compat import parse_qs
from botocore import utils
from botocore import credentials
from botocore.stub import Stubber


_LOADER = botocore.loaders.Loader()


def _all_services():
    session = botocore.session.Session()
    service_names = session.get_available_services()
    return [session.get_service_model(name) for name in service_names]


# Only compute our service models once
ALL_SERVICES = _all_services()


def skip_unless_has_memory_collection(cls):
    """Class decorator to skip tests that require memory collection.

    Any test that uses memory collection (such as the resource leak tests)
    can decorate their class with skip_unless_has_memory_collection to
    indicate that if the platform does not support memory collection
    the tests should be skipped.
    """
    if platform.system() not in ['Darwin', 'Linux']:
        return unittest.skip('Memory tests only supported on mac/linux.')(cls)
    return cls


def skip_if_windows(reason):
    """Decorator to skip tests that should not be run on windows.
    Example usage:
        @skip_if_windows("Not valid")
        def test_some_non_windows_stuff(self):
            self.assertEqual(...)
    """
    def decorator(func):
        return unittest.skipIf(
            platform.system() not in ['Darwin', 'Linux'], reason)(func)
    return decorator


def random_chars(num_chars):
    """Returns random hex characters.

    Useful for creating resources with random names.

    """
    return binascii.hexlify(os.urandom(int(num_chars / 2))).decode('ascii')


def create_session(**kwargs):
    # Create a Session object.  By default,
    # the _LOADER object is used as the loader
    # so that we reused the same models across tests.
    session = botocore.session.Session(**kwargs)
    session.register_component('data_loader', _LOADER)
    session.set_config_variable('credentials_file', 'noexist/foo/botocore')
    return session


@contextlib.contextmanager
def temporary_file(mode):
    """This is a cross platform temporary file creation.

    tempfile.NamedTemporary file on windows creates a secure temp file
    that can't be read by other processes and can't be opened a second time.

    For tests, we generally *want* them to be read multiple times.
    The test fixture writes the temp file contents, the test reads the
    temp file.

    """
    temporary_directory = tempfile.mkdtemp()
    basename = 'tmpfile-%s-%s' % (int(time.time()), random.randint(1, 1000))
    full_filename = os.path.join(temporary_directory, basename)
    open(full_filename, 'w').close()
    try:
        with open(full_filename, mode) as f:
            yield f
    finally:
        shutil.rmtree(temporary_directory)


class BaseEnvVar(unittest.TestCase):
    def setUp(self):
        # Automatically patches out os.environ for you
        # and gives you a self.environ attribute that simulates
        # the environment.  Also will automatically restore state
        # for you in tearDown()
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

    def tearDown(self):
        self.environ_patch.stop()


class BaseSessionTest(BaseEnvVar):
    """Base class used to provide credentials.

    This class can be used as a base class that want to use a real
    session class but want to be completely isolated from the
    external environment (including environment variables).

    This class will also set credential vars so you can make fake
    requests to services.

    """

    def setUp(self, **environ):
        super(BaseSessionTest, self).setUp()
        self.environ['AWS_ACCESS_KEY_ID'] = 'access_key'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'secret_key'
        self.environ['AWS_CONFIG_FILE'] = 'no-exist-foo'
        self.environ.update(environ)
        self.session = create_session()
        self.session.config_filename = 'no-exist-foo'


@skip_unless_has_memory_collection
class BaseClientDriverTest(unittest.TestCase):
    INJECT_DUMMY_CREDS = False

    def setUp(self):
        self.driver = ClientDriver()
        env = os.environ.copy()
        if self.INJECT_DUMMY_CREDS:
            env['AWS_ACCESS_KEY_ID'] = 'foo'
            env['AWS_SECRET_ACCESS_KEY'] = 'bar'
        self.driver.start(env=env)

    def cmd(self, *args):
        self.driver.cmd(*args)

    def send_cmd(self, *args):
        self.driver.send_cmd(*args)

    def record_memory(self):
        self.driver.record_memory()

    @property
    def memory_samples(self):
        return self.driver.memory_samples

    def tearDown(self):
        self.driver.stop()


class ClientDriver(object):
    CLIENT_SERVER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'cmd-runner'
    )

    def __init__(self):
        self._popen = None
        self.memory_samples = []

    def _get_memory_with_ps(self, pid):
        # It would be better to eventually switch to psutil,
        # which should allow us to test on windows, but for now
        # we'll just use ps and run on POSIX platforms.
        command_list = ['ps', '-p', str(pid), '-o', 'rss']
        p = Popen(command_list, stdout=PIPE)
        stdout = p.communicate()[0]
        if not p.returncode == 0:
            raise RuntimeError("Could not retrieve memory")
        else:
            # Get the RSS from output that looks like this:
            # RSS
            # 4496
            return int(stdout.splitlines()[1].split()[0]) * 1024

    def record_memory(self):
        mem = self._get_memory_with_ps(self._popen.pid)
        self.memory_samples.append(mem)

    def start(self, env=None):
        """Start up the command runner process."""
        self._popen = Popen([sys.executable, self.CLIENT_SERVER],
                            stdout=PIPE, stdin=PIPE, env=env)

    def stop(self):
        """Shutdown the command runner process."""
        self.cmd('exit')
        self._popen.wait()

    def send_cmd(self, *cmd):
        """Send a command and return immediately.

        This is a lower level method than cmd().
        This method will instruct the cmd-runner process
        to execute a command, but this method will
        immediately return.  You will need to use
        ``is_cmd_finished()`` to check that the command
        is finished.

        This method is useful if you want to record attributes
        about the process while an operation is occurring.  For
        example, if you want to instruct the cmd-runner process
        to upload a 1GB file to S3 and you'd like to record
        the memory during the upload process, you can use
        send_cmd() instead of cmd().

        """
        cmd_str = ' '.join(cmd) + '\n'
        cmd_bytes = cmd_str.encode('utf-8')
        self._popen.stdin.write(cmd_bytes)
        self._popen.stdin.flush()

    def is_cmd_finished(self):
        rlist = [self._popen.stdout.fileno()]
        result = select.select(rlist, [], [], 0.01)
        if result[0]:
            return True
        return False

    def cmd(self, *cmd):
        """Send a command and block until it finishes.

        This method will send a command to the cmd-runner process
        to run.  It will block until the cmd-runner process is
        finished executing the command and sends back a status
        response.

        """
        self.send_cmd(*cmd)
        result = self._popen.stdout.readline().strip()
        if result != b'OK':
            raise RuntimeError(
                "Error from command '%s': %s" % (cmd, result))


# This is added to this file because it's used in both
# the functional and unit tests for cred refresh.
class IntegerRefresher(credentials.RefreshableCredentials):
    """Refreshable credentials to help with testing.

    This class makes testing refreshable credentials easier.
    It has the following functionality:

        * A counter, self.refresh_counter, to indicate how many
          times refresh was called.
        * A way to specify how many seconds to make credentials
          valid.
        * Configurable advisory/mandatory refresh.
        * An easy way to check consistency.  Each time creds are
          refreshed, all the cred values are set to the next
          incrementing integer.  Frozen credentials should always
          have this value.
    """

    _advisory_refresh_timeout = 2
    _mandatory_refresh_timeout = 1
    _credentials_expire = 3

    def __init__(self, creds_last_for=_credentials_expire,
                 advisory_refresh=_advisory_refresh_timeout,
                 mandatory_refresh=_mandatory_refresh_timeout,
                 refresh_function=None):
        expires_in = (
            self._current_datetime() +
            datetime.timedelta(seconds=creds_last_for))
        if refresh_function is None:
            refresh_function = self._do_refresh
        super(IntegerRefresher, self).__init__(
            '0', '0', '0', expires_in,
            refresh_function, 'INTREFRESH')
        self.creds_last_for = creds_last_for
        self.refresh_counter = 0
        self._advisory_refresh_timeout = advisory_refresh
        self._mandatory_refresh_timeout = mandatory_refresh

    def _do_refresh(self):
        self.refresh_counter += 1
        current = int(self._access_key)
        next_id = str(current + 1)

        return {
            'access_key': next_id,
            'secret_key': next_id,
            'token': next_id,
            'expiry_time': self._seconds_later(self.creds_last_for),
        }

    def _seconds_later(self, num_seconds):
        # We need to guarantee at *least* num_seconds.
        # Because this doesn't handle subsecond precision
        # we'll round up to the next second.
        num_seconds += 1
        t = self._current_datetime() + datetime.timedelta(seconds=num_seconds)
        return self._to_timestamp(t)

    def _to_timestamp(self, datetime_obj):
        obj = utils.parse_to_aware_datetime(datetime_obj)
        return obj.strftime('%Y-%m-%dT%H:%M:%SZ')

    def _current_timestamp(self):
        return self._to_timestamp(self._current_datetime())

    def _current_datetime(self):
        return datetime.datetime.now(tzlocal())


def _urlparse(url):
    if isinstance(url, six.binary_type):
        # Not really necessary, but it helps to reduce noise on Python 2.x
        url = url.decode('utf8')
    return urlparse(url)

def assert_url_equal(url1, url2):
    parts1 = _urlparse(url1)
    parts2 = _urlparse(url2)

    # Because the query string ordering isn't relevant, we have to parse
    # every single part manually and then handle the query string.
    assert parts1.scheme == parts2.scheme
    assert parts1.netloc == parts2.netloc
    assert parts1.path == parts2.path
    assert parts1.params == parts2.params
    assert parts1.fragment == parts2.fragment
    assert parts1.username == parts2.username
    assert parts1.password == parts2.password
    assert parts1.hostname == parts2.hostname
    assert parts1.port == parts2.port
    assert parse_qs(parts1.query) == parse_qs(parts2.query)


class HTTPStubberException(Exception):
    pass


class RawResponse(BytesIO):
    # TODO: There's a few objects similar to this in various tests, let's
    # try and consolidate to this one in a future commit.
    def stream(self, **kwargs):
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


class BaseHTTPStubber(object):
    def __init__(self, obj_with_event_emitter, strict=True):
        self.reset()
        self._strict = strict
        self._obj_with_event_emitter = obj_with_event_emitter

    def reset(self):
        self.requests = []
        self.responses = []

    def add_response(self, url='https://example.com', status=200, headers=None,
                     body=b''):
        if headers is None:
            headers = {}

        raw = RawResponse(body)
        response = AWSResponse(url, status, headers, raw)
        self.responses.append(response)

    @property
    def _events(self):
        raise NotImplementedError('_events')

    def start(self):
        self._events.register('before-send', self)

    def stop(self):
        self._events.unregister('before-send', self)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def __call__(self, request, **kwargs):
        self.requests.append(request)
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            else:
                return response
        elif self._strict:
            raise HTTPStubberException('Insufficient responses')
        else:
            return None


class ClientHTTPStubber(BaseHTTPStubber):
    @property
    def _events(self):
        return self._obj_with_event_emitter.meta.events


class SessionHTTPStubber(BaseHTTPStubber):
    @property
    def _events(self):
        return self._obj_with_event_emitter.get_component('event_emitter')


class ConsistencyWaiterException(Exception):
    pass


class ConsistencyWaiter(object):
    """
    A waiter class for some check to reach a consistent state.

    :type min_successes: int
    :param min_successes: The minimum number of successful check calls to
    treat the check as stable. Default of 1 success.

    :type max_attempts: int
    :param min_successes: The maximum number of times to attempt calling
    the check. Default of 20 attempts.

    :type delay: int
    :param delay: The number of seconds to delay the next API call after a
    failed check call. Default of 5 seconds.
    """
    def __init__(self, min_successes=1, max_attempts=20, delay=5,
                 delay_initial_poll=False):
        self.min_successes = min_successes
        self.max_attempts = max_attempts
        self.delay = delay
        self.delay_initial_poll = delay_initial_poll

    def wait(self, check, *args, **kwargs):
        """
        Wait until the check succeeds the configured number of times

        :type check: callable
        :param check: A callable that returns True or False to indicate
        if the check succeeded or failed.

        :type args: list
        :param args: Any ordered arguments to be passed to the check.

        :type kwargs: dict
        :param kwargs: Any keyword arguments to be passed to the check.
        """
        attempts = 0
        successes = 0
        if self.delay_initial_poll:
            time.sleep(self.delay)
        while attempts < self.max_attempts:
            attempts += 1
            if check(*args, **kwargs):
                successes += 1
                if successes >= self.min_successes:
                    return
            else:
                time.sleep(self.delay)
        fail_msg = self._fail_message(attempts, successes)
        raise ConsistencyWaiterException(fail_msg)

    def _fail_message(self, attempts, successes):
        format_args = (attempts, successes)
        return 'Failed after %s attempts, only had %s successes' % format_args


class StubbedSession(botocore.session.Session):
    def __init__(self, *args, **kwargs):
        super(StubbedSession, self).__init__(*args, **kwargs)
        self._cached_clients = {}
        self._client_stubs = {}

    @property
    def cached_clients(self):
        return self._cached_clients

    @property
    def client_stubs(self):
        return self._client_stubs

    def create_client(self, service_name, *args, **kwargs):
        if service_name not in self._cached_clients:
            client = self._create_stubbed_client(service_name, *args, **kwargs)
            self._cached_clients[service_name] = client
        return self._cached_clients[service_name]

    def _create_stubbed_client(self, service_name, *args, **kwargs):
        client = super(StubbedSession, self).create_client(
            service_name, *args, **kwargs)
        stubber = Stubber(client)
        self._client_stubs[service_name] = stubber
        return client

    def stub(self, service_name, *args, **kwargs):
        if service_name not in self._client_stubs:
            self.create_client(service_name, *args, **kwargs)
        return self._client_stubs[service_name]

    def activate_stubs(self):
        for stub in self._client_stubs.values():
            stub.activate()

    def verify_stubs(self):
        for stub in self._client_stubs.values():
            stub.assert_no_pending_responses()


class FreezeTime(contextlib.ContextDecorator):
    """
    Context manager for mocking out datetime in arbitrary modules when creating
    performing actions like signing which require point in time specificity.

    :type module: module
    :param module: reference to imported module to patch (e.g. botocore.auth.datetime)

    :type date: datetime.datetime
    :param date: datetime object specifying the output for utcnow()
    """

    def __init__(self, module, date=None):
        if date is None:
            date = datetime.datetime.utcnow()
        self.date = date
        self.datetime_patcher = mock.patch.object(
            module, 'datetime',
            mock.Mock(wraps=datetime.datetime)
        )

    def __enter__(self, *args, **kwargs):
        mock = self.datetime_patcher.start()
        mock.utcnow.return_value = self.date

    def __exit__(self, *args, **kwargs):
        self.datetime_patcher.stop()


def patch_load_service_model(
    session, monkeypatch, service_model_json, ruleset_json
):
    def mock_load_service_model(service_name, type_name, api_version=None):
        if type_name == 'service-2':
            return service_model_json
        if type_name == 'endpoint-rule-set-1':
            return ruleset_json

    loader = session.get_component('data_loader')
    monkeypatch.setattr(loader, 'load_service_model', mock_load_service_model)
