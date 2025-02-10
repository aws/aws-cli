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


DELETE = {'name': 'delete', 'action': 'store_true',
          'help_text': (
              "Files that exist in the destination but not in the source are "
              "deleted during sync. Note that files excluded by filters are "
              "excluded from deletion.")}


class DeleteSync(BaseSync):

    ARGUMENT = DELETE

    def determine_should_sync(self, src_file, dest_file):
        dest_file.operation_name = 'delete'
        LOG.debug("syncing: (None) -> %s (remove), file does not "
                  "exist at source (%s) and delete mode enabled",
                  dest_file.src, dest_file.dest)
        return True
