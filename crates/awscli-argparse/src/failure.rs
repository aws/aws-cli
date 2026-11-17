//! Structured parser diagnostics before AWS error-handler framing.
use crate::pyrepr;
use crate::tables::CommandKind;
use crate::unpack::{PYTHON_INT_MAX_STR_DIGITS, ParseIntError};
use std::ffi::{OsStr, OsString};
/// CPython formats the literal of an int() failure with `%.200R`.
const INTEGER_REPR_CODEPOINTS_MAX: usize = 200;
/// Parser syntax failure and its retained usage.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseFailure {
    pub argument_name: Option<String>,
    pub kind: Box<ParseFailureKind>,
    pub usage: String,
    pub colored_usage: Option<String>,
}
/// Exact argparse message alternatives. The argv values they quote stay
/// operating-system strings, which render as Python's stderr writes the
/// surrogates argv decodes to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseFailureKind {
    ExpectedOneArgument,
    ExpectedAtMostOneArgument,
    ExpectedAtLeastOneArgument,
    ExpectedCount(u8),
    IgnoredExplicitArgument(OsString),
    AmbiguousOption {
        /// Original spelling including any equals value.
        token: OsString,
        /// Canonical candidates in table order.
        matches: Vec<String>,
    },
    RequiredMissing(Vec<String>),
    /// CLIArgParser._check_value: the rejected value and difflib's close
    /// matches among the choices, best first.
    InvalidChoice {
        value: OsString,
        suggestions: Vec<String>,
    },
}
/// Pure inputs to CPython's color selection.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Color {
    pub stdout_is_tty: bool,
    pub no_color: bool,
    pub force_color: bool,
    pub term_dumb: bool,
}
impl ParseFailure {
    /// Render str(ArgumentError).
    pub fn message(&self) -> String {
        let prefix = self
            .argument_name
            .as_ref()
            .map(|s| format!("argument {s}: "))
            .unwrap_or_default();
        let body = match &*self.kind {
            ParseFailureKind::ExpectedOneArgument => "expected one argument".into(),
            ParseFailureKind::ExpectedAtMostOneArgument => "expected at most one argument".into(),
            ParseFailureKind::ExpectedAtLeastOneArgument => "expected at least one argument".into(),
            ParseFailureKind::ExpectedCount(n) => {
                format!("expected {n} argument{}", if *n == 1 { "" } else { "s" })
            }
            ParseFailureKind::IgnoredExplicitArgument(v) => {
                format!("ignored explicit argument {}", pyrepr::argv(v))
            }
            ParseFailureKind::AmbiguousOption { token, matches } => format!(
                "ambiguous option: {} could match {}",
                stderr_text(token),
                matches.join(", ")
            ),
            ParseFailureKind::RequiredMissing(names) => {
                format!("the following arguments are required: {}", names.join(", "))
            }
            ParseFailureKind::InvalidChoice { value, suggestions } => {
                let mut text = format!("Found invalid choice '{}'\n", stderr_text(value));
                if !suggestions.is_empty() {
                    text.push_str("\nMaybe you meant:\n");
                }
                for suggestion in suggestions {
                    text.push_str(&format!("\n  * {suggestion}"));
                }
                text
            }
        };
        prefix + &body
    }
    /// Render CLIArgParser.error, including its trailing newline.
    pub fn error_text(&self, color: Color) -> String {
        let enabled =
            !color.no_color && (color.force_color || (!color.term_dumb && color.stdout_is_tty));
        let usage = if enabled {
            self.colored_usage.clone().unwrap_or_else(|| {
                format!("\x1b[1;34musage: \x1b[0m\x1b[35m{}\x1b[0m\n", self.usage)
            })
        } else {
            format!("usage: {}\n", self.usage.trim_end_matches('\n'))
        };
        format!("{}\n\n{usage}", self.message())
    }
}
/// Upstream handler category; cli-core's `cli_error` frames the failure and
/// sets its exit status.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FailureClass {
    /// ParamValidationErrorsHandler: exit 252, code ParamValidation.
    ParamValidation,
    /// UnknownArgumentErrorHandler: prints the fixed usage line first. Exit 252.
    UnknownArgument,
    /// GeneralExceptionHandler: exit 255, plain text only.
    General,
}
impl FailureClass {
    /// The class as the argparse tool's JSON and the corpus spell it.
    pub const fn name(self) -> &'static str {
        match self {
            Self::ParamValidation => "param_validation",
            Self::UnknownArgument => "unknown_argument",
            Self::General => "general",
        }
    }
}
/// In-scope upstream exception sources, with the operands their text needs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FailureKind {
    /// CLIArgParser.error at some level: ArgParseException.
    Parse(Box<ParseFailure>),
    /// validate_auto_prompt_args_are_mutually_exclusive: ParamValidationError.
    AutoPromptConflict,
    /// globalargs._resolve_endpoint_url: ParamValidationError, naming the URL.
    EndpointUrlScheme(OsString),
    /// The `urlparse` of globalargs._resolve_endpoint_url raising for the
    /// brackets in the URL's authority: a bare ValueError. The payload is
    /// `str(exception)`.
    EndpointUrlBrackets(String),
    /// globalargs._resolve_timeout or the unpack loop's int(): a bare
    /// ValueError with the literal's repr.
    InvalidInteger(OsString),
    /// The same int() on a valid literal with more digits than CPython's
    /// limit: a bare ValueError naming the limit and the literal's digit
    /// count, its payload.
    IntegerDigitLimit(usize),
    /// Native policy with no upstream counterpart: an int() literal outside
    /// i64. Upstream forwards any magnitude to the service.
    IntegerOutOfRange(String),
    /// Leftover tokens after the unpack loop, rendered by
    /// argparser.format_unknown_options_error. BasicCommand.__call__ raises
    /// it as ParamValidationError; ServiceOperation.__call__ as
    /// UnknownArgumentError.
    UnknownOptions {
        /// Unconsumed tokens in argv order.
        tokens: Vec<OsString>,
        /// The command implementation, which selects the handler class.
        kind: CommandKind,
        /// The "Maybe you meant" lines, in the order upstream lists them.
        suggestions: Vec<Suggestion>,
    },
    /// BasicCommand._raise_usage_error for a parent command without a
    /// subcommand: ParamValidationError carrying its own usage and
    /// error-prefix lines, so the rendered output has two prefixes. The
    /// payload is the lineage's command names, outermost first.
    TooFewArguments(Vec<&'static str>),
    /// paramfile.get_file's OSError, as argprocess.ParamError, which
    /// prefixes "Error parsing parameter 'NAME': ".
    ParamfileLoad {
        /// The argument's cli_name for the ParamError prefix: "--sse-c-key"
        /// for an option, "paths" for a positional.
        name: String,
        /// The original URI, before path expansion.
        uri: String,
        /// Python's OSError text, "[Errno N] STRERROR: 'PATH'", with the
        /// expanded path.
        errno_text: String,
    },
    /// paramfile.get_file's UnicodeDecodeError on file://, as ParamError.
    ParamfileDecode {
        /// The argument's cli_name for the ParamError prefix.
        name: String,
        /// The expanded path as Python's stderr writes it.
        path: String,
    },
    /// shorthand.ShorthandParseError as ParamError: the grammar's message
    /// with its caret block.
    Shorthand {
        /// The argument's cli_name for the ParamError prefix.
        name: String,
        /// The grammar's message, including its caret block.
        text: String,
    },
    /// argprocess._unpack_json_cli_arg as ParamError: "Invalid JSON:
    /// MSG\nJSON received: VALUE". MSG explains the syntax error and its
    /// location.
    InvalidJson {
        /// The argument's cli_name for the ParamError prefix.
        name: String,
        /// The decoder's explanation, with its location.
        decoder_text: String,
        /// The value as given, after parameter-file loading.
        value: String,
    },
    /// argprocess._unpack_complex_cli_arg on a map value that starts with
    /// '[' after lstrip, as ParamError: "Invalid JSON:\nVALUE".
    NotJsonObject {
        /// The argument's cli_name for the ParamError prefix.
        name: String,
        /// The value as given, after parameter-file loading.
        value: String,
    },
    /// botocore validate_parameters: "Parameter validation failed:\n" and
    /// one line per error, as botocore's ParamValidationError.
    SchemaValidation {
        /// The error lines joined by newlines, in source order.
        report: String,
    },
    /// An exception a `session-initialized` handler lets through
    /// (`CLIDriver.main`), raised once the top-level arguments are handled
    /// and before the command parses its own. The payload is
    /// `str(exception)`.
    SessionInitialized(String),
}
/// One "  * --MATCH (instead of --NAME)" line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Suggestion {
    /// The option the misspelling is close to, without dashes.
    pub matched: String,
    /// The misspelled name's encoded bytes, without dashes or any `=VALUE`.
    pub name: Vec<u8>,
}
impl FailureKind {
    /// The kind's name, the `kind` field of the argparse tool's JSON.
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Parse(_) => "parse",
            Self::AutoPromptConflict => "auto_prompt_conflict",
            Self::EndpointUrlScheme(_) => "endpoint_url_scheme",
            Self::EndpointUrlBrackets(_) => "endpoint_url_brackets",
            Self::InvalidInteger(_) => "invalid_integer",
            Self::IntegerDigitLimit(_) => "integer_digit_limit",
            Self::IntegerOutOfRange(_) => "integer_out_of_range",
            Self::UnknownOptions { .. } => "unknown_options",
            Self::TooFewArguments(_) => "too_few_arguments",
            Self::ParamfileLoad { .. } => "paramfile_load",
            Self::ParamfileDecode { .. } => "paramfile_decode",
            Self::Shorthand { .. } => "shorthand",
            Self::InvalidJson { .. } => "invalid_json",
            Self::NotJsonObject { .. } => "not_json_object",
            Self::SchemaValidation { .. } => "schema_validation",
            Self::SessionInitialized(_) => "session_initialized",
        }
    }
    /// Identify the upstream exception handler.
    pub const fn class(&self) -> FailureClass {
        match self {
            Self::EndpointUrlBrackets(_)
            | Self::InvalidInteger(_)
            | Self::IntegerDigitLimit(_)
            | Self::IntegerOutOfRange(_)
            | Self::SessionInitialized(_) => FailureClass::General,
            Self::UnknownOptions { kind, .. } => match kind {
                CommandKind::Operation => FailureClass::UnknownArgument,
                CommandKind::Basic | CommandKind::Service => FailureClass::ParamValidation,
            },
            Self::Parse(_)
            | Self::AutoPromptConflict
            | Self::EndpointUrlScheme(_)
            | Self::TooFewArguments(_)
            | Self::ParamfileLoad { .. }
            | Self::ParamfileDecode { .. }
            | Self::Shorthand { .. }
            | Self::InvalidJson { .. }
            | Self::NotJsonObject { .. }
            | Self::SchemaValidation { .. } => FailureClass::ParamValidation,
        }
    }
    /// The cli_name a ParamError names; the other kinds name no parameter.
    pub fn parameter(&self) -> Option<&str> {
        match self {
            Self::ParamfileLoad { name, .. }
            | Self::ParamfileDecode { name, .. }
            | Self::Shorthand { name, .. }
            | Self::InvalidJson { name, .. }
            | Self::NotJsonObject { name, .. } => Some(name),
            _ => None,
        }
    }
    /// Render str(exception), with no error-handler prefix.
    pub fn error_text(&self, color: Color) -> String {
        match self {
            Self::Parse(failure) => failure.error_text(color),
            Self::AutoPromptConflict => {
                "Both --cli-auto-prompt and --no-cli-auto-prompt cannot be specified at the same \
                 time."
                    .into()
            }
            Self::EndpointUrlScheme(url) => format!(
                "Bad value for --endpoint-url \"{}\": scheme is missing.  Must be of the \
                 form http://<hostname>/ or https://<hostname>/",
                stderr_text(url)
            ),
            Self::InvalidInteger(value) => format!(
                "invalid literal for int() with base 10: {}",
                pyrepr::limited(value, INTEGER_REPR_CODEPOINTS_MAX)
            ),
            Self::IntegerDigitLimit(digits) => format!(
                "Exceeds the limit ({PYTHON_INT_MAX_STR_DIGITS} digits) for integer string \
                 conversion: value has {digits} digits; use sys.set_int_max_str_digits() to \
                 increase the limit"
            ),
            Self::IntegerOutOfRange(value) => format!(
                "integer outside the 64-bit range of the native command: {}",
                pyrepr::limited(value, INTEGER_REPR_CODEPOINTS_MAX)
            ),
            Self::UnknownOptions {
                tokens,
                suggestions,
                ..
            } => error_text_unknown_options(tokens, suggestions),
            Self::TooFewArguments(lineage) => {
                let mut text = String::from("usage: aws [options]");
                for name in lineage {
                    text.push(' ');
                    text.push_str(name);
                }
                text + " <subcommand> [parameters]\naws: [ERROR]: too few arguments"
            }
            Self::EndpointUrlBrackets(text) | Self::SessionInitialized(text) => text.clone(),
            _ => self.error_text_value(),
        }
    }
    #[expect(
        clippy::unreachable,
        reason = "error_text dispatches only the value kinds here"
    )]
    fn error_text_value(&self) -> String {
        match self {
            Self::ParamfileLoad {
                name,
                uri,
                errno_text,
            } => format!(
                "Error parsing parameter '{name}': Unable to load paramfile {uri}: {errno_text}"
            ),
            Self::ParamfileDecode { name, path } => format!(
                "Error parsing parameter '{name}': Unable to load paramfile ({path}), text \
                 contents could not be decoded.  If this is a binary file, please use the \
                 fileb:// prefix instead of the file:// prefix."
            ),
            Self::Shorthand { name, text } => format!("Error parsing parameter '{name}': {text}"),
            Self::InvalidJson {
                name,
                decoder_text,
                value,
            } => format!(
                "Error parsing parameter '{name}': Invalid JSON: {decoder_text}\nJSON received: \
                 {value}"
            ),
            Self::NotJsonObject { name, value } => {
                format!("Error parsing parameter '{name}': Invalid JSON:\n{value}")
            }
            Self::SchemaValidation { report } => format!("Parameter validation failed:\n{report}"),
            _ => unreachable!("not a value failure: {}", self.name()),
        }
    }
}
/// A kind equals its name, so a check can name the kind it expects, as the
/// argparse tool's JSON spells it, without building the kind's operands.
impl PartialEq<&str> for FailureKind {
    fn eq(&self, other: &&str) -> bool {
        self.name() == *other
    }
}
fn error_text_unknown_options(tokens: &[OsString], suggestions: &[Suggestion]) -> String {
    let tokens: Vec<_> = tokens.iter().map(|token| stderr_text(token)).collect();
    let mut text = format!("Unknown options: {}", tokens.join(", "));
    if !suggestions.is_empty() {
        text.push_str("\n\nMaybe you meant:");
    }
    for suggestion in suggestions {
        text.push_str(&format!(
            "\n  * --{} (instead of --{})",
            suggestion.matched,
            pyrepr::backslash_replaced(&suggestion.name)
        ));
    }
    text
}
/// An argv value a failure's text carries unquoted, as Python's stderr
/// writes the surrogates its undecodable bytes decode to: `\udcff` for the
/// byte 0xFF.
fn stderr_text(value: &OsStr) -> String {
    pyrepr::backslash_replaced(value.as_encoded_bytes())
}
/// AWS CLI parsing failure: its kind and the handler class it maps to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Failure {
    /// `kind.class()`, which `Failure::new` records so the handler chain
    /// reads the class without matching the kind.
    pub class: FailureClass,
    /// Check and diagnostic operands.
    pub kind: FailureKind,
}
impl Failure {
    pub fn new(kind: FailureKind) -> Self {
        Self {
            class: kind.class(),
            kind,
        }
    }
    pub fn parsing(parse: ParseFailure) -> Self {
        Self::new(FailureKind::Parse(Box::new(parse)))
    }
    /// An int() literal Python rejects, one over its digit limit, or one
    /// outside the native i64 range.
    pub fn integer(text: &str, error: ParseIntError) -> Self {
        Self::new(match error {
            ParseIntError::InvalidLiteral => FailureKind::InvalidInteger(text.into()),
            ParseIntError::DigitLimit(digits) => FailureKind::IntegerDigitLimit(digits),
            ParseIntError::OutOfRange => FailureKind::IntegerOutOfRange(text.into()),
        })
    }
    /// Render str(exception), with no error-handler prefix.
    pub fn error_text(&self, color: Color) -> String {
        self.kind.error_text(color)
    }
    /// The cli_name a ParamError names.
    pub fn parameter(&self) -> Option<&str> {
        self.kind.parameter()
    }
}
#[cfg(test)]
mod tests;
