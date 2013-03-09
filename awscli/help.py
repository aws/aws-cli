# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys
import os

def do_man(man_page):
    manpath = os.path.split(__file__)[0]
    manpath = os.path.split(manpath)[0]
    manpath = os.path.join(manpath, 'man')
    args = ['man', '-M', manpath, man_page]
    sys.stdout.flush()
    sys.stderr.flush()
    os.execvp('man', args)

def get_provider_help(provider='aws'):
    do_man(provider)

def get_service_help(service):
    do_man(service.cli_name)

def get_operation_help(operation):
    do_man(operation.service.cli_name + '-' + operation.cli_name)
