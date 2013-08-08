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

import awscli
from awscli import EnvironmentVariables
from awscli.argparser import ServiceArgParser, OperationArgParser
from awscli.help import HelpCommand, ServiceHelpCommand
from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.fileformat import FileFormat
from awscli.customizations.s3.filegenerator import find_bucket_key, \
    FileInfo, FileGenerator
from awscli.customizations.s3.filters import Filter
from awscli.customizations.s3.s3handler import S3Handler, check_error
from bcdoc.clidocs import CLIDocumentEventHandler
import bcdoc.clidocevents


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


"""
This is a dictionary useful for automatically adding the different commands,
the amount of arguments it takes, and the optional parameters that can appear
on the same line as the command.  It also contains descriptions and usage
keys for help command and doc generation.
"""
cmd_dict = {'cp': {'options': {'nargs': 2},
                   'params': ['dryrun', 'quiet', 'recursive',
                              'include', 'exclude', 'acl']},
            'mv': {'options': {'nargs': 2},
                   'params': ['dryrun', 'quiet', 'recursive',
                              'include', 'exclude', 'acl']},
            'rm': {'options': {'nargs': 1},
                   'params': ['dryrun', 'quiet', 'recursive',
                              'include', 'exclude']},
            'sync': {'options': {'nargs': 2},
                     'params': ['dryrun', 'delete', 'exclude',
                                'include', 'quiet', 'acl']},
            'ls': {'options': {'nargs': '?', 'default': 's3://'},
                   'params': [], 'default': 's3://'},
            'mb': {'options': {'nargs': 1}, 'params': []},
            'rb': {'options': {'nargs': 1}, 'params': ['force']}
            }

cmd_dict['cp']['description'] = "Copies a local file or S3 object to another \
                                location locally or in S3"
cmd_dict['cp']['usage'] = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
                          "or <S3Path> <S3Path>"
cmd_dict['mv']['description'] = "Moves a local file or S3 object to" \
                                "another location locally or in S3"
cmd_dict['mv']['usage'] = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
                          "or <S3Path> <S3Path>"
cmd_dict['rm']['description'] = "Deletes an S3 object"
cmd_dict['rm']['usage'] = "<S3Path>"
cmd_dict['sync']['description'] = "Syncs directories and S3 prefixes"
cmd_dict['sync']['usage'] = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
                            "or <S3Path> <S3Path>"
cmd_dict['ls']['description'] = "List S3 objects and common prefixes " \
                                "under a prefix or all S3 buckets"
cmd_dict['ls']['usage'] = "<S3Path> or NONE"
cmd_dict['mb']['description'] = "Creates an S3 bucket"
cmd_dict['mb']['usage'] = "<S3Path>"
cmd_dict['rb']['description'] = "Deletes an S3 bucket"
cmd_dict['rb']['usage'] = "<S3Path>"

"""
This is a dictionary useful for keeping track of the parameters passed to
add_argument when the parameter is added to the parser.  The documents
key is a description of what the parameter does and is used for the help
command and doc generation.
"""
params_dict = {'dryrun': {'options': {'action': 'store_true'}},
               'delete': {'options': {'action': 'store_true'}},
               'quiet': {'options': {'action': 'store_true'}},
               'force': {'options': {'action': 'store_true'}},
               'recursive': {'options': {'action': 'store_true',
                                         'dest': 'dir_op'}},
               'exclude': {'options': {'action': AppendFilter, 'nargs': 1,
                           'dest': 'filters'}},
               'include': {'options': {'action': AppendFilter, 'nargs': 1,
                           'dest': 'filters'}},
               'acl': {'options': {'nargs': 1,
                                   'choices': ['private', 'public-read',
                                               'public-read-write']}}
               }

params_dict['dryrun']['documents'] = "Displays the operations that would " \
    "be performed using the specified command without actually running them."

params_dict['quiet']['documents'] = "Does not display the operations " \
    "performed from the specified command."

params_dict['recursive']['documents'] = "Command is performed on all files " \
    "or objects under the specified directory or prefix."

params_dict['delete']['documents'] = "Files that exist in the destination " \
    "but not in the source are deleted during sync."

params_dict['exclude']['documents'] = "Exclude all files or objects from " \
    "the command that follow the specified pattern."

params_dict['include']['documents'] = "Include all files or objects in " \
    "the command that follow the specified pattern."

params_dict['acl']['documents'] = "Sets the ACl for the object when the " \
    "command is performed.  Only accepts values of ``private``, \
    ``public-read``, or ``public-read-write``."

params_dict['force']['documents'] = "Deletes all objects in the bucket " \
    "including the bucket itself."


def awscli_initialize(cli):
    """
    This function is require to use the plugin.  It calls the functions
    required to add all neccessary commands and parameters to the CLI.
    This function is necessary to install the plugin using a configuration
    file
    """
    cli.register("building-command-table.main", add_s3)
    cli.register("building-operation-table.s3", add_commands)
    cli.register("doc-examples.S3.*", add_s3_examples)
    for cmd in cmd_dict.keys():
        cli.register("building-parameter-table.s3.%s" % cmd, add_cmd_params)


def s3_plugin_initialize(event_handlers):
    """
    This is a wrapper to make the plugin built-in to the cli as opposed
    to specifiying it in the configuration file.
    """
    awscli_initialize(event_handlers)


def add_s3(command_table, session, **kwargs):
    """
    This creates a new service object for the s3 plugin
    """
    command_table['s3'] = S3('s3', session)


def add_commands(operation_table, session, **kwargs):
    """
    This create the S3Command objects for each command
    """
    for cmd in cmd_dict.keys():
        operation_table[cmd] = S3Command(cmd, session,
                                         cmd_dict[cmd]['options'],
                                         cmd_dict[cmd]['description'],
                                         cmd_dict[cmd]['usage'])


def add_cmd_params(parameter_table, command, **kwargs):
    """
    This creates the ParameterArgument object for each possible parameter
    in a specified command
    """
    for param in cmd_dict[command]['params']:
        parameter_table[param] = S3Parameter(param,
                                             params_dict[param]['options'],
                                             params_dict[param]['documents'])


def add_s3_examples(help_command, **kwargs):
    """
    This function is used to add examples for each command.  It reads in
    reStructuredTexts in the ``docs/examples`` directory and injects them into
    the help docs for each command.  Each command should have one of these
    example docs.
    """
    doc_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(awscli.__file__))), 'doc', 'source',
                                                    'examples', 's3')
    file_name = 's3-%s.rst' % help_command.obj._name
    doc_path = os.path.join(doc_path, file_name)
    if os.path.isfile(doc_path):
        help_command.doc.style.h2('Examples')
        fp = open(doc_path)
        for line in fp.readlines():
            help_command.doc.write(line)


class S3DocumentEventHandler(CLIDocumentEventHandler):
    """
    This is the document handler for both the service, s3, and
    the commands. It is the basis for the help command and generating docs.
    """
    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        command = help_command.obj
        doc.style.h1(command._name)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        command = help_command.obj
        doc.style.h2('Description')
        doc.include_doc_string(command.documentation)
        if help_command.obj._name == 's3':
            doc_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(awscli.__file__))), 'doc', 'source',
                                                            'tutorial', 's3')
            doc_path = os.path.join(doc_path, 'concepts.rst')
            if os.path.isfile(doc_path):
                help_command.doc.style.h2('Important Concepts')
                fp = open(doc_path)
                for line in fp.readlines():
                    help_command.doc.write(line)

    def doc_synopsis_start(self, help_command, **kwargs):
        if help_command.obj._name != 's3':
            doc = help_command.doc
            command = help_command.obj
            doc.style.h2('Synopsis')
            doc.style.start_codeblock()
            doc.writeln('%s %s' % (command._name, command.usage))

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        option_str = argument._name
        if 'nargs' in argument.options:
            for i in range(argument.options['nargs']):
                option_str += " <value>"
        doc.writeln('[--%s]' % option_str)

    def doc_synopsis_end(self, help_command, **kwargs):
        if help_command.obj._name != 's3':
            doc = help_command.doc
            doc.style.end_codeblock()

    def doc_options_start(self, help_command, **kwargs):
        if help_command.obj._name != 's3':
            doc = help_command.doc
            operation = help_command.obj
            doc.style.h2('Options')
            if len(help_command.arg_table) == 0:
                doc.write('*None*\n')

    def doc_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        doc.write('``--%s``\n' % argument._name)
        doc.style.indent()
        doc.include_doc_string(argument.documentation)
        doc.style.dedent()
        doc.style.new_paragraph()

    def doc_subitems_start(self, help_command, **kwargs):
        if help_command.command_table:
            doc = help_command.doc
            command = help_command.obj
            doc.style.h2('Available Commands')
            doc.style.toctree()

    def doc_subitem(self, command_name, help_command, **kwargs):
        doc = help_command.doc
        command = help_command.obj
        doc.style.tocitem(command_name)


class S3HelpCommand(HelpCommand):
    """
    This is a wrapper to handle the interactions between the commmand and the
    documentation pipeline/
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

    def __init__(self, name, session, op_table={}):
        self._name = name
        self._service_object = S3Service()
        self._session = session
        self.op_table = op_table
        self.documentation = "This provides higher level S3 commands for " \
                             "AWS CLI"

    def __call__(self, args, parsed_globals):
        """
        This function instantiates the operations table to be filled with
        commands.  Creates a parser based off of the commands in the
        operations table.  Parses the valid arguments and passes the
        remaining off to a corresponding S3Command object to be called
        on.
        """
        self._create_operations_table()
        service_parser = self._create_service_parser(self.op_table)
        parsed_args, remaining = service_parser.parse_known_args(args)
        return self.op_table[parsed_args.operation](remaining, parsed_globals)

    def _create_service_parser(self, operation_table):
        """
        Creates the parser required to parse the commands on the
        command line
        """
        return ServiceArgParser(
            operations_table=operation_table, service_name=self._name)

    def _create_operations_table(self):
        """
        Creates an empty dictionary to be filled with S3Command objects
        when the event is emmitted.
        """

        self._session.emit('building-operation-table.%s' % self._name,
                           operation_table=self.op_table,
                           session=self._session)
        self.op_table['help'] = S3HelpCommand(self._session, self,
                                              command_table=self.op_table,
                                              arg_table=None)

    def create_help_command(self):
        """
        This function returns a help command object with a filled command
        table.  This command is necessary for generating html docs.
        """
        command_table = {}
        add_commands(command_table, self._session)
        return S3HelpCommand(self._session, self,
                             command_table=command_table,
                             arg_table=None)


class S3Command(object):
    """
    This is the object corresponding to a S3 command.
    """

    def __init__(self, name, session, options, documentation="", usage=""):
        """
        It stores the name of the command, its current session, and how many
        arguments the command requires.
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
        dictionary is passed to a CommandParameters object that stores
        all of the parameters and does much of the initial error checking for
        the plugin.  The formatted dictionary of parameters in the
        CommandParameters are passed to a CommandArchitecture object and
        sets up the components for the operation and runs the operation.
        """
        param_table = self._create_parameter_table()
        operation_parser = self._create_operation_parser(param_table)
        parsed_args, remaining = operation_parser.parse_known_args(args)
        if remaining:
            raise Exception(
                "Unknown options: %s" % ', '.join(remaining))
        if 'help' in parsed_args and parsed_args.help == 'help':
            help_object = S3HelpCommand(self._session, self,
                                        command_table=None,
                                        arg_table=param_table)
            help_object(remaining, parsed_globals)
        else:
            if not isinstance(parsed_args.paths, list):
                parsed_args.paths = [parsed_args.paths]
            for i in range(len(parsed_args.paths)):
                path = parsed_args.paths[i]
                if isinstance(path, six.binary_type):
                    dec_path = path.decode(sys.getfilesystemencoding())
                    enc_path = dec_path.encode('utf-8')
                    new_path = enc_path.decode('utf-8')
                    parsed_args.paths[i] = new_path
            params = self._build_call_parameters(parsed_args, {})
            cmd_params = CommandParameters(self._session, self._name, params)
            cmd_params.check_region(parsed_globals)
            cmd_params.add_paths(parsed_args.paths)
            cmd_params.check_force(args, parsed_globals)
            cmd = CommandArchitecture(self._session, self._name,
                                      cmd_params.parameters)
            cmd.create_instructions()
            cmd.run()

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
        This creates the OperationArgParser for the command.  It adds
        an extra argument to the parser, paths, which represents a required
        the number of positional argument that must follow the command's name.
        """
        parser = OperationArgParser(parameter_table, self._name)
        parser.add_argument("paths", **self.options)
        return parser


class S3Parameter(object):
    """
    This is a class that is used to add a parameter to the the parser along
    with its respective actions, dest, etc.
    """
    def __init__(self, name, options, documentation=''):
        self._name = name
        self.options = options
        self.documentation = documentation

    def add_to_parser(self, parser):
        parser.add_argument('--'+self._name, **self.options)


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

    def create_instructions(self):
        """
        This function creates the instructions based on the command name and
        extra parameters.  Note that all commands must have an s3_handler
        instruction in the instructions and must be at the end of the
        instruction list because it sends the request to S3 and does not
        yield anything.
        """
        if self.cmd not in ['ls', 'mb', 'rb']:
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
        either a FileFormat or FileInfo object, depending on the
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
        cmd_translation['s3'] = {'rm': 'delete', 'ls': 'list_objects',
                                 'mb': 'make_bucket', 'rb': 'remove_bucket'}
        operation = cmd_translation[paths_type][self.cmd]

        file_generator = FileGenerator(self.session, operation,
                                       self.parameters)
        rev_generator = FileGenerator(self.session, '',
                                      self.parameters)
        fileinfo = [FileInfo(src=files['src']['path'],
                             size=0, operation=operation)]
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

        command_dict['ls'] = {'setup': [fileinfo],
                              's3_handler': [s3handler]}

        command_dict['mb'] = {'setup': [fileinfo],
                              's3_handler': [s3handler]}

        command_dict['rb'] = {'setup': [fileinfo],
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


class CommandParameters(object):
    """
    This class is used to do some initial error based on the
    parameters and arguments passed to the command line.
    """
    def __init__(self, session, cmd, parameters):
        """
        Stores command name and parameters.  Ensures that the dir_op flag
        is true if a certain command is being used.
        """
        self.session = session
        self.cmd = cmd
        self.parameters = parameters
        if 'dir_op' not in parameters:
            self.parameters['dir_op'] = False
        if self.cmd in ['sync', 'ls', 'mb', 'rb']:
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

    def check_path_type(self, paths):
        """
        This initial check ensures that the path types for the specified
        command is correct.
        """
        template_type = {'s3s3': ['cp', 'sync', 'mv'],
                         's3local': ['cp', 'sync', 'mv'],
                         'locals3': ['cp', 'sync', 'mv'],
                         's3': ['ls', 'mb', 'rb', 'rm'],
                         'local': [], 'locallocal': []}
        paths_type = ''
        usage = "usage: aws s3 %s %s" % (self.cmd,
                                         cmd_dict[self.cmd]['usage'])
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
        caught with check_error() funciton.  If the operation is on a
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
            if self.cmd in ['ls', 'mb', 'rb']:
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
            html_response, response_data = operation.call(endpoint,
                                                          bucket=bucket,
                                                          prefix=key,
                                                          delimiter='/')
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

    def check_force(self, args, parsed_globals):
        """
        This function recursive deletes objects in a bucket if the force
        parameters was thrown when using the remove bucket command.
        """
        if 'force' in self.parameters:
            if self.parameters['force']:
                bucket, key = find_bucket_key(self.parameters['src'][5:])
                path = 's3://'+bucket
                try:
                    del_objects = S3Command('rm', self.session, {'nargs': 1})
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
        region = self.session.get_config()['region']
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
