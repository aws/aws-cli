# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import sys
from functools import partial

from awscli.compat import urlopen
from awscli.customizations.commands import BasicCommand
from awscli.utils import create_nested_client


class GetGameSessionLogCommand(BasicCommand):
    NAME = 'get-game-session-log'
    DESCRIPTION = 'Download a compressed log file for a game session.'
    ARG_TABLE = [
        {'name': 'game-session-id', 'required': True,
         'help_text': 'The game session ID'},
        {'name': 'save-as', 'required': True,
         'help_text': 'The filename to which the file should be saved (.zip)'}
    ]

    def _run_main(self, args, parsed_globals):
        client = create_nested_client(
            self._session, 'gamelift', region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )

        # Retrieve a signed url.
        response = client.get_game_session_log_url(
            GameSessionId=args.game_session_id)
        url = response['PreSignedUrl']

        # Retrieve the content from the presigned url and save it locally.
        contents = urlopen(url)

        sys.stdout.write(
            'Downloading log archive for game session %s...\r' %
            args.game_session_id
        )

        with open(args.save_as, 'wb') as f:
            for chunk in iter(partial(contents.read, 1024), b''):
                f.write(chunk)

        sys.stdout.write(
            'Successfully downloaded log archive for game '
            'session %s to %s\n' % (args.game_session_id, args.save_as))

        return 0
