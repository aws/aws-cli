# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Run the fake credential daemon by hand.

    scripts/credential-daemon-mock serve
    export AWS_CREDENTIAL_DAEMON_SOCKET=<the path serve prints>
    scripts/credential-daemon-mock call credential/list
    scripts/credential-daemon-mock call mock/set_principal \\
        '{"principal": "arn:aws:sts::123456789012:assumed-role/Admin/bob"}'
"""

import argparse
import json
import logging
import sys

from tests.utils.credential_daemon._protocol import (
    DEFAULT_PRINCIPAL,
)
from tests.utils.credential_daemon.rawclient import RawClient, RawRpcError
from tests.utils.credential_daemon.server import (
    FakeCredentialDaemon,
    default_socket_path,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='credential-daemon-mock',
        description=(
            'A fake credential daemon for developing the CLI against.'
        ),
    )
    commands = parser.add_subparsers(dest='command', required=True)

    serve = commands.add_parser('serve', help='run the fake daemon')
    serve.add_argument('--socket', default=default_socket_path())
    serve.add_argument(
        '--signin',
        choices=['auto', 'manual'],
        default='auto',
        help=(
            'auto finishes each browser sign-in after --signin-delay; '
            'manual waits for "call mock/complete_signin"'
        ),
    )
    serve.add_argument('--signin-delay', type=float, default=1.0)
    serve.add_argument(
        '--principal',
        default=DEFAULT_PRINCIPAL,
        help='who signs in, until mock/set_principal changes it',
    )
    serve.add_argument(
        '--backing-profile',
        help=(
            'hand out real credentials from this profile, so commands '
            'reach AWS'
        ),
    )
    serve.add_argument('--credential-minutes', type=float, default=15)
    serve.add_argument('--session-days', type=float, default=90)
    serve.add_argument('--auth-timeout', type=float, default=300)
    serve.add_argument('-v', '--verbose', action='store_true')

    call = commands.add_parser(
        'call', help='send one call and print its result'
    )
    call.add_argument('method')
    call.add_argument('params', nargs='?', default='{}')
    call.add_argument('--socket', default=default_socket_path())

    args = parser.parse_args(argv)
    if args.command == 'serve':
        return _serve(args)
    return _call(args)


def _serve(args):
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s %(message)s',
    )
    fake = FakeCredentialDaemon(
        socket_path=args.socket,
        signin=args.signin,
        signin_delay=args.signin_delay,
        auth_timeout=args.auth_timeout,
        credential_lifetime=int(args.credential_minutes * 60),
        session_lifetime=int(args.session_days * 24 * 3600),
        backing_profile=args.backing_profile,
    )
    fake.next_principal = args.principal
    fake.start()
    print(
        f'Fake credential daemon listening on {fake.socket_path}\n'
        f'Point the CLI at it with:\n'
        f'  export AWS_CREDENTIAL_DAEMON_SOCKET={fake.socket_path}',
        flush=True,
    )
    try:
        fake.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def _call(args):
    try:
        params = json.loads(args.params)
    except ValueError as e:
        print(f'params must be JSON: {e}', file=sys.stderr)
        return 2
    with RawClient(args.socket, timeout=None) as client:
        try:
            result = client.call(
                args.method,
                params,
                on_notification=lambda _, n: print(
                    json.dumps(n), file=sys.stderr
                ),
            )
        except RawRpcError as e:
            print(
                json.dumps(
                    {'code': e.code, 'message': e.message, 'data': e.data}
                ),
                file=sys.stderr,
            )
            return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
