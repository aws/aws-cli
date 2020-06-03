#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import shutil
import tempfile
import os
import zipfile

from unittest import TestCase
from awscli.customizations.cloudformation.artifact_exporter import make_zip
from awscli.customizations.cloudformation.yamlhelper import yaml_dump
from awscli.customizations.cloudformation.artifact_exporter import Template
from awscli.testutils import skip_if_windows


class TestPackageZipFiles(TestCase):

    def setUp(self):
        self.rootdir = tempfile.mkdtemp()
        self.ziproot = os.path.join(self.rootdir, "zipcontents")

        os.mkdir(self.ziproot)

    def tearDown(self):
        shutil.rmtree(self.rootdir)

    @skip_if_windows(
        "Symlinks are not supported on Python 2.x + Windows, and require "
        "administrator privleges on Python 3.x + Windows."
    )
    def test_must_follow_symlinks(self):
        data = "hello world"
        data_file = os.path.join(self.rootdir, "data.txt")

        with open(data_file, "w") as fp:
            fp.write(data)

        # Create symlink within the zip root
        link_name = os.path.join(self.ziproot, "data-link.txt")
        os.symlink(data_file, link_name)

        # Zip up the contents of folder `ziproot` which contains the symlink
        zipfile_path = make_zip(os.path.join(self.rootdir, "archive"), self.ziproot)

        # Now verify that the zipfile includes contents of the data file we created
        myzip = zipfile.ZipFile(zipfile_path)
        # Data file should be the only file within the zip
        self.assertEquals(["data-link.txt"], myzip.namelist())
        myfile = myzip.open("data-link.txt", "r")

        # Its content should be equal the value we wrote.
        self.assertEquals(data.encode("utf-8"), myfile.read())


def test_known_templates():
    test_case_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'deploy_templates'
    )
    for case in os.listdir(test_case_path):
        case_path = os.path.join(test_case_path, case)
        yield (
            _assert_input_does_match_expected_output,
            os.path.join(case_path, 'input.yml'),
            os.path.join(case_path, 'output.yml'),
        )


def _assert_input_does_match_expected_output(input_template, output_template):
    template = Template(input_template, os.getcwd(), None)
    exported = template.export()
    result = yaml_dump(exported)
    expected = open(output_template, 'r').read()

    assert result == expected, (
        '\nAcutal template:\n'
        '%s'
        '\nDiffers from expected template:\n'
        '%s' % (
            result, expected
        )
    )
