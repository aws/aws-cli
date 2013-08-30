# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import awscli.clidriver
import sys

def complete(cmdline, point=None):
    if point is None:
        point = len(cmdline)
    service_name = None
    driver = awscli.clidriver.create_clidriver()
    main_hc = driver.create_help_command()
    words = cmdline[0:point].split()
    current_word = words[-1]
    if len(words) >= 2:
        previous_word = words[-2]
    else:
        previous_word = None
    # First find all non-options words in command line
    non_options = [w for w in words if not w.startswith('-')]
    # Look for a service name in the non_options
    for w in non_options:
        if w in main_hc.command_table:
            service_name = w
            break
    if current_word.startswith('-'):
        current_word = current_word.lstrip('-')
        l = ['--' + n for n in main_hc.arg_table if n.startswith(current_word)]
        return l
    if not service_name:
        retval = []
        if current_word == 'aws':
            retval = main_hc.command_table.keys()
        # Otherwise, see if they have entered a partial service name
        l = [n for n in main_hc.command_table if n.startswith(current_word)]
        if l:
            retval = l
        return retval


if __name__ == '__main__':
    if len(sys.argv) == 3:
        print(complete(sys.argv[1], int(sys.argv[2])))
    elif len(sys.argv) == 2:
        print(complete(sys.argv[1]))
    else:
        print('usage: %s <cmdline> <point>' % sys.argv[0])
