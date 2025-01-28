import csv
import json
import math
import time
import psutil

import s3transfer
import os
import subprocess
import uuid
import shutil
import argparse
import tempfile
from awscli.botocore.awsrequest import AWSResponse

from unittest import mock
from awscli.clidriver import AWSCLIEntryPoint, create_clidriver
from awscli.compat import BytesIO


class Summarizer:
    DATA_INDEX_IN_ROW = {'time': 0, 'memory': 1, 'cpu': 2}

    def __init__(self):
        self._num_rows = 0
        self._start_time = None
        self._end_time = None
        self._averages = {
            'memory': 0.0,
            'cpu': 0.0,
        }
        self._samples = {
            'memory': [],
            'cpu': [],
        }
        self._maximums = {'memory': 0.0, 'cpu': 0.0}

    def summarize(self, benchmark_file):
        """Processes the data from the CSV file"""
        with open(benchmark_file) as f:
            reader = csv.reader(f)
            # Process each row from the CSV file
            row = None
            for row in reader:
                self._validate_row(row, benchmark_file)
                self.process_data_row(row)
            self._validate_row(row, benchmark_file)
            self._end_time = self._get_time(row)
            metrics = self._finalize_processed_data_for_file()
        return metrics

    def _validate_row(self, row, filename):
        if not row:
            raise RuntimeError(
                f'Row: {row} could not be processed. The CSV file ({filename}) may be '
                'empty.'
            )

    def process_data_row(self, row):
        # If the row is the first row collect the start time.
        if self._num_rows == 0:
            self._start_time = self._get_time(row)
        self._num_rows += 1
        self.process_data_point(row, 'memory')
        self.process_data_point(row, 'cpu')

    def process_data_point(self, row, name):
        # Determine where in the CSV row the requested data is located.
        index = self.DATA_INDEX_IN_ROW[name]
        # Get the data point.
        data_point = float(row[index])
        self._add_to_average(name, data_point)
        self._account_for_maximum(name, data_point)
        self._samples[name].append(data_point)

    def _finalize_processed_data_for_file(self):
        self._samples['memory'].sort()
        self._samples['cpu'].sort()
        metrics = {
            'time': self._end_time - self._start_time,
            'average_memory': self._averages['memory'] / self._num_rows,
            'average_cpu': self._averages['cpu'] / self._num_rows,
            'max_memory': self._maximums['memory'],
            'max_cpu': self._maximums['cpu'],
            'memory_p50': self._compute_metric_percentile(50, 'memory'),
            'memory_p95': self._compute_metric_percentile(95, 'memory'),
            'cpu_p50': self._compute_metric_percentile(50, 'cpu'),
            'cpu_p95': self._compute_metric_percentile(95, 'cpu'),
        }
        # Reset some of the data needed to be tracked for each execution
        self._num_rows = 0
        self._maximums = self._maximums.fromkeys(self._maximums, 0.0)
        self._averages = self._averages.fromkeys(self._averages, 0.0)
        self._samples['memory'].clear()
        self._samples['cpu'].clear()
        return metrics

    def _compute_metric_percentile(self, percentile, name):
        num_samples = len(self._samples[name])
        p_idx = math.ceil(percentile*num_samples/100) - 1
        return self._samples[name][p_idx]

    def _get_time(self, row):
        return float(row[self.DATA_INDEX_IN_ROW['time']])

    def _add_to_average(self, name, data_point):
        self._averages[name] += data_point

    def _account_for_maximum(self, name, data_point):
        if data_point > self._maximums[name]:
            self._maximums[name] = data_point


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
    Periodically samples CPU and memory usage of a process given its pid. Writes
    all collected samples to a CSV file.
    """
    def benchmark_process(self, pid, output_file, data_interval):
        parent_pid = os.getpid()
        try:
            # Benchmark the process where the script is being run.
            self._run_benchmark(pid, output_file, data_interval)
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


    def _run_benchmark(self, pid, output_file, data_interval):
        process_to_measure = psutil.Process(pid)
        output_f = open(output_file, 'w')

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

            # Save all the data into a CSV file.
            output_f.write(
                f"{current_time},{memory_used},{cpu_percent}\n"
            )
            output_f.flush()


class BenchmarkHarness(object):
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

    def _default_config_file_contents(self):
        return (
            '[default]'
        )

    def _create_file_with_size(self, path, size):
        """
        Creates a full-access file in the given directory with the
        specified name and size.
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
        to be created is specified by file_count.
        """
        os.mkdir(dir_path, 0o777)
        for i in range(int(file_count)):
            file_path = os.path.join(dir_path, f'{i}')
            self._create_file_with_size(file_path, size)

    def _setup_environment(self, env, result_dir, config_file):
        """
        Creates all files / directories defined in the env struct.
        Also, writes a config file named 'config' to the result directory
        with contents optionally specified by the env struct.
        """
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
        with open(config_file, 'w') as f:
            f.write(env.get('config', self._default_config_file_contents()))
            f.flush()

    def _setup_iteration(
            self,
            benchmark,
            client,
            result_dir,
            performance_dir,
            config_file
    ):
        """
        Performs the setup for a single iteration of a benchmark. This
        includes creating the files used by a command and stubbing
        the HTTP client to use during execution.
        """
        env = benchmark.get('environment', {})
        self._setup_environment(env, result_dir, config_file)
        client.setup()
        self._stub_responses(
            benchmark.get('responses', [{"headers": {}, "body": ""}]),
            client
        )
        if os.path.exists(performance_dir):
            shutil.rmtree(performance_dir)
        os.makedirs(performance_dir, 0o777)

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

    def _run_command_with_metric_hooks(self, cmd, result_dir):
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
        AWSCLIEntryPoint(driver).main(cmd)
        end_time = time.time()

        # write the collected metrics to a file
        metrics_f = open(os.path.join(result_dir, 'metrics.json'), 'w')
        metrics_f.write(json.dumps(
            {
                'start_time': start_time,
                'end_time': end_time,
                'first_client_invocation_time': first_client_invocation_time
            }
        ))
        metrics_f.close()
        os._exit(0)

    def _run_isolated_benchmark(
            self,
            result_dir,
            performance_dir,
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
        out_file = os.path.join(performance_dir, 'performance.csv')
        assets_dir = os.path.join(result_dir, 'assets')
        config_file = os.path.join(assets_dir, 'config')
        # setup for iteration of benchmark
        self._setup_iteration(benchmark, client, result_dir, performance_dir, config_file)
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
                self._run_command_with_metric_hooks(benchmark['command'], result_dir)

            # benchmark child process from parent process until child terminates
            process_benchmarker.benchmark_process(
                pid,
                out_file,
                args.data_interval
            )
            # summarize benchmark results and process summary
            summary = self._summarizer.summarize(out_file)
            # load the internally-collected metrics and append to the summary
            metrics_f = json.load(open(os.path.join(result_dir, 'metrics.json'), 'r'))
            # override the summarizer's sample-based timing with the
            # wall-clock time measured by the child process
            del summary['time']
            summary['total_time'] = metrics_f['end_time'] - metrics_f['start_time']
            summary['first_client_invocation_time'] = (metrics_f['first_client_invocation_time']
                                                       - metrics_f['start_time'])
        finally:
            # cleanup iteration of benchmark
            client.tearDown()
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir, 0o777)
            shutil.rmtree(assets_dir, ignore_errors=True)
            os.makedirs(assets_dir, 0o777)
            env_patch.stop()
            self._time_of_call = None
        return summary

    def run_benchmarks(self, args):
        """
        Orchestrates benchmarking via the benchmark definitions in
        the arguments.
        """
        summaries = {'results': []}
        result_dir = args.result_dir
        assets_dir = os.path.join(result_dir, 'assets')
        performance_dir = os.path.join(result_dir, 'performance')
        client = StubbedHTTPClient()
        process_benchmarker = ProcessBenchmarker()
        definitions = json.load(open(args.benchmark_definitions, 'r'))
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)
        os.makedirs(result_dir, 0o777)
        if os.path.exists(assets_dir):
            shutil.rmtree(assets_dir)
        os.makedirs(assets_dir, 0o777)

        try:
            for benchmark in definitions:
                benchmark_result = {
                    'name': benchmark['name'],
                    'dimensions': benchmark['dimensions'],
                    'measurements': []
                }
                for _ in range(args.num_iterations):
                    measurements = self._run_isolated_benchmark(
                        result_dir,
                        performance_dir,
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


def summarize(script, result_dir, summary_dir):
    """Run the given summary script on every file in the given directory.

    :param script: A summarization script that takes a list of csv files.
    :param result_dir: A directory containing csv performance result files.
    :param summary_dir: The directory to put the summary file in.
    """
    summarize_args = [script]
    for f in os.listdir(result_dir):
        path = os.path.join(result_dir, f)
        if os.path.isfile(path):
            summarize_args.append(path)

    with open(os.path.join(summary_dir, 'summary.txt'), 'wb') as f:
        subprocess.check_call(summarize_args, stdout=f)
    with open(os.path.join(summary_dir, 'summary.json'), 'wb') as f:
        summarize_args.extend(['--output-format', 'json'])
        subprocess.check_call(summarize_args, stdout=f)


def _get_s3transfer_performance_script(script_name):
    """Retrieves an s3transfer performance script if available."""
    s3transfer_directory = os.path.dirname(s3transfer.__file__)
    s3transfer_directory = os.path.dirname(s3transfer_directory)
    scripts_directory = 'scripts/performance'
    scripts_directory = os.path.join(s3transfer_directory, scripts_directory)
    script = os.path.join(scripts_directory, script_name)

    if os.path.isfile(script):
        return script
    else:
        return None


def get_benchmark_script():
    return _get_s3transfer_performance_script('benchmark')


def get_summarize_script():
    return _get_s3transfer_performance_script('summarize')


def backup(source, recursive):
    """Backup a given source to a temporary location.

    :type source: str
    :param source: A local path or s3 path to backup.

    :type recursive: bool
    :param recursive: if True, the source will be treated as a directory.
    """
    if source[:5] == 's3://':
        parts = source.split('/')
        parts.insert(3, str(uuid.uuid4()))
        backup_path = '/'.join(parts)
    else:
        name = os.path.split(source)[-1]
        temp_dir = tempfile.mkdtemp()
        backup_path = os.path.join(temp_dir, name)

    copy(source, backup_path, recursive)
    return backup_path


def copy(source, destination, recursive):
    """Copy files from one location to another.

    The source and destination must both be s3 paths or both be local paths.

    :type source: str
    :param source: A local path or s3 path to backup.

    :type destination: str
    :param destination: A local path or s3 path to backup the source to.

    :type recursive: bool
    :param recursive: if True, the source will be treated as a directory.
    """
    if 's3://' in [source[:5], destination[:5]]:
        cp_args = ['aws', 's3', 'cp', source, destination, '--quiet']
        if recursive:
            cp_args.append('--recursive')
        subprocess.check_call(cp_args)
        return

    if recursive:
        shutil.copytree(source, destination)
    else:
        shutil.copy(source, destination)


def clean(destination, recursive):
    """Delete a file or directory either locally or on S3."""
    if destination[:5] == 's3://':
        rm_args = ['aws', 's3', 'rm', '--quiet', destination]
        if recursive:
            rm_args.append('--recursive')
        subprocess.check_call(rm_args)
    else:
        if recursive:
            shutil.rmtree(destination)
        else:
            os.remove(destination)


def create_random_subfolder(destination):
    """Create a random subdirectory in a given directory."""
    folder_name = str(uuid.uuid4())
    if destination.startswith('s3://'):
        parts = destination.split('/')
        parts.append(folder_name)
        return '/'.join(parts)
    else:
        parts = list(os.path.split(destination))
        parts.append(folder_name)
        path = os.path.join(*parts)
        os.makedirs(path)
        return path


def get_transfer_command(command, recursive, quiet):
    """Get a full cli transfer command.

    Performs common transformations, e.g. adding --quiet
    """
    cli_command = 'aws s3 ' + command

    if recursive:
        cli_command += ' --recursive'

    if quiet:
        cli_command += ' --quiet'
    else:
        print(cli_command)

    return cli_command


def benchmark_command(command, benchmark_script, summarize_script,
                      output_dir, num_iterations, dry_run, upkeep=None,
                      cleanup=None):
    """Benchmark several runs of a long-running command.

    :type command: str
    :param command: The full aws cli command to benchmark

    :type benchmark_script: str
    :param benchmark_script: A benchmark script that takes a command to run
        and outputs performance data to a file. This should be from s3transfer.

    :type summarize_script: str
    :param summarize_script:  A summarization script that the output of the
        benchmark script. This should be from s3transfer.

    :type output_dir: str
    :param output_dir: The directory to output performance results to.

    :type num_iterations: int
    :param num_iterations: The number of times to run the benchmark on the
        command.

    :type dry_run: bool
    :param dry_run: Whether or not to actually run the benchmarks.

    :type upkeep: function that takes no arguments
    :param upkeep: A function that is run after every iteration of the
        benchmark process. This should be used for upkeep, such as restoring
        files that were deleted as part of the command executing.

    :type cleanup: function that takes no arguments
    :param cleanup: A function that is run at the end of the benchmark
        process or if there are any problems during the benchmark process.
        It should be uses for the final cleanup, such as deleting files that
        were created at some destination.
    """
    performance_dir = os.path.join(output_dir, 'performance')
    if os.path.exists(performance_dir):
        shutil.rmtree(performance_dir)
    os.makedirs(performance_dir)

    try:
        for i in range(num_iterations):
            out_file = 'performance%s.csv' % i
            out_file = os.path.join(performance_dir, out_file)
            benchmark_args = [
                benchmark_script, command, '--output-file', out_file
            ]
            if not dry_run:
                subprocess.check_call(benchmark_args)
                if upkeep is not None:
                    upkeep()

        if not dry_run:
            summarize(summarize_script, performance_dir, output_dir)
    finally:
        if not dry_run and cleanup is not None:
            cleanup()


def get_default_argparser():
    """Get an ArgumentParser with all the base benchmark arguments added in."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--no-cleanup', action='store_true', default=False,
        help='Do not remove the destination after the tests complete.'
    )
    parser.add_argument(
        '--recursive', action='store_true', default=False,
        help='Indicates that this is a recursive transfer.'
    )
    benchmark_script = get_benchmark_script()
    parser.add_argument(
        '--benchmark-script', default=benchmark_script,
        required=benchmark_script is None,
        help=('The benchmark script to run the commands with. This should be '
              'from s3transfer.')
    )
    summarize_script = get_summarize_script()
    parser.add_argument(
        '--summarize-script', default=summarize_script,
        required=summarize_script is None,
        help=('The summarize script to run the commands with. This should be '
              'from s3transfer.')
    )
    parser.add_argument(
        '-o', '--result-dir', default='results',
        help='The directory to output performance results to. Existing '
             'results will be deleted.'
    )
    parser.add_argument(
        '--dry-run', default=False, action='store_true',
        help='If set, commands will only be printed out, not executed.'
    )
    parser.add_argument(
        '--quiet', default=False, action='store_true',
        help='If set, output is suppressed.'
    )
    parser.add_argument(
        '-n', '--num-iterations', default=1, type=int,
        help='The number of times to run the test.'
    )
    return parser