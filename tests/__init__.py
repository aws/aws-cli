import collections
import copy
import os

import awscli
from awscli.clidriver import create_clidriver
from awscli.compat import collections_abc
from awscli.testutils import mock, capture_output

import botocore.awsrequest
import botocore.loaders
import botocore.model
import botocore.serialize
import botocore.validate


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
        self._session_stubber.register(driver.session)
        rc = driver.main(cmdline)
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
        # Botocore's interface uses content instead of body so just
        # making the content an alias to the body.
        self.content = body

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
