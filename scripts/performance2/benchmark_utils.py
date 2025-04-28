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


class BenchmarkSuite:
    # TODO Q: How can we migrate from using sequence generators to something cleaner / more Pythonic
    # In itself, it is a complex requirement:
    #   Benchmark 1+ commands each iteration, and flowing the results back to the harness

    # Either the suite calls it or the harness calls it:
    # If harness calls it:
    #   Right now we have the suite return an ordered list of functions so the harness knows what order to call it in.
    #   This is as good as it gets because alternatives would have to do weird things like decorators to track each function order (then you can't reorder functions which is weird!)

    #   The main alternative would be for suites to control the control flow of executing the CLI command, with all function calls in a single statement (or equivalent)
    #   This would look more like the pseudocodes defined on the cbor docs, for example, with a yield between each sequence.

    # or if we don't want
    def before_suite(self, args):
        # return [sequence_generator]
        # each generator generates args.num_iterations times
        raise NotImplementedError()

    def begin_iteration(self, case, workspace_path, assets_path, iteration):
        pass

    def consume_case_results(self, case, results):
        raise NotImplementedError()

    def end_iteration(self, iteration):
        pass

    def provide_sequence_results(self):
        raise NotImplementedError()

    def after_suite(self):
        pass

# for each sequence generator
#   for each case (call to sequence generator)
#       call begin_iteration
#       run benchmark on the case
#       call suite.collect_results with (case, results)

#

# cloudwatch / secrets
# generators mostly the same, except it tracks iteration with its own loop above a yield
# stores protocol, dimension in dimensions list of the case
# stores test case in name

# in collect_results, pull the protocol, dimension, and test_case from the case
# use these store results in instance state, with dimension,protocol,test_case as key

# for EchoService,
# - Create EchoServiceSuite, override / recreate stubbed client to send request as response
#
class JSONStubbedBenchmarkSuite(BenchmarkSuite):
    def __init__(self):
        self._client = StubbedHTTPClient()
        self._benchmark_results = {}

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

    # TODO Q: do we want to abstract the stubbing code into parent
    # StubbedBenchmarkSuite ? leaning towards not at the moment
    # only observed 2 stub cases: json and echo. echo needed to define its
    # own stubbed client logic, doesn't fit the pattern of a stack of responses
    # known ahead-of-time.

    # maybe stubbedclient would be abstract, each suite can override the base impl
    # as needed. echo would override get response to return request. most suites
    # would use add response
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

    def before_suite(self, args):
        self._client = StubbedHTTPClient()
        self._benchmark_results.clear()
        definitions = json.load(open(args.benchmark_definitions, 'r'))
        return [(definition for _ in range(args.num_iterations)) for definition in definitions]

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
        # TODO Q: we're patching HTTP client & environment but not files.
        # pros and cons
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
            # todo SWITCH from binary-content key to using mode (default w)
            for file_lit in env['file_literals']:
                path = os.path.join(workspace_path, file_lit['name'])
                mode, content = ('wb', file_lit['binary-content']) if 'binary-content' in file_lit else (
                'w', file_lit['content'])
                with open(path, mode) as f:
                    os.chmod(path, 0o777)
                    f.write(content)

    def consume_case_results(self, case, results):
        # TODO when adding support for multi-command sequences to JSON,
        # the commands will become cases and each json object becomes sequences,
        # and each command will need a name/suffix to key it separately in the results
        # but for now, we can just key using the sequence name since it's 1:1 to commands

        # HOWEVER, when implementing secretsmanager, we used two structs (one command each)
        # to achieve multi-command workflows / sequences. So we should pick which of the two
        # (list of commands of list of structs with 1 command each) is more robust.

        if case['name'] not in self._benchmark_results:
            self._benchmark_results[case['name']] = {
                'name':  case['name'],
                'dimensions': case.get('dimensions', []),
                'measurements': [],
            }
        self._benchmark_results[case['name']]['measurements'].append(results)

    def end_iteration(self, iteration):
        self._client.tear_down()
        self._env_patch.stop()

    def provide_sequence_results(self):
        values = self._benchmark_results.values()
        self._benchmark_results.clear()
        return values


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
        # TODO replace with numpy calls ?
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


class ProcessBenchmarker:
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

    def _run_benchmark(self, pid, data_interval):
        process_to_measure = psutil.Process(pid)
        samples = []

        while process_to_measure.is_running():
            if process_to_measure.status() == psutil.STATUS_ZOMBIE:
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
    """
    Orchestrates running benchmarks in isolated, configurable environments defined
    via a specified JSON file.
    """
    def __init__(self):
        self._summarizer = Summarizer()

    def _run_command_with_metric_hooks(self, cmd, out_file, service_id, service_operation_name):
        """
        Runs a CLI command and logs CLI-specific metrics to a file.
        """
        first_client_invocation_time = None
        start_time = time.time()
        driver = create_clidriver()
        event_emitter = driver.session.get_component('event_emitter')

        def _log_invocation_time(params, request_signer, model, **kwargs):
            nonlocal first_client_invocation_time
            if first_client_invocation_time is None:
                first_client_invocation_time = time.time()

        event_emitter.register_last(
            'before-call',
            _log_invocation_time,
            'benchmarks.log-invocation-time',
        )

        rc = AWSCLIEntryPoint(driver).main(cmd)
        end_time = time.time()

        # write the collected metrics to a file
        # TODO swap to with open context manager
        metrics_f = open(out_file, 'w')
        metrics_f.write(
            json.dumps(
                {
                    'return_code': rc,
                    'start_time': start_time,
                    'end_time': end_time,
                    'first_client_invocation_time': first_client_invocation_time,
                }
            )
        )
        metrics_f.flush()
        os.fsync(metrics_f.fileno())
        metrics_f.close()

    def _run_isolated_benchmark(
        self, result_dir, iteration, benchmark, suite, process_benchmarker, args
    ):
        """
        Runs a single iteration of one benchmark execution. Includes setting up
        the environment, running the benchmarked execution, formatting
        the results, and cleaning up the environment.
        """
        # TODO, like the idea of splitting workspace (results) and assets to sibling folders
        assets_path = os.path.join(result_dir, 'assets')
        metrics_path = os.path.join(assets_path, 'metrics.json')
        child_output_path = os.path.join(assets_path, 'output.txt')
        child_err_path = os.path.join(assets_path, 'err.txt')

        # setup for iteration of benchmark
        suite.begin_iteration(benchmark, result_dir, assets_path, iteration)
        os.chdir(result_dir)

        # fork a child process to run the command on.
        pid = os.fork()

        try:
            if pid == 0:
                with open(child_output_path, 'w') as out, open(
                    child_err_path, 'w'
                ) as err:
                    # redirect standard output of the child process to a file
                    os.dup2(out.fileno(), sys.stdout.fileno())
                    os.dup2(err.fileno(), sys.stderr.fileno())
                    # execute command on child process
                    self._run_command_with_metric_hooks(
                        benchmark['command'], metrics_path, benchmark.get('service_id', ''), benchmark.get('operation_name', '')
                    )
                    # terminate the child process
                    os._exit(0)

            # benchmark child process from parent process until child becomes zombie
            samples = process_benchmarker.benchmark_process(
                pid, args.data_interval
            )

            # reap the child process and error on unsuccessful return codes
            _, status = os.waitpid(pid,0)
            if status != 0:
                raise RuntimeError(f'Child process execution failed: status code {status}')

            # load child-collected metrics
            if not os.path.exists(metrics_path):
                raise RuntimeError(
                    'Child process execution failed: output file not found.'
                )
            metrics_f = json.load(open(metrics_path, 'r'))

            # raise error if CLI execution unsuccessful.
            # this is different from the process return code checked above,
            # because the process can succeed while the CLI execution failed
            if (rc := metrics_f['return_code']) != 0:
                with open(child_err_path, 'r') as err:
                    raise RuntimeError(
                        f'CLI execution failed: return code {rc}.\n'
                        f'Error: {err.read()}'
                    )

            # summarize benchmark results and process summary
            # TODO Q: move the summarizer to the suites?
            # that would support the use case when a specific format is needed (e.g. cbor benchmarks)
            # this would mean consume_case_results gets the raw results
            # and provide_sequence_results calls (internal) summary on each metrics data in the sequence
            summary = self._summarizer.summarize(samples)
            summary['total_time'] = (
                metrics_f['end_time'] - metrics_f['start_time']
            )
            summary['first_client_invocation_time'] = (
                metrics_f['first_client_invocation_time']
                - metrics_f['start_time']
            )
        finally:
            # --- END-ITERATION (cleanup of resources made in BEGIN-ITERATION, reset the result directory, ...)
            suite.end_iteration(iteration)
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir, 0o777)
        return summary

    def run_benchmarks(self, suite: BenchmarkSuite, args):
        """
        Orchestrates benchmarking via the benchmark definitions in
        the arguments.
        """
        summaries = {'results': []}
        result_dir = args.result_dir
        process_benchmarker = ProcessBenchmarker()
        # --- BEFORE-SUITE (resource creation, retrieve/return sequence generators, ...)
        # optionally, files per iteration could be created here all at once (e.g. for caching reasons)
        # but it is preferred to be done per-iteration to minimize the life of files
        # on the disk to the time that they're needed/used by the application
        sequence_generators = suite.before_suite(args)
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)
        os.makedirs(result_dir, 0o777)

        try:
            for seq_generator in sequence_generators:
                # --- BEFORE-ITERATION / BEGIN-SUITE (setup/reset state for generating each iteration call. including the result object(s))
                benchmark_results = {}

                for idx in range(args.num_iterations):
                    # --- BEGIN-ITERATION (generate plethora/sequence using iteration-specific information, generate resources
                    # to be used this iteration and to be cleaned up at end of iteration, apply client stubs as needed, patch env)
                    for test_case in seq_generator:
                        # BEGIN-ITERATION and END-ITERATION. two options:
                        # 1) Have them both called here. So this function owns the logic for calling the suite functions,
                        # and run_isolated_benchmark can focus on running the benchmark itself.
                        # 2) Run them in the isolated benchmark. This way we can guarantee that all environment setup
                        # has been done before calling begin_iteration.
                        # A use case of #2 is mocking client responses with env files, which was done in the
                        # s3transfer suite.

                        # Im leaning towards pulling the setup and cleanup code into this function
                        # and pulling suite begin and end iteration here as well.
                        # To prevent passing so many paths between functions, we can store them
                        # in the class state (maybe in constructor if possible).

                        # Next, do we want a function that gets called to cleanup in the case
                        # there was an exception? Currently, that's end_iteration whether there
                        # was an exception. Maybe we can pass exception information to end_iteration.

                        # TODO NEXT: finalize these architecture changes. and TODOs
                        suite.consume_case_results(test_case, self._run_isolated_benchmark(
                            result_dir,
                            idx,
                            test_case,
                            suite,
                            process_benchmarker,
                            args,
                        ))


                # --- PROVIDE-SEQUENCE-RESULTS (add/transform results from each case in the sequence/plethora)
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

