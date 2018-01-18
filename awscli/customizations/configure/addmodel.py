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
import json
import os

from botocore.model import ServiceModel

from awscli.customizations.commands import BasicCommand


def _get_endpoint_prefix_to_name_mappings(session):
    # Get the mappings of endpoint prefixes to service names from the
    # available service models.
    prefixes_to_services = {}
    for service_name in session.get_available_services():
        service_model = session.get_service_model(service_name)
        prefixes_to_services[service_model.endpoint_prefix] = service_name
    return prefixes_to_services


def _get_service_name(session, endpoint_prefix):
    if endpoint_prefix in session.get_available_services():
        # Check if the endpoint prefix is a pre-existing service.
        # If it is, use that endpoint prefix as the service name.
        return endpoint_prefix
    else:
        # The service may have a different endpoint prefix than its name
        # So we need to determine what the correct mapping may be.

        # Figure out the mappings of endpoint prefix to service names.
        name_mappings = _get_endpoint_prefix_to_name_mappings(session)
        # Determine the service name from the mapping.
        # If it does not exist in the mapping, return the original endpoint
        # prefix.
        return name_mappings.get(endpoint_prefix, endpoint_prefix)


def get_model_location(session, service_definition, service_name=None):
    """Gets the path of where a service-2.json file should go in ~/.aws/models

    :type session: botocore.session.Session
    :param session: A session object

    :type service_definition: dict
    :param service_definition: The json loaded service definition

    :type service_name: str
    :param service_name: The service name to use. If this not provided,
        this will be determined from a combination of available services
        and the service definition.

    :returns: The path to where are model should be placed based on
        the service defintion and the current services in botocore.
    """
    # Add the ServiceModel abstraction over the service json definition to
    # make it easier to work with.
    service_model = ServiceModel(service_definition)

    # Determine the service_name if not provided
    if service_name is None:
        endpoint_prefix = service_model.endpoint_prefix
        service_name = _get_service_name(session, endpoint_prefix)
    api_version = service_model.api_version

    # For the model location we only want the custom data path (~/.aws/models
    # not the one set by AWS_DATA_PATH)
    data_path = session.get_component('data_loader').CUSTOMER_DATA_PATH
    # Use the version of the model to determine the file's naming convention.
    service_model_name = (
        'service-%d.json' % int(
            float(service_definition.get('version', '2.0'))))
    return os.path.join(data_path, service_name, api_version,
        service_model_name)


class AddModelCommand(BasicCommand):
    NAME = 'add-model'
    DESCRIPTION = (
        'Adds a service JSON model to the appropriate location in '
        '~/.aws/models. Once the model gets added, CLI commands and Boto3 '
        'clients will be immediately available for the service JSON model '
        'provided.'
    )
    ARG_TABLE = [
        {'name': 'service-model', 'required': True, 'help_text': (
            'The contents of the service JSON model.')},
        {'name': 'service-name', 'help_text': (
            'Overrides the default name used by the service JSON '
            'model to generate CLI service commands and Boto3 clients.')}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        service_definition = json.loads(parsed_args.service_model)

        # Get the path to where the model should be written
        model_location = get_model_location(
            self._session, service_definition, parsed_args.service_name
        )

        # If the service_name/api_version directories do not exist,
        # then create them.
        model_directory = os.path.dirname(model_location)
        if not os.path.exists(model_directory):
            os.makedirs(model_directory)

        # Write the model to the specified location
        with open(model_location, 'wb') as f:
            f.write(parsed_args.service_model.encode('utf-8'))

        return 0
