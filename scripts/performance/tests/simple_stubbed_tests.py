import json
import os

from unittest import mock

from awscli.botocore.awsrequest import AWSResponse
from awscli.compat import BytesIO
from scripts.performance.tests import BaseBenchmarkSuite


class RawResponse(BytesIO):
    """
    A bytes-like streamable HTTP response representation.
    """
    def stream(self, **kwargs):
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


class StubbedHTTPClient:
    def _get_response(self, request):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def setup(self):
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
        self._send.side_effect = self._get_response
        self._responses = []

    def tear_down(self):
        self._urllib3_patch.stop()

    def add_response(self, body, headers, status_code):
        response = AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers=headers,
            raw=RawResponse(body.encode()),
        )
        self._responses.append(response)


class JSONStubbedBenchmarkSuite(BaseBenchmarkSuite):
    def __init__(self):
        self._client = StubbedHTTPClient()
        self._benchmark_results = {}

    def _create_file_with_size(self, path, size):
        """
        Creates a full-access file in the given directory with the
        specified name and size. The created file will be full of
        null bytes to achieve the specified size.
        """
        with open(path, 'wb') as f:
            os.chmod(path, 0o777)
            size = int(size)
            f.truncate(size)

    def _create_file_dir(self, dir_path, file_count, size):
        """
        Creates a directory with the specified name. Also creates identical files
        with the given size in the created directory. The number of identical files
        to be created is specified by file_count. Each file will be full of
        null bytes to achieve the specified size.
        """
        os.mkdir(dir_path, 0o777)
        for i in range(int(file_count)):
            file_path = os.path.join(dir_path, f'{i}')
            self._create_file_with_size(file_path, size)

    def _stub_responses(self, responses, client: StubbedHTTPClient):
        """
        Stubs the supplied HTTP client using the response instructions in the supplied
        responses struct. Each instruction will generate one or more stubbed responses.
        """
        for response in responses:
            body = response.get("body", "")
            headers = response.get("headers", {})
            status_code = response.get("status_code", 200)
            # use the instances key to support duplicating responses a configured number of times
            if "instances" in response:
                for _ in range(int(response['instances'])):
                    client.add_response(body, headers, status_code)
            else:
                client.add_response(body, headers, status_code)

    def _get_env_vars(self, config_path):
        return {
            'AWS_CONFIG_FILE': config_path,
            'AWS_DEFAULT_REGION': 'us-west-2',
        }

    def get_test_cases(self, args):
        definitions = json.load(open(args.benchmark_definitions, 'r'))
        def generator(definition):
            for iteration in range(args.num_iterations):
                yield definition
        return [generator(definition) for definition in definitions]

    def begin_iteration(self, case, workspace_path, assets_path, iteration):
        env = case.get('environment', {})
        config_path = os.path.join(assets_path, 'config')
        self._client.setup()
        self._stub_responses(case.get('responses', []), self._client)
        os.makedirs(os.path.dirname(config_path), mode=0o777, exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(env.get('config', "[DEFAULT]"))
            f.flush()
        self._env_patch = mock.patch.dict(
            'os.environ', self._get_env_vars(config_path)
        )
        self._env_patch.start()
        if "files" in env:
            for file_def in env['files']:
                path = os.path.join(workspace_path, file_def['name'])
                self._create_file_with_size(path, file_def['size'])
        if "file_dirs" in env:
            for file_dir_def in env['file_dirs']:
                dir_path = os.path.join(workspace_path, file_dir_def['name'])
                self._create_file_dir(
                    dir_path,
                    file_dir_def['file_count'],
                    file_dir_def['file_size'],
                )
        if "file_literals" in env:
            for file_lit in env['file_literals']:
                path = os.path.join(workspace_path, file_lit['name'])
                with open(path, file_lit.get('mode', 'w')) as f:
                    os.chmod(path, 0o777)
                    f.write(file_lit['content'])

    def end_iteration(self, case, iteration):
        self._client.tear_down()
        self._env_patch.stop()