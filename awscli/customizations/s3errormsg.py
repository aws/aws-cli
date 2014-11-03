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
"""Give better S3 error messages.
"""
from awscli.customizations import utils


REGION_ERROR_MSG = (
    'You can fix this issue by explicitly providing the correct region '
    'location using the --region argument, the AWS_DEFAULT_REGION '
    'environment variable, or the region variable in the AWS CLI '
    "configuration file.  You can get the bucket's location by "
    'running "aws s3api get-bucket-location --bucket BUCKET".'
)


def register_s3_error_msg(event_handlers):
    event_handlers.register('after-call.s3', enhance_error_msg)


def enhance_error_msg(parsed, **kwargs):
    if parsed is None or 'Error' not in parsed:
        # There's no error message to enhance so we can continue.
        return
    if _is_sigv4_error_message(parsed):
        message = (
            'You are attempting to operate on a bucket in a region '
            'that requires Signature Version 4.  '
        )
        message += REGION_ERROR_MSG
        parsed['Error']['Message'] = message
    elif _is_permanent_redirect_message(parsed):
        endpoint = parsed['Error']['Endpoint']
        message = parsed['Error']['Message']
        new_message = message[:-1] + ': %s\n' % endpoint
        new_message += REGION_ERROR_MSG
        parsed['Error']['Message'] = new_message


def _is_sigv4_error_message(parsed):
    return ('Please use AWS4-HMAC-SHA256' in
            parsed.get('Error', {}).get('Message', ''))


def _is_permanent_redirect_message(parsed):
    return parsed.get('Error', {}).get('Code', '') == 'PermanentRedirect'
