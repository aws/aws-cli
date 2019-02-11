# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging

from awscli.customizations.s3.syncstrategy.base import BaseSync


LOG = logging.getLogger(__name__)

REMOTE_ETAG = {
    'name': 'remote-etag',
    'action': 'store_true',
    'help_text': ('Compare remote ETags to decide whether to sync from source to destination.')
}


class RemoteEtagSync(BaseSync):

    ARGUMENT = REMOTE_ETAG

    def determine_should_sync(self, src_file, dest_file):
        src_etag = '""'
        if src_file and src_file.response_data:
            src_etag = src_file.response_data.get('ETag', '""').lower()

        dest_etag = '""'
        if dest_file and dest_file.response_data:
            dest_etag = dest_file.response_data.get('ETag', '""').lower()

        should_sync = False

        cmd = src_file.operation_name
        if cmd == 'copy':
            should_sync = not (src_etag == dest_etag)

        if should_sync:
            LOG.debug(
                "syncing: %s -> %s, etag: %s -> %s",
                src_file.src, src_file.dest,
                src_etag, dest_etag)

        return should_sync

