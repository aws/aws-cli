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
import stat
import subprocess
from awscli.utils import create_nested_client

DEFAULT_CONFIG_FILE = 'codedeploy.onpremises.yml'

# Security descriptor for the Windows configuration file: a protected DACL
# (nothing inherited from the directory) granting full control only to
# LocalSystem and Administrators.
_WINDOWS_CONFIG_FILE_SDDL = 'D:P(A;;FA;;;SY)(A;;FA;;;BA)'


def _create_windows_file(path, sddl):
    """Create ``path`` with the DACL in ``sddl`` and return a writable fd.

    Windows ignores the mode passed to os.open, so the file would take its
    ACL from its directory. Here CreateFileW sets the DACL when it creates
    the file, so the file is never accessible with any other ACL.
    CREATE_NEW makes this fail if ``path`` already exists.
    """
    import msvcrt
    from ctypes import wintypes

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [
            ('nLength', wintypes.DWORD),
            ('lpSecurityDescriptor', ctypes.c_void_p),
            ('bInheritHandle', wintypes.BOOL),
        ]

    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.ULONG),
    ]
    convert.restype = wintypes.BOOL

    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE

    local_free = kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    sddl_revision_1 = 1
    generic_write = 0x40000000
    # No other handle may read, write or delete the file while it is open.
    no_sharing = 0
    create_new = 1
    file_attribute_normal = 0x80
    invalid_handle_value = ctypes.c_void_p(-1).value

    descriptor = ctypes.c_void_p()
    if not convert(sddl, sddl_revision_1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = SecurityAttributes(
            ctypes.sizeof(SecurityAttributes), descriptor.value, False
        )
        handle = create_file(
            path,
            generic_write,
            no_sharing,
            ctypes.byref(attributes),
            create_new,
            file_attribute_normal,
            None,
        )
        if handle is None or handle == invalid_handle_value:
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        local_free(descriptor)
    try:
        return msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)
    except Exception:
        close_handle(handle)
        raise


class System:
    UNSUPPORTED_SYSTEM_MSG = (
        'Only Ubuntu Server, Red Hat Enterprise Linux Server and '
        'Windows Server operating systems are supported.'
    )

    # Whether install replaces an existing configuration file with one from
    # create_config_file, rather than truncating it in place.
    RECREATE_CONFIG_FILE = False

    def __init__(self, params):
        self.session = params.session
        self.s3 = create_nested_client(
            self.session,
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
    # An existing file is replaced rather than truncated, which would keep
    # its ACL and any handles opened to it before.
    RECREATE_CONFIG_FILE = True

    def validate_administrator(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            raise RuntimeError(
                'You must run this command as an Administrator.'
            )

    def create_config_file(self):
        """Replace CONFIG_PATH with a new, empty file and return its fd.

        The new file grants access only to LocalSystem and Administrators,
        whatever the ACL of CONFIG_DIR.
        """
        try:
            # os.remove fails on read-only files, so clear the attribute.
            os.chmod(self.CONFIG_PATH, stat.S_IWRITE)
            os.remove(self.CONFIG_PATH)
        except FileNotFoundError:
            pass
        except PermissionError as e:
            raise RuntimeError(
                'Failed to replace the existing on-premises instance '
                f'configuration file {self.CONFIG_PATH}: {e}. Make sure no '
                'other process has the file open, then run install again.'
            )
        try:
            return _create_windows_file(
                self.CONFIG_PATH, _WINDOWS_CONFIG_FILE_SDDL
            )
        except OSError as e:
            raise RuntimeError(f'Failed to create {self.CONFIG_PATH}: {e}')

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
