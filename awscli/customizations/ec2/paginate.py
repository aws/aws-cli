# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
DEFAULT_MAX_RESULTS = 1000


def set_max_results_default(parsed_args, parsed_globals, **kwargs):
    """
    In order to have EC2 return results you can paginate you need to inject
    the `MaxItems` parameter. In the CLI we should be setting this by default
    to avoid users having to wait exceedingly long times for the full results.
    """

    # The check for page size validates that the operation is a pagination
    # operation.
    if parsed_globals.paginate and hasattr(parsed_args, 'page_size') and \
            parsed_args.page_size is None and parsed_args.max_results is None:
        parsed_args.page_size = DEFAULT_MAX_RESULTS
