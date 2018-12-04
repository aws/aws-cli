import s3transfer
import os
import subprocess
import uuid
import shutil
import argparse
import tempfile


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
