import dataclasses
from io import BytesIO, TextIOWrapper
import collections
import copy
import os
from typing import Optional, Callable

import awscli
from awscli.clidriver import create_clidriver, AWSCLIEntryPoint
from awscli.compat import collections_abc
from awscli.testutils import mock, capture_output

import botocore.awsrequest
import botocore.loaders
import botocore.model
import botocore.serialize
import botocore.validate

import prompt_toolkit
import prompt_toolkit.input
import prompt_toolkit.output
import prompt_toolkit.input.defaults
import prompt_toolkit.keys
import prompt_toolkit.utils
import prompt_toolkit.key_binding.key_processor

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


class FakeApplicationInput(prompt_toolkit.input.DummyInput):
    def fileno(self):
        return 0

    @property
    def closed(self):
        return False


class FakeApplicationOutput(prompt_toolkit.output.DummyOutput):
    def fileno(self):
        return 1


@dataclasses.dataclass
class AppKeyPressAction:
    key: str


@dataclasses.dataclass
class AppAssertionAction:
    assertion: Callable[[prompt_toolkit.Application], None]
    failure_message_format: Optional[str] = None


@dataclasses.dataclass
class AppCallbackAction:
    callback: Callable[[prompt_toolkit.Application], None]


class PromptToolkitApplicationStubber:
    def __init__(self, app):
        self._app = app
        self._queue = []

    def add_keypress(self, key, app_assertion=None):
        self._queue.append(AppKeyPressAction(key))
        if app_assertion:
            failure_message_format = (
                f'Incorrect action on key press "{key}": '
                '{message}'
            )
            self._queue.append(
                AppAssertionAction(
                    assertion=app_assertion,
                    failure_message_format=failure_message_format
                )
            )

    def add_app_assertion(self, assertion):
        self._queue.append(AppAssertionAction(assertion))

    def start_completion_for_current_buffer(self):
        def start_completion(app):
            app.current_buffer.start_completion()
        self._queue.append(AppCallbackAction(callback=start_completion))

    def add_text_to_current_buffer(self, text):
        def set_current_buffer(app):
            app.current_buffer.text = text
            app.current_buffer.cursor_position = len(text)
        self._queue.append(AppCallbackAction(callback=set_current_buffer))

    def run(self, pre_run=None):
        key_processor = self._app.key_processor
        # After each rendering application will run this callback
        # it takes the next action from the queue and performs it
        # some key_presses can lead to rerender, after which this callback
        # will be run again before re-rendering app.invalidated property
        # set to True.
        # On exit this callback also run so we need to remove it before exit

        def callback(app):
            while self._queue and not app.invalidated:
                action = self._queue.pop(0)
                if hasattr(action, 'key'):
                    key_processor.feed(
                        prompt_toolkit.key_binding.key_processor.KeyPress(
                            action.key, ''
                        )
                    )
                    key_processor.process_keys()
                if hasattr(action, 'callback'):
                    action.callback(app)
                if getattr(action, 'assertion', None):
                    try:
                        action.assertion(app)
                    except AssertionError as e:
                        message = str(e)
                        if getattr(action, 'failure_message_format'):
                            message = action.failure_message_format.format(
                                message=message
                            )
                        app.after_render = prompt_toolkit.utils.Event(
                            app, None)
                        app.exit(exception=AssertionError(message))
                        return
                if app.future.done():
                    app.after_render = prompt_toolkit.utils.Event(app, None)
                    return
            if not self._queue:
                app.after_render = prompt_toolkit.utils.Event(app, None)
                app.exit()

        self._app.input = FakeApplicationInput()
        self._app.after_render = prompt_toolkit.utils.Event(
            self._app, callback)

        _stdout = TextIOWrapper(BytesIO(), encoding="utf-8")
        self._app.output.stdout = _stdout
        self._app.run(pre_run=pre_run)
