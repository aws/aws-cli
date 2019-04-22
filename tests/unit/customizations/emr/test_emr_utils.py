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

from awscli.customizations.emr.emrutils import which
from awscli.customizations.emr.emrutils import apply_boolean_options
from nose.tools import assert_equal
from nose.tools import assert_not_equal


class TestEMRutils(object):

    def test_which_with_existing_command(self):
        pythonPath = which('python') or which('python.exe')
        assert_not_equal(pythonPath, None)

    def test_which_with_non_existing_command(self):
        path = which('klajsflklj')
        assert_equal(path, None)

    def test_apply_boolean_options_true_option(self):
        boolean_option = apply_boolean_options(True, '', None, '')
        assert_equal(boolean_option, True)

    def test_apply_boolean_options_false_option(self):
        boolean_option = apply_boolean_options(None, '', True, '')
        assert_equal(boolean_option, False)

    def test_apply_boolean_options_none_option(self):
        boolean_option = apply_boolean_options(None, '', None, '')
        assert_equal(boolean_option, None)
