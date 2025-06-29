# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


import botocore.session
from botocore.exceptions import ClientError


def test_ambiguous_error_parsing():
    # We map errors from services to modeled errors based on the error code, but
    # cloudwatch has two errors that are both modeled to the `ResourceNotFound`
    # code: `DashboardNotFoundError` and `ResourceNotFound`.  Botocore picks the one
    # that is defined later, which in this case is `ResourceNotFound`.  This test
    # ensures that we continue to select the latter error going forward.
    session = botocore.session.get_session()
    client = session.create_client('cloudwatch', region_name='us-west-2')
    try:
        client.get_dashboard(DashboardName='dashboard-which-does-not-exist')
        assert False, "No error raised for non-existant dashboard"
    except Exception as exception:
        exception_class = exception.__class__
        error_response = exception.response['Error']
        assert isinstance(exception, ClientError)
        assert (
            f"{exception_class.__module__}.{exception_class.__name__}"
            == 'botocore.errorfactory.ResourceNotFound'
        )
        assert error_response['Type'] == 'Sender'
        assert error_response['Code'] == 'ResourceNotFound'
