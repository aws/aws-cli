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


class EC2PageSizeInjector(object):

    # Operations to auto-paginate and their specific whitelists.
    # Format:
    #    Key:   Operation
    #    Value: List of parameters to add to whitelist for that operation.
    TARGET_OPERATIONS = {
        "describe-volumes": [],
        "describe-snapshots": ['owner_ids', 'restorable_by_user_ids']
    }

    # Parameters which should be whitelisted for every operation.
    GLOBAL_WHITELIST = [
        'cli_input_json', 'generate_cli_skeleton', 'help', 'max_items',
        'next_token', 'dry_run', 'starting_token'
    ]

    DEFAULT_PAGE_SIZE = 1000

    def register(self, event_emitter):
        """ Register `inject` for each target operation. """
        event_template = "operation-args-parsed.ec2.%s"
        for operation in self.TARGET_OPERATIONS.keys():
            event = event_template % operation
            event_emitter.register(event, self.inject)

    def inject(self, event_name, parsed_args, parsed_globals, **kwargs):
        """ Conditionally inject page_size. """
        if not parsed_globals.paginate:
            return

        operation_name = event_name.split('.')[-1]

        whitelisted_params = self.TARGET_OPERATIONS.get(operation_name, None)
        if whitelisted_params is None:
            return

        whitelisted_params += self.GLOBAL_WHITELIST
        specified_params = self._get_specified_params(parsed_args)

        for param in specified_params:
            if param not in whitelisted_params:
                return

        parsed_args.page_size = self.DEFAULT_PAGE_SIZE

    def _get_specified_params(self, namespace):
        attrs = dir(namespace)
        params = []
        for attr in attrs:
            if attr[0] != '_' and getattr(namespace, attr) is not None:
                params.append(attr)

        return params

