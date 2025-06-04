import json
import math
import sys
import time
import psutil
import os
import shutil

from awscli.clidriver import AWSCLIEntryPoint, create_clidriver
from scripts.performance.tests import BaseBenchmarkSuite
from scripts.performance.tests.simple_stubbed_tests import JSONStubbedBenchmarkSuite


class Metric:
    def __init__(self, description, unit, value):
        self.description = description
        self.unit = unit
        self.value = value

class BenchmarkResultsSerializer:
    """
    A class that serializes the execution results of a performance test case.
    """

    def __init__(self):
        self._summarizer = Summarizer()
        self._benchmark_results = {}

    def add_execution_results(self, case, samples, execution_results):
        """
        Store a performance test case's execution result.
        """
        summarized_results = self._summarizer.summarize(samples, execution_results)
        for (metric, val) in summarized_results.items():
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

    def get_processed_results(self):
        """
        Returns a list of dictionaries representing all stored execution
        results. The key-value pairs will be converted to JSON and displayed as part
        of the final output.
        """
        return list(self._benchmark_results.values())

    def reset(self):
        """
        Resets the stored list of execution results.
        """
        self._benchmark_results.clear()


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

    def summarize(self, samples, worker_results):
        """
        Processes benchmark data from samples and the output of the benchmark
        worker.
        """
        self._samples = samples
        self._validate_samples(samples)
        for idx, sample in enumerate(samples):
            # If the sample is the first one, collect the start time.
            if idx == 0:
                self._start_time = self._get_time(sample)
            self.process_data_sample(sample)
        self._end_time = self._get_time(samples[-1])
        metrics = self._finalize_processed_data_for_file(samples, worker_results)
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

    def _finalize_processed_data_for_file(self, samples, worker_results):
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
            'mean.run.memory': Metric(
                'Mean memory usage of a single command execution.',
                'Bytes',
                self._sums['memory'] / len(samples)
            ),
            'mean.run.cpu': Metric(
                'Mean CPU usage of a single command execution.',
                'Percent',
                self._sums['cpu'] / len(samples)
            ),
            'peak.run.memory': Metric(
                'Peak memory usage of a single command execution.',
                'Bytes',
                max_memory
            ),
            'peak.run.cpu': Metric(
                'Peak CPU usage of a single command execution.',
                'Percent',
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
                'Percent',
                cpu_p50
            ),
            'p95.run.cpu': Metric(
                'p95 CPU usage of a single command execution.',
                'Percent',
                cpu_p95
            ),
            'run.time': Metric(
                'Total running time of the Python process executing the CLI command.',
                'Seconds',
                worker_results['end_time'] - worker_results['start_time'],
            ),
            'pre.marshal.time': Metric(
                'Elapsed time from the start of the Python process until just '
                'before the HTTP request is created.',
                'Seconds',
                worker_results['first_client_invocation_time'] - worker_results['start_time']
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


class ProcessBenchmarker:
    """
    Periodically samples CPU and memory usage of a process given its pid.
    These measurements are sampled until the process is no longer running.
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
    Orchestrates running benchmarks in isolated, configurable environments.
    """
    def __init__(self, results_processor=BenchmarkResultsSerializer()):
        self._results_processor = results_processor

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
            'benchmarks.log-invocation-time',
        )

        rc = AWSCLIEntryPoint(driver).main(cmd)
        end_time = time.time()

        # write the collected metrics to a file
        with open(out_file, 'w') as metrics_f:
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

    def _run_isolated_benchmark(
        self, result_dir, iteration, benchmark, suite, process_benchmarker, args
    ):
        """
        Runs a single iteration of one benchmark execution. Includes setting up
        the environment, running the benchmarked execution, formatting
        the results, and cleaning up the environment.
        """
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
                    self._run_command_with_metric_hooks(benchmark['command'], metrics_path)
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
            worker_results = json.load(open(metrics_path, 'r'))

            # raise error if CLI execution unsuccessful.
            # this is different from the process return code checked above,
            # because the process can succeed while the CLI execution failed
            if (rc := worker_results['return_code']) != 0:
                with open(child_err_path, 'r') as err:
                    raise RuntimeError(
                        f'CLI execution failed: return code {rc}.\n'
                        f'Error: {err.read()}'
                    )

            # summarize benchmark results and process summary
            return samples, worker_results
        finally:
            suite.end_iteration(benchmark, iteration)
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir, 0o777)

    def get_test_suites(self, args):
        """
        Returns all test suites that should be executed by the default
        performance test runner.
        """
        return [suite() for suite in BenchmarkHarness.BENCHMARK_SUITES]

    def run_benchmarks(self, cases, args):
        """
        Orchestrates benchmarking via the supplied list of performance test
        cases.
        """
        summaries = {'results': []}
        result_dir = args.result_dir
        process_benchmarker = ProcessBenchmarker()

        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)
        os.makedirs(result_dir, 0o777)
        try:
            for (suite, case) in cases:
                for idx in range(args.num_iterations):
                    for cmd in case:
                        samples, execution_results = self._run_isolated_benchmark(
                            result_dir,
                            idx,
                            cmd,
                            suite,
                            process_benchmarker,
                            args,
                        )
                        self._results_processor.add_execution_results(
                            cmd,
                            samples,
                            execution_results
                        )
                summaries['results'].extend(self._results_processor.get_processed_results())
                self._results_processor.reset()
        finally:
            # final cleanup
            shutil.rmtree(result_dir, ignore_errors=True)
        print(json.dumps(summaries, indent=2))


    def run_benchmark_suite(self, suite: BaseBenchmarkSuite, args):
        """
        Orchestrates benchmarking a particular benchmark suite.
        """
        sequence_generators = suite.get_test_cases(args)
        self.run_benchmarks(sequence_generators, args)