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

from awscli.customizations.s3.subcommands import NO_OVERWRITE
from awscli.customizations.s3.syncstrategy.base import BaseSync

LOG = logging.getLogger(__name__)


class NoOverwriteSync(BaseSync):
    """Sync strategy that prevents overwriting of existing files at the destination.
    This strategy will only sync files that don't exist at the destination.
    If a file exists at both source and destination, it will be skipped regardless
    of size or modification time differences.
    """

    ARGUMENT = NO_OVERWRITE

    def determine_should_sync(self, src_file, dest_file):
        if not dest_file:
            # Sync if file does not exist at destination
            return True
        elif src_file.compare_key != dest_file.compare_key:
            # Sync if file exists at both source and destination but the
            # source file's key is different than the destination file's key
            return True
        else:
            # Skip if file exists at both source and destination
            LOG.debug(
                "Warning: Skipping file %s as it already exists on %s",
                src_file.src,
                src_file.dest,
            )
            return False
