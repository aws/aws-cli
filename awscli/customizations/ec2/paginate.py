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

    DEFAULT_TARGET_OPERATIONS = {
        "describe-volumes": [],
        "describe-snapshots": ['owner-ids', 'restorable_by_user_ids']
    }

    DEFAULT_GLOBAL_WHITELIST = [
        'cli_input_json', 'generate_cli_skeleton', 'help', 'max_items',
        'next_token', 'dry_run', 'starting_token'
    ]

    def __init__(self, default_page_size=1000, target_operations=None,
                 global_whitelist=None):
        """
        :type default_page_size: int
        :param default_page_size: The value to inject for page_size.

        :type target_operations: dict
        :param target_operations: A dictionary whose keys are operations and
            whose values are parameters that are white-listed for that
            operation. If a parameter is specified that is not in that list,
            page_size will not be set.

        :type global_whitelist: list of str
        :param global_whitelist: A list of parameters that should be
            whitelisted for every operation.
        """
        self._default_page_size = default_page_size
        self._target_operations = target_operations
        if self._target_operations is None:
            self._target_operations = self.DEFAULT_TARGET_OPERATIONS
        self._global_whitelist = global_whitelist
        if self._global_whitelist is None:
            self._global_whitelist = self.DEFAULT_GLOBAL_WHITELIST

    def register(self, event_emitter):
        """ Register `inject` for each target operation. """
        event_template = "operation-args-parsed.ec2.%s"
        for operation in self._target_operations.keys():
            event = event_template % operation
            event_emitter.register(event, self.inject)

    def inject(self, event_name, parsed_args, parsed_globals, **kwargs):
        """ Conditionally inject page_size. """
        if not parsed_globals.paginate:
            return

        operation_name = event_name.split('.')[-1]

        whitelisted_params = self._target_operations.get(operation_name, None)
        if whitelisted_params is None:
            return

        whitelisted_params += self._global_whitelist
        specified_params = self._get_specified_params(parsed_args)

        for param in specified_params:
            if param not in whitelisted_params:
                return

        parsed_args.page_size = self._default_page_size

    def _get_specified_params(self, namespace):
        attrs = dir(namespace)
        params = []
        for attr in attrs:
            # The default value of generate_cli_skeleton is False where
            # usually a boolean argument still defaults to None. Therefore
            # it must be specifically ignored.
            if attr == 'generate_cli_skeleton':
                continue

            if attr[0] != '_' and getattr(namespace, attr) is not None:
                params.append(attr)

        return params

