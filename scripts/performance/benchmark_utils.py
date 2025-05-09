import json
import math
import sys
import time
import psutil

import os
import shutil
from awscli.botocore.awsrequest import AWSResponse

from unittest import mock
from awscli.clidriver import AWSCLIEntryPoint, create_clidriver
from awscli.compat import BytesIO


class Metric:
    def __init__(self, description, unit, value):
        self.description = description
        self.unit = unit
        self.value = value

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
    def get_test_cases(self, args):
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
            # todo SWITCH from binary-content key to using mode (default w)
            for file_lit in env['file_literals']:
                path = os.path.join(workspace_path, file_lit['name'])
                mode, content = ('wb', file_lit['binary-content']) if 'binary-content' in file_lit else (
                'w', file_lit['content'])
                with open(path, mode) as f:
                    os.chmod(path, 0o777)
                    f.write(content)

    def consume_case_results(self, case, results):
        for (metric, val) in results.items():
            key = f'{case["name"]}.{metric}'
            if key not in self._benchmark_results:
                self._benchmark_results[key] = {
                    'name': key,
                    'description': val.description,
                    'unit': val.unit,
                    'dimensions': case.get('dimensions', []),
                    'measurements': [],
                }
            self._benchmark_results[key]['measurements'].append(val.value)

    def end_iteration(self, iteration):
        self._client.tear_down()
        self._env_patch.stop()

    def provide_sequence_results(self):
        values = list(self._benchmark_results.values())
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
        # TODO replace with numpy calls
        memory_p50 = self._compute_metric_percentile(50, 'memory')
        memory_p95 = self._compute_metric_percentile(95, 'memory')
        self._samples.sort(key=self._get_cpu)
        cpu_p50 = self._compute_metric_percentile(50, 'cpu')
        cpu_p95 = self._compute_metric_percentile(95, 'cpu')
        max_memory = max(samples, key=self._get_memory)['memory']
        max_cpu = max(samples, key=self._get_cpu)['cpu']
        # format computed statistics
        metrics = {
            'mean.run.memory': Metric(
                'Mean memory usage of a single command execution.',
                'Bytes',
                self._sums['memory'] / len(samples)
            ),
            'mean.run.cpu': Metric(
                'Mean CPU usage of a single command execution.',
                'Percentage',
                self._sums['cpu'] / len(samples)
            ),
            'peak.run.memory': Metric(
                'Peak memory usage of a single command execution.',
                'Bytes',
                max_memory
            ),
            'peak.run.cpu': Metric(
                'Peak CPU usage of a single command execution.',
                'Percentage',
                max_cpu
            ),
            'p50.run.memory': Metric(
                'p50 memory usage of a single command execution.',
                'Bytes',
                memory_p50
            ),
            'p95.run.memory': Metric(
                'p95 memory usage of a single command execution.',
                'Bytes',
                memory_p95
            ),
            'p50.run.cpu': Metric(
                'p50 CPU usage of a single command execution.',
                'Percentage',
                cpu_p50
            ),
            'p95.run.cpu': Metric(
                'p95 CPU usage of a single command execution.',
                'Percentage',
                cpu_p95
            ),
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


class BenchmarkHarness:
    BENCHMARK_SUITES = [JSONStubbedBenchmarkSuite]
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
                    if not args.debug_dir:
                        # redirect standard output of the child process to a file
                        os.dup2(out.fileno(), sys.stdout.fileno())
                        os.dup2(err.fileno(), sys.stderr.fileno())
                    else:
                        with open(
                            os.path.abspath(
                                os.path.join(
                                    args.debug_dir,
                                    f'{benchmark["name"]}-{iteration}.txt',
                                )
                            ),
                            'w',
                        ) as f:
                            with open(
                                os.path.abspath(
                                    os.path.join(
                                        args.debug_dir,
                                        f'{benchmark["name"]}-{iteration}-err.txt',
                                    )
                                ),
                                'w',
                            ) as f_err:
                                os.dup2(f.fileno(), sys.stdout.fileno())
                                os.dup2(f_err.fileno(), sys.stderr.fileno())
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

            # LEANING TOWARDS NO. should be easy to override the summarizer when needed
            # for one-off investigations/goals. but benchmark_utils must maintain a
            # contract in its output format

            summary = self._summarizer.summarize(samples)
            # TODO move the below internal metrics summarization into the summarizer by accepting
            # extra internal-metric input ?
            summary['run.time'] = Metric(
                'Total running time of the Python process executing the CLI command.',
                'Seconds',
                metrics_f['end_time'] - metrics_f['start_time'],
            )
            summary['pre.marshal.time'] = Metric(
                'Elapsed time from the start of the Python process until just before the HTTP '
                'request is created.',
                'Seconds',
                metrics_f['first_client_invocation_time'] - metrics_f['start_time']
            )
        finally:
            # --- END-ITERATION (cleanup of resources made in BEGIN-ITERATION, reset the result directory, ...)
            suite.end_iteration(iteration)
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir, 0o777)
        return summary

    def get_test_suites(self, args):
        return [suite() for suite in BenchmarkHarness.BENCHMARK_SUITES]

    def run_benchmarks(self, cases, args):
        """
        Orchestrates benchmarking via the supplied list of test case
        generators.
        """
        summaries = {'results': []}
        result_dir = args.result_dir
        process_benchmarker = ProcessBenchmarker()

        # --- BEGIN-SUITE (resource creation, retrieve/return sequence generators, ...)
        # optionally, files per iteration could be created here all at once (e.g. for caching reasons)
        # but it is preferred to be done per-iteration to minimize the life of files
        # on the disk to the time that they're needed/used by the application, and to
        # not rely on shared state between tests
        # .. temporarily removed begin-suite to discourage sharing state between tests
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)
        os.makedirs(result_dir, 0o777)
        try:
            for (suite, case) in cases:
                # --- BEFORE-ITERATION / BEGIN-SUITE (setup/reset state for generating each iteration call. including the result object(s))
                for idx in range(args.num_iterations):
                    # --- BEGIN-ITERATION (generate plethora/sequence using iteration-specific information, generate resources
                    # to be used this iteration and to be cleaned up at end of iteration, apply client stubs as needed, patch env)
                    for cmd in case:
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
                        suite.consume_case_results(cmd, self._run_isolated_benchmark(
                            result_dir,
                            idx,
                            cmd,
                            suite,
                            process_benchmarker,
                            args,
                        ))
                # --- PROVIDE-SEQUENCE-RESULTS (add/transform results from each case in the sequence/plethora)
                summaries['results'].extend(suite.provide_sequence_results())

            # --- END-SUITE (cleanup, resource deletion, ...)
            # temporarily removed end-suite to disincentive sharing state between tests
        finally:
            # final cleanup
            shutil.rmtree(result_dir, ignore_errors=True)
        print(json.dumps(summaries, indent=2))


    def run_benchmark_suite(self, suite: BenchmarkSuite, args):
        """
        Orchestrates benchmarking via the benchmark definitions in
        the arguments.
        """
        # --- GET-TEST-CASES (retrieve case generators)
        sequence_generators = suite.get_test_cases(args)
        self.run_benchmarks(sequence_generators, args)