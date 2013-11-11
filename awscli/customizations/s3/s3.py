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
import argparse
import os
import six
import sys

from dateutil.parser import parse
from dateutil.tz import tzlocal

import awscli
from awscli.arguments import BaseCLIArgument
from awscli.argparser import ServiceArgParser, ArgTableArgParser
from awscli.help import HelpCommand
from awscli.customizations import utils
from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.fileformat import FileFormat
from awscli.customizations.s3.filegenerator import FileGenerator
from awscli.customizations.s3.fileinfo import TaskInfo
from awscli.customizations.s3.filters import Filter
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.description import add_command_descriptions, \
    add_param_descriptions
from awscli.customizations.s3.utils import find_bucket_key, check_error, \
        uni_print
from awscli.customizations.s3.dochandler import S3DocumentEventHandler


class AppendFilter(argparse.Action):
    """
    This class is used as an action when parsing the parameters.
    Specifically it is used for actions corresponding to exclude
    and include filters.  What it does is that it appends a list
    consisting of the name of the parameter and its value onto
    a list containing these [parameter, value] lists.  In this
    case, the name of the parameter will either be --include or
    --exclude and the value will be the rule to apply.  This will
    format all of the rules inputted into the command line
    in a way compatible with the Filter class.  Note that rules that
    appear later in the command line take preferance over rulers that
    appear earlier.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        filter_list = getattr(namespace, self.dest)
        if filter_list:
            filter_list.append([option_string, values[0]])
        else:
            filter_list = [[option_string, values[0]]]
        setattr(namespace, self.dest, filter_list)


def awscli_initialize(cli):
    """
    This function is require to use the plugin.  It calls the functions
    required to add all neccessary commands and parameters to the CLI.
    This function is necessary to install the plugin using a configuration
    file
    """
    cli.register("building-command-table.main", add_s3)
    cli.register("doc-examples.S3.*", add_s3_examples)
    for cmd in CMD_DICT.keys():
        cli.register("building-parameter-table.s3.%s" % cmd, add_cmd_params)


def s3_plugin_initialize(event_handlers):
    """
    This is a wrapper to make the plugin built-in to the cli as opposed
    to specifiying it in the configuration file.
    """
    awscli_initialize(event_handlers)


def add_s3(command_table, session, **kwargs):
    """
    This creates a new service object for the s3 plugin.  It sends the
    old s3 commands to the namespace ``s3api``.
    """
    utils.rename_command(command_table, 's3', 's3api')
    command_table['s3'] = S3('s3', session)


def add_cmd_params(parameter_table, command, **kwargs):
    """
    This creates the ParameterArgument object for each possible parameter
    in a specified command
    """
    for param in CMD_DICT[command]['params']:
        parameter_table[param] = S3Parameter(param,
                                             PARAMS_DICT[param]['options'],
                                             PARAMS_DICT[param]['documents'])


def add_s3_examples(help_command, **kwargs):
    """
    This function is used to add examples for each command.  It reads in
    reStructuredTexts in the ``doc/source/examples`` directory
    and injects them into the help docs for each command.  Each command
    should have one of these example docs.
    """
    doc_path = os.path.join(
        os.path.abspath(os.path.dirname(awscli.__file__)), 'examples', 's3')
    file_name = '%s.rst' % help_command.obj._name
    doc_path = os.path.join(doc_path, file_name)
    if os.path.isfile(doc_path):
        help_command.doc.style.h2('Examples')
        fp = open(doc_path)
        for line in fp.readlines():
            help_command.doc.write(line)


class S3HelpCommand(HelpCommand):
    """
    This is a wrapper to handle the interactions between the commmand and the
    documentation pipeline.
    """
    EventHandlerClass = S3DocumentEventHandler
    event_class = 'S3'
    name = 's3'


class S3Service(object):
    """
    This is a small class that represents the service object for s3.  Its
    only purpose is to give the s3 a service and a name.  This is
    currently required for doc generation
    """
    def __init__(self):
        self.service_full_name = 'Amazon Simple Storage Service'


class S3(object):
    """
    The service for the plugin.
    """

    def __init__(self, name, session):
        self._name = name
        self._service_object = S3Service()
        self._session = session
        self.documentation = "This provides higher level S3 commands for " \
                             "the AWS CLI."

    def __call__(self, args, parsed_globals):
        """
        This function instantiates the operations table to be filled with
        commands.  Creates a parser based off of the commands in the
        operations table.  Parses the valid arguments and passes the
        remaining off to a corresponding ``S3SubCommand`` object to be called
        on.
        """
        subcommand_table = self._create_subcommand_table()
        service_parser = self._create_service_parser(subcommand_table)
        parsed_args, remaining = service_parser.parse_known_args(args)
        return subcommand_table[parsed_args.operation](
            remaining, parsed_globals)

    def _create_service_parser(self, subcommand_table):
        """
        Creates the parser required to parse the commands on the
        command line
        """
        return ServiceArgParser(
            operations_table=subcommand_table, service_name=self._name)

    def _create_subcommand_table(self):
        """
        Creates an empty dictionary to be filled with ``S3SubCommand`` objects
        when the event is emmitted.
        """
        subcommand_table = {}
        for cmd in CMD_DICT.keys():
            cmd_specification = CMD_DICT[cmd]
            cmd_class = cmd_specification.get('command_class', S3SubCommand)
            # If a cmd_class is provided, the we'll try to grab the
            # description and usage off of that object, otherwise
            # we'll look in the command dict.
            description, usage = self._get_command_usage(cmd_class)
            subcommand_table[cmd] = cmd_class(
                cmd, self._session, cmd_specification['options'],
                cmd_specification.get('description', description),
                cmd_specification.get('usage', usage))

        self._session.emit('building-operation-table.%s' % self._name,
                           operation_table=subcommand_table,
                           session=self._session)
        subcommand_table['help'] = S3HelpCommand(self._session, self,
                                                command_table=subcommand_table,
                                                arg_table=None)
        return subcommand_table

    def _get_command_usage(self, cmd_class):
        return (getattr(cmd_class, 'DESCRIPTION', None),
                getattr(cmd_class, 'USAGE', None))

    def create_help_command(self):
        """
        This function returns a help command object with a filled command
        table.  This command is necessary for generating html docs.
        """
        subcommand_table = self._create_subcommand_table()
        del subcommand_table['help']
        return S3HelpCommand(self._session, self,
                             command_table=subcommand_table,
                             arg_table=None)


class S3SubCommand(object):
    """
    This is the object corresponding to a S3 subcommand.
    """
    DESCRIPTION = None
    USAGE = None

    def __init__(self, name, session, options, documentation="", usage=""):
        """

        :type name: str
        :param name: The name of the subcommand (``ls``, ``cp``, etc.)

        :type session: ``botocore.session.Session``
        :param session: Session object.

        :type options: dict
        :param options: The options for the ``paths`` argument.

        :type documentation: str
        :param documentation: Documentation for the subcommand.

        :type usage: str
        :param usage: The usage string of the subcommand

        """
        self._name = name
        self._session = session
        self.options = options
        self.documentation = documentation
        self.usage = usage

    def __call__(self, args, parsed_globals):
        """
        The call method first creates a parameter table to be filled with
        the possible parameters for a specified command.  Then a parser is
        created to determine the path(s) used for the command along with
        any extra parameters included in the command line.  The argument
        are parsed and put into a namespace.  All of the parameters in the
        namespace are then stored in a dictionary.  This newly created
        dictionary is passed to a ``CommandParameters`` object that stores
        all of the parameters and does much of the initial error checking for
        the plugin.  The formatted dictionary of parameters in the
        CommandParameters are passed to a CommandArchitecture object and
        sets up the components for the operation and runs the operation.
        """
        param_table = self._create_parameter_table()
        operation_parser = self._create_operation_parser(param_table)
        parsed_args, remaining = operation_parser.parse_known_args(args)
        if remaining:
            raise ValueError(
                "Unknown options: %s" % ', '.join(remaining))
        if 'help' in parsed_args and parsed_args.help == 'help':
            help_object = S3HelpCommand(self._session, self,
                                        command_table=None,
                                        arg_table=param_table)
            help_object(remaining, parsed_globals)
        else:
            self._convert_path_args(parsed_args)
            return self._do_command(parsed_args, parsed_globals)

    def _do_command(self, parsed_args, parsed_globals):
        params = self._build_call_parameters(parsed_args, {})
        cmd_params = CommandParameters(self._session, self._name, params)
        cmd_params.check_region(parsed_globals)
        cmd_params.add_paths(parsed_args.paths)
        cmd_params.check_force(parsed_globals)
        cmd = CommandArchitecture(self._session, self._name,
                                    cmd_params.parameters)
        cmd.create_instructions()
        return cmd.run()

    def _convert_path_args(self, parsed_args):
        if not isinstance(parsed_args.paths, list):
            parsed_args.paths = [parsed_args.paths]
        for i in range(len(parsed_args.paths)):
            path = parsed_args.paths[i]
            if isinstance(path, six.binary_type):
                dec_path = path.decode(sys.getfilesystemencoding())
                enc_path = dec_path.encode('utf-8')
                new_path = enc_path.decode('utf-8')
                parsed_args.paths[i] = new_path

    def create_help_command(self):
        """
        This function returns a help command object with a filled arg
        table.  This command is necessary for generating html docs for
        the specified command.
        """
        arg_table = {}
        add_cmd_params(arg_table, self._name)
        return S3HelpCommand(self._session, self,
                             command_table=None,
                             arg_table=arg_table)

    def _create_parameter_table(self):
        """
        This creates an empty parameter table that will be filled with
        S3Parameter objects corresponding to the specified command when
        the event is emitted.
        """
        parameter_table = {}
        self._session.emit('building-parameter-table.s3.%s' % self._name,
                           parameter_table=parameter_table,
                           command=self._name)

        return parameter_table

    def _build_call_parameters(self, args, service_params):
        """
        This takes all of the commands in the name space and puts them
        into a dictionary
        """
        for name, value in vars(args).items():
            service_params[name] = value
        return service_params

    def _create_operation_parser(self, parameter_table):
        """
        This creates the ArgTableArgParser for the command.  It adds
        an extra argument to the parser, paths, which represents a required
        the number of positional argument that must follow the command's name.
        """
        parser = ArgTableArgParser(parameter_table)
        parser.add_argument("paths", **self.options)
        return parser


class ListCommand(S3SubCommand):
    def _do_command(self, parsed_args, parsed_globals):
        bucket, key = find_bucket_key(parsed_args.paths[0][5:])
        self.service = self._session.get_service('s3')
        self.endpoint = self.service.get_endpoint(parsed_globals.region)
        if not bucket:
            self._list_all_buckets()
        else:
            self._list_all_objects(bucket, key)
        return 0

    def _list_all_objects(self, bucket, key):
        operation = self.service.get_operation('ListObjects')
        iterator = operation.paginate(self.endpoint, bucket=bucket,
                                      prefix=key, delimiter='/')
        for _, response_data in iterator:
            common_prefixes = response_data['CommonPrefixes']
            contents = response_data['Contents']
            for common_prefix in common_prefixes:
                prefix_components = common_prefix['Prefix'].split('/')
                prefix = prefix_components[-2]
                pre_string = "PRE".rjust(30, " ")
                print_str = pre_string + ' ' + prefix + '/\n'
                uni_print(print_str)
                sys.stdout.flush()
            for content in contents:
                last_mod_str = self._make_last_mod_str(content['LastModified'])
                size_str = self._make_size_str(content['Size'])
                filename_components = content['Key'].split('/')
                filename = filename_components[-1]
                print_str = last_mod_str + ' ' + size_str + ' ' + \
                    filename + '\n'
                uni_print(print_str)
                sys.stdout.flush()

    def _list_all_buckets(self):
        operation = self.service.get_operation('ListBuckets')
        response_data = operation.call(self.endpoint)[1]
        buckets = response_data['Buckets']
        for bucket in buckets:
            last_mod_str = self._make_last_mod_str(bucket['CreationDate'])
            print_str = last_mod_str + ' ' + bucket['Name'] + '\n'
            uni_print(print_str)
            sys.stdout.flush()

    def _make_last_mod_str(self, last_mod):
        """
        This function creates the last modified time string whenever objects
        or buckets are being listed
        """
        last_mod = parse(last_mod)
        last_mod = last_mod.astimezone(tzlocal())
        last_mod_tup = (str(last_mod.year), str(last_mod.month).zfill(2),
                        str(last_mod.day).zfill(2), str(last_mod.hour).zfill(2),
                        str(last_mod.minute).zfill(2),
                        str(last_mod.second).zfill(2))
        last_mod_str = "%s-%s-%s %s:%s:%s" % last_mod_tup
        return last_mod_str.ljust(19, ' ')

    def _make_size_str(self, size):
        """
        This function creates the size string when objects are being listed.
        """
        size_str = str(size)
        return size_str.rjust(10, ' ')


class WebsiteCommand(S3SubCommand):
    DESCRIPTION = 'Set the website configuration for a bucket.'
    USAGE = 's3://bucket [--index-document|--error-document] value'

    def _do_command(self, parsed_args, parsed_globals):
        service = self._session.get_service('s3')
        endpoint = service.get_endpoint(parsed_globals.region)
        operation = service.get_operation('PutBucketWebsite')
        bucket = self._get_bucket_name(parsed_args.paths[0])
        website_configuration = self._build_website_configuration(parsed_args)
        operation.call(endpoint, bucket=bucket,
                       website_configuration=website_configuration)
        return 0

    def _build_website_configuration(self, parsed_args):
        website_config = {}
        if parsed_args.index_document is not None:
            website_config['IndexDocument'] = {'Suffix': parsed_args.index_document}
        elif parsed_args.error_document is not None:
            website_config['ErrorDocument'] = {'Key': parsed_args.error_document}
        return website_config

    def _get_bucket_name(self, path):
        # We support either:
        # s3://bucketname
        # bucketname
        #
        # We also strip off the trailing slash if a user
        # accidently appends a slash.
        if path.startswith('s3://'):
            path = path[5:]
        if path.endswith('/'):
            path = path[:-1]
        return path


class S3Parameter(BaseCLIArgument):
    """
    This is a class that is used to add a parameter to the the parser along
    with its respective actions, dest, etc.
    """
    def __init__(self, name, options, documentation=''):
        self._name = name
        self.options = options
        self._documentation = documentation

    @property
    def documentation(self):
        return self._documentation

    def add_to_parser(self, parser):
        parser.add_argument('--' + self._name, **self.options)


class CommandArchitecture(object):
    """
    This class drives the actual command.  A command is performed in two
    steps.  First a list of instructions is generated.  This list of
    instructions identifies which type of components are required based on the
    name of the command and the parameters passed to the command line.  After
    the instructions are generated the second step involves using the
    lsit of instructions to wire together an assortment of generators to
    perform the command.
    """
    def __init__(self, session, cmd, parameters):
        self.session = session
        self.cmd = cmd
        self.parameters = parameters
        self.instructions = []
        self._service = self.session.get_service('s3')
        self._endpoint = self._service.get_endpoint(self.parameters['region'])

    def create_instructions(self):
        """
        This function creates the instructions based on the command name and
        extra parameters.  Note that all commands must have an s3_handler
        instruction in the instructions and must be at the end of the
        instruction list because it sends the request to S3 and does not
        yield anything.
        """
        if self.cmd not in ['mb', 'rb']:
            self.instructions.append('file_generator')
        if self.parameters.get('filters'):
            self.instructions.append('filters')
        if self.cmd == 'sync':
            self.instructions.append('comparator')
        self.instructions.append('s3_handler')

    def run(self):
        """
        This function wires together all of the generators and completes
        the command.  First a dictionary is created that is indexed first by
        the command name.  Then using the instruction, another dictionary
        can be indexed to obtain the objects corresponding to the
        particular instruction for that command.  To begin the wiring,
        either a ``FileFormat`` or ``TaskInfo`` object, depending on the
        command, is put into a list.  Then the function enters a while loop
        that pops off an instruction.  It then determines the object needed
        and calls the call function of the object using the list as the input.
        Depending on the number of objects in the input list and the number
        of components in the list corresponding to the instruction, the call
        method of the component can be called two different ways.  If the
        number of inputs is equal to the number of components a 1:1 mapping of
        inputs to components is used when calling the call function.  If the
        there are more inputs than components, then a 2:1 mapping of inputs to
        components is used where the component call method takes two inputs
        instead of one.  Whatever files are yielded from the call function
        is appended to a list and used as the input for the next repetition
        of the while loop until there are no more instructions.
        """
        src = self.parameters['src']
        dest = self.parameters['dest']
        paths_type = self.parameters['paths_type']
        files = FileFormat().format(src, dest, self.parameters)
        rev_files = FileFormat().format(dest, src, self.parameters)

        cmd_translation = {}
        cmd_translation['locals3'] = {'cp': 'upload', 'sync': 'upload',
                                      'mv': 'move'}
        cmd_translation['s3s3'] = {'cp': 'copy', 'sync': 'copy', 'mv': 'move'}
        cmd_translation['s3local'] = {'cp': 'download', 'sync': 'download',
                                      'mv': 'move'}
        cmd_translation['s3'] = {
            'rm': 'delete',
            'mb': 'make_bucket',
            'rb': 'remove_bucket'
        }
        operation_name = cmd_translation[paths_type][self.cmd]

        file_generator = FileGenerator(self._service, self._endpoint,
                                       operation_name,
                                       self.parameters)
        rev_generator = FileGenerator(self._service, self._endpoint, '',
                                      self.parameters)
        taskinfo = [TaskInfo(src=files['src']['path'],
                             src_type='s3',
                             operation_name=operation_name,
                             service=self._service,
                             endpoint=self._endpoint)]
        s3handler = S3Handler(self.session, self.parameters)

        command_dict = {}
        command_dict['sync'] = {'setup': [files, rev_files],
                                'file_generator': [file_generator,
                                                   rev_generator],
                                'filters': [Filter(self.parameters),
                                            Filter(self.parameters)],
                                'comparator': [Comparator(self.parameters)],
                                's3_handler': [s3handler]}

        command_dict['cp'] = {'setup': [files],
                              'file_generator': [file_generator],
                              'filters': [Filter(self.parameters)],
                              's3_handler': [s3handler]}

        command_dict['rm'] = {'setup': [files],
                              'file_generator': [file_generator],
                              'filters': [Filter(self.parameters)],
                              's3_handler': [s3handler]}

        command_dict['mv'] = {'setup': [files],
                              'file_generator': [file_generator],
                              'filters': [Filter(self.parameters)],
                              's3_handler': [s3handler]}

        command_dict['mb'] = {'setup': [taskinfo],
                              's3_handler': [s3handler]}

        command_dict['rb'] = {'setup': [taskinfo],
                              's3_handler': [s3handler]}

        files = command_dict[self.cmd]['setup']

        while self.instructions:
            instruction = self.instructions.pop(0)
            file_list = []
            components = command_dict[self.cmd][instruction]
            for i in range(len(components)):
                if len(files) > len(components):
                    file_list.append(components[i].call(*files))
                else:
                    file_list.append(components[i].call(files[i]))
            files = file_list
        # This is kinda quirky, but each call through the instructions
        # will replaces the files attr with the return value of the
        # file_list.  The very last call is a single list of
        # [s3_handler], and the s3_handler returns the number of
        # tasks failed.  This means that files[0] now contains
        # the number of failed tasks.  In terms of the RC, we're
        # keeping it simple and saying that > 0 failed tasks
        # will give a 1 RC.
        rc = 0
        if files[0] > 0:
            rc = 1
        return rc


class CommandParameters(object):
    """
    This class is used to do some initial error based on the
    parameters and arguments passed to the command line.
    """
    def __init__(self, session, cmd, parameters):
        """
        Stores command name and parameters.  Ensures that the ``dir_op`` flag
        is true if a certain command is being used.
        """
        self.session = session
        self.cmd = cmd
        self.parameters = parameters
        if 'dir_op' not in parameters:
            self.parameters['dir_op'] = False
        if self.cmd in ['sync', 'mb', 'rb']:
            self.parameters['dir_op'] = True

    def add_paths(self, paths):
        """
        Reformats the parameters dictionary by including a key and
        value for the source and the destination.  If a destination is
        not used the destination is the same as the source to ensure
        the destination always have some value.
        """
        self.check_path_type(paths)
        self.check_src_path(paths)
        src_path = paths[0]
        self.parameters['src'] = src_path
        if len(paths) == 2:
            self.parameters['dest'] = paths[1]
        elif len(paths) == 1:
            self.parameters['dest'] = paths[0]
        self.check_dest_path(self.parameters['dest'])

    def check_dest_path(self, destination):
        if destination.startswith('s3://') and \
                self.cmd in ['cp', 'sync', 'mv']:
            bucket, key = find_bucket_key(destination[5:])
            # A bucket is not always provided (like 'aws s3 ls')
            # so only verify the bucket exists if we actually have
            # a bucket.
            if bucket:
                self._verify_bucket_exists(bucket)

    def _verify_bucket_exists(self, bucket_name):
        session = self.session
        service = session.get_service('s3')
        endpoint = service.get_endpoint(self.parameters['region'])
        operation = service.get_operation('ListObjects')
        # This will raise an exception if the bucket does not exist.
        operation.call(endpoint, bucket=bucket_name, max_keys=0)

    def check_path_type(self, paths):
        """
        This initial check ensures that the path types for the specified
        command is correct.
        """
        template_type = {'s3s3': ['cp', 'sync', 'mv'],
                         's3local': ['cp', 'sync', 'mv'],
                         'locals3': ['cp', 'sync', 'mv'],
                         's3': ['mb', 'rb', 'rm'],
                         'local': [], 'locallocal': []}
        paths_type = ''
        usage = "usage: aws s3 %s %s" % (self.cmd,
                                         CMD_DICT[self.cmd]['usage'])
        for i in range(len(paths)):
            if paths[i].startswith('s3://'):
                paths_type = paths_type + 's3'
            else:
                paths_type = paths_type + 'local'
        if self.cmd in template_type[paths_type]:
            self.parameters['paths_type'] = paths_type
        else:
            raise TypeError("%s\nError: Invalid argument type" % usage)

    def check_src_path(self, paths):
        """
        This checks the source paths to deem if they are valid.  The check
        performed in S3 is first it lists the objects using the source path.
        If there is an error like the bucket does not exist, the error will be
        caught with ``check_error()`` function.  If the operation is on a
        single object in s3, it checks that a list of object was returned and
        that the first object listed is the name of the specified in the
        command line.  If the operation is on objects under a common prefix,
        it will check that there are common prefixes and objects under
        the specified prefix.
        For local files, it first checks that the path exists.  Then it checks
        that the path is a directory if it is a directory operation or that
        the path is a file if the operation is on a single file.
        """
        src_path = paths[0]
        dir_op = self.parameters['dir_op']
        if src_path.startswith('s3://'):
            if self.cmd in ['mb', 'rb']:
                return
            session = self.session
            service = session.get_service('s3')
            endpoint = service.get_endpoint(self.parameters['region'])
            src_path = src_path[5:]
            if dir_op:
                if not src_path.endswith('/'):
                    src_path += '/'  # all prefixes must end with a /
            bucket, key = find_bucket_key(src_path)
            operation = service.get_operation('ListObjects')
            response_data = operation.call(endpoint, bucket=bucket, prefix=key,
                                           delimiter='/')[1]
            check_error(response_data)
            contents = response_data['Contents']
            common_prefixes = response_data['CommonPrefixes']
            if not dir_op:
                if contents:
                    if contents[0]['Key'] == key:
                        pass
                    else:
                        raise Exception("Error: S3 Object does not exist")
                else:
                    raise Exception('Error: S3 Object does not exist')
            else:
                if not contents and not common_prefixes:
                    raise Exception('Error: S3 Prefix does not exist')

        else:
            src_path = os.path.abspath(src_path)
            if os.path.exists(src_path):
                if os.path.isdir(src_path) and not dir_op:
                    raise Exception("Error: Requires a local file")
                elif os.path.isfile(src_path) and dir_op:
                    raise Exception("Error: Requires a local directory")
                else:
                    pass
            else:
                raise Exception("Error: Local path does not exist")

    def check_force(self, parsed_globals):
        """
        This function recursive deletes objects in a bucket if the force
        parameters was thrown when using the remove bucket command.
        """
        if 'force' in self.parameters:
            if self.parameters['force']:
                bucket = find_bucket_key(self.parameters['src'][5:])[0]
                path = 's3://' + bucket
                try:
                    del_objects = S3SubCommand('rm', self.session, {'nargs': 1})
                    del_objects([path, '--recursive'], parsed_globals)
                except:
                    pass

    def check_region(self, parsed_globals):
        """
        This ensures that a region has been specified whether it was using
        a configuration file, environment variable, or using the command line.
        If the region is specified on the command line it takes priority
        over specification via a configuration file or environment variable.
        """
        configuration = self.session.get_config()
        env = os.environ.copy()
        region = None
        if 'region' in configuration.keys():
            region = configuration['region']
        if 'AWS_DEFAULT_REGION' in env.keys():
            region = env['AWS_DEFAULT_REGION']
        parsed_region = None
        if 'region' in parsed_globals:
            parsed_region = getattr(parsed_globals, 'region')
        if not region and not parsed_region:
            raise Exception("A region must be specified --region or "
                            "specifying the region\nin a configuration "
                            "file or as an environment variable\n")
        if parsed_region:
            self.parameters['region'] = parsed_region
        else:
            self.parameters['region'] = region


# This is a dictionary useful for automatically adding the different commands,
# the amount of arguments it takes, and the optional parameters that can appear
# on the same line as the command.  It also contains descriptions and usage
# keys for help command and doc generation.
CMD_DICT = {'cp': {'options': {'nargs': 2},
                   'params': ['dryrun', 'quiet', 'recursive',
                              'include', 'exclude', 'acl',
                              'no-guess-mime-type',
                              'sse', 'storage-class', 'grants',
                              'website-redirect', 'content-type',
                              'cache-control', 'content-disposition',
                              'content-encoding', 'content-language',
                              'expires']},
            'mv': {'options': {'nargs': 2},
                   'params': ['dryrun', 'quiet', 'recursive',
                              'include', 'exclude', 'acl',
                              'sse', 'storage-class', 'grants',
                              'website-redirect', 'content-type',
                              'cache-control', 'content-disposition',
                              'content-encoding', 'content-language',
                              'expires']},
            'rm': {'options': {'nargs': 1},
                   'params': ['dryrun', 'quiet', 'recursive',
                              'include', 'exclude']},
            'sync': {'options': {'nargs': 2},
                     'params': ['dryrun', 'delete', 'exclude',
                                'include', 'quiet', 'acl', 'grants',
                                'no-guess-mime-type',
                                'sse', 'storage-class', 'content-type',
                                'cache-control', 'content-disposition',
                                'content-encoding', 'content-language',
                                'expires']},
            'ls': {'options': {'nargs': '?', 'default': 's3://'},
                   'params': [], 'default': 's3://',
                   'command_class': ListCommand},
            'mb': {'options': {'nargs': 1}, 'params': []},
            'rb': {'options': {'nargs': 1}, 'params': ['force']},
            'website': {'options': {'nargs': 1},
                        'params': ['index-document', 'error-document'],
                        'command_class': WebsiteCommand},
            }

add_command_descriptions(CMD_DICT)


# This is a dictionary useful for keeping track of the parameters passed to
# add_argument when the parameter is added to the parser.  The documents
# key is a description of what the parameter does and is used for the help
# command and doc generation.
PARAMS_DICT = {'dryrun': {'options': {'action': 'store_true'}},
               'delete': {'options': {'action': 'store_true'}},
               'quiet': {'options': {'action': 'store_true'}},
               'force': {'options': {'action': 'store_true'}},
               'no-guess-mime-type': {'options': {'action': 'store_false',
                                                  'dest': 'guess_mime_type',
                                                  'default': True}},
               'content-type': {'options': {'nargs': 1}},
               'recursive': {'options': {'action': 'store_true',
                                         'dest': 'dir_op'}},
               'exclude': {'options': {'action': AppendFilter, 'nargs': 1,
                           'dest': 'filters'}},
               'include': {'options': {'action': AppendFilter, 'nargs': 1,
                           'dest': 'filters'}},
               'acl': {'options': {'nargs': 1,
                                   'choices': ['private', 'public-read',
                                               'public-read-write']}},
               'grants': {'options': {'nargs': '+'}},
               'sse': {'options': {'action': 'store_true'}},
               'storage-class': {'options': {'nargs': 1,
                                             'choices': [
                                                 'STANDARD',
                                                 'REDUCED_REDUNDANCY']}},
               'website-redirect': {'options': {'nargs': 1}},
               'cache-control': {'options': {'nargs': 1}},
               'content-disposition': {'options': {'nargs': 1}},
               'content-encoding': {'options': {'nargs': 1}},
               'content-language': {'options': {'nargs': 1}},
               'expires': {'options': {'nargs': 1}},
               'index-document': {'options': {}, 'documents':
                   ('A suffix that is appended to a request that is for a '
                    'directory on the website endpoint (e.g. if the suffix '
                    'is index.html and you make a request to '
                    'samplebucket/images/ the data that is returned will '
                    'be for the object with the key name images/index.html) '
                    'The suffix must not be empty and must not include a '
                    'slash character.')},
               'error-document': {'options': {}, 'documents':
                   'The object key name to use when a 4XX class error occurs.'}

               }
add_param_descriptions(PARAMS_DICT)
