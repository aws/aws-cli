#!/usr/bin/env python
import argparse
import gc
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, REPO_ROOT)

# Importing awscli installs the meta path finder that aliases the
# top-level "botocore"/"s3transfer" imports to the vendored copies under
# awscli/. Must happen before `import botocore...`.
import awscli  # noqa: E402, F401
import awscli.clidriver  # noqa: E402
import botocore.loaders  # noqa: E402
import botocore.session  # noqa: E402

SERVICES = ['ec2', 's3', 'signin', 'dynamodb']

# A no-required-arg operation per service, for the end-to-end subprocess
# benchmark. Each reaches request serialization/signing and attempts a
# connection before failing, so the command must be syntactically valid
# but needs no real resources.
#
# signin is deliberately excluded here even though it's in SERVICES:
# unlike every other service, its endpoint resolution does not honor
# --endpoint-url, so the e2e recipe's "fail fast against a local closed
# port" trick doesn't apply - it would instead send a real request to
# AWS. That's fine for the in-process benchmarks below (no network
# involved), but not for something this script runs in a loop.
E2E_OPERATIONS = [
    ('ec2', 'describe-instances'),
    # The CLI command namespace is "s3api" (the thin, direct mapping onto
    # the "s3" service model loaded in SERVICES above); "s3" is the
    # separate, higher-level customization layer on top of it.
    ('s3api', 'list-buckets'),
    ('dynamodb', 'list-tables'),
]


def timeit(func, iterations, warmup=3, *args, **kwargs):
    """Run func(*args, **kwargs) `warmup` times (untimed, to pull the
    service data into the OS page cache so the measurement reflects the
    code's own cost rather than cold-disk I/O noise), then `iterations`
    times, each as its own timed sample. Returns the timed samples, in
    seconds."""
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(warmup):
            func(*args, **kwargs)
        samples = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            func(*args, **kwargs)
            samples.append(time.perf_counter() - t0)
    finally:
        if gc_was_enabled:
            gc.enable()
    return samples


def summarize(samples):
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    p50 = sorted_samples[n // 2]
    p95 = sorted_samples[min(n - 1, int(n * 0.95))]
    mean = statistics.mean(samples)
    stdev = statistics.stdev(samples) if n > 1 else 0.0
    # Relative standard deviation / coefficient of variation, and the
    # standard error of the mean - the two numbers that actually tell you
    # whether `mean_ms` is trustworthy or just noise.
    cv_pct = (stdev / mean * 100) if mean else 0.0
    sem_ms = (stdev / (n ** 0.5)) * 1000 if n > 1 else 0.0
    return {
        'min_ms': min(samples) * 1000,
        'mean_ms': mean * 1000,
        'stdev_ms': stdev * 1000,
        'cv_pct': cv_pct,
        'sem_ms': sem_ms,
        'p50_ms': p50 * 1000,
        'p95_ms': p95 * 1000,
        'max_ms': max(samples) * 1000,
        'n': n,
    }


# ---------------------------------------------------------------------------
# Individual benchmark cases. Each returns {case_name: samples}.
# ---------------------------------------------------------------------------

def bench_list_available_services_cold(iterations, warmup):
    results = {}
    for type_name in ('service-2', 'paginators-1', 'waiters-2'):
        def run(type_name=type_name):
            loader = botocore.loaders.Loader()
            loader.list_available_services(type_name)

        results[f'list_available_services({type_name}) [cold loader]'] = (
            timeit(run, iterations, warmup)
        )
    return results


def bench_load_service_model_cold(iterations, warmup):
    results = {}
    for service_name in SERVICES:
        def run(service_name=service_name):
            loader = botocore.loaders.Loader()
            loader.load_service_model(service_name, 'service-2')

        results[f'load_service_model({service_name}) [cold loader]'] = (
            timeit(run, iterations, warmup)
        )
    return results


def bench_json_file_loader(iterations, warmup):
    """Benchmarks the actual production code path - JSONFileLoader.load_file
    - rather than a bare json.loads() on pre-read bytes. This includes the
    file open/read/decode that load_file does on every call, not just the
    parse."""
    results = {}
    data_dir = botocore.loaders.Loader.BUILTIN_DATA_PATH
    file_loader = botocore.loaders.JSONFileLoader()
    for service_name in SERVICES:
        service_dir = os.path.join(data_dir, service_name)
        api_version = sorted(os.listdir(service_dir))[-1]
        # load_file() takes the path *without* the .json suffix - it
        # appends that itself.
        path_without_suffix = os.path.join(
            service_dir, api_version, 'service-2'
        )

        def run(path_without_suffix=path_without_suffix):
            file_loader.load_file(path_without_suffix)

        results[f'JSONFileLoader.load_file({service_name})'] = timeit(
            run, iterations, warmup
        )
    return results


def bench_multi_type_name_same_loader(iterations, warmup):
    """What a real `aws` invocation actually does: one process/Loader
    touching several type_names in sequence for one service (e.g. ec2
    loads service-2, waiters-2, paginators-1, and endpoint-rule-set-1).
    The isolated single-type_name cases above don't exercise this -
    they measure first-touch cost, not repeat-touch-with-a-different-
    type_name cost on the same instance."""

    def run():
        loader = botocore.loaders.Loader()
        for type_name in (
            'service-2',
            'waiters-2',
            'paginators-1',
            'endpoint-rule-set-1',
        ):
            loader.list_available_services(type_name)

    return {
        'list_available_services, 4 type_names, 1 loader [cold]': timeit(
            run, iterations, warmup
        )
    }


def bench_e2e_cli_invocation(iterations, warmup):
    """True end-to-end: spawn a real `aws <command>` subprocess and time
    the whole thing - Python startup, CLIDriver command-table build,
    service model discovery/load, argument parsing, request
    serialization, and signing.

    To stay fast, deterministic, and fully offline:
      * AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are fake static values,
        so credential resolution doesn't probe IMDS or SSO over the
        network.
      * --endpoint-url points at 127.0.0.1 on a port nothing listens on,
        so the connection fails (refused) in under a millisecond instead
        of hitting real AWS.
      * AWS_MAX_ATTEMPTS=1 and --cli-connect-timeout 1 disable retries,
        so one failed connection attempt doesn't turn into a multi-second
        retry-with-backoff loop.
    The command therefore always exits non-zero (connection error) - that
    failure happens *after* everything this script's other benchmarks
    measure, so timing it end-to-end still captures their cost.
    """
    aws_entry_point = os.path.join(REPO_ROOT, 'bin', 'aws')
    fake_home = tempfile.mkdtemp(prefix='aws-bench-home-')
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': fake_home,
        'AWS_ACCESS_KEY_ID': 'AKIAFAKEFAKEFAKEFAKE',
        'AWS_SECRET_ACCESS_KEY': 'fakefakefakefakefakefakefakefakefakefake',
        'AWS_MAX_ATTEMPTS': '1',
    }

    results = {}
    for service_name, operation in E2E_OPERATIONS:
        command = [
            sys.executable,
            aws_entry_point,
            service_name,
            operation,
            '--region',
            'us-east-1',
            '--endpoint-url',
            'http://127.0.0.1:1',
            '--cli-connect-timeout',
            '1',
        ]

        def run(command=command):
            subprocess.run(command, capture_output=True, env=env)

        results[f'e2e: aws {service_name} {operation}'] = timeit(
            run, iterations, warmup
        )
    return results


def bench_session_get_available_services(iterations, warmup):
    def run():
        session = botocore.session.Session()
        session.get_available_services()

    return {
        'Session().get_available_services() [cold session]': timeit(
            run, iterations, warmup
        )
    }


def bench_clidriver_command_table(iterations, warmup):
    """End-to-end: what every single `aws` invocation pays to build its
    top-level command table, before the requested operation even starts
    executing."""

    def run():
        driver = awscli.clidriver.create_clidriver()
        driver._get_command_table()

    return {
        'CLIDriver: full command table build [cold]': timeit(
            run, iterations, warmup
        )
    }


BENCHMARKS = [
    ('Directory-scan validation cost (loaders.py)', bench_list_available_services_cold),
    ('load_service_model, cold (scan + parse)', bench_load_service_model_cold),
    ('JSONFileLoader.load_file (real production path)', bench_json_file_loader),
    ('Multiple type_names, one loader (realistic per-invocation cost)', bench_multi_type_name_same_loader),
    ('Session.get_available_services (clidriver dependency)', bench_session_get_available_services),
    ('CLIDriver command table build (end-to-end)', bench_clidriver_command_table),
    ('True end-to-end: real `aws <command>` subprocess', bench_e2e_cli_invocation),
]

# bench_e2e_cli_invocation spawns a real subprocess per sample (~0.3-0.4s
# each), far slower than the in-process cases, so it gets its own
# (smaller) iteration count via --e2e-iterations instead of --iterations.
E2E_BENCHMARK = bench_e2e_cli_invocation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--iterations',
        type=int,
        default=20,
        help='Number of timed samples per case (default: 20).',
    )
    parser.add_argument(
        '--warmup',
        type=int,
        default=3,
        help=(
            'Untimed calls run before the timed samples, to pull service '
            'data into the OS page cache (default: 3). Does not warm '
            'botocore\'s own @instance_cache for "cold loader" cases, '
            'since those construct a fresh Loader on every call.'
        ),
    )
    parser.add_argument(
        '--e2e-iterations',
        type=int,
        default=10,
        help=(
            'Number of real `aws` subprocess invocations to time for the '
            'end-to-end case (default: 10). Each spawn costs ~0.3-0.4s, '
            'far more than the in-process cases, so this is intentionally '
            'separate from --iterations.'
        ),
    )
    parser.add_argument(
        '--skip-e2e',
        action='store_true',
        help='Skip the subprocess-spawning end-to-end case entirely.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit raw results as JSON instead of a formatted table.',
    )
    args = parser.parse_args()

    benchmarks = BENCHMARKS
    if args.skip_e2e:
        benchmarks = [
            (name, func)
            for name, func in BENCHMARKS
            if func is not E2E_BENCHMARK
        ]

    all_results = {}
    high_variance = []
    for group_name, bench_func in benchmarks:
        if not args.json:
            print(f'\n== {group_name} ==')
        iterations = (
            args.e2e_iterations
            if bench_func is E2E_BENCHMARK
            else args.iterations
        )
        case_results = bench_func(iterations, args.warmup)
        for case_name, samples in case_results.items():
            stats = summarize(samples)
            all_results[case_name] = stats
            if stats['cv_pct'] > 10:
                high_variance.append((case_name, stats['cv_pct']))
            if not args.json:
                print(
                    f'  {case_name:55s} '
                    f'mean={stats["mean_ms"]:7.3f}ms  '
                    f'stdev={stats["stdev_ms"]:6.3f}ms  '
                    f'cv={stats["cv_pct"]:5.1f}%  '
                    f'sem={stats["sem_ms"]:6.3f}ms  '
                    f'p50={stats["p50_ms"]:7.3f}ms  '
                    f'p95={stats["p95_ms"]:7.3f}ms  '
                    f'min={stats["min_ms"]:7.3f}ms'
                )

    if args.json:
        print(json.dumps(all_results, indent=2))
    elif high_variance:
        print(
            f'\nNote: {len(high_variance)} case(s) have CV > 10% - the mean '
            f'is noisy. Re-run with a higher --iterations, close other '
            f'apps, and prefer p50 over mean for these:'
        )
        for case_name, cv_pct in high_variance:
            print(f'  - {case_name} (cv={cv_pct:.1f}%)')


if __name__ == '__main__':
    main()
