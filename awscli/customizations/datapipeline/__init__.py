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

import json
from datetime import datetime, timedelta

from awscli.formatter import get_formatter
from awscli.arguments import CustomArgument
from awscli.customizations.commands import BasicCommand
from awscli.customizations.datapipeline import translator
from awscli.customizations.datapipeline.createdefaultroles \
    import CreateDefaultRoles
from awscli.customizations.datapipeline.listrunsformatter \
    import ListRunsFormatter


DEFINITION_HELP_TEXT = """\
The JSON pipeline definition.  If the pipeline definition
is in a file you can use the file://<filename> syntax to
specify a filename.
"""
PARAMETER_OBJECTS_HELP_TEXT = """\
The JSON parameter objects.  If the parameter objects are
in a file you can use the file://<filename> syntax to
specify a filename. You can optionally provide these in
pipeline definition as well. Parameter objects provided
on command line would replace the one in definition.
"""
PARAMETER_VALUES_HELP_TEXT = """\
The JSON parameter values.  If the parameter values are
in a file you can use the file://<filename> syntax to
specify a filename. You can optionally provide these in
pipeline definition as well. Parameter values provided
on command line would replace the one in definition.
"""
INLINE_PARAMETER_VALUES_HELP_TEXT = """\
The JSON parameter values. You can specify these as
key-value pairs in the key=value format. Multiple parameters
are separated by a space. For list type parameter values
you can use the same key name and specify each value as
a key value pair. e.g. arrayValue=value1 arrayValue=value2
"""
MAX_ITEMS_PER_DESCRIBE = 100


class DocSectionNotFoundError(Exception):
    pass


class ParameterDefinitionError(Exception):
    def __init__(self, msg):
        full_msg = ("Error in parameter: %s\n" % msg)
        super(ParameterDefinitionError, self).__init__(full_msg)
        self.msg = msg


def register_customizations(cli):
    cli.register(
        'building-argument-table.datapipeline.put-pipeline-definition',
        add_pipeline_definition)
    cli.register(
        'building-argument-table.datapipeline.activate-pipeline',
        activate_pipeline_definition)
    cli.register(
        'after-call.datapipeline.GetPipelineDefinition',
        translate_definition)
    cli.register(
        'building-command-table.datapipeline',
        register_commands)
    cli.register_last(
        'doc-output.datapipeline.get-pipeline-definition',
        document_translation)


def register_commands(command_table, session, **kwargs):
    command_table['list-runs'] = ListRunsCommand(session)
    command_table['create-default-roles'] = CreateDefaultRoles(session)


def document_translation(help_command, **kwargs):
    # Remove all the writes until we get to the output.
    # I don't think this is the ideal way to do this, we should
    # improve our plugin/doc system to make this easier.
    doc = help_command.doc
    current = ''
    while current != '======\nOutput\n======':
        try:
            current = doc.pop_write()
        except IndexError:
            # This should never happen, but in the rare case that it does
            # we should be raising something with a helpful error message.
            raise DocSectionNotFoundError(
                'Could not find the "output" section for the command: %s'
                % help_command)
    doc.write('======\nOutput\n======')
    doc.write(
        '\nThe output of this command is the pipeline definition, which'
        ' is documented in the '
        '`Pipeline Definition File Syntax '
        '<http://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/'
        'dp-writing-pipeline-definition.html>`__')


def add_pipeline_definition(argument_table, **kwargs):
    argument_table['pipeline-definition'] = PipelineDefinitionArgument(
        'pipeline-definition', required=True,
        help_text=DEFINITION_HELP_TEXT)

    argument_table['parameter-objects'] = ParameterObjectsArgument(
        'parameter-objects', required=False,
        help_text=PARAMETER_OBJECTS_HELP_TEXT)

    argument_table['parameter-values-uri'] = ParameterValuesArgument(
        'parameter-values-uri',
        required=False,
        help_text=PARAMETER_VALUES_HELP_TEXT)

    # Need to use an argument model for inline parameters to accept a list
    argument_table['parameter-values'] = ParameterValuesInlineArgument(
        'parameter-values',
        required=False,
        nargs='+',
        help_text=INLINE_PARAMETER_VALUES_HELP_TEXT)

    # The pipeline-objects is no longer needed required because
    # a user can provide a pipeline-definition instead.
    # get-pipeline-definition also displays the output in the
    # translated format.

    del argument_table['pipeline-objects']


def activate_pipeline_definition(argument_table, **kwargs):
    argument_table['parameter-values-uri'] = ParameterValuesArgument(
        'parameter-values-uri', required=False,
        help_text=PARAMETER_VALUES_HELP_TEXT)

    # Need to use an argument model for inline parameters to accept a list
    argument_table['parameter-values'] = ParameterValuesInlineArgument(
        'parameter-values',
        required=False,
        nargs='+',
        help_text=INLINE_PARAMETER_VALUES_HELP_TEXT,
        )


def translate_definition(parsed, **kwargs):
    translator.api_to_definition(parsed)


def convert_described_objects(api_describe_objects, sort_key_func=None):
    # We need to take a field list that looks like this:
    # {u'key': u'@sphere', u'stringValue': u'INSTANCE'},
    # into {"@sphere": "INSTANCE}.
    # We convert the fields list into a field dict.
    converted = []
    for obj in api_describe_objects:
        new_fields = {
            '@id': obj['id'],
            'name': obj['name'],
        }
        for field in obj['fields']:
            new_fields[field['key']] = field.get('stringValue',
                                                 field.get('refValue'))
        converted.append(new_fields)
    if sort_key_func is not None:
        converted.sort(key=sort_key_func)
    return converted


class QueryArgBuilder(object):
    """
    Convert CLI arguments to Query arguments used by QueryObject.
    """
    def __init__(self, current_time=None):
        if current_time is None:
            current_time = datetime.utcnow()
        self.current_time = current_time

    def build_query(self, parsed_args):
        selectors = []
        if parsed_args.start_interval is None and \
                parsed_args.schedule_interval is None:
            # If no intervals are specified, default
            # to a start time of 4 days ago and an end time
            # of right now.
            end_datetime = self.current_time
            start_datetime = end_datetime - timedelta(days=4)
            start_time_str = start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            end_time_str = end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            selectors.append({
                'fieldName': '@actualStartTime',
                'operator': {
                    'type': 'BETWEEN',
                    'values': [start_time_str, end_time_str]
                }
            })
        else:
            self._build_schedule_times(selectors, parsed_args)
        if parsed_args.status is not None:
            self._build_status(selectors, parsed_args)
        query = {'selectors': selectors}
        return query

    def _build_schedule_times(self, selectors, parsed_args):
        if parsed_args.start_interval is not None:
            start_time_str = parsed_args.start_interval[0]
            end_time_str = parsed_args.start_interval[1]
            selectors.append({
                'fieldName': '@actualStartTime',
                'operator': {
                    'type': 'BETWEEN',
                    'values': [start_time_str, end_time_str]
                }
            })
        if parsed_args.schedule_interval is not None:
            start_time_str = parsed_args.schedule_interval[0]
            end_time_str = parsed_args.schedule_interval[1]
            selectors.append({
                'fieldName': '@scheduledStartTime',
                'operator': {
                    'type': 'BETWEEN',
                    'values': [start_time_str, end_time_str]
                }
            })

    def _build_status(self, selectors, parsed_args):
        selectors.append({
            'fieldName': '@status',
            'operator': {
                'type': 'EQ',
                'values': [status.upper() for status in parsed_args.status]
            }
        })


class PipelineDefinitionArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        parsed = json.loads(value)
        api_objects = translator.definition_to_api_objects(parsed)
        parameter_objects = translator.definition_to_api_parameters(parsed)
        parameter_values = translator.definition_to_parameter_values(parsed)
        parameters['pipelineObjects'] = api_objects
        # Use Parameter objects and values from def if not already provided
        if 'parameterObjects' not in parameters \
                and parameter_objects is not None:
            parameters['parameterObjects'] = parameter_objects
        if 'parameterValues' not in parameters \
                and parameter_values is not None:
            parameters['parameterValues'] = parameter_values


class ParameterObjectsArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        parsed = json.loads(value)
        parameter_objects = translator.definition_to_api_parameters(parsed)
        parameters['parameterObjects'] = parameter_objects


class ParameterValuesArgument(CustomArgument):
    def add_to_params(self, parameters, value):

        if value is None:
            return

        if parameters.get('parameterValues', None) is not None:
            raise Exception(
                "Only parameter-values or parameter-values-uri is allowed"
            )

        parsed = json.loads(value)
        parameter_values = translator.definition_to_parameter_values(parsed)
        parameters['parameterValues'] = parameter_values


class ParameterValuesInlineArgument(CustomArgument):
    def add_to_params(self, parameters, value):

        if value is None:
            return

        if parameters.get('parameterValues', None) is not None:
            raise Exception(
                "Only parameter-values or parameter-values-uri is allowed"
            )

        parameter_object = {}
        # break string into = point
        for argument in value:
            try:
                argument_components = argument.split('=', 1)
                key = argument_components[0]
                value = argument_components[1]
                if key in parameter_object:
                    if isinstance(parameter_object[key], list):
                        parameter_object[key].append(value)
                    else:
                        parameter_object[key] = [parameter_object[key], value]
                else:
                    parameter_object[key] = value
            except IndexError:
                raise ParameterDefinitionError(
                    "Invalid inline parameter format: %s" % argument
                )
        parsed = {'values': parameter_object}
        parameter_values = translator.definition_to_parameter_values(parsed)
        parameters['parameterValues'] = parameter_values


class ListRunsCommand(BasicCommand):
    NAME = 'list-runs'
    DESCRIPTION = (
        'Lists the times the specified pipeline has run. '
        'You can optionally filter the complete list of '
        'results to include only the runs you are interested in.')
    ARG_TABLE = [
        {'name': 'pipeline-id', 'help_text': 'The identifier of the pipeline.',
         'action': 'store', 'required': True, 'cli_type_name': 'string', },
        {'name': 'status',
         'help_text': (
             'Filters the list to include only runs in the '
             'specified statuses. '
             'The valid statuses are as follows: waiting, pending, cancelled, '
             'running, finished, failed, waiting_for_runner, '
             'and waiting_on_dependencies.'),
         'action': 'store'},
        {'name': 'start-interval',
         'help_text': (
             'Filters the list to include only runs that started '
             'within the specified interval.'),
         'action': 'store', 'required': False, 'cli_type_name': 'string', },
        {'name': 'schedule-interval',
         'help_text': (
             'Filters the list to include only runs that are scheduled to '
             'start within the specified interval.'),
         'action': 'store', 'required': False, 'cli_type_name': 'string', },
    ]
    VALID_STATUS = ['waiting', 'pending', 'cancelled', 'running',
                    'finished', 'failed', 'waiting_for_runner',
                    'waiting_on_dependencies', 'shutting_down']

    def _run_main(self, parsed_args, parsed_globals, **kwargs):
        self._set_client(parsed_globals)
        self._parse_type_args(parsed_args)
        self._list_runs(parsed_args, parsed_globals)

    def _set_client(self, parsed_globals):
        # This is called from _run_main and is used to ensure that we have
        # a service/endpoint object to work with.
        self.client = self._session.create_client(
            'datapipeline',
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)

    def _parse_type_args(self, parsed_args):
        # TODO: give good error messages!
        # Parse the start/schedule times.
        # Parse the status csv.
        if parsed_args.start_interval is not None:
            parsed_args.start_interval = [
                arg.strip() for arg in
                parsed_args.start_interval.split(',')]
        if parsed_args.schedule_interval is not None:
            parsed_args.schedule_interval = [
                arg.strip() for arg in
                parsed_args.schedule_interval.split(',')]
        if parsed_args.status is not None:
            parsed_args.status = [
                arg.strip() for arg in
                parsed_args.status.split(',')]
            self._validate_status_choices(parsed_args.status)

    def _validate_status_choices(self, statuses):
        for status in statuses:
            if status not in self.VALID_STATUS:
                raise ValueError("Invalid status: %s, must be one of: %s" %
                                 (status, ', '.join(self.VALID_STATUS)))

    def _list_runs(self, parsed_args, parsed_globals):
        query = QueryArgBuilder().build_query(parsed_args)
        object_ids = self._query_objects(parsed_args.pipeline_id, query)
        objects = self._describe_objects(parsed_args.pipeline_id, object_ids)
        converted = convert_described_objects(
            objects,
            sort_key_func=lambda x: (x.get('@scheduledStartTime'),
                                     x.get('name')))
        formatter = self._get_formatter(parsed_globals)
        formatter(self.NAME, converted)

    def _describe_objects(self, pipeline_id, object_ids):
        # DescribeObjects will only accept 100 objectIds at a time,
        # so we need to break up the list passed in into chunks that are at
        # most that size. We then aggregate the results to return.
        objects = []
        for i in range(0, len(object_ids), MAX_ITEMS_PER_DESCRIBE):
            current_object_ids = object_ids[i:i + MAX_ITEMS_PER_DESCRIBE]
            result = self.client.describe_objects(
                pipelineId=pipeline_id, objectIds=current_object_ids)
            objects.extend(result['pipelineObjects'])

        return objects

    def _query_objects(self, pipeline_id, query):
        paginator = self.client.get_paginator('query_objects').paginate(
            pipelineId=pipeline_id,
            sphere='INSTANCE', query=query)
        parsed = paginator.build_full_result()
        return parsed['ids']

    def _get_formatter(self, parsed_globals):
        output = parsed_globals.output
        if output is None:
            return ListRunsFormatter(parsed_globals)
        else:
            return get_formatter(output, parsed_globals)
