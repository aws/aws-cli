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


SIZE_ONLY = {'name': 'size-only', 'action': 'store_true',
             'help_text': (
                 'Makes the size of each key the only criteria used to '
                 'decide whether to sync from source to destination.')}


class SizeOnlySync(BaseSync):

    ARGUMENT = SIZE_ONLY

    def determine_should_sync(self, src_file, dest_file):
        same_size = self.compare_size(src_file, dest_file)
        should_sync = not same_size
        if should_sync:
            LOG.debug("syncing: %s -> %s, size_changed: %s",
                      src_file.src, src_file.dest, not same_size)
        return should_sync
