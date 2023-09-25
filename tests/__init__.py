import asyncio
import contextlib
import dataclasses
from io import BytesIO
import base64
import collections
import copy
import os
import sys
import threading
import time

# Both nose and py.test will add the first parent directory it
# encounters that does not have a __init__.py to the sys.path. In
# our case, this is the root of the repository. This means that Python
# will import the awscli package from source instead of any installed
# distribution. This environment variable provides the option to remove the
# repository root from sys.path to be able to rely on the installed
# distribution when running the tests.
if os.environ.get('TESTS_REMOVE_REPO_ROOT_FROM_PATH'):
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path = [
        path for path in sys.path
        if not os.path.isdir(path) or not os.path.samefile(path, rootdir)
    ]

import awscli
from awscli.clidriver import create_clidriver, AWSCLIEntryPoint
from awscli.compat import collections_abc, six
from awscli.testutils import (
    unittest, mock, capture_output, if_windows, skip_if_windows, create_bucket,
    FileCreator, ConsistencyWaiter
)

import botocore.awsrequest
import botocore.loaders
import botocore.model
import botocore.serialize
import botocore.validate
from botocore.exceptions import ClientError, WaiterError

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, \
    PublicFormat, load_pem_private_key

import prompt_toolkit
import prompt_toolkit.buffer
import prompt_toolkit.input
import prompt_toolkit.output
import prompt_toolkit.input.defaults
import prompt_toolkit.keys
import prompt_toolkit.utils
import prompt_toolkit.key_binding.key_processor
from prompt_toolkit.input.ansi_escape_sequences import REVERSE_ANSI_SEQUENCES

# Botocore testing utilities that we want to preserve import statements for
# in botocore specific tests.
from tests.utils.botocore import (
    assert_url_equal, create_session, random_chars, temporary_file,
    patch_load_service_model, ALL_SERVICES, BaseEnvVar, BaseSessionTest,
    BaseClientDriverTest, StubbedSession, ClientHTTPStubber, SessionHTTPStubber,
    IntegerRefresher, FreezeTime,
)
# S3transfer testing utilities that we want to preserve import statements for
# in s3transfer specific tests.
from tests.utils.s3transfer import (
     HAS_CRT, requires_crt, skip_if_using_serial_implementation,
     random_bucket_name, assert_files_equal,
     NonSeekableReader, NonSeekableWriter, StreamWithError,
     RecordingSubscriber, FileSizeProvider, RecordingOSUtils,
     RecordingExecutor, TransferCoordinatorWithInterrupt, BaseTaskTest,
     BaseSubmissionTaskTest, BaseGeneralInterfaceTest, StubbedClientTest,
)

# A shared loader to use for classes in this module. This allows us to
# load models outside of influence of a session and take advantage of
# caching to speed up tests.
_LOADER = botocore.loaders.Loader()


class CLIRunner(object):
    """Runs CLI commands in a stubbed environment"""
    def __init__(self, env=None, session_stubber=None):
        if env is None:
            env = self._get_default_env()
        self.env = env
        if session_stubber is None:
            session_stubber = SessionStubber()
        self._session_stubber = session_stubber

    def run(self, cmdline):
        with mock.patch('os.environ', self.env):
            with capture_output() as output:
                runner_result = self._do_run(cmdline)
                runner_result.stdout = output.stdout.getvalue()
                runner_result.stderr = output.stderr.getvalue()
                return runner_result

    def add_response(self, response):
        self._session_stubber.add_response(response)

    def _get_default_env(self):
        # awscli/__init__.py injects AWS_DATA_PATH at import time
        # so that we can find cli.json.  This might be fixed in the
        # future, but for now we are just replicating the logic in
        # this abstraction.
        cli_data_dir = os.path.join(
            os.path.dirname(os.path.abspath(awscli.__file__)),
            'data'
        )
        return {
            'AWS_DATA_PATH': cli_data_dir,
            'AWS_DEFAULT_REGION': 'us-west-2',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
            'AWS_CONFIG_FILE': '',
            'AWS_SHARED_CREDENTIALS_FILE': '',
        }

    def _do_run(self, cmdline):
        driver = create_clidriver()
        entry_point = AWSCLIEntryPoint(driver)
        self._session_stubber.register(driver.session)
        rc = entry_point.main(cmdline)
        self._session_stubber.assert_no_remaining_responses()
        runner_result = CLIRunnerResult(rc)
        runner_result.aws_requests = copy.copy(
            self._session_stubber.received_aws_requests
        )
        return runner_result


class SessionStubber(object):
    def __init__(self):
        self.received_aws_requests = []
        self._responses = collections.deque()

    def register(self, session):
        events = session.get_component('event_emitter')
        events.register_first(
            'before-parameter-build.*.*', self._capture_aws_request,
        )
        events.register_last(
            'request-created', self._capture_http_request
        )
        events.register_first(
            'before-send.*.*', self._return_queued_http_response,
        )

    def add_response(self, response):
        self._responses.append(response)

    def assert_no_remaining_responses(self):
        if len(self._responses) != 0:
            raise AssertionError(
                "The following queued responses are remaining: %s" %
                self._responses
            )

    def _capture_aws_request(self, params, model, context, **kwargs):
        aws_request = AWSRequest(
            service_name=model.service_model.service_name,
            operation_name=model.name,
            params=params,
        )
        self.received_aws_requests.append(aws_request)
        context['current_aws_request'] = aws_request

    def _capture_http_request(self, request, **kwargs):
        request.context['current_aws_request'].http_requests.append(
            HTTPRequest(
                method=request.method,
                url=request.url,
                headers=request.headers,
                body=request.body,
            )
        )

    def _return_queued_http_response(self, request, **kwargs):
        response = self._responses.popleft()
        return response.on_http_request_sent(request)


class BaseResponse(object):
    def on_http_request_sent(self, request):
        raise NotImplementedError('on_http_request_sent')


class AWSResponse(BaseResponse):
    def __init__(self, service_name, operation_name, parsed_response,
                 validate=True):
        self._service_name = service_name
        self._operation_name = operation_name
        self._parsed_response = parsed_response
        self._service_model = self._get_service_model()
        self._operation_model = self._service_model.operation_model(
            self._operation_name)
        if validate:
            self._validate_parsed_response()

    def on_http_request_sent(self, request):
        return self._generate_http_response()

    def __repr__(self):
        return (
            'AWSResponse(service_name=%r, operation_name=%r, '
            'parsed_response=%r)' %
            (self._service_name, self._operation_name, self._parsed_response)
        )

    def _get_service_model(self):
        loaded_service_model = _LOADER.load_service_model(
            service_name=self._service_name, type_name='service-2'
        )
        return botocore.model.ServiceModel(
            loaded_service_model, service_name=self._service_name)

    def _validate_parsed_response(self):
        if self._operation_model.output_shape:
            botocore.validate.validate_parameters(
                self._parsed_response, self._operation_model.output_shape)

    def _generate_http_response(self):
        serialized = self._reverse_serialize_parsed_response()
        return HTTPResponse(
            headers=serialized['headers'],
            body=serialized['body']
        )

    def _reverse_serialize_parsed_response(self):
        # NOTE: This is fairly hacky, but it gets us a reasonable,
        # serialized response with a fairly low amount of effort. Basically,
        # we swap the operation model so that its input shape points to its
        # output shape so that we can use the serializer to reverse the
        # parsing logic and generate a raw HTTP response instead of a raw HTTP
        # request.
        #
        # Theoretically this should work for many use cases (e.g. JSON
        # protocols), but there are definitely edge cases that are not
        # being handled (e.g. query protocol). Going forward as more tests
        # adopt this, we **will** have to build up the logic around this.
        serializer = botocore.serialize.create_serializer(
            protocol_name=self._service_model.metadata['protocol'],
            include_validation=False,
        )
        self._operation_model.input_shape = self._operation_model.output_shape
        return serializer.serialize_to_request(
            self._parsed_response, self._operation_model)


class HTTPResponse(BaseResponse):
    def __init__(self, status_code=200, headers=None, body=b''):
        self.status_code = status_code
        if headers is None:
            headers = {}
        self.headers = headers
        self.body = body
        # Botocore's interface uses content and raw instead of body so just
        # making the content and raw aliases to the body.
        self.content = body
        self.raw = body

    def on_http_request_sent(self, request):
        return self


class CLIRunnerResult(object):
    def __init__(self, rc, stdout=None, stderr=None):
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.aws_requests = []


class AWSRequest(object):
    def __init__(self, service_name, operation_name, params):
        self.service_name = service_name
        self.operation_name = operation_name
        self.params = params
        self.http_requests = []

    def __repr__(self):
        return (
            'AWSRequest(service_name=%r, operation_name=%r, params=%r)' %
            (self.service_name, self.operation_name, self.params)
        )

    def __eq__(self, other):
        return (
            self.service_name == other.service_name and
            self.operation_name == other.operation_name and
            self.params == other.params
        )

    def __ne__(self, other):
        return not self.__eq__(other)


class HTTPRequest(object):
    def __init__(self, method, url, headers, body):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    def __repr__(self):
        return (
            'HTTPRequest(method=%r, url=%r, headers=%r, body=%r)' %
            (self.method, self.url, self.headers, self.body)
        )

    def __eq__(self, other):
        return (
            self.method == other.method and
            self.url == other.url and
            self.headers == other.headers and
            self.body == other.body
        )

    def __ne__(self, other):
        return not self.__eq__(other)


# CaseInsensitiveDict from requests that must be serializble.
class CaseInsensitiveDict(collections_abc.MutableMapping):
    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, collections_abc.Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))


class RawResponse(BytesIO):
    # TODO: There's a few objects similar to this in various tests, let's
    # try and consolidate to this one in a future commit.
    def stream(self, **kwargs):
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


@dataclasses.dataclass
class AppRunContext:
    return_value = None
    raised_exception = None


class PromptToolkitAppRunner:
    _EVENT_WAIT_TIMEOUT = 2

    def __init__(self, app, pre_run=None):
        self.app = app
        self._pre_run = pre_run
        self._done_rendering_event = threading.Event()
        self.app.after_render = prompt_toolkit.utils.Event(
            self.app, self._notify_done_rendering)
        self._done_completing_event = threading.Event()

    @contextlib.contextmanager
    def run_app_in_thread(self, target=None, args=None):
        if target is None:
            target = self.app.run
        if args is None:
            args = (self._pre_run,)

        run_context = AppRunContext()
        thread = threading.Thread(
            target=self._do_run_app, args=(target, args, run_context))
        try:
            thread.start()
            self._wait_until_app_is_done_updating()
            yield run_context
        finally:
            if self._app_is_exitable():
                self.app.exit()
            thread.join()

    def feed_input(self, *keys):
        for key in keys:
            self._done_rendering_event.clear()
            self.app.input.send_text(
                self._convert_key_to_vt100_data(key)
            )
            self._wait_until_app_is_done_updating()

    def wait_for_completions_on_current_buffer(self):
        if self._current_buffer_has_completions():
            return
        self.app.current_buffer.on_completions_changed.add_handler(
            self._notify_done_completing
        )
        self._done_completing_event.wait(self._EVENT_WAIT_TIMEOUT)
        self._done_completing_event.clear()

    def _do_run_app(self, target, target_args, app_run_context):
        # This is the function that will be passed to our thread to
        # actually run the application
        try:
            # When we run the app in a separate thread, there is no
            # default event loop. This ensures we create one as it is
            # likely the application will try to grab the default loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            app_run_context.return_value = target(*target_args)
        except BaseException as e:
            app_run_context.raised_exception = e
        finally:
            loop.close()

    def _wait_until_app_is_done_updating(self):
        self._wait_until_app_is_done_rendering()
        # Generally it is not a safe assumption to make that once the
        # app is done rendering the UI will be in its final state.
        # It is possible that because of the rendering it triggers another
        # redraw of the application. So here we manually invalidate the app
        # to flush out any pending changes to the UI and then wait for those
        # changes to be rendered.
        self.app.invalidate()
        self._wait_until_app_is_done_rendering()

    def _wait_until_app_is_done_rendering(self):
        self._done_rendering_event.wait(self._EVENT_WAIT_TIMEOUT)
        self._done_rendering_event.clear()

    def _notify_done_rendering(self, app):
        self._done_rendering_event.set()

    def _notify_done_completing(self, app):
        self._done_completing_event.set()

    def _current_buffer_has_completions(self):
        return (
            self.app.current_buffer.complete_state and
            self.app.current_buffer.complete_state.completions
        )

    def _app_is_exitable(self):
        # This needs to be used instead of app.done() because prompt toolkit
        # sets the future to None when it finishes run_async. So it is
        # indeterminable whether app.done() is actually done because
        # the future being None results in a return value of False.
        # So instead we have our own custom check to see if there is a future
        # present on the app (meaning the run_async has not finished) and the
        # result for that future has not been set.
        return self.app.future and not self.app.future.done()

    def _convert_key_to_vt100_data(self, key):
        return REVERSE_ANSI_SEQUENCES.get(key, key)


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

class PublicPrivateKeyLoader:
    def load_private_key_and_generate_public_key(private_key_path):
        with open(private_key_path, 'rb') as f:
            private_key_byte_input = f.read()

        private_key = load_pem_private_key(private_key_byte_input, None,
                                           default_backend())
        public_key = private_key.public_key()
        pub_bytes = public_key.public_bytes(Encoding.DER, PublicFormat.PKCS1)
        public_key_b64 = base64.b64encode(pub_bytes)

        return public_key_b64, private_key
