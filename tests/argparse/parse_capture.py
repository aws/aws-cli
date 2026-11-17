"""Parse capture compiled into the noninstalled parser oracle executable.

build_capture.py combines this source with the runtime bootstrap at build
time, replacing CLIDriver dispatch with capture_parse_requests. The request
file is a command-line argument; no environment variable selects code.

For an S3 lineage the capture continues past the argument table through the
unpack loop of BasicCommand.__call__, with the parameter-file and shorthand
handlers registered as the CLI registers them, and the leftover check, then
stops where the command would execute.
"""

import argparse
import base64
import copy
import io
import itertools
import json
import os
import re
import sys
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

import awscli.argparser as parsers
from awscli import clidriver
from awscli.argprocess import (
    ParamError,
    ParamShorthandParser,
    ParamSyntaxError,
    unpack_argument,
    unpack_cli_arg,
)
from awscli.arguments import CustomArgument
from awscli.commands import help_requested
from awscli.customizations import globalargs
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.s3.s3 import S3, register_s3_sync_strategies
from awscli.errorhandler import construct_entry_point_handlers_chain
from awscli.paramfile import LOCAL_PREFIX_MAP, URIArgumentHandler
from botocore.exceptions import (
    ParamValidationError as BotocoreParamValidationError,
)
from botocore.loaders import Loader
from botocore.session import Session

# argprocess.ParamError's text: the cli_name it was raised for, then the
# message of the failure.
PARAM_ERROR = re.compile(
    r"^Error parsing parameter '(?P<parameter>[^']*)': (?P<message>.*)\Z",
    re.DOTALL,
)
PARAM_VALIDATION_ERRORS = (
    parsers.ArgParseException,
    ParamValidationError,
    ParamError,
    ParamSyntaxError,
    BotocoreParamValidationError,
)


def jsonable(value: Any) -> Any:
    """The corpus shape of an unpacked value: bytes as base64 under $bytes,
    and a str that is not UTF-8, which json.loads builds from a lone
    surrogate escape, as its unicode_escape spelling under $unicode_escape
    so the corpus stays UTF-8 for the native JSON reader. A key that is
    not UTF-8 is spelled the same way in place."""
    if isinstance(value, bytes):
        return {"$bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {unicode_key(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, str) and not is_utf8(value):
        return {"$unicode_escape": unicode_escape(value)}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise NotImplementedError(f"corpus shape does not cover {value!r}")


def is_utf8(text: str) -> bool:
    """Whether the text encodes as UTF-8, which lone surrogates do not."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def unicode_escape(text: str) -> str:
    """The ASCII unicode_escape spelling of a str."""
    return text.encode("unicode_escape").decode("ascii")


def unicode_key(key: Any) -> Any:
    """A dict key, spelled with unicode_escape when it is not UTF-8."""
    if isinstance(key, str) and not is_utf8(key):
        return unicode_escape(key)
    return key


class NumberSpelling:
    """A JSON number token as the native decoder reports it: its source
    spelling, typed by the presence of a decimal point or an exponent."""

    def __init__(self, token: str) -> None:
        self.token = token

    def __repr__(self) -> str:
        return self.token

    def __str__(self) -> str:
        return self.token


# Named so botocore's report prints <class 'int'> and <class 'float'>.
IntSpelling = type("int", (NumberSpelling,), {"__module__": "builtins"})
FloatSpelling = type("float", (NumberSpelling,), {"__module__": "builtins"})


def spelled_report(
    validate: Callable[[Any, Any], None], model: Any, loaded: Any
) -> str | None:
    """The schema report with JSON numbers kept as their source spelling.

    The native decoder keeps number tokens as text, so its report shows
    `1E2` where json.loads gives `100.0`. None unless `loaded` is a JSON
    object whose spelled values fail validation.
    """
    if not isinstance(loaded, str) or not loaded.lstrip().startswith("{"):
        return None
    try:
        spelled = json.loads(
            loaded,
            object_pairs_hook=OrderedDict,
            parse_int=IntSpelling,
            parse_float=FloatSpelling,
        )
    except ValueError:
        return None
    try:
        validate(model, spelled)
    except BotocoreParamValidationError as error:
        return str(error)
    return None


def capture_parse_requests(request_path: str, data_path: str) -> None:
    """Test-only oracle: stop at raw argument tables, never dispatch commands.

    The comparison observes argparse internals (seen_actions and raw
    per-level namespaces). These hooks are confined to the capture process.
    """

    def deny_network(event: str, args: tuple[object, ...]) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("parse capture attempted network access")

    sys.addaudithook(deny_network)
    session = Session()
    # Preserve HOME and profile variables while excluding user model overrides.
    session.register_component(
        "data_loader",
        Loader(
            extra_search_paths=[data_path],
            include_default_search_paths=False,
        ),
    )
    register_s3_sync_strategies(session)
    # The handlers the unpack loop's events reach in the real CLI.
    session.register(
        "load-cli-arg", URIArgumentHandler(copy.deepcopy(LOCAL_PREFIX_MAP))
    )
    session.register("process-cli-arg", ParamShorthandParser())
    root = S3(session)
    children = root.subcommand_table
    # Building each child table fires sync strategy registration exactly once.
    child_tables = {}
    for name, command in children.items():
        _ = command.subcommand_table
        child_tables[name] = command.arg_table
    definitions = session.get_component("data_loader").load_data("cli")["options"]
    globals_table = {}
    for name, definition in definitions.items():
        data = {
            key: value
            for key, value in definition.items()
            if key not in {"type", "help"}
        }
        globals_table[name] = CustomArgument(name, **data)

    def describe(parser: Any) -> list[dict[str, Any]]:
        actions = {
            "_StoreAction": "store",
            "_StoreTrueAction": "store_true",
            "_StoreFalseAction": "store_false",
            "_AppendAction": "append",
            "_VersionAction": "version",
            "AppendFilter": "append_named",
            "CommandAction": "command",
        }
        result = []
        for action in parser._actions:
            name = (
                action.option_strings[0][2:] if action.option_strings else action.dest
            )
            kind = actions[type(action).__name__]
            choices = action.choices or []
            if isinstance(parser, parsers.MainArgParser) and name == "command":
                kind, choices = "store", []
            result.append(
                {
                    "name": name,
                    "positional": not action.option_strings,
                    "action": kind,
                    "nargs": action.nargs if action.nargs != 0 else None,
                    "const": action.const
                    if kind not in {"store_true", "store_false"}
                    else None,
                    "default": None
                    if action.default == argparse.SUPPRESS
                    else action.default,
                    "choices": list(choices),
                    "dest": action.dest,
                    "required": action.required,
                    "cli_type": None,
                }
            )
        return result

    def capture(request: dict[str, Any]) -> dict[str, Any]:
        argv = request["argv"]
        output = {
            "argv": argv,
            "scope": request.get("scope", "s3"),
            "color": request.get("color", False),
            "levels": [],
            "outcome": "parsed",
            "stage": "auto_prompt",
            "lineage": [],
            "first_pass": {},
            "first_pass_seen": [],
            "globals": {},
            "globals_seen": [],
            "args": {},
            "args_seen": [],
            "remaining": [],
            "skipped": [],
            "values": None,
            "unsupported": None,
            "error": None,
        }
        current_dest = None
        native_report = None

        def unpack(
            command: Any, argument_table: Any, parsed_args: Any
        ) -> dict[str, Any]:
            """The unpack loop of BasicCommand.__call__, verbatim."""
            nonlocal current_dest, native_report
            values = {}
            for key, value in vars(parsed_args).items():
                current_dest = key
                cli_argument = argument_table.get(key.replace("_", "-"))
                value = unpack_argument(
                    session, "custom", command.name, cli_argument, value
                )
                loaded = value
                if command._should_allow_plugins_override(cli_argument, value):
                    override = session.emit_first_non_none_response(
                        f"process-cli-arg.custom.{command.name}",
                        cli_argument=cli_argument,
                        value=value,
                        operation=None,
                    )
                    if override is not None:
                        value = override
                    else:
                        value = unpack_cli_arg(cli_argument, value)
                    validate = command._validate_value_against_schema
                    try:
                        validate(cli_argument.argument_model, value)
                    except BotocoreParamValidationError as error:
                        spelled = spelled_report(
                            validate, cli_argument.argument_model, loaded
                        )
                        if spelled is not None and spelled != str(error):
                            native_report = spelled
                        raise
                values[key] = value
            current_dest = None
            return jsonable(values)

        def level(parser: Any, tokens: list[str]) -> tuple[Any, list[str]]:
            seen = set()
            original = parser._get_values
            choice = None

            def get_values(action: Any, strings: list[str]) -> Any:
                nonlocal choice
                seen.add(action)
                try:
                    return original(action, strings)
                except argparse.ArgumentError:
                    if action.choices:
                        rejected = next(
                            value for value in strings if value not in action.choices
                        )
                        choice = {
                            "argument": action.option_strings[0]
                            if action.option_strings
                            else action.dest,
                            "value": rejected,
                        }
                    raise

            parser._get_values = get_values
            record = {
                "parser": type(parser).__name__,
                "help_mode": getattr(parser, "_help_mode", False),
                "argv": tokens,
                "table": describe(parser),
                "namespace": None,
                "usage": parser.usage or "aws [--profile PROFILE] [--debug]",
                "colored_usage": (
                    parser.format_usage()
                    if parser.usage is None and request.get("color")
                    else None
                ),
                "seen": [],
                "remaining": [],
                "version": False,
                "help": False,
                "error": None,
            }
            output["levels"].append(record)
            try:
                if isinstance(parser, parsers.SubCommandArgParser):
                    parsed, remaining = parsers.ArgTableArgParser.parse_known_args(
                        parser, tokens
                    )
                elif isinstance(parser, parsers.MainArgParser):
                    # The help-mode retry of MainArgParser.parse_known_args
                    # runs as a level of its own, so its parse is recorded.
                    parsed, remaining = parsers.CLIArgParser.parse_known_args(
                        parser, tokens
                    )
                else:
                    parsed, remaining = parser.parse_known_args(tokens)
            except SystemExit:
                record["version"] = True
                raise
            except parsers.ArgParseException as error:
                record["error"] = {
                    "class": "param_validation",
                    "text": str(error),
                    "choice": choice,
                    "usage": parser.format_usage(),
                }
                raise
            finally:
                record["seen"] = [
                    item["name"]
                    for action, item in zip(parser._actions, record["table"])
                    if action in seen
                ]
            record["namespace"] = copy.deepcopy(vars(parsed))
            record["remaining"] = remaining
            record["help"] = getattr(parsed, "help", None) == "help"
            return parsed, remaining

        try:
            clidriver.validate_auto_prompt_args_are_mutually_exclusive(argv)
            output["stage"] = "first_pass"
            parsed, _ = level(parsers.FirstPassGlobalArgParser(prog="aws"), argv)
            output["first_pass"] = vars(parsed)
            output["first_pass_seen"] = output["levels"][-1]["seen"]
            output["stage"] = "main"

            def main_parser(help_mode: bool) -> Any:
                main = parsers.MainArgParser(
                    {"s3": None},
                    "",
                    "",
                    globals_table,
                    prog="aws",
                    help_mode=help_mode,
                )
                check = main._check_value

                def check_main(action: Any, value: Any) -> None:
                    if action.dest != "command":
                        check(action, value)

                main._check_value = check_main

                # The capture does not compare version output; discard it.
                def discard_version(message: str, file: Any = None) -> None:
                    pass

                main._print_message = discard_version
                return main

            try:
                parsed, remaining = level(main_parser(help_mode=False), argv)
            except parsers.ArgParseException:
                # MainArgParser._parse_help_request: parse again in help mode,
                # and keep that parse only when it asks for help. Otherwise the
                # first failure stands, and the retry leaves no level behind.
                failed = len(output["levels"])
                try:
                    parsed, remaining = level(main_parser(help_mode=True), argv)
                except parsers.ArgParseException:
                    parsed = None
                if not getattr(parsed, "help", False):
                    del output["levels"][failed:]
                    raise
            output["globals"] = vars(parsed)
            output["globals_seen"] = output["levels"][-1]["seen"]
            output["stage"] = "dispatch"
            if parsed.command != "s3":
                output["outcome"] = "unresolved"
                output["scope"] = "boundary"
                output["remaining"] = remaining
                return output
            output["lineage"] = ["s3"]
            output["stage"] = "top_level"
            # Run the actual handlers, preserving their ordering and errors.
            # A valid compiled query is recorded as its original raw string.
            query = parsed.query
            try:
                globalargs.resolve_types(parsed)
            finally:
                parsed.query = query
            globalargs.no_sign_request(parsed, session)
            globalargs.resolve_verify_ssl(parsed, session)
            current_dest = "read_timeout"
            globalargs.resolve_cli_read_timeout(parsed, session)
            current_dest = "connect_timeout"
            globalargs.resolve_cli_connect_timeout(parsed, session)
            current_dest = None
            command_table = children
            argument_table = root.arg_table
            output["stage"] = "probe"
            probe, _ = level(
                parsers.SubCommandArgParser(argument_table, command_table),
                remaining,
            )
            name = getattr(probe, "subcommand", None)
            if name is not None:
                remaining = remaining.copy()
                remaining.remove(name)
                output["lineage"].append(name)
                argument_table = child_tables[name]
                command_table = {}
            output["stage"] = "table"
            if help_requested(parsed):
                # BasicCommand.__call__ renders help before it parses the table.
                output["outcome"] = "help"
                return output
            parsed_args, remaining = level(
                parsers.ArgTableArgParser(argument_table, command_table),
                remaining,
            )
            output["args"] = vars(parsed_args)
            output["args_seen"] = output["levels"][-1]["seen"]
            output["remaining"] = remaining
            if getattr(parsed_args, "help", None) == "help":
                # The sentinel's namespace holds only `help`, which the
                # unpack loop cannot change, so help settles at the table.
                output["outcome"] = "help"
                return output
            command = root if name is None else children[name]
            output["stage"] = "unpack"
            output["values"] = unpack(command, argument_table, parsed_args)
            output["stage"] = "leftover"
            if remaining:
                raise ParamValidationError(
                    parsers.format_unknown_options_error(
                        remaining,
                        parsers.get_option_suggestion_candidates(
                            argument_table, session
                        ),
                    )
                )
            # S3._run_main with no subcommand; a leaf would execute here.
            if name is None:
                root._raise_usage_error()
        except SystemExit:
            output["outcome"] = "version"
        except (*PARAM_VALIDATION_ERRORS, ValueError, TypeError) as error:
            # The entry point hands any other Exception to the general
            # handler, so the unpack loop's ValueError (int()) and TypeError
            # (bytes reaching the shorthand parser) are rejections too.
            category = (
                "param_validation"
                if isinstance(error, PARAM_VALIDATION_ERRORS)
                else "general"
            )
            output["outcome"] = "reject"
            output["error"] = {
                "class": category,
                "text": str(error),
                "comparison": "exact",
                "dest": current_dest,
            }
            if isinstance(error, parsers.ArgParseException):
                detail = output["levels"][-1]["error"]
                output["error"].update(choice=detail["choice"], usage=detail["usage"])
                if detail["choice"] is not None:
                    output["error"]["comparison"] = "invalid_choice"
            framing = PARAM_ERROR.match(str(error))
            if isinstance(error, ParamError) and framing is not None:
                # The native decoder words a JSON syntax error its own way;
                # the framing and the received value are compared instead.
                output["error"]["parameter"] = framing.group("parameter")
                if framing.group("message").startswith("Invalid JSON: "):
                    output["error"]["comparison"] = "json_syntax"
            if native_report is not None:
                output["error"]["native_text"] = native_report
                output["error"]["comparison"] = "json_number"
            # Exit status and stderr come from upstream handlers, not command dispatch.
            stderr = io.StringIO()
            status = construct_entry_point_handlers_chain().handle_exception(
                error,
                io.StringIO(),
                stderr,
                parsed_globals=argparse.Namespace(**output["globals"]),
            )
            output["error"]["exit_status"] = status
            output["error"]["stderr"] = stderr.getvalue()
        return output

    def capture_patterns() -> dict[str, Any]:
        patterns = [
            "".join(chars)
            for length in range(7)
            for chars in itertools.product("AO-", repeat=length)
        ]
        result = []
        for positional in (False, True):
            for nargs in (None, "?", "*", "+", 0, 1, 2, 6):
                parser = argparse.ArgumentParser(add_help=False)
                action = argparse.Action(
                    option_strings=[] if positional else ["--value"],
                    dest="value",
                    nargs=nargs,
                )
                regex = parser._get_nargs_pattern(action)
                matches = [re.match(regex, pattern) for pattern in patterns]
                result.append(
                    {
                        "positional": positional,
                        "nargs": nargs,
                        "regex": regex,
                        "counts": [
                            len(match.group(1)) if match else None for match in matches
                        ],
                    }
                )
        return {
            "python": sys.version.split()[0],
            "patterns": result,
        }

    with open(request_path, encoding="utf-8") as requests:
        for line in requests:
            request = json.loads(line)
            if request.get("patterns"):
                print(json.dumps(capture_patterns(), separators=(",", ":")))
                continue
            saved = {key: os.environ.get(key) for key in ("NO_COLOR", "FORCE_COLOR")}
            try:
                if request.get("color", False):
                    os.environ.pop("NO_COLOR", None)
                    os.environ["FORCE_COLOR"] = "1"
                else:
                    os.environ["NO_COLOR"] = "1"
                    os.environ.pop("FORCE_COLOR", None)
                output = capture(request)
            finally:
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            print(json.dumps(output, ensure_ascii=True, separators=(",", ":")))
