import json
import math
import time
import psutil

import os
import shutil
from awscli.botocore.awsrequest import AWSResponse

from unittest import mock
from awscli.clidriver import AWSCLIEntryPoint, create_clidriver
from awscli.compat import BytesIO


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
        p_idx = math.ceil(percentile*num_samples/100) - 1
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
    def setup(self):
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
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
            raw=RawResponse(body.encode())
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

    def _run_benchmark(self, pid, data_interval):
        process_to_measure = psutil.Process(pid)
        samples = []

        while process_to_measure.is_running():
            if process_to_measure.status() == psutil.STATUS_ZOMBIE:
                process_to_measure.kill()
                break
            time.sleep(data_interval)
            try:
                # Collect the memory and cpu usage.
                memory_used = process_to_measure.memory_info().rss
                cpu_percent = process_to_measure.cpu_percent()
            except (psutil.AccessDenied, psutil.ZombieProcess):
                # Trying to get process information from a closed or
                # zombie process will result in corresponding exceptions.
                break
            # Determine the lapsed time for bookkeeping
            current_time = time.time()
            samples.append({
                "time": current_time, "memory": memory_used, "cpu": cpu_percent
            })
        return samples


class BenchmarkHarness(object):
    _DEFAULT_FILE_CONFIG_CONTENTS = "[default]"

    """
    Orchestrates running benchmarks in isolated, configurable environments defined
    via a specified JSON file.
    """
    def __init__(self):
        self._summarizer = Summarizer()

    def _get_default_env(self, config_file):
        return {
            'AWS_CONFIG_FILE': config_file,
            'AWS_DEFAULT_REGION': 'us-west-2',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key'
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

    def _setup_iteration(
            self,
            benchmark,
            client,
            result_dir,
            config_file
    ):
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
                    file_dir_def['file_size']
                )
        if "file_literals" in env:
            for file_lit in env['file_literals']:
                path = os.path.join(result_dir, file_lit['name'])
                f = open(path, 'w')
                os.chmod(path, 0o777)
                f.write(file_lit['content'])
                f.close()
        # create config file at specified path
        with open(config_file, 'w') as f:
            f.write(env.get('config', self._DEFAULT_FILE_CONFIG_CONTENTS))
            f.flush()
        # setup and stub HTTP client
        client.setup()
        self._stub_responses(
            benchmark.get('responses', [{"headers": {}, "body": ""}]),
            client
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

    def _run_command_with_metric_hooks(self, cmd, out_file):
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
            'benchmarks.log-invocation-time'
        )
        rc = AWSCLIEntryPoint(driver).main(cmd)
        end_time = time.time()

        # write the collected metrics to a file
        metrics_f = open(out_file, 'w')
        metrics_f.write(json.dumps(
            {
                'return_code': rc,
                'start_time': start_time,
                'end_time': end_time,
                'first_client_invocation_time': first_client_invocation_time
            }
        ))
        metrics_f.close()
        # terminate the process
        os._exit(0)

    def _run_isolated_benchmark(
            self,
            result_dir,
            benchmark,
            client,
            process_benchmarker,
            args
    ):
        """
        Runs a single iteration of one benchmark execution. Includes setting up
        the environment, running the benchmarked execution, formatting
        the results, and cleaning up the environment.
        """
        assets_dir = os.path.join(result_dir, 'assets')
        config_file = os.path.join(assets_dir, 'config')
        metrics_file = os.path.join(result_dir, 'metrics.json')
        os.makedirs(assets_dir, 0o777)
        # setup for iteration of benchmark
        self._setup_iteration(benchmark, client, result_dir, config_file)
        os.chdir(result_dir)
        # patch the OS environment with our supplied defaults
        env_patch = mock.patch.dict('os.environ', self._get_default_env(config_file))
        env_patch.start()
        # fork a child process to run the command on.
        # the parent process benchmarks the child process until the child terminates.
        pid = os.fork()

        try:
            # execute command on child process
            if pid == 0:
                self._run_command_with_metric_hooks(benchmark['command'], metrics_file)
            # benchmark child process from parent process until child terminates
            samples = process_benchmarker.benchmark_process(
                pid,
                args.data_interval
            )
            # load child-collected metrics if exists
            if not os.path.exists(metrics_file):
                raise RuntimeError('Child process execution failed: output file not found.')
            metrics_f = json.load(open(os.path.join(result_dir, 'metrics.json'), 'r'))
            # raise error if child process failed
            if (rc := metrics_f['return_code']) != 0:
                raise RuntimeError(f'Child process execution failed: return code {rc}')
            # summarize benchmark results and process summary
            summary = self._summarizer.summarize(samples)
            summary['total_time'] = metrics_f['end_time'] - metrics_f['start_time']
            summary['first_client_invocation_time'] = (metrics_f['first_client_invocation_time']
                                                       - metrics_f['start_time'])
        finally:
            # cleanup iteration of benchmark
            client.tearDown()
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir, 0o777)
            env_patch.stop()
        return summary

    def run_benchmarks(self, args):
        """
        Orchestrates benchmarking via the benchmark definitions in
        the arguments.
        """
        summaries = {'results': []}
        result_dir = args.result_dir
        client = StubbedHTTPClient()
        process_benchmarker = ProcessBenchmarker()
        definitions = json.load(open(args.benchmark_definitions, 'r'))
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)
        os.makedirs(result_dir, 0o777)

        try:
            for benchmark in definitions:
                benchmark_result = {
                    'name': benchmark['name'],
                    'measurements': []
                }
                if 'dimensions' in benchmark:
                    benchmark_result['dimensions'] = benchmark['dimensions']
                for _ in range(args.num_iterations):
                    measurements = self._run_isolated_benchmark(
                        result_dir,
                        benchmark,
                        client,
                        process_benchmarker,
                        args
                    )
                    benchmark_result['measurements'].append(measurements)
                summaries['results'].append(benchmark_result)
        finally:
            # final cleanup
            shutil.rmtree(result_dir, ignore_errors=True)
        print(json.dumps(summaries, indent=2))
