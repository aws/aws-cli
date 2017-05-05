import logging
import os

from botocore import model
from botocore.compat import OrderedDict
from botocore.validate import validate_parameters
from botocore.docs.bcdoc import docevents

import awscli
from awscli.argparser import ArgTableArgParser
from awscli.argprocess import unpack_argument, unpack_cli_arg
from awscli.arguments import CustomArgument, create_argument_model_from_schema
from awscli.clidocs import OperationDocumentEventHandler
from awscli.clidriver import CLICommand
from awscli.help import HelpCommand
from awscli.schema import SchemaTransformer

LOG = logging.getLogger(__name__)
_open = open


class _FromFile(object):

    def __init__(self, *paths, **kwargs):
        """
        ``**kwargs`` can contain a ``root_module`` argument
        that contains the root module where the file contents
        should be searched.  This is an optional argument, and if
        no value is provided, will default to ``awscli``.  This means
        that by default we look for examples in the ``awscli`` module.

        """
        self.filename = None
        if paths:
            self.filename = os.path.join(*paths)
        if 'root_module' in kwargs:
            self.root_module = kwargs['root_module']
        else:
            self.root_module = awscli


class BasicCommand(CLICommand):

    """Basic top level command with no subcommands.

    If you want to create a new command, subclass this and
    provide the values documented below.

    """

    # This is the name of your command, so if you want to
    # create an 'aws mycommand ...' command, the NAME would be
    # 'mycommand'
    NAME = 'commandname'
    # This is the description that will be used for the 'help'
    # command.
    DESCRIPTION = 'describe the command'
    # This is optional, if you are fine with the default synopsis
    # (the way all the built in operations are documented) then you
    # can leave this empty.
    SYNOPSIS = ''
    # If you want to provide some hand written examples, you can do
    # so here.  This is written in RST format.  This is optional,
    # you don't have to provide any examples, though highly encouraged!
    EXAMPLES = ''
    # If your command has arguments, you can specify them here.  This is
    # somewhat of an implementation detail, but this is a list of dicts
    # where the dicts match the kwargs of the CustomArgument's __init__.
    # For example, if I want to add a '--argument-one' and an
    # '--argument-two' command, I'd say:
    #
    # ARG_TABLE = [
    #     {'name': 'argument-one', 'help_text': 'This argument does foo bar.',
    #      'action': 'store', 'required': False, 'cli_type_name': 'string',},
    #     {'name': 'argument-two', 'help_text': 'This argument does some other thing.',
    #      'action': 'store', 'choices': ['a', 'b', 'c']},
    # ]
    #
    # A `schema` parameter option is available to accept a custom JSON
    # structure as input. See the file `awscli/schema.py` for more info.
    ARG_TABLE = []
    # If you want the command to have subcommands, you can provide a list of
    # dicts.  We use a list here because we want to allow a user to provide
    # the order they want to use for subcommands.
    # SUBCOMMANDS = [
    #     {'name': 'subcommand1', 'command_class': SubcommandClass},
    #     {'name': 'subcommand2', 'command_class': SubcommandClass2},
    # ]
    # The command_class must subclass from ``BasicCommand``.
    SUBCOMMANDS = []

    FROM_FILE = _FromFile
    # You can set the DESCRIPTION, SYNOPSIS, and EXAMPLES to FROM_FILE
    # and we'll automatically read in that data from the file.
    # This is useful if you have a lot of content and would prefer to keep
    # the docs out of the class definition.  For example:
    #
    # DESCRIPTION = FROM_FILE
    #
    # will set the DESCRIPTION value to the contents of
    # awscli/examples/<command name>/_description.rst
    # The naming conventions for these attributes are:
    #
    # DESCRIPTION = awscli/examples/<command name>/_description.rst
    # SYNOPSIS = awscli/examples/<command name>/_synopsis.rst
    # EXAMPLES = awscli/examples/<command name>/_examples.rst
    #
    # You can also provide a relative path and we'll load the file
    # from the specified location:
    #
    # DESCRIPTION = awscli/examples/<filename>
    #
    # For example:
    #
    # DESCRIPTION = FROM_FILE('command, 'subcommand, '_description.rst')
    # DESCRIPTION = 'awscli/examples/command/subcommand/_description.rst'
    #

    # At this point, the only other thing you have to implement is a _run_main
    # method (see the method for more information).

    def __init__(self, session):
        self._session = session
        self._arg_table = None
        self._subcommand_table = None
        self._lineage = [self]

    def __call__(self, args, parsed_globals):
        # args is the remaining unparsed args.
        # We might be able to parse these args so we need to create
        # an arg parser and parse them.
        self._subcommand_table = self._build_subcommand_table()
        self._arg_table = self._build_arg_table()
        event = 'before-building-argument-table-parser.%s' % \
            ".".join(self.lineage_names)
        self._session.emit(event, argument_table=self._arg_table, args=args,
                           session=self._session)
        parser = ArgTableArgParser(self.arg_table, self.subcommand_table)
        parsed_args, remaining = parser.parse_known_args(args)

        # Unpack arguments
        for key, value in vars(parsed_args).items():
            cli_argument = None

            # Convert the name to use dashes instead of underscore
            # as these are how the parameters are stored in the
            # `arg_table`.
            xformed = key.replace('_', '-')
            if xformed in self.arg_table:
                cli_argument = self.arg_table[xformed]

            value = unpack_argument(
                self._session,
                'custom',
                self.name,
                cli_argument,
                value
            )

            # If this parameter has a schema defined, then allow plugins
            # a chance to process and override its value.
            if self._should_allow_plugins_override(cli_argument, value):
                override = self._session\
                    .emit_first_non_none_response(
                        'process-cli-arg.%s.%s' % ('custom', self.name),
                        cli_argument=cli_argument, value=value, operation=None)

                if override is not None:
                    # A plugin supplied a conversion
                    value = override
                else:
                    # Unpack the argument, which is a string, into the
                    # correct Python type (dict, list, etc)
                    value = unpack_cli_arg(cli_argument, value)
                self._validate_value_against_schema(
                    cli_argument.argument_model, value)

            setattr(parsed_args, key, value)

        if hasattr(parsed_args, 'help'):
            self._display_help(parsed_args, parsed_globals)
        elif getattr(parsed_args, 'subcommand', None) is None:
            # No subcommand was specified so call the main
            # function for this top level command.
            if remaining:
                raise ValueError("Unknown options: %s" % ','.join(remaining))
            return self._run_main(parsed_args, parsed_globals)
        else:
            return self.subcommand_table[parsed_args.subcommand](remaining,
                                                                 parsed_globals)

    def _validate_value_against_schema(self, model, value):
        validate_parameters(value, model)

    def _should_allow_plugins_override(self, param, value):
        if (param and param.argument_model is not None and
                value is not None):
            return True
        return False

    def _run_main(self, parsed_args, parsed_globals):
        # Subclasses should implement this method.
        # parsed_globals are the parsed global args (things like region,
        # profile, output, etc.)
        # parsed_args are any arguments you've defined in your ARG_TABLE
        # that are parsed.  These will come through as whatever you've
        # provided as the 'dest' key.  Otherwise they default to the
        # 'name' key.  For example: ARG_TABLE[0] = {"name": "foo-arg", ...}
        # can be accessed by ``parsed_args.foo_arg``.
        raise NotImplementedError("_run_main")

    def _build_subcommand_table(self):
        subcommand_table = OrderedDict()
        for subcommand in self.SUBCOMMANDS:
            subcommand_name = subcommand['name']
            subcommand_class = subcommand['command_class']
            subcommand_table[subcommand_name] = subcommand_class(self._session)
        self._session.emit('building-command-table.%s' % self.NAME,
                           command_table=subcommand_table,
                           session=self._session,
                           command_object=self)
        self._add_lineage(subcommand_table)
        return subcommand_table

    def _display_help(self, parsed_args, parsed_globals):
        help_command = self.create_help_command()
        help_command(parsed_args, parsed_globals)

    def create_help_command(self):
        command_help_table = {}
        if self.SUBCOMMANDS:
            command_help_table = self.create_help_command_table()
        return BasicHelp(self._session, self, command_table=command_help_table,
                         arg_table=self.arg_table)

    def create_help_command_table(self):
        """
        Create the command table into a form that can be handled by the
        BasicDocHandler.
        """
        commands = {}
        for command in self.SUBCOMMANDS:
            commands[command['name']] = command['command_class'](self._session)
        self._add_lineage(commands)
        return commands

    def _build_arg_table(self):
        arg_table = OrderedDict()
        self._session.emit('building-arg-table.%s' % self.NAME,
                           arg_table=self.ARG_TABLE)
        for arg_data in self.ARG_TABLE:

            # If a custom schema was passed in, create the argument_model
            # so that it can be validated and docs can be generated.
            if 'schema' in arg_data:
                argument_model = create_argument_model_from_schema(
                    arg_data.pop('schema'))
                arg_data['argument_model'] = argument_model
            custom_argument = CustomArgument(**arg_data)

            arg_table[arg_data['name']] = custom_argument
        return arg_table

    def _add_lineage(self, command_table):
        for command in command_table:
            command_obj = command_table[command]
            command_obj.lineage = self.lineage + [command_obj]

    @property
    def arg_table(self):
        if self._arg_table is None:
            self._arg_table = self._build_arg_table()
        return self._arg_table

    @property
    def subcommand_table(self):
        if self._subcommand_table is None:
            self._subcommand_table = self._build_subcommand_table()
        return self._subcommand_table

    @classmethod
    def add_command(cls, command_table, session, **kwargs):
        command_table[cls.NAME] = cls(session)

    @property
    def name(self):
        return self.NAME

    @property
    def lineage(self):
        return self._lineage

    @lineage.setter
    def lineage(self, value):
        self._lineage = value


class BasicHelp(HelpCommand):

    def __init__(self, session, command_object, command_table, arg_table,
                 event_handler_class=None):
        super(BasicHelp, self).__init__(session, command_object,
                                        command_table, arg_table)
        # This is defined in HelpCommand so we're matching the
        # casing here.
        if event_handler_class is None:
            event_handler_class = BasicDocHandler
        self.EventHandlerClass = event_handler_class

        # These are public attributes that are mapped from the command
        # object.  These are used by the BasicDocHandler below.
        self._description = command_object.DESCRIPTION
        self._synopsis = command_object.SYNOPSIS
        self._examples = command_object.EXAMPLES

    @property
    def name(self):
        return self.obj.NAME

    @property
    def description(self):
        return self._get_doc_contents('_description')

    @property
    def synopsis(self):
        return self._get_doc_contents('_synopsis')

    @property
    def examples(self):
        return self._get_doc_contents('_examples')

    @property
    def event_class(self):
        return '.'.join(self.obj.lineage_names)

    def _get_doc_contents(self, attr_name):
        value = getattr(self, attr_name)
        if isinstance(value, BasicCommand.FROM_FILE):
            if value.filename is not None:
                trailing_path = value.filename
            else:
                trailing_path = os.path.join(self.name, attr_name + '.rst')
            root_module = value.root_module
            doc_path = os.path.join(
                os.path.abspath(os.path.dirname(root_module.__file__)),
                'examples', trailing_path)
            with _open(doc_path) as f:
                return f.read()
        else:
            return value

    def __call__(self, args, parsed_globals):
        # Create an event handler for a Provider Document
        instance = self.EventHandlerClass(self)
        # Now generate all of the events for a Provider document.
        # We pass ourselves along so that we can, in turn, get passed
        # to all event handlers.
        docevents.generate_events(self.session, self)
        self.renderer.render(self.doc.getvalue())
        instance.unregister()


class BasicDocHandler(OperationDocumentEventHandler):

    def __init__(self, help_command):
        super(BasicDocHandler, self).__init__(help_command)
        self.doc = help_command.doc

    def build_translation_map(self):
        return {}

    def doc_description(self, help_command, **kwargs):
        self.doc.style.h2('Description')
        self.doc.write(help_command.description)
        self.doc.style.new_paragraph()

    def doc_synopsis_start(self, help_command, **kwargs):
        if not help_command.synopsis:
            super(BasicDocHandler, self).doc_synopsis_start(
                help_command=help_command, **kwargs)
        else:
            self.doc.style.h2('Synopsis')
            self.doc.style.start_codeblock()
            self.doc.writeln(help_command.synopsis)

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        if not help_command.synopsis:
            doc = help_command.doc
            argument = help_command.arg_table[arg_name]
            if argument.synopsis:
                option_str = argument.synopsis
            elif argument.group_name in self._arg_groups:
                if argument.group_name in self._documented_arg_groups:
                    # This arg is already documented so we can move on.
                    return
                option_str = ' | '.join(
                    [a.cli_name for a in
                     self._arg_groups[argument.group_name]])
                self._documented_arg_groups.append(argument.group_name)
            elif argument.cli_type_name == 'boolean':
                option_str = '%s' % argument.cli_name
            elif argument.nargs == '+':
                option_str = "%s <value> [<value>...]" % argument.cli_name
            else:
                option_str = '%s <value>' % argument.cli_name
            if not (argument.required or argument.positional_arg):
                option_str = '[%s]' % option_str
            doc.writeln('%s' % option_str)

        else:
            # A synopsis has been provided so we don't need to write
            # anything here.
            pass

    def doc_synopsis_end(self, help_command, **kwargs):
        if not help_command.synopsis:
            super(BasicDocHandler, self).doc_synopsis_end(
                help_command=help_command, **kwargs)
        else:
            self.doc.style.end_codeblock()

    def doc_examples(self, help_command, **kwargs):
        if help_command.examples:
            self.doc.style.h2('Examples')
            self.doc.write(help_command.examples)

    def doc_subitems_start(self, help_command, **kwargs):
        if help_command.command_table:
            doc = help_command.doc
            doc.style.h2('Available Commands')
            doc.style.toctree()

    def doc_subitem(self, command_name, help_command, **kwargs):
        if help_command.command_table:
            doc = help_command.doc
            doc.style.tocitem(command_name)

    def doc_subitems_end(self, help_command, **kwargs):
        pass

    def doc_output(self, help_command, event_name, **kwargs):
        pass
