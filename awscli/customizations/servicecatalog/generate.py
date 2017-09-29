# Copyright 2012-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.commands import BasicCommand
from awscli.customizations.servicecatalog import helptext
from awscli.customizations.servicecatalog.generateproduct \
    import GenerateProductCommand
from awscli.customizations.servicecatalog.generateprovisioningartifact \
    import GenerateProvisioningArtifactCommand


class GenerateCommand(BasicCommand):
    NAME = "generate"
    DESCRIPTION = helptext.GENERATE_COMMAND
    SUBCOMMANDS = [
        {'name': 'product',
         'command_class': GenerateProductCommand},
        {'name': 'provisioning-artifact',
         'command_class': GenerateProvisioningArtifactCommand}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            raise ValueError("usage: aws [options] <command> <subcommand> "
                             "[parameters]\naws: error: too few arguments")
