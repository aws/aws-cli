# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def register_ec2_page_size_injector(event_emitter):
    EC2PageSizeInjector().register(event_emitter)


class EC2PageSizeInjector(object):

    # Operations to auto-paginate and their specific whitelists.
    # Format:
    #    Key:   Operation
    #    Value: List of parameters to add to whitelist for that operation.
    TARGET_OPERATIONS = {
        "describe-volumes": [],
        "describe-snapshots": ['OwnerIds', 'RestorableByUserIds']
    }

    # Parameters which should be whitelisted for every operation.
    UNIVERSAL_WHITELIST = ['NextToken', 'DryRun', 'PaginationConfig']

    DEFAULT_PAGE_SIZE = 1000

    def register(self, event_emitter):
        """Register `inject` for each target operation."""
        event_template = "calling-command.ec2.%s"
        for operation in self.TARGET_OPERATIONS:
            event = event_template % operation
            event_emitter.register_last(event, self.inject)

    def inject(self, event_name, parsed_globals, call_parameters, **kwargs):
        """Conditionally inject PageSize."""
        if not parsed_globals.paginate:
            return

        pagination_config = call_parameters.get('PaginationConfig', {})
        if 'PageSize' in pagination_config:
            return

        operation_name = event_name.split('.')[-1]

        whitelisted_params = self.TARGET_OPERATIONS.get(operation_name)
        if whitelisted_params is None:
            return

        whitelisted_params = whitelisted_params + self.UNIVERSAL_WHITELIST

        for param in call_parameters:
            if param not in whitelisted_params:
                return

        pagination_config['PageSize'] = self.DEFAULT_PAGE_SIZE
        call_parameters['PaginationConfig'] = pagination_config
