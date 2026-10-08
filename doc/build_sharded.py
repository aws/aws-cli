#!/usr/bin/env python
"""Builds Sphinx output in batches of services instead of one sphinx-build
over the entire site.

A single sphinx-build invocation holds the doctree/cross-reference
environment for every generated page in memory for the whole build. Since
the AWS CLI reference docs are hundreds of independent services, that peak
scales with the full site rather than any one service. This script runs
sphinx-build once per batch of services (plus the shared top-level/topic
pages every time), each with its own fresh doctree environment, so peak
memory is bounded by the batch size instead of the whole site.

Each batch writes into the same output directory. Pages for services
outside the current batch are excluded from that invocation (via the
DOC_SHARD_EXCLUDE env var read by conf.py) and are produced by their own
batch instead, so the final output directory ends up with the full site
after all batches complete.

Known limitation: Sphinx's search index (searchindex.js) and sitemap are
regenerated per batch, scoped only to the batch's own pages, and the final
batch's version is what's left on disk. Site search across the full
service catalog needs a separate merge step before this replaces the
monolithic build in production.
"""
import argparse
import os
import subprocess
import sys

SOURCE_DIR = 'source'
REF_DIR_NAME = 'reference'


def discover_services(source_dir):
    ref_path = os.path.join(source_dir, REF_DIR_NAME)
    return sorted(
        d
        for d in os.listdir(ref_path)
        if os.path.isdir(os.path.join(ref_path, d))
    )


def batches(services, batch_size):
    for i in range(0, len(services), batch_size):
        yield services[i : i + batch_size]


def run_batch(batch_num, total_batches, batch, all_services, args):
    exclude = [
        f'{REF_DIR_NAME}/{svc}/**' for svc in all_services if svc not in batch
    ]
    env = dict(os.environ)
    env['DOC_SHARD_EXCLUDE'] = '::'.join(exclude)
    doctree_dir = os.path.join(args.doctree_root, f'shard-{batch_num}')
    cmd = [
        'sphinx-build',
        '-b',
        args.builder,
        '-d',
        doctree_dir,
        args.source_dir,
        args.outputdir,
    ]
    print(
        f'--- batch {batch_num}/{total_batches}: '
        f'{batch[0]}..{batch[-1]} ({len(batch)} services) ---',
        file=sys.stderr,
    )
    subprocess.run(cmd, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-b', '--builder', default='html')
    parser.add_argument('-o', '--outputdir', default='build/html')
    parser.add_argument('--source-dir', default=SOURCE_DIR)
    parser.add_argument('--doctree-root', default='build/doctrees-sharded')
    parser.add_argument('--batch-size', type=int, default=40)
    parser.add_argument(
        '--limit-services',
        type=int,
        default=None,
        help='Only process the first N services (for local testing).',
    )
    args = parser.parse_args()

    services = discover_services(args.source_dir)
    if args.limit_services:
        services = services[: args.limit_services]

    service_batches = list(batches(services, args.batch_size))
    print(
        f'{len(services)} services in {len(service_batches)} batch(es) of '
        f'up to {args.batch_size}',
        file=sys.stderr,
    )

    for batch_num, batch in enumerate(service_batches, start=1):
        run_batch(
            batch_num, len(service_batches), batch, services, args
        )


if __name__ == '__main__':
    main()
