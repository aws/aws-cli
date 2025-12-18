# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import sys
import webbrowser

from awscli.customizations.commands import BasicCommand


class OpenConsoleCommand(BasicCommand):
    NAME = 'console'
    DESCRIPTION = (
        'Open the AWS Management Console in the default browser.'
    )
    ARG_TABLE = [
    ]

    def __init__(
        self,
        session,
        token_loader=None,
        config_file_writer=None,
    ):
        super().__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        console_url = 'https://console.aws.amazon.com/'
        try:
            webbrowser.open_new_tab(console_url)
        except webbrowser.Error:
            print(f'Failed to open browser. Please visit: {console_url}', file=sys.stderr)
            return 1
        return 0
