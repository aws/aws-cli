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
"""Disable endpoint url customizations for s3.

There's a customization in botocore such that for S3 operations
we try to fix the S3 endpoint url based on whether a bucket is
dns compatible.  We also try to map the endpoint url to the
standard S3 region (s3.amazonaws.com).  This normally happens
even if a user provides an --endpoint-url (if the bucket is
DNS compatible).

This customization ensures that if a user specifies
an --endpoint-url, then we turn off the botocore customization
that messes with endpoint url.

"""
from functools import partial

from botocore.utils import fix_s3_host


def register_s3_endpoint(cli):
    handler = partial(on_top_level_args_parsed, event_handler=cli)
    cli.register(
        'top-level-args-parsed', handler, unique_id='s3-endpoint')


def on_top_level_args_parsed(parsed_args, event_handler, **kwargs):
    # The fix_s3_host has logic to set the endpoint to the
    # standard region endpoint for s3 (s3.amazonaws.com) under
    # certain conditions.  We're making sure that if
    # the user provides an --endpoint-url, that entire handler
    # is disabled.
    if parsed_args.command in ['s3', 's3api'] and \
            parsed_args.endpoint_url is not None:
        event_handler.unregister('before-sign.s3', fix_s3_host)
