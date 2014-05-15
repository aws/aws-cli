# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from awscli.customizations.emr import constants


def build_hbase_restore_from_backup_args(dir, backup_version=None):
    args = [constants.HBASE_MAIN,
            constants.HBASE_RESTORE,
            constants.HBASE_BACKUP_DIR, dir]

    if backup_version is not None:
        args.append(constants.HBASE_BACKUP_VERSION_FOR_RESTORE)
        args.append(backup_version)

    return args