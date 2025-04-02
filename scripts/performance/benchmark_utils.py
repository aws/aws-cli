import datetime
import json
import math
import random
import string
import sys
import time
import uuid
import traceback
import numpy as np

import psutil

import os
import shutil
from awscli.botocore.awsrequest import AWSResponse

from unittest import mock
from awscli.clidriver import AWSCLIEntryPoint, create_clidriver
from awscli.compat import BytesIO
from botocore.config import Config

from botocore.session import get_session


class Summarizer:
    DATA_INDEX_IN_ROW = {'time': 0, 'memory': 1, 'cpu': 2}

    def __init__(self):
        self._start_time = None
        self._end_time = None
        self._samples = []
        self._sums = {
            'memory': 0.0,
            'cpu': 0.0,
        }

    def summarize(self, samples):
        """Processes benchmark data from a dictionary."""
        self._samples = samples
        self._validate_samples(samples)
        for idx, sample in enumerate(samples):
            # If the sample is the first one, collect the start time.
            if idx == 0:
                self._start_time = self._get_time(sample)
            self.process_data_sample(sample)
        self._end_time = self._get_time(samples[-1])
        metrics = self._finalize_processed_data_for_file(samples)
        return metrics

    def _validate_samples(self, samples):
        if not samples:
            raise RuntimeError(
                'Benchmark samples could not be processed. '
                'The samples list is empty'
            )

    def process_data_sample(self, sample):
        self._add_to_sums('memory', sample['memory'])
        self._add_to_sums('cpu', sample['cpu'])

    def _finalize_processed_data_for_file(self, samples):
        # compute percentiles
        self._samples.sort(key=self._get_memory)
        memory_p50 = self._compute_metric_percentile(50, 'memory')
        memory_p95 = self._compute_metric_percentile(95, 'memory')
        self._samples.sort(key=self._get_cpu)
        cpu_p50 = self._compute_metric_percentile(50, 'cpu')
        cpu_p95 = self._compute_metric_percentile(95, 'cpu')
        max_memory = max(samples, key=self._get_memory)['memory']
        max_cpu = max(samples, key=self._get_cpu)['cpu']
        # format computed statistics
        metrics = {
            'average_memory': self._sums['memory'] / len(samples),
            'average_cpu': self._sums['cpu'] / len(samples),
            'max_memory': max_memory,
            'max_cpu': max_cpu,
            'memory_p50': memory_p50,
            'memory_p95': memory_p95,
            'cpu_p50': cpu_p50,
            'cpu_p95': cpu_p95,
        }
        # reset data state
        self._samples.clear()
        self._sums = self._sums.fromkeys(self._sums, 0.0)
        return metrics

    def _compute_metric_percentile(self, percentile, name):
        num_samples = len(self._samples)
        p_idx = math.ceil(percentile * num_samples / 100) - 1
        return self._samples[p_idx][name]

    def _get_time(self, sample):
        return sample['time']

    def _get_memory(self, sample):
        return sample['memory']

    def _get_cpu(self, sample):
        return sample['cpu']

    def _add_to_sums(self, name, data_point):
        self._sums[name] += data_point


class RawResponse(BytesIO):
    """
    A bytes-like streamable HTTP response representation.
    """

    def stream(self, **kwargs):
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


class StubbedHTTPClient(object):
    """
    A generic stubbed HTTP client.
    """

    def __init__(self, echo=False):
        self._echo = echo

    def setup(self, echo=False):
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()

        def _echo(request):
            return AWSResponse('url', 200, request.headers, RawResponse(request.body))
        if self._echo:
            self._send.side_effect = _echo
        else:
            self._send.side_effect = self.get_response
        self._responses = []

    def tearDown(self):
        self._urllib3_patch.stop()

    def get_response(self, request):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def add_response(self, body, headers, status_code):
        response = AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers=headers,
            raw=RawResponse(body.encode()),
        )
        self._responses.append(response)


class ProcessBenchmarker(object):
    """
    Periodically samples CPU and memory usage of a process given its pid.
    """

    def benchmark_process(self, pid, data_interval):
        parent_pid = os.getpid()
        try:
            # Benchmark the process where the script is being run.
            return self._run_benchmark(pid, data_interval)
        except KeyboardInterrupt:
            # If there is an interrupt, then try to clean everything up.
            proc = psutil.Process(parent_pid)
            procs = proc.children(recursive=True)

            for child in procs:
                child.terminate()

            gone, alive = psutil.wait_procs(procs, timeout=1)
            for child in alive:
                child.kill()
            raise
        # finally:
            # print(f'CHILD PROCESS ENDED.')

    def _run_benchmark(self, pid, data_interval):
        process_to_measure = psutil.Process(pid)
        samples = []

        while process_to_measure.is_running():
            if process_to_measure.status() == psutil.STATUS_ZOMBIE:
                # process_to_measure.kill()
                break
            time.sleep(data_interval)
            try:
                # Collect the memory and cpu usage.
                memory_used = process_to_measure.memory_info().rss
                cpu_percent = process_to_measure.cpu_percent()
            except (
                psutil.AccessDenied,
                psutil.ZombieProcess,
                psutil.NoSuchProcess,
            ):
                # Trying to get process information from a closed or
                # zombie process will result in corresponding exceptions.
                break
            # Determine the lapsed time for bookkeeping
            current_time = time.time()
            samples.append(
                {
                    "time": current_time,
                    "memory": memory_used,
                    "cpu": cpu_percent,
                }
            )
        return samples


class BenchmarkHarness(object):
    _DEFAULT_FILE_CONFIG_CONTENTS = "[default]"

    """
    Orchestrates running benchmarks in isolated, configurable environments defined
    via a specified JSON file.
    """

    def __init__(self):
        self._summarizer = Summarizer()

    def _get_default_env(self, config_file, credentials_file):
        return {
            'AWS_CONFIG_FILE': config_file,
            # 'AWS_SHARED_CREDENTIALS_FILE': credentials_file,
            'AWS_DEFAULT_REGION': 'us-west-2',
        }

    def _create_file_with_size(self, path, size):
        """
        Creates a full-access file in the given directory with the
        specified name and size. The created file will be full of
        null bytes to achieve the specified size.
        """
        f = open(path, 'wb')
        os.chmod(path, 0o777)
        size = int(size)
        f.truncate(size)
        f.close()

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

    def _setup_iteration(self, benchmark, client, result_dir, config_file, credentials_file):
        """
        Performs the environment setup for a single iteration of a
        benchmark. This includes creating the files used by a
        command and stubbing the HTTP client to use during execution.
        """
        # create necessary files for iteration
        env = benchmark.get('environment', {})
        if "files" in env:
            for file_def in env['files']:
                path = os.path.join(result_dir, file_def['name'])
                self._create_file_with_size(path, file_def['size'])
        if "file_dirs" in env:
            for file_dir_def in env['file_dirs']:
                dir_path = os.path.join(result_dir, file_dir_def['name'])
                self._create_file_dir(
                    dir_path,
                    file_dir_def['file_count'],
                    file_dir_def['file_size'],
                )
        if "file_literals" in env:
            for file_lit in env['file_literals']:
                path = os.path.join(result_dir, file_lit['name'])
                mode, content = ('wb', file_lit['binary-content']) if 'binary-content' in file_lit else ('w', file_lit['content'])
                with open(path, mode) as f:
                    os.chmod(path, 0o777)
                    f.write(content)
        # create config file at specified path
        os.makedirs(os.path.dirname(config_file), mode=0o777, exist_ok=True)
        with open(config_file, 'w') as f:
            f.write(env.get('config', self._DEFAULT_FILE_CONFIG_CONTENTS))
            f.flush()
        with open(credentials_file, 'w') as f:
            f.write(env.get('config', self._DEFAULT_FILE_CONFIG_CONTENTS))
            f.flush()
        # setup and stub HTTP client
        if client is not None:
            client.setup()
            self._stub_responses(
                benchmark.get('responses', []), client
            )

    def _stub_responses(self, responses, client):
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

    def _run_command_with_metric_hooks(self, cmd, out_file, service_id, service_operation_name):
        """
        Runs a CLI command and logs CLI-specific metrics to a file.
        """
        first_client_invocation_time = None
        serialization_time = None
        deserialization_time = None
        request_payload_size = None
        response_payload_size = None
        start_time = time.time()
        driver = create_clidriver()
        event_emitter = driver.session.get_component('event_emitter')

        def _log_invocation_time(params, request_signer, model, **kwargs):
            nonlocal first_client_invocation_time
            if first_client_invocation_time is None:
                first_client_invocation_time = time.time()

        def _log_metrics_from_context(**kwargs):
            context = kwargs['context']
            parsed_response = kwargs['parsed_response']
            nonlocal first_client_invocation_time
            nonlocal serialization_time
            nonlocal deserialization_time
            nonlocal request_payload_size
            nonlocal response_payload_size
            if serialization_time is None and context is not None and 'serialize_time' in context:
                serialization_time = context['serialize_time']
            if deserialization_time is None and context is not None and 'deserialize_time' in context:
                deserialization_time = context['deserialize_time']
            if request_payload_size is None and parsed_response is not None and parsed_response['ResponseMetadata'] is not None:
                request_payload_size = parsed_response['ResponseMetadata']['RequestPayloadSize']
            if response_payload_size is None and parsed_response is not None and parsed_response['ResponseMetadata'] is not None:
                response_payload_size = parsed_response['ResponseMetadata']['ResponsePayloadSize']

        event_emitter.register_last(
            'before-call',
            _log_invocation_time,
            'benchmarks.log-invocation-time',
        )
        event_emitter.register(
            f'response-received.{service_id}.{service_operation_name}',
            _log_metrics_from_context,
            'benchmarks.log-metrics-from-context',
        )
        # print(f'hooked to events: {cmd}')
        rc, req_time = AWSCLIEntryPoint(driver).main(cmd)
        end_time = time.time()
        # print('completed main')

        # write the collected metrics to a file
        metrics_f = open(out_file, 'w')
        metrics_f.write(
            json.dumps(
                {
                    'return_code': rc,
                    'start_time': start_time,
                    'end_time': end_time,
                    'first_client_invocation_time': first_client_invocation_time,
                    'serialization_time': serialization_time,
                    'deserialization_time': deserialization_time,
                    'request_payload_size': request_payload_size,
                    'response_payload_size': response_payload_size,
                    'total_request_time':  req_time,
                }
            )
        )
        metrics_f.flush()
        os.fsync(metrics_f.fileno())
        metrics_f.close()

    def _run_isolated_benchmark(
        self, result_dir, benchmark, client, process_benchmarker, args
    ):
        """
        Runs a single iteration of one benchmark execution. Includes setting up
        the environment, running the benchmarked execution, formatting
        the results, and cleaning up the environment.
        """
        assets_path = os.path.join(result_dir, 'assets')
        config_path = os.path.join(assets_path, 'config')
        credentials_path = os.path.join(assets_path, 'credentials')
        metrics_path = os.path.join(assets_path, 'metrics.json')
        child_output_path = os.path.join(assets_path, 'output.txt')
        child_err_path = os.path.join(assets_path, 'err.txt')
        # setup for iteration of benchmark
        self._setup_iteration(benchmark, client, result_dir, config_path, credentials_path)
        os.chdir(result_dir)
        # patch the OS environment with our supplied defaults
        env_patch = mock.patch.dict(
            'os.environ', self._get_default_env(config_path, credentials_path)
        )
        env_patch.start()
        # fork a child process to run the command on.
        # the parent process benchmarks the child process until the child terminates.
        pid = os.fork()

        try:
            if pid == 0:
                with open(child_output_path, 'w') as out, open(
                    child_err_path, 'w'
                ) as err:
                    try:
                        # redirect standard output of the child process to a file
                        os.dup2(out.fileno(), sys.stdout.fileno())
                        os.dup2(err.fileno(), sys.stderr.fileno())
                        # execute command on child process
                        # print('BEGIN CHILD PROCESS')
                        self._run_command_with_metric_hooks(
                            benchmark['command'], metrics_path, benchmark.get('service_id', ''), benchmark.get('operation_name', '')
                        )
                        # terminate the child process
                        # print('run command w/ metric completed')
                        os._exit(0)
                        # sys.exit(0)
                    except Exception as e:
                        print(traceback.print_exc())


            # benchmark child process from parent process until child terminates
            samples = process_benchmarker.benchmark_process(
                pid, args.data_interval
            )

            # print(f'num samples: {len(samples)}')

            _, status = os.waitpid(pid,0)
            if status != 0:
                # print(f'Warning: status code {status}')
                raise RuntimeError(f'Child process execution failed: status code {status}')
            # load child-collected metrics if exists
            if not os.path.exists(metrics_path):
                raise RuntimeError(
                    'Child process execution failed: output file not found.'
                )
            metrics_f = json.load(open(metrics_path, 'r'))
            # raise error if child process failed
            if (rc := metrics_f['return_code']) != 0:
                with open(child_err_path, 'r') as err:
                    raise RuntimeError(
                        f'Child process execution failed: return code {rc}.\n'
                        f'Error: {err.read()}'
                    )
            # summarize benchmark results and process summary
            summary = self._summarizer.summarize(samples)
            summary['total_time'] = (
                metrics_f['end_time'] - metrics_f['start_time']
            )
            summary['first_client_invocation_time'] = (
                metrics_f['first_client_invocation_time']
                - metrics_f['start_time']
            )
            summary['serialization_time'] = metrics_f['serialization_time']
            summary['deserialization_time'] = metrics_f['deserialization_time']
            summary['request_payload_size'] = metrics_f['request_payload_size']
            summary['response_payload_size'] = metrics_f['response_payload_size']
            summary['total_request_time'] = metrics_f['total_request_time']
        finally:
            # --- END-ITERATION (cleanup of resources made in BEGIN-ITERATION, reset the result directory, ...)
            if client is not None:
                client.tearDown()
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir, 0o777)
            env_patch.stop()
        return summary

    def _get_random_string(self, str_len):
        CHARACTERS = string.ascii_letters + string.digits

        return ''.join((char.replace("'", "\\'").replace('"', '\\"') if (char := random.choice(CHARACTERS)) in '\'"' else char) for _ in range(str_len))

    def _get_list_of_random_strings(self, list_len, str_len):
        return [f'{self._get_random_string(str_len)}' for _ in range(list_len)]

    def _get_list_of_complex_objects(self, list_len, start_timestamp):
        # gets SHORTHAND-syntax list of complex objects
        return [
            f'booleanMember={random.choice(["true", "false"])},'
            f'stringMember={self._get_random_string(32)},'
            f'longMember={random.randint(-9223372036854775808, 9223372036854775807)},'
            f'doubleMember={random.uniform(-9223372036854775808, 9223372036854775807)},'
            f'timestampMember={datetime.datetime.fromtimestamp(start_timestamp)},'
            f'listOfStringsMember={",".join(self._get_list_of_random_strings(8, 32))}'
        for _ in range(list_len)]

    def _get_string_to_string_map(self, map_size, key_len, val_len):
        string_to_string_map = { self._get_random_string(key_len): self._get_random_string(val_len) for _ in range(map_size) }
        return [f'{key}={val}' for (key, val) in string_to_string_map.items()]

    def _get_string_to_string_map_shorthand(self, map_size, key_len, val_len):
        str_str_map = self._get_string_to_string_map(map_size, key_len, val_len)
        return ','.join(str_str_map)

    def _get_string_to_string_hash_literal(self, map_size, key_len, val_len):
        return '{' + ','.join(self._get_string_to_string_map(map_size, key_len, val_len)) + '}'

    def _get_all_types_sequence(self, service_cmd, run_start_time, protocol):
        return [({
            'name': 'All types',
            'service_id': 'echo',
            'operation_name': 'EchoOperation',
            'command': [
               service_cmd, 'echo-operation', f'{random.choice(["--boolean-member", "--no-boolean-member"])}',
                    '--string-member', f'{self._get_random_string(32)}',
                    '--integer-member', f'{random.randint(-9223372036854775808, 9223372036854775807)}',
                    '--long-member', f'{random.randint(-9223372036854775808, 9223372036854775807)}',
                    '--float-member', '{:f}'.format(random.uniform(-3.4e38, 3.4e38)),
                    '--double-member', f'{random.uniform(-1.7e308, 1.7e308)}',
                    '--timestamp-member', f'{datetime.datetime.fromtimestamp(run_start_time)}',
                    '--blob-member', f'fileb://blob-file-{run_start_time}',
                    '--list-of-strings-member', *self._get_list_of_random_strings(8, 32),
                    '--map-of-string-to-string-member', self._get_string_to_string_map_shorthand(8, 32, 64),
                    '--complex-struct-member', f'stringMember={self._get_random_string(32)},complexStructMember={{stringMember={self._get_random_string(32)}}}',
                    '--no-cli-pager'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2',
                'file_literals': [
                    {
                        'name': f'blob-file-{run_start_time}',
                        'binary-content': random.randbytes(128)
                    }
                ]
            },
        }, 'Local only', 'All types', protocol, 0)]

    def _get_long_list_strings(self, service_cmd, protocol):
        return [({
            'name': 'Long list of strings',
            'service_id': 'echo',
            'operation_name': 'EchoOperation',
            'command': [
                service_cmd, 'echo-operation', '--list-of-strings-member',
                *self._get_list_of_random_strings(256, 64),
                '--no-cli-pager'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2'
            },
        }, 'Local only', 'Long list of strings', protocol, 0)]

    def _get_complex_object(self, service_cmd, protocol):
        return [({
            'name': 'Complex object',
            'service_id': 'echo',
            'operation_name': 'EchoOperation',
            'command': [
                service_cmd, 'echo-operation', '--complex-struct-member',
                    f'booleanMember={random.choice([True, False])},'
                    f'blobMember@=fileb://binary-file,'
                    f'stringMember={self._get_random_string(32)},'
                    f'complexStructMember={{'f'integerMember={random.randint(-9223372036854775808, 9223372036854775807)},'
                        f'longMember={random.randint(-9223372036854775808, 9223372036854775807)},'
                        f'stringMember={self._get_random_string(32)},'
                        f'complexStructMember={{listOfStringsMember=[{",".join(self._get_list_of_random_strings(8, 32))}],complexStructMember={{mapOfStringToStringMember={self._get_string_to_string_hash_literal(8, 32, 64)}}}}}}}',
                '--no-cli-pager'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2',
                'file_literals': [
                    {
                        'name': 'binary-file',
                        'binary-content': random.randbytes(128),
                    },
                ]
            },
        }, 'Local only', 'Complex object', protocol, 0)]

    def _get_list_complex_objects(self, service_cmd, run_start_time, protocol):
        return [({
            'name': 'List of complex objects',
            'service_id': 'echo',
            'operation_name': 'EchoOperation',
            'command': [
                service_cmd, 'echo-operation', '--list-of-complex-object-member',
                *self._get_list_of_complex_objects(64, run_start_time),
                '--no-cli-pager'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2',
            },
        }, 'Local only', 'List of complex objects', protocol, 0)]

    def _get_very_large_blob(self, service_cmd, protocol):
        return [({
            'name': 'Very large blob',
            'service_id': 'echo',
            'operation_name': 'EchoOperation',
            'command': [
                service_cmd, 'echo-operation', '--blob-member',
                'fileb://large-blob-file',
                '--no-cli-pager'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2',
                'file_literals': [
                    {
                        'name': 'large-blob-file',
                        'binary-content': random.randbytes(262144)
                    }
                ]
            },
        }, 'Local only', 'Very large blob', protocol, 0)]

    def _get_echo_generators(self, run_start_time):
        return [
            lambda iteration: self._get_all_types_sequence('echo-cbor', run_start_time, 'cbor'),
            lambda iteration: self._get_long_list_strings('echo-cbor', 'cbor'),
            lambda iteration: self._get_complex_object('echo-cbor', 'cbor'),
            lambda iteration: self._get_list_complex_objects('echo-cbor', run_start_time, 'cbor'),
            lambda iteration: self._get_very_large_blob('echo-cbor', 'cbor'),
            lambda iteration: self._get_all_types_sequence('echo-json', run_start_time, 'json'),
            lambda iteration: self._get_long_list_strings('echo-json', 'json'),
            lambda iteration: self._get_complex_object('echo-json', 'json'),
            lambda iteration: self._get_list_complex_objects('echo-json', run_start_time, 'json'),
            lambda iteration: self._get_very_large_blob('echo-json', 'json'),
        ]

    def _generate_metric_data_list(self, metric_count, suite_id, base_time):
        # creates the shorthand-ready list of metric data
        return [
            f'MetricName=TestMetric,Dimensions=[{{Name=TestDimension,Value={suite_id}-{metric_count}}}],Value={random.random()},Unit=None,Timestamp={datetime.datetime.fromtimestamp(base_time + (2 * (idx + 1)))}'
        for idx in range(metric_count)]

    def _generate_put_metric_data_benchmark(self, metric_count, suite_id, base_time, service_cmd):
        return {
            'name': 'Put metric data',
            'service_id': 'cloudwatch',
            'operation_name': 'PutMetricData',
            'command': [
                service_cmd, 'put-metric-data', '--namespace', 'TestNamespace',
                '--metric-data', *self._generate_metric_data_list(metric_count, suite_id, base_time)
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2\ndisable_request_compression=true\n'
            },
        }

    def _generate_get_metric_data_benchmark(self, metric_count, suite_id, base_time, service_cmd):
        return {
            'name': 'Get metric data',
            'service_id': 'cloudwatch',
            'operation_name': 'GetMetricData',
            'command': [
                service_cmd, 'get-metric-data', '--start-time', f'{datetime.datetime.fromtimestamp(base_time)}', '--end-time', f'{datetime.datetime.fromtimestamp(base_time + 3600000)}',
                '--metric-data-queries', f'Id=m0,ReturnData=true,MetricStat={{Unit=None,Stat=Sum,Metric={{Namespace=TestNamespace,MetricName=TestMetric,Dimensions=[{{Name=TestDimension,Value={suite_id}-{metric_count}}}]}},Period=60}}'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2\ndisable_request_compression=true'
            },
        }

    def _generate_list_metric_data_benchmark(self, service_cmd):
        return {
            'name': 'List metrics',
            'service_id': 'cloudwatch',
            'operation_name': 'ListMetrics',
            'command': [
                service_cmd, 'list-metrics', '--namespace', 'TestNamespace', '--no-cli-pager'
            ],
            'environment': {
                'config': '[default]\nregion=us-west-2\ndisable_request_compression=true'
            },
        }

    def _generate_cloudwatch_benchmarks(self, suite_id, base_time):
        return [
            (self._generate_put_metric_data_benchmark(16, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Put metric data', 'cbor', 16),
            (self._generate_get_metric_data_benchmark(16, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Get metric data', 'cbor', 16),
            (self._generate_put_metric_data_benchmark(64, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Put metric data', 'cbor', 64),
            (self._generate_get_metric_data_benchmark(64, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Get metric data', 'cbor', 64),
            (self._generate_put_metric_data_benchmark(256, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Put metric data', 'cbor', 256),
            (self._generate_get_metric_data_benchmark(256, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Get metric data', 'cbor', 256),
            (self._generate_put_metric_data_benchmark(1000, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Put metric data', 'cbor', 1000),
            (self._generate_get_metric_data_benchmark(1000, suite_id, base_time, 'cloudwatch-cbor'), 'CloudWatch', 'Get metric data', 'cbor', 1000),
            (self._generate_list_metric_data_benchmark('cloudwatch-cbor'), 'CloudWatch', 'List metrics', 'cbor', 0),
            (self._generate_put_metric_data_benchmark(16, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Put metric data', 'query', 16),
            (self._generate_get_metric_data_benchmark(16, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Get metric data', 'query', 16),
            (self._generate_put_metric_data_benchmark(64, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Put metric data', 'query', 64),
            (self._generate_get_metric_data_benchmark(64, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Get metric data', 'query', 64),
            (self._generate_put_metric_data_benchmark(256, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Put metric data', 'query', 256),
            (self._generate_get_metric_data_benchmark(256, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Get metric data', 'query', 256),
            (self._generate_put_metric_data_benchmark(1000, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Put metric data', 'query', 1000),
            (self._generate_get_metric_data_benchmark(1000, suite_id, base_time, 'cloudwatch'), 'CloudWatch', 'Get metric data', 'query', 1000),
            (self._generate_list_metric_data_benchmark('cloudwatch'), 'CloudWatch', 'List metrics', 'query', 0),
        ]

    def _generate_put_plethora(self, iteration, size, run_start_time, service_cmd, protocol):
        return [
            ({
                'name': 'Put string secret',
                'service_id': 'secrets-manager',
                'operation_name': 'PutSecretValue',
                'command': [
                    service_cmd, 'put-secret-value', '--secret-id', f'TestSecret_{run_start_time}_{iteration:0>3}',
                    '--secret-string', self._get_random_string(size),
                ],
                'environment': {
                    'config': '[default]\nregion=us-west-2'
                },
            }, 'SecretsManager', 'Put string secret', protocol, size),
            ({
                'name': 'Put binary secret',
                'service_id': 'secrets-manager',
                'operation_name': 'PutSecretValue',
                'command': [
                    service_cmd, 'put-secret-value', '--secret-id', f'TestBinarySecret_{run_start_time}_{iteration:0>3}',
                    '--secret-binary', f'fileb://secret-value-{iteration}-{size}.json'
                ],
                'environment': {
                    'config': '[default]\nregion=us-west-2',
                    'file_literals': [
                        {
                            'name': f'secret-value-{iteration}-{size}.json',
                            'binary-content': random.randbytes(size)
                        }
                    ]
                },
            }, 'SecretsManager', 'Put binary secret', protocol, size),
        ]

    def _generate_get_plethora(self, iteration, run_start_time, size, service_cmd, protocol):
        return [
            ({
                'name': 'Get string secret',
                'service_id': 'secrets-manager',
                'operation_name': 'GetSecretValue',
                'command': [
                    service_cmd, 'get-secret-value', '--secret-id', f'TestSecret_{run_start_time}_{iteration:0>3}', '--no-cli-pager'
                ],
                'environment': {
                    'config': '[default]\nregion=us-west-2'
                },
            }, 'SecretsManager', 'Get string secret', protocol, size),
            ({
                'name': 'Get binary secret',
                'service_id': 'secrets-manager',
                'operation_name': 'GetSecretValue',
                'command': [
                    service_cmd, 'get-secret-value', '--secret-id', f'TestBinarySecret_{run_start_time}_{iteration:0>3}', '--no-cli-pager'
                ],
                'environment': {
                    'config': '[default]\nregion=us-west-2'
                },
            }, 'SecretsManager', 'Get binary secret', protocol, size),
        ]

    def _generate_describe_list_plethora(self, iteration, run_start_time, service_cmd, protocol):
        return [
            ({
                'name': 'Describe secret',
                'service_id': 'secrets-manager',
                'operation_name': 'DescribeSecret',
                'command': [
                    service_cmd, 'describe-secret', '--secret-id', f'TestSecret_{run_start_time}_{iteration:0>3}', '--no-cli-pager'
                ],
                'environment': {
                    'config': '[default]\nregion=us-west-2'
                },
            }, 'SecretsManager', 'Describe secret', protocol, 0),
            ({
                'name': 'List secrets',
                'service_id': 'secrets-manager',
                'operation_name': 'ListSecrets',
                'command': [
                    service_cmd, 'list-secrets', '--filters', f'Key=tag-key,Values=[{iteration}]', f'Key=tag-value,Values=[{iteration}]'
                ],
                'environment': {
                    'config': '[default]\nregion=us-west-2'
                },
            }, 'SecretsManager', 'List secrets', protocol, 0),
        ]

    def _get_secrets_iteration_generators(self, run_start_time):
        # returns a plethora case-generators
        return [
            lambda iteration: self._generate_put_plethora(iteration, 64, run_start_time, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 64, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_put_plethora(iteration, 512, run_start_time, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 512, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_put_plethora(iteration, 4096, run_start_time, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 4096, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_put_plethora(iteration, 8192, run_start_time, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 8192, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_put_plethora(iteration, 45056, run_start_time, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 45056, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_describe_list_plethora(iteration, run_start_time, 'secretsmanager-cbor', 'cbor'),
            lambda iteration: self._generate_put_plethora(iteration, 64, run_start_time, 'secretsmanager', 'json'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 64, 'secretsmanager', 'json'),
            lambda iteration: self._generate_put_plethora(iteration, 512, run_start_time, 'secretsmanager', 'json'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 512, 'secretsmanager', 'json'),
            lambda iteration: self._generate_put_plethora(iteration, 4096, run_start_time, 'secretsmanager', 'json'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 4096, 'secretsmanager', 'json'),
            lambda iteration: self._generate_put_plethora(iteration, 8192, run_start_time, 'secretsmanager', 'json'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 8196, 'secretsmanager', 'json'),
            lambda iteration: self._generate_put_plethora(iteration, 45056, run_start_time, 'secretsmanager', 'json'),
            lambda iteration: self._generate_get_plethora(iteration, run_start_time, 45056, 'secretsmanager', 'json'),
            lambda iteration: self._generate_describe_list_plethora(iteration, run_start_time, 'secretsmanager', 'json'),
        ]

    def run_benchmarks(self, args):
        """
        Orchestrates benchmarking via the benchmark definitions in
        the arguments.
        """
        summaries = {'results': []}
        result_dir = args.result_dir
        process_benchmarker = ProcessBenchmarker()
        # --- BEFORE-SUITE (resource creation, retrieve/return sequence generators, ...)
        # optionally, files per iteration could be created here all at once
        # but it is preferred to be done per-iteration to minimize the life of files
        # on the disk to the time that they're needed/used by the application
        if args.service and args.service == 'echo':
            client = StubbedHTTPClient(echo=True)
            run_start_time = int(time.time()) # seconds
            definitions = self._get_echo_generators(run_start_time)
        elif args.service and args.service == 'cloudwatch':
            # generate suite ID
            client = None
            suite_id = uuid.uuid4()
            base_time = time.time() - (2 * 60 * 60) # seconds of time two hours ago
            definitions = self._generate_cloudwatch_benchmarks(suite_id, base_time)
        elif args.service and args.service == 'secrets':
            # create initial resources (suite setup)
            session = get_session()
            client = None
            config = Config(retries={'max_attempts': 1})
            sm_cbor = session.create_client('secretsmanager-cbor', config=config, region_name='us-west-2')
            run_start_time = int(time.time())

            # Create initial remote resources, no profiling necessary
            for i in range(args.num_iterations):
                iteration = f"{i:0>3}"
                tags = [
                    {"Key": "Stage", "Value": "Production"},
                    {"Key": "Iteration", "Value": f"{iteration}"}
                ]
                string_secret_name = f"TestSecret_{run_start_time}_{iteration}"
                binary_secret_name = f"TestBinarySecret_{run_start_time}_{iteration}"
                sm_cbor.create_secret(
                    Name=string_secret_name,
                    SecretString="A temporary secret value",
                    Description=f"The testing secret for run {string_secret_name.split('_')[-1]}",
                    Tags=tags
                )
                sm_cbor.create_secret(
                    Name=binary_secret_name,
                    SecretBinary=b"A temporary secret value",
                    Description=f"The testing secret for run {binary_secret_name.split('_')[-1]}",
                    Tags=tags
                )
            definitions = self._get_secrets_iteration_generators(run_start_time)

        else:
            client = StubbedHTTPClient()
            definitions = json.load(open(args.benchmark_definitions, 'r'))
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)
        os.makedirs(result_dir, 0o777)

        #   List[CaseResult]:
        #       {
        #           service: <service name>
        #           test_case: <case name>
        #           protocol: <protocol name>
        #           dimension_value: <dimension value>
        #           List[IterationResult]:
        #               {
        #                   Collected Metrics map
        #               }
        #       }

        # transformation: for each caseresult, map to a list (size #metrics) containing one output per metric

        try:
            # --- this now becomes plethora/sequence generators. a sequence of cases to run each iteration.
            for benchmark in definitions:
                # print(benchmark)
                # --- BEFORE-ITERATION / BEGIN-SUITE (setup/reset state for generating each iteration call. including the result object(s))
                benchmark_results = {}
                if not args.service or args.service == 'cloudwatch':
                    pass
                    # benchmark_results = {}
                    # if 'dimensions' in benchmark:
                    #     benchmark_result['dimensions'] = benchmark['dimensions']
                elif args.service and args.service == 'secrets':
                    pass
                    # benchmark_results = {}
                elif args.service and args.service == 'echo':
                    pass
                    benchmark_results = {}
                for idx in range(args.num_iterations):
                    # --- BEGIN-ITERATION (generate plethora/sequence using iteration-specific information, generate resources
                    # to be used this iteration and to be cleaned up at end of iteration, apply client stubs as needed, patch env)
                    if args.service and args.service == 'secrets':
                        plethora = benchmark(idx)
                        for (case, service, test_case, protocol, dimension) in plethora:
                            if (service, test_case, protocol, dimension) not in benchmark_results:
                                benchmark_results[(service, test_case, protocol, dimension)] = []
                            # print(test_case)
                            # print(case)
                            benchmark_results[(service, test_case, protocol, dimension)].append(self._run_isolated_benchmark(
                                result_dir,
                                case,
                                client,
                                process_benchmarker,
                                args,
                            ))
                    elif args.service and args.service == 'echo':
                        sequence = benchmark(idx)
                        for (case, service, test_case, protocol, dimension) in sequence:
                            if (service, test_case, protocol, dimension) not in benchmark_results:
                                benchmark_results[(service, test_case, protocol, dimension)] = []
                            benchmark_results[(service, test_case, protocol, dimension)].append(self._run_isolated_benchmark(
                                result_dir,
                                case,
                                client,
                                process_benchmarker,
                                args,
                            ))
                    elif args.service and args.service == 'cloudwatch':
                        # print(benchmark)
                        case, service, test_case, protocol, dimension = benchmark
                        if (service, test_case, protocol, dimension) not in benchmark_results:
                            benchmark_results[(service, test_case, protocol, dimension)] = []
                        benchmark_results[(service, test_case, protocol, dimension)].append(
                            self._run_isolated_benchmark(
                                result_dir,
                                case,
                                client,
                                process_benchmarker,
                                args,
                            ))
                    else:
                        measurements = self._run_isolated_benchmark(
                            result_dir,
                            benchmark,
                            client,
                            process_benchmarker,
                            args,
                        )
                        # benchmark_result['measurements'].append(measurements) # part of the END-ITERATION nested in run_isolated benchmark

                    if args.service and (args.service == 'cloudwatch' or args.service == 'secrets'): # part of END-ITERATION
                        if idx % 50 == 0:
                            time.sleep(2)

                # --- PUSH-RESULTS (add/transform results from each case in the sequence/plethora)
                if args.service and (args.service == 'secrets' or args.service == 'echo' or args.service == 'cloudwatch'):
                    # for each caseresult, map to a list (size  # metrics) containing one output per metric
                    for ((service, case, protocol, dimension), metrics) in benchmark_results.items():
                        # Serialization time (ms)
                        serialization_measures = np.array([metric['serialization_time'] for metric in metrics if metric['serialization_time'] is not None], dtype=np.float64)
                        deserialization_measures = np.array([metric['deserialization_time'] for metric in metrics if metric['deserialization_time'] is not None], dtype=np.float64)
                        req_payload_measures = np.array([metric['request_payload_size'] for metric in metrics if metric['request_payload_size'] is not None], dtype=np.float64)
                        res_payload_measures = np.array([metric['response_payload_size'] for metric in metrics if metric['response_payload_size'] is not None], dtype=np.float64)
                        req_time_measures = np.array([metric['total_request_time'] for metric in metrics if metric['total_request_time'] is not None], dtype=np.float64)
                        serialization_case_result = {
                            'service': service,
                            'test_case': case,
                            'protocol': protocol,
                            'dimension_value': dimension,
                            'metric': 'Serialization time (ms)',
                            'p50': np.percentile(serialization_measures, 50) * 1000,
                            'p90': np.percentile(serialization_measures, 90) * 1000,
                            'max': np.max(serialization_measures) * 1000,
                        }

                        # Deserialization time (ms)
                        deserialization_case_result = {
                            'service': service,
                            'test_case': case,
                            'protocol': protocol,
                            'dimension_value': dimension,
                            'metric': 'Deserialization time (ms)',
                            'p50': np.percentile(deserialization_measures, 50) * 1000,
                            'p90': np.percentile(deserialization_measures, 90) * 1000,
                            'max': np.max(deserialization_measures) * 1000,
                        }
                        # Request payload size (bytes)
                        req_payload_case_result = {
                            'service': service,
                            'test_case': case,
                            'protocol': protocol,
                            'dimension_value': dimension,
                            'metric': 'Request payload size (bytes)',
                            'p50': np.percentile(req_payload_measures, 50),
                            'p90': np.percentile(req_payload_measures, 90),
                            'max': np.max(req_payload_measures),
                        }
                        # Response payload size (bytes)
                        res_payload_case_result = {
                            'service': service,
                            'test_case': case,
                            'protocol': protocol,
                            'dimension_value': dimension,
                            'metric': 'Response payload size (bytes)',
                            'p50': np.percentile(res_payload_measures, 50),
                            'p90': np.percentile(res_payload_measures, 90),
                            'max': np.max(res_payload_measures),
                        }
                        summaries['results'] += [serialization_case_result, deserialization_case_result, req_payload_case_result, res_payload_case_result]
                        if args.service == 'secrets' or args.service == 'cloudwatch':
                            summaries['results'].append({
                                'service': service,
                                'test_case': case,
                                'protocol': protocol,
                                'dimension_value': dimension,
                                'metric': 'Total request time (ms)',
                                'p50': np.percentile(req_time_measures, 50) * 1000,
                                'p90': np.percentile(req_time_measures, 90) * 1000,
                                'max': np.max(req_time_measures) * 1000,
                            })
                        # print('END CODE PUSH RESULTS FOR')
                        # TODO Total request time (ms) for secrets and cloudwatch
                    # summaries['results'] += benchmark_results.values()
                # summaries['results'].append(benchmark_result)

            # --- AFTER-SUITE (cleanup, resource deletion, ...)
            if args.service and args.service == 'secrets':
                # post-suite code: Clean up resources
                for i in range(args.num_iterations):
                    iteration = f"{i:0>3}"
                    string_secret_name = f"TestSecret_{run_start_time}_{iteration}"
                    binary_secret_name = f"TestBinarySecret_{run_start_time}_{iteration}"
                    sm_cbor.delete_secret(SecretId=string_secret_name)
                    sm_cbor.delete_secret(SecretId=binary_secret_name)
        finally:
            # final cleanup
            shutil.rmtree(result_dir, ignore_errors=True)
        print(json.dumps(summaries, indent=2))
