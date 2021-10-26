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
import pytest


@pytest.mark.usefixtures('clean_shared_buckets')
class BaseS3IntegrationTest:
    def assert_no_errors(self, p):
        assert p.rc == 0, (
            f'Non zero rc ({p.rc}) received: {p.stdout + p.stderr}'
        )
        assert 'Error:' not in p.stderr
        assert 'failed:' not in p.stderr
        assert 'client error' not in p.stderr
        assert 'server error' not in p.stderr
