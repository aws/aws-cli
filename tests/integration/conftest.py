# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# These files only exercise local service models (no AWS calls) and are
# parametrized over every CLI command or operation, so they contain most of
# the integration tests. They are distributed across workers per test
# instead of running every test in the file on a single worker.
_DISTRIBUTE_PER_TEST = (
    'integration/customizations/test_generatecliskeleton.py',
    'integration/botocore/test_utils.py',
)

# These files contain many slow, independent test classes, so they are
# distributed across workers per class instead of per file. Their shared
# fixtures (e.g. S3 buckets) are package scoped, so each worker creates its
# own.
_DISTRIBUTE_PER_CLASS = ('integration/customizations/s3/test_plugin.py',)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    # With ``--dist loadgroup``, tests in the same ``xdist_group`` run on the
    # same worker and ungrouped tests are distributed individually. Grouping
    # the remaining tests by file preserves the ``--dist loadfile`` behavior
    # they rely on, such as sharing module and class scoped fixtures that
    # create AWS resources.
    for item in items:
        parts = item.nodeid.split('::')
        path = parts[0]
        if path.endswith(_DISTRIBUTE_PER_TEST):
            continue
        if path.endswith(_DISTRIBUTE_PER_CLASS) and len(parts) > 2:
            group = '::'.join(parts[:2])
        else:
            group = path
        item.add_marker(pytest.mark.xdist_group(group))
