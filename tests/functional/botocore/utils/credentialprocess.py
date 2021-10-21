# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""This is a dummy implementation of a credential provider process."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raise-error', action='store_true', help=(
        'If set, this will cause the process to return a non-zero exit code '
        'and print to stderr.'
    ))
    args = parser.parse_args()
    if args.raise_error:
        raise Exception('Failed to fetch credentials.')
    print(json.dumps({
        'AccessKeyId': 'spam',
        'SecretAccessKey': 'eggs',
        'Version': 1
    }))


if __name__ == "__main__":
    main()
