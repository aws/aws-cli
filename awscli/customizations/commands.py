from bcdoc.clidocs import CLIDocumentEventHandler
import bcdoc.clidocevents

from awscli.argparser import ArgTableArgParser
from awscli.clidriver import CLICommand
from awscli.arguments import CustomArgument
from awscli.help import HelpCommand


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
    ARG_TABLE = []

    # At this point, the only other thing you have to implement is a _run_main
    # method (see the method for more information).

    def __init__(self, session):
        self._session = session

    def __call__(self, args, parsed_globals):
        # args is the remaining unparsed args.
        # We might be able to parse these args so we need to create
        # an arg parser and parse them.
        parser = ArgTableArgParser(self.arg_table)
        parsed_args = parser.parse_args(args)
        if hasattr(parsed_args, 'help'):
            self._display_help(parsed_args, parsed_globals)
        else:
            self._run_main(parsed_args, parsed_globals)

    def _run_main(self, parsed_args, parsed_globals):
        # Subclasses should implement this method.
        # parsed_globals are the parsed global args (things like region,
        # profile, output, etc.)
        # parsed_args are any arguments you've defined in your ARG_TABLE
        # that are parsed.  These will come through as whatever you've
        # provided as the 'dest' key.  Otherwise they default to the
        # 'name' key.  For example: ARG_TABLE[0] = {"name": "foo-arg", ...}
        # can be accessed by ``parsed_args.foo_arg``.
        raise NotImlementedError("_run_main")

    def _display_help(self, parsed_args, parsed_globals):
        help_command = self.create_help_command()
        help_command(parsed_args, parsed_globals)

    def create_help_command(self):
        return BasicHelp(self._session, self, command_table={},
                         arg_table=self.arg_table)

    @property
    def arg_table(self):
        arg_table = {}
        for arg_data in self.ARG_TABLE:
            custom_argument = CustomArgument(**arg_data)
            arg_table[arg_data['name']] = custom_argument
        return arg_table

    @classmethod
    def add_command(cls, command_table, session, **kwargs):
        command_table[cls.NAME] = cls(session)


class BasicHelp(HelpCommand):
    event_class = 'command'

    def __init__(self, session, command_object, command_table, arg_table,
                 event_handler_class=None):
        super(BasicHelp, self).__init__(session, command_object,
                                        command_table, arg_table)
        # This is defined in HelpCommand so we're matching the
        # casing here.
        if event_handler_class is None:
            event_handler_class=BasicDocHandler
        self.EventHandlerClass = event_handler_class

        # These are public attributes that are mapped from the command
        # object.  These are used by the BasicDocHandler below.
        self.description = command_object.DESCRIPTION
        self.synopsis = command_object.SYNOPSIS
        self.examples = command_object.EXAMPLES

    @property
    def name(self):
        return self.obj.NAME

    def __call__(self, args, parsed_globals):
        # Create an event handler for a Provider Document
        instance = self.EventHandlerClass(self)
        # Now generate all of the events for a Provider document.
        # We pass ourselves along so that we can, in turn, get passed
        # to all event handlers.
        bcdoc.clidocevents.generate_events(self.session, self)
        self.renderer.render(self.doc.getvalue())
        instance.unregister()


class BasicDocHandler(CLIDocumentEventHandler):
    def __init__(self, help_command):
        super(BasicDocHandler, self).__init__(help_command)
        self.doc = help_command.doc

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

    def doc_synopsis_end(self, help_command, **kwargs):
        if not help_command.synopsis:
            super(BasicDocHandler, self).doc_synopsis_end(
                help_command=help_command, **kwargs)
        else:
            self.doc.style.end_codeblock()

    def doc_option_example(self, arg_name, help_command, **kwargs):
        pass

    def doc_examples(self, help_command, **kwargs):
        if help_command.examples:
            self.doc.style.h2('Examples')
            self.doc.write(help_command.examples)

    def doc_subitems_start(self, help_command, **kwargs):
        pass

    def doc_subitem(self, command_name, help_command, **kwargs):
        pass

    def doc_subitems_end(self, help_command, **kwargs):
        pass
