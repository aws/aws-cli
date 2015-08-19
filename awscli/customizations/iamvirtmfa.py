# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
This customization makes it easier to deal with the bootstrapping
data returned by the ``iam create-virtual-mfa-device`` command.
You can choose to bootstrap via a QRCode or via a Base32String.
You specify your choice via the ``--bootstrap-method`` option
which should be either "QRCodePNG" or "Base32StringSeed".  You
then specify the path to where you would like your bootstrapping
data saved using the ``--outfile`` option.  The command will
pull the appropriate data field out of the response and write it
to the specified file.  It will also remove the two bootstrap data
fields from the response.
"""
import base64
import os

from awscli.arguments import CustomArgument


CHOICES = ('QRCodePNG', 'Base32StringSeed')
OUTPUT_HELP = ('The output path and file name where the bootstrap '
               'information will be stored.')
BOOTSTRAP_HELP = ('Method to use to seed the virtual MFA.  '
                  'Valid values are: %s | %s' % CHOICES)


class StatefulArgument(CustomArgument):

    def __init__(self, *args, **kwargs):
        super(StatefulArgument, self).__init__(*args, **kwargs)
        self._value = None

    def add_to_params(self, parameters, value):
        self._value = value

    @property
    def value(self):
        return self._value


class FileArgument(StatefulArgument):

    def add_to_params(self, parameters, value):
        # Validate the file here so we can raise an error prior
        # calling the service.
        outfile = os.path.expandvars(value)
        outfile = os.path.expanduser(outfile)
        if not os.access(os.path.dirname(os.path.abspath(outfile)), os.W_OK):
            raise ValueError('Unable to write to file: %s' % outfile)
        self._value = outfile


class IAMVMFAWrapper(object):

    def __init__(self, event_handler):
        self._event_handler = event_handler
        self._outfile = FileArgument(
            'outfile', help_text=OUTPUT_HELP, required=True)
        self._method = StatefulArgument(
            'bootstrap-method', help_text=BOOTSTRAP_HELP,
            choices=CHOICES, required=True)
        self._event_handler.register(
            'building-argument-table.iam.create-virtual-mfa-device',
            self._add_options)
        self._event_handler.register(
            'after-call.iam.CreateVirtualMFADevice', self._save_file)

    def _add_options(self, argument_table, **kwargs):
        argument_table['outfile'] = self._outfile
        argument_table['bootstrap-method'] = self._method

    def _save_file(self, parsed, **kwargs):
        if 'Error' in parsed:
            return
        method = self._method.value
        outfile = self._outfile.value
        if method in parsed['VirtualMFADevice']:
            body = parsed['VirtualMFADevice'][method]
            with open(outfile, 'wb') as fp:
                fp.write(base64.b64decode(body))
            for choice in CHOICES:
                if choice in parsed['VirtualMFADevice']:
                    del parsed['VirtualMFADevice'][choice]
