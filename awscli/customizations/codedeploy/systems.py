# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import ctypes
import os
import subprocess

DEFAULT_CONFIG_FILE = 'codedeploy.onpremises.yml'


class System:
    UNSUPPORTED_SYSTEM_MSG = (
        'Only Ubuntu Server, Red Hat Enterprise Linux Server and '
        'Windows Server operating systems are supported.'
    )

    def __init__(self, params):
        self.session = params.session
        self.s3 = self.session.create_client(
            's3',
            region_name=params.region
        )

    def validate_administrator(self):
        raise NotImplementedError('validate_administrator')

    def install(self, params):
        raise NotImplementedError('install')

    def uninstall(self, params):
        raise NotImplementedError('uninstall')


class Windows(System):
    CONFIG_DIR = r'C:\ProgramData\Amazon\CodeDeploy'
    CONFIG_FILE = 'conf.onpremises.yml'
    CONFIG_PATH = r'{0}\{1}'.format(CONFIG_DIR, CONFIG_FILE)
    INSTALLER = 'codedeploy-agent.msi'

    def validate_administrator(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            raise RuntimeError(
                'You must run this command as an Administrator.'
            )

    def install(self, params):
        if 'installer' in params:
            self.INSTALLER = params.installer

        process = subprocess.Popen(
            [
                'powershell.exe',
                '-Command', 'Stop-Service',
                '-Name', 'codedeployagent'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, error) = process.communicate()
        not_found = (
            "Cannot find any service with service name 'codedeployagent'"
        )
        if process.returncode != 0 and not_found not in error:
            raise RuntimeError(
                'Failed to stop the AWS CodeDeploy Agent:\n{0}'.format(error)
            )

        response = self.s3.get_object(Bucket=params.bucket, Key=params.key)
        with open(self.INSTALLER, 'wb') as f:
            f.write(response['Body'].read())

        subprocess.check_call(
            [
                r'.\{0}'.format(self.INSTALLER),
                '/quiet',
                '/l', r'.\codedeploy-agent-install-log.txt'
            ],
            shell=True
        )
        subprocess.check_call([
            'powershell.exe',
            '-Command', 'Restart-Service',
            '-Name', 'codedeployagent'
        ])

        process = subprocess.Popen(
            [
                'powershell.exe',
                '-Command', 'Get-Service',
                '-Name', 'codedeployagent'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, error) = process.communicate()
        if "Running" not in output:
            raise RuntimeError(
                'The AWS CodeDeploy Agent did not start after installation.'
            )

    def uninstall(self, params):
        process = subprocess.Popen(
            [
                'powershell.exe',
                '-Command', 'Stop-Service',
                '-Name', 'codedeployagent'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, error) = process.communicate()
        not_found = (
            "Cannot find any service with service name 'codedeployagent'"
        )
        if process.returncode == 0:
            self._remove_agent()
        elif not_found not in error:
            raise RuntimeError(
                'Failed to stop the AWS CodeDeploy Agent:\n{0}'.format(error)
            )

    def _remove_agent(self):
        process = subprocess.Popen(
            [
                'wmic',
                'product', 'where', 'name="CodeDeploy Host Agent"',
                'call', 'uninstall', '/nointeractive'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, error) = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                'Failed to uninstall the AWS CodeDeploy Agent:\n{0}'.format(
                    error
                )
            )


class Linux(System):
    CONFIG_DIR = '/etc/codedeploy-agent/conf'
    CONFIG_FILE = DEFAULT_CONFIG_FILE
    CONFIG_PATH = '{0}/{1}'.format(CONFIG_DIR, CONFIG_FILE)
    INSTALLER = 'install'

    def validate_administrator(self):
        if os.geteuid() != 0:
            raise RuntimeError('You must run this command as sudo.')

    def install(self, params):
        if 'installer' in params:
            self.INSTALLER = params.installer

        self._update_system(params)
        self._stop_agent(params)

        response = self.s3.get_object(Bucket=params.bucket, Key=params.key)
        with open(self.INSTALLER, 'wb') as f:
            f.write(response['Body'].read())

        subprocess.check_call(
            ['chmod', '+x', './{0}'.format(self.INSTALLER)]
        )

        credentials = self.session.get_credentials()
        environment = os.environ.copy()
        environment['AWS_REGION'] = params.region
        environment['AWS_ACCESS_KEY_ID'] = credentials.access_key
        environment['AWS_SECRET_ACCESS_KEY'] = credentials.secret_key
        if credentials.token is not None:
            environment['AWS_SESSION_TOKEN'] = credentials.token
        subprocess.check_call(
            ['./{0}'.format(self.INSTALLER), 'auto'],
            env=environment
        )

    def uninstall(self, params):
        process = self._stop_agent(params)
        if process.returncode == 0:
            self._remove_agent(params)

    def _update_system(self, params):
        raise NotImplementedError('preinstall')

    def _remove_agent(self, params):
        raise NotImplementedError('remove_agent')

    def _stop_agent(self, params):
        process = subprocess.Popen(
            ['service', 'codedeploy-agent', 'stop'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, error) = process.communicate()
        if process.returncode != 0 and params.not_found_msg not in error:
            raise RuntimeError(
                'Failed to stop the AWS CodeDeploy Agent:\n{0}'.format(error)
            )
        return process


class Ubuntu(Linux):
    def _update_system(self, params):
        subprocess.check_call(['apt-get', '-y', 'update'])
        subprocess.check_call(['apt-get', '-y', 'install', 'ruby2.0'])

    def _remove_agent(self, params):
        subprocess.check_call(['dpkg', '-r', 'codedeploy-agent'])

    def _stop_agent(self, params):
        params.not_found_msg = 'codedeploy-agent: unrecognized service'
        return Linux._stop_agent(self, params)


class RHEL(Linux):
    def _update_system(self, params):
        subprocess.check_call(['yum', '-y', 'install', 'ruby'])

    def _remove_agent(self, params):
        subprocess.check_call(['yum', '-y', 'erase', 'codedeploy-agent'])

    def _stop_agent(self, params):
        params.not_found_msg = 'Redirecting to /bin/systemctl stop  codedeploy-agent.service'
        return Linux._stop_agent(self, params)
