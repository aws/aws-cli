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


from awscli.customizations.emr import applicationutils
from awscli.customizations.emr import argumentschema
from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import helptext
from awscli.customizations.emr.command import Command


class InstallApplications(Command):
    NAME = 'install-applications'
    DESCRIPTION = ('Installs applications on a running cluster. Currently only'
                   ' Hive and Pig can be installed using this command, and'
                   ' this command is only supported by AMI versions'
                   ' (3.x and 2.x).')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'applications', 'required': True,
         'help_text': helptext.INSTALL_APPLICATIONS,
         'schema': argumentschema.APPLICATIONS_SCHEMA},
    ]
    # Applications supported by the install-applications command.
    supported_apps = ['HIVE', 'PIG']

    def _run_main_command(self, parsed_args, parsed_globals):

        parameters = {'JobFlowId': parsed_args.cluster_id}

        self._check_for_supported_apps(parsed_args.applications)
        parameters['Steps'] = applicationutils.build_applications(
            self.region, parsed_args.applications)[2]

        emrutils.call_and_display_response(self._session, 'AddJobFlowSteps',
                                           parameters, parsed_globals)
        return 0

    def _check_for_supported_apps(self, parsed_applications):
        for app_config in parsed_applications:
            app_name = app_config['Name'].upper()

            if app_name in constants.APPLICATIONS:
                if app_name not in self.supported_apps:
                    raise ValueError(
                        "aws: error: " + app_config['Name'] + " cannot be"
                        " installed on a running cluster. 'Name' should be one"
                        " of the following: " +
                        ', '.join(self.supported_apps))
            else:
                raise ValueError(
                    "aws: error: Unknown application: " + app_config['Name'] +
                    ". 'Name' should be one of the following: " +
                    ', '.join(constants.APPLICATIONS))
