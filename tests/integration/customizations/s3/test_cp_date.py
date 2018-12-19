# -*- coding: utf-8 -*-
# Copyright 2018 Transposit Corporation. All Rights Reserved.
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
#
# Written by Al Nikolov <root@toor.fi.eu.org>
#
# The following tests are performed to ensure that the `aws s3 cp --date`
# command works as expected at a glance

import filecmp
import os.path
import time

import awscli.testutils

def dircmp(dcmp):
    """Recursively compare directories and files"""
    if dcmp.left_only:
        return "Left %s (%s %s)" % (dcmp.left_only, dcmp.left, dcmp.right)
    if dcmp.right_only:
        return "Right %s (%s %s)" % (dcmp.right_only, dcmp.left, dcmp.right)
    if dcmp.diff_files:
        return "Diff %s (%s %s)" % (dcmp.diff_files, dcmp.left, dcmp.right)
    for sub in dcmp.subdirs.values():
        res = dircmp(sub)
        if res:
            return res

class S3CpDateTest(awscli.testutils.BaseS3CLICommand):
    """Test `cp --date` command capability to copy older versions of S3 files

    5 local direcories represent distint revisions of the same files. They are
    uploaded consecutively with a significant delay.
    """

    delay = 5
    s3_scheme = "s3://"
    s3_prefix = "s3-"
    mod = {}

    def sync_up(self, ver):
        """Call `s3 sync` and assert success, record the latest modification
        timestamp for this version
        """
        res = awscli.testutils.aws(
            "s3 sync --delete %s %s"
            % (self.files.full_path(ver), self.s3_scheme + self.t_bucket)
        )
        self.assert_no_errors(res)
        time.sleep(self.delay)
        versions = self.client.list_object_versions(
            Bucket=self.t_bucket
        )
        scope = versions.get("DeleteMarkers", []) + versions.get("Versions", [])
        self.mod[ver] = sorted(
            [ mark["LastModified"] for mark in scope ]
        )[-1]

    def purge_versions(self):
        """Purge all versions from S3"""
        versions = self.client.list_object_versions(
            Bucket=self.t_bucket
        )
        scope = versions.get("DeleteMarkers", []) + versions.get("Versions", [])
        self.client.delete_objects(
            Bucket=self.t_bucket,
            Delete={
                "Objects": [
                    {"Key": mark["Key"], "VersionId": mark["VersionId"]}
                    for mark in scope
                ]
            }
        )

    def extra_setup(self):
        # Create a versionned bucket
        self.t_bucket = self.create_bucket()
        self.addCleanup(self.purge_versions)
        self.client.put_bucket_versioning(
            Bucket=self.t_bucket,
            VersioningConfiguration={"Status": "Enabled"})

        # Create the 1st revision of files
        ver = "v1"
        self.files.create_file(os.path.join(ver, "foo"), "")
        self.files.create_file(os.path.join(ver, "bar"), "")
        self.files.create_file(os.path.join(ver, "dir", "foo"), "")
        self.files.create_file(os.path.join(ver, "dir", "bar"), "")
        self.sync_up(ver)

        # Create the 2nd revision of files:
        # "foo" is modified
        # "dir/foo" is removed
        ver = "v2"
        self.files.create_file(os.path.join(ver, "foo"), "x")
        self.files.create_file(os.path.join(ver, "bar"), "")
        self.files.create_file(os.path.join(ver, "dir", "bar"), "")
        self.sync_up(ver)

        # Create the 3rd revision of files:
        # "foo" is modified
        # "dir/foo" is restored as in v1
        ver = "v3"
        self.files.create_file(os.path.join(ver, "foo"), "xx")
        self.files.create_file(os.path.join(ver, "bar"), "")
        self.files.create_file(os.path.join(ver, "dir", "foo"), "")
        self.files.create_file(os.path.join(ver, "dir", "bar"), "")
        self.sync_up(ver)

        # Create the 4th revision of files:
        # "foo" and "bar" are removed
        # "dir/foo" is modified
        ver = "v4"
        self.files.create_file(os.path.join(ver, "dir", "foo"), "x")
        self.files.create_file(os.path.join(ver, "dir", "bar"), "")
        self.sync_up(ver)

        # Create the 5th revision of files:
        # "foo" and "bar" are restored as in v1
        # "dir" is removed
        ver = "v5"
        self.files.create_file(os.path.join(ver, "foo"), "")
        self.files.create_file(os.path.join(ver, "bar"), "")
        self.sync_up(ver)

    def test_cp_date(self):
        """Recursively download each single version of all files from S3 bucket
        and compare to the local files
        """
        for ver in "v1", "v2", "v3", "v4", "v5":
            date = self.mod[ver].isoformat()
            res = awscli.testutils.aws(
                "s3 cp --recursive --date %s %s %s" % (
                    date,
                    self.s3_scheme + self.t_bucket,
                    self.files.full_path(self.s3_prefix + ver)
                )
            )
            self.assert_no_errors(res)
            compare = filecmp.dircmp(
                self.files.full_path(ver),
                self.files.full_path(self.s3_prefix + ver)
            )
            self.assertIsNone(dircmp(compare))
