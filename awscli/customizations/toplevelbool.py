# language governing permissions and limitations under the License.
"""
Top Level Boolean Parameters
----------------------------

This customization will take a parameter that has
a structure of a single boolean element and allow the argument
to be specified without a value.

Instead of having to say::

    --ebs-optimized '{"Value": true}'
    --ebs-optimized '{"Value": false}'

You can instead say `--ebs-optimized/--no-ebs-optimized`.


"""
import logging
from functools import partial


from awscli.argprocess import detect_shape_structure
from awscli import arguments
from awscli.customizations.utils import validate_mutually_exclusive_handler


LOG = logging.getLogger(__name__)
# This sentinel object is used to distinguish when
# a parameter is not specified vs. specified with no value
# (a value of None).
_NOT_SPECIFIED = object()


def register_bool_params(event_handler):
    event_handler.register('building-argument-table.ec2.*',
                           partial(pull_up_bool,
                                   event_handler=event_handler))


def _qualifies_for_simplification(arg_model):
    if detect_shape_structure(arg_model) == 'structure(scalar)':
        members = arg_model.members
        if (len(members) == 1 and
            list(members.keys())[0] == 'Value' and
            list(members.values())[0].type_name == 'boolean'):
            return True
    return False


def pull_up_bool(argument_table, event_handler, **kwargs):
    # List of tuples of (positive_bool, negative_bool)
    # This is used to validate that we don't specify
    # an --option and a --no-option.
    boolean_pairs = []
    event_handler.register(
        'operation-args-parsed.ec2.*',
        partial(validate_boolean_mutex_groups,
                boolean_pairs=boolean_pairs))
    for value in list(argument_table.values()):
        if hasattr(value, 'argument_model'):
            arg_model = value.argument_model
            if _qualifies_for_simplification(arg_model):
                # Swap out the existing CLIArgument for two args:
                # one that supports --option and --option <some value>
                # and another arg of --no-option.
                new_arg = PositiveBooleanArgument(
                    value.name, arg_model, value._operation_model,
                    value._event_emitter,
                    group_name=value.name,
                    serialized_name=value._serialized_name)
                argument_table[value.name] = new_arg
                negative_name = 'no-%s' % value.name
                negative_arg = NegativeBooleanParameter(
                    negative_name, arg_model, value._operation_model,
                    value._event_emitter,
                    action='store_true', dest='no_%s' % new_arg.py_name,
                    group_name=value.name,
                    serialized_name=value._serialized_name)
                argument_table[negative_name] = negative_arg
                # If we've pulled up a structure(scalar) arg
                # into a pair of top level boolean args, we need
                # to validate that a user only provides the argument
                # once.  They can't say --option/--no-option, nor
                # can they say --option --option Value=false.
                boolean_pairs.append((new_arg, negative_arg))


def validate_boolean_mutex_groups(boolean_pairs, parsed_args, **kwargs):
    # Validate we didn't pass in an --option and a --no-option.
    for positive, negative in boolean_pairs:
        if getattr(parsed_args, positive.py_name) is not _NOT_SPECIFIED and \
                getattr(parsed_args, negative.py_name) is not _NOT_SPECIFIED:
            raise ValueError(
                'Cannot specify both the "%s" option and '
                'the "%s" option.' % (positive.cli_name, negative.cli_name))


class PositiveBooleanArgument(arguments.CLIArgument):
    def __init__(self, name, argument_model, operation_model,
                 event_emitter, serialized_name, group_name):
        super(PositiveBooleanArgument, self).__init__(
            name, argument_model, operation_model, event_emitter,
            serialized_name=serialized_name)
        self._group_name = group_name

    @property
    def group_name(self):
        return self._group_name

    def add_to_parser(self, parser):
        # We need to support three forms:
        # --option-name
        # --option-name Value=(true|false)
        parser.add_argument(self.cli_name,
                            help=self.documentation,
                            action='store',
                            default=_NOT_SPECIFIED,
                            nargs='?')

    def add_to_params(self, parameters, value):
        if value is _NOT_SPECIFIED:
            return
        elif value is None:
            # Then this means that the user explicitly
            # specified this arg with no value,
            # e.g. --boolean-parameter
            # which means we should add a true value
            # to the parameters dict.
            parameters[self._serialized_name] = {'Value': True}
        else:
            # Otherwise the arg was specified with a value.
            parameters[self._serialized_name] = self._unpack_argument(
                value)


class NegativeBooleanParameter(arguments.BooleanArgument):
    def __init__(self, name, argument_model, operation_model,
                 event_emitter, serialized_name, action='store_true',
                 dest=None, group_name=None):
        super(NegativeBooleanParameter, self).__init__(
            name, argument_model, operation_model, event_emitter,
            default=_NOT_SPECIFIED, serialized_name=serialized_name)
        self._group_name = group_name

    def add_to_params(self, parameters, value):
        if value is not _NOT_SPECIFIED and value:
            parameters[self._serialized_name] = {'Value': False}
