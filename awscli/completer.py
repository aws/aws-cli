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
import logging
import copy
import subprocess
from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)


class Completer(object):

    S3_SCHEME = 's3://'

    def __init__(self, driver=None, region=None):
        if driver is not None:
            self.driver = driver
        else:
            self.driver = awscli.clidriver.create_clidriver()
        self.region = region
        self.main_help = None
        self.s3 = None

    def complete(self, cmdline, point=None):
        if point is not None:
            cmdline = cmdline[0:point]

        args = cmdline.split()
        current_arg = args[-1]

        if (not cmdline.endswith(current_arg)
            and not current_arg.startswith('-')):
            # There are spaces after the arg, treat it as a new arg
            current_arg = ''
            args.append('')

        if len(args) > 1 and args[-2] == '--profile':
            return [n for n in self.driver.session.available_profiles
                if n.startswith(args[-1])]

        args_set = set(args)
        if 's3' in args_set and not current_arg.startswith('-'):
            if len(args_set & set(['cp', 'mv', 'sync'])) > 0:
                return self._complete_s3_arg(current_arg, True)
            elif len(args_set & set(['ls', 'presign', 'rm'])) > 0:
                return self._complete_s3_arg(current_arg, False)

        cmd_args = [w for w in args if not w.startswith('-')]
        opts = [w for w in args if w.startswith('-')]

        self.main_help = self.driver.create_help_command()
        cmd_name, cmd = self._get_command(self.main_help, cmd_args)
        subcmd_name, subcmd = self._get_command(cmd, cmd_args)

        if cmd_name is None:
            # If we didn't find any command names in the cmdline
            # lets try to complete provider options
            return self._complete_provider(current_arg, opts)
        elif subcmd_name is None:
            return self._complete_command(cmd_name, cmd, current_arg, opts)
        return self._complete_subcommand(subcmd_name, subcmd, current_arg, opts)

    def _complete_command(self, command_name, command_help, current_arg, opts):
        if current_arg == command_name:
            if command_help:
                return self._get_documented_completions(
                    command_help.command_table)
        elif current_arg.startswith('-'):
            return self._find_possible_options(current_arg, opts)
        elif command_help is not None:
            # See if they have entered a partial command name
            return self._get_documented_completions(
                command_help.command_table, current_arg)
        return []


    def _complete_s3_bucket(self, current_arg):
        response = self.s3.list_buckets()
        result = []
        for bucket in response['Buckets']:
            if bucket['Name'].startswith(current_arg):
                result.append(bucket['Name'] + '/')
        return result

    def _complete_s3_prefix(self, current_arg):
        split_arg = current_arg.split('/', 1)
        if len(split_arg) < 2:
            return self._complete_s3_bucket(current_arg)

        bucket_name, prefix = split_arg
        paginator = self.s3.get_paginator('list_objects')
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix,
            Delimiter='/')

        result = []
        for page in page_iterator:
            if 'CommonPrefixes' in page:
                for item in page['CommonPrefixes']:
                    result.append('%s/%s' % (bucket_name, item['Prefix']))
            if 'Contents' in page:
                for item in page['Contents']:
                    result.append('%s/%s' % (bucket_name, item['Key']))

        return result

    def _complete_s3_prefix_loop(self, current_arg=''):
        result = []
        for i in range(10):
            try:
                cur = self._complete_s3_prefix(current_arg)
            except ClientError:
                break
            if len(cur) == 0:
                break

            result = cur
            if len(cur) != 1:
                break
            current_arg = cur[0]

        return [self.S3_SCHEME + n for n in result]

    def _complete_local_path(self, current_arg):
        # Delegate to compgen for local file completion
        cmd_args = ['bash', '-c', 'compgen -f -- %s' % current_arg]
        try:
            return (subprocess.check_output(cmd_args).decode('utf-8')
                .splitlines())
        except subprocess.CalledProcessError:
            return []

    def _complete_s3_arg(self, current_arg, local):
        self.s3 = self.driver.session.create_client('s3',
            region_name=self.region)

        result = []
        if current_arg.startswith(self.S3_SCHEME):
            # S3 path completion
            result = self._complete_s3_prefix_loop(
                current_arg[len(self.S3_SCHEME):])
        else:
            if self.S3_SCHEME.startswith(current_arg):
                # Arg is a prefix of s3 scheme - perform s3 path completion
                result = self._complete_s3_prefix_loop()

            if local:
                # Local path completion
                result += self._complete_local_path(current_arg)

        if ':' in current_arg:
            # Bash starts the completion from the last :, strip anything that
            # precedes it
            strip = current_arg.rfind(':') + 1
            result = [n[strip:] for n in result]

        return result

    def _complete_subcommand(self, subcmd_name, subcmd_help, current_arg, opts):
        if current_arg != subcmd_name and current_arg.startswith('-'):
            return self._find_possible_options(current_arg, opts, subcmd_help)
        return []

    def _complete_option(self, option_name):
        if option_name == '--endpoint-url':
            return []
        if option_name == '--output':
            cli_data = self.driver.session.get_data('cli')
            return cli_data['options']['output']['choices']
        if option_name == '--profile':
            return self.driver.session.available_profiles
        return []

    def _complete_provider(self, current_arg, opts):
        if current_arg.startswith('-'):
            return self._find_possible_options(current_arg, opts)
        elif current_arg == 'aws':
            return self._get_documented_completions(
                self.main_help.command_table)
        else:
            # Otherwise, see if they have entered a partial command name
            return self._get_documented_completions(
                self.main_help.command_table, current_arg)

    def _get_command(self, command_help, command_args):
        if command_help is not None and command_help.command_table is not None:
            for command_name in command_args:
                if command_name in command_help.command_table:
                    cmd_obj = command_help.command_table[command_name]
                    return command_name, cmd_obj.create_help_command()
        return None, None

    def _get_documented_completions(self, table, startswith=None):
        names = []
        for key, command in table.items():
            if getattr(command, '_UNDOCUMENTED', False):
                # Don't tab complete undocumented commands/params
                continue
            if startswith is not None and not key.startswith(startswith):
                continue
            if getattr(command, 'positional_arg', False):
                continue
            names.append(key)
        return names

    def _find_possible_options(self, current_arg, opts, subcmd_help=None):
        main_options = self._get_documented_completions(
            self.main_help.arg_table)
        all_options = copy.copy(main_options)
        if subcmd_help is not None:
            all_options += self._get_documented_completions(
                subcmd_help.arg_table)

        for option in opts:
            # Look through list of options on cmdline. If there are
            # options that have already been specified and they are
            # not the current word, remove them from list of possibles.
            if option != current_arg:
                stripped_opt = option.lstrip('-')
                if stripped_opt in all_options:
                    all_options.remove(stripped_opt)
        cw = current_arg.lstrip('-')
        possibilities = ['--' + n for n in all_options if n.startswith(cw)]
        if len(possibilities) == 1 and possibilities[0] == current_arg:
            return self._complete_option(possibilities[0])
        return possibilities


def complete(cmdline, point):
    # Get the profile and region args
    args = cmdline[0:point].split()

    profile = None
    if '--profile' in args[:-2]:
        profile = args[args.index('--profile') + 1]

    region = None
    if '--region' in args[:-2]:
        region = args[args.index('--region') + 1]

    driver = awscli.clidriver.create_clidriver(profile=profile)
    choices = Completer(driver, region).complete(cmdline, point)
    print(' \n'.join(choices))


if __name__ == '__main__':
    if len(sys.argv) == 3:
        cmdline = sys.argv[1]
        point = int(sys.argv[2])
    elif len(sys.argv) == 2:
        cmdline = sys.argv[1]
    else:
        print('usage: %s <cmdline> <point>' % sys.argv[0])
        sys.exit(1)
    print(complete(cmdline, point))
