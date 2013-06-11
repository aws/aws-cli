import argparse
from difflib import get_close_matches


class CLIArgParser(argparse.ArgumentParser):
    Formatter = argparse.RawTextHelpFormatter

    # When displaying invalid choice error messages,
    # this controls how many options to show per line.
    ChoicesPerLine = 2

    def _check_value(self, action, value):
        """
        It's probably not a great idea to override a "hidden" method
        but the default behavior is pretty ugly and there doesn't
        seem to be any other way to change it.
        """
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            msg = ['Invalid choice, valid choices are:\n']
            for i in range(len(action.choices))[::self.ChoicesPerLine]:
                current = []
                for choice in action.choices[i:i+self.ChoicesPerLine]:
                    current.append('%-40s' % choice)
                msg.append(' | '.join(current))
            possible = get_close_matches(value, action.choices, cutoff=0.8)
            if possible:
                extra = ['\n\nInvalid choice: %r, maybe you meant:\n' % value]
                for word in possible:
                    extra.append('  * %s' % word)
                msg.extend(extra)
            raise argparse.ArgumentError(action, '\n'.join(msg))


class MainArgParser(CLIArgParser):
    Formatter = argparse.RawTextHelpFormatter

    Description = (
        "The AWS Command Line Interface is a unified tool that provides "
        "a consistent interface for interacting with all parts of AWS.")
    Usage = ("aws [options] <service_name> <operation> [parameters]")

    def __init__(self, command_table, version_string, available_regions):
        super(MainArgParser, self).__init__(
            formatter_class=self.Formatter,
            add_help=False,
            conflict_handler='resolve',
            usage=self.Usage,
            description=self.Description)
        self._build(command_table, version_string, available_regions)

    def _build(self, command_table, version_string, available_regions):
        # TODO: refactor this.
        self.add_argument('--debug', action="store_true", help="Turn on debug logging")
        self.add_argument('--endpoint-url', help="Override service's default URL with the given URL")
        self.add_argument('--no-verify-ssl', action="store_true",
                          help='Override default behavior of verifying SSL certificates')
        self.add_argument('--no-paginate', action='store_false', help='Disable automatic pagination', dest='paginate')
        self.add_argument('--output', choices=['json', 'text', 'table'], metavar='output_format')
        self.add_argument('--profile', help='Use a specific profile from your credential file', metavar='profile_name')
        self.add_argument('--region', metavar='region_name', choices=available_regions)
        self.add_argument('--version', action="version",
                          version=version_string, help='Display the version of this tool')
        self.add_argument('--color', choices=['on', 'off', 'auto'],
                          default='auto', help='Turn on/off color output')
        self.add_argument('command', choices=list(command_table.keys()))


class ServiceArgParser(CLIArgParser):

    Usage = ("aws [options] <service_name> <operation> [parameters]")

    def __init__(self, operations_table, service_name):
        super(ServiceArgParser, self).__init__(
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False,
            conflict_handler='resolve',
            usage=self.Usage)
        self._build(operations_table)
        self._service_name = service_name

    def _build(self, operations_table):
        self.add_argument('operation', choices=list(operations_table.keys()))


class OperationArgParser(CLIArgParser):
    Formatter = argparse.RawTextHelpFormatter
    Usage = ("aws [options] <service_name> <operation> [parameters]")

    type_map = {
        'structure': str,
        'map': str,
        'timestamp': str,
        'list': str,
        'string': str,
        'float': float,
        'integer': str,
        'long': int,
        'boolean': bool,
        'double': float,
        'blob': str}

    def __init__(self, argument_table, name):
        super(OperationArgParser, self).__init__(
            formatter_class=self.Formatter,
            add_help=False,
            usage=self.Usage,
            conflict_handler='resolve')
        self._build(argument_table, name)

    def _build(self, argument_table, name):
        for param in argument_table:
            argument = argument_table[param]
            argument.add_to_parser(self, param)

    def parse_known_args(self, args):
        if len(args) == 1 and args[0] == 'help':
            namespace = argparse.Namespace()
            namespace.help = 'help'
            return namespace, []
        else:
            return super(OperationArgParser, self).parse_known_args(args)
