//! Validated tables and the parse_known_args algorithm.
use crate::failure::{ParseFailure, ParseFailureKind};
use crate::pattern::{self, Kind};
use crate::token::{self, Token};
use crate::{
    ARG_COUNT_MAX, ARG_LEN_MAX, ARGUMENT_COUNT_MAX, Action, Argument, DefaultValue, Namespace,
    Nargs, POSITIONAL_COUNT_MAX, VALUE_DEPTH_MAX, Value,
};
/// Behavior selected by argparse subclasses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Options {
    /// Fixed usage text following the prefix.
    pub usage: String,
    /// Generated usage may color program, option names, and metavars separately.
    pub colored_usage: Option<String>,
    /// Basename used by generated first-pass usage.
    pub prog: String,
    /// Recognize exactly one help token before parsing.
    pub help_sentinel: bool,
    /// Disable required-option checks for a subcommand probe.
    pub ignore_required: bool,
    /// Permit unambiguous long-option prefixes.
    pub allow_abbrev: bool,
    /// The runtime-built choices of the table's `Action::Command` argument:
    /// the subcommand names. `Argument` holds `&'static` choices, so they
    /// travel here instead of on the argument, and `Parser::new` rejects a
    /// Command argument without them.
    pub command_choices: Option<Vec<&'static str>>,
}
impl Default for Options {
    fn default() -> Self {
        Self {
            usage: String::new(),
            colored_usage: None,
            prog: "aws".into(),
            help_sentinel: false,
            ignore_required: false,
            allow_abbrev: true,
            command_choices: None,
        }
    }
}
impl Options {
    pub fn new(usage: impl Into<String>) -> Self {
        Self {
            usage: usage.into(),
            ..Self::default()
        }
    }
}
/// An invalid argument table.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InitError {
    ConstWithoutOptionalNargs,
    ZeroNargs,
    NegativeNumberLikeOption,
    TableTooLarge,
    CommandWithoutChoices,
}
impl std::fmt::Display for InitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "invalid argument table: {self:?}")
    }
}
impl std::error::Error for InitError {}
/// Successful known-arguments parse.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Parsed {
    pub namespace: Namespace,
    pub seen: Vec<bool>,
    pub remaining: Vec<Token>,
    pub version: bool,
}
/// Syntax rejection retaining the partly assigned namespace.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Rejected {
    pub failure: ParseFailure,
    pub namespace: Namespace,
}
/// Validated table with argparse conflict resolution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Parser {
    pub arguments: Vec<Argument>,
    pub names: Vec<String>,
    pub dests: Vec<String>,
    pub options: Options,
}
#[derive(Debug, Clone, Default)]
struct Optional {
    index: Option<usize>,
    matches: Vec<String>,
    explicit: Option<Token>,
}
struct State<'a> {
    parser: &'a Parser,
    namespace: Namespace,
    args: &'a [Token],
    kinds: Vec<Kind>,
    options: Vec<Optional>,
    seen: Vec<bool>,
    extras: Vec<Token>,
    positionals: Vec<usize>,
    positional_index: usize,
    version: bool,
}
impl Parser {
    /// Validate definitions and resolve duplicate option strings as argparse does.
    pub fn new(arguments: &[Argument], options: Options) -> Result<Self, InitError> {
        if arguments.len() > ARGUMENT_COUNT_MAX {
            return Err(InitError::TableTooLarge);
        }
        let mut table = Vec::new();
        let mut positional_count = 0;
        for (i, arg) in arguments.iter().enumerate() {
            init_validate_argument(*arg)?;
            init_validate_command(*arg, &options)?;
            if arg.positional {
                positional_count += 1;
            } else if init_option_replaced(*arg, &arguments[i + 1..]) {
                continue;
            }
            table.push(*arg);
        }
        if positional_count > POSITIONAL_COUNT_MAX {
            return Err(InitError::TableTooLarge);
        }
        assert!(table.len() <= arguments.len());
        let names: Vec<_> = table.iter().map(|a| a.spelling()).collect();
        if names
            .iter()
            .zip(&table)
            .any(|(n, a)| !a.positional && is_negative_number(n))
        {
            return Err(InitError::NegativeNumberLikeOption);
        }
        let dests = table.iter().map(|a| a.destination()).collect();
        Ok(Self {
            arguments: table,
            names,
            dests,
            options,
        })
    }
    pub fn parse_known_args(&self, args: &[String]) -> Result<Parsed, Rejected> {
        let arguments: Vec<_> = args.iter().map(std::ffi::OsString::from).collect();
        self.parse_tokens(&token::from_os(&arguments))
    }
    pub fn parse_known_os_args(&self, args: &[std::ffi::OsString]) -> Result<Parsed, Rejected> {
        self.parse_tokens(&token::from_os(args))
    }
    pub(crate) fn parse_tokens(&self, args: &[Token]) -> Result<Parsed, Rejected> {
        assert!(args.len() <= ARG_COUNT_MAX);
        assert!(args.iter().all(|a| a.as_os_str().len() <= ARG_LEN_MAX));
        let mut state = State {
            parser: self,
            namespace: Namespace::default(),
            args,
            kinds: Vec::new(),
            options: Vec::new(),
            seen: vec![false; self.arguments.len()],
            extras: Vec::new(),
            positionals: Vec::new(),
            positional_index: 0,
            version: false,
        };
        for (i, (arg, dest)) in self.arguments.iter().zip(&self.dests).enumerate() {
            if state.namespace.value(dest).is_none() && arg.action != Action::Version {
                state.namespace.put(dest, arg.default_value(), false);
            }
            if arg.positional {
                state.positionals.push(i);
            }
        }
        if let Err(failure) = state.parse() {
            return Err(Rejected {
                failure,
                namespace: state.namespace,
            });
        }
        Ok(Parsed {
            namespace: state.namespace,
            seen: state.seen,
            remaining: state.extras,
            version: state.version,
        })
    }
}
impl State<'_> {
    fn failure(&self, index: Option<usize>, kind: ParseFailureKind) -> ParseFailure {
        ParseFailure {
            argument_name: index.map(|i| self.parser.names[i].clone()),
            kind: Box::new(kind),
            usage: self.parser.options.usage.clone(),
            colored_usage: self.parser.options.colored_usage.clone(),
        }
    }
    fn parse_optional(&self, token: &Token) -> Option<Optional> {
        let bytes = token.as_os_str().as_encoded_bytes();
        if bytes.len() < 2 || !bytes.starts_with(b"-") {
            return None;
        }
        // _parse_optional checks the entire option string before splitting '='.
        if let Some(index) = token
            .as_str()
            .and_then(|text| self.parse_optional_exact(text))
        {
            return Some(Optional {
                index: Some(index),
                ..Optional::default()
            });
        }
        if let Some(option) = self.parse_optional_prefix(token) {
            return Some(option);
        }
        if is_negative_number_bytes(bytes) || bytes.contains(&b' ') {
            None
        } else {
            Some(Optional::default())
        }
    }
    fn parse_optional_prefix(&self, token: &Token) -> Option<Optional> {
        let split = token.split_equal();
        let (prefix, explicit) = split
            .as_ref()
            .map_or((token.as_os_str(), None), |(prefix, explicit)| {
                (prefix.as_os_str(), Some(explicit.clone()))
            });
        if let Some(index) = prefix
            .to_str()
            .and_then(|prefix| self.parse_optional_exact(prefix))
        {
            return Some(Optional {
                index: Some(index),
                explicit,
                ..Optional::default()
            });
        }
        let bytes = token.as_os_str().as_encoded_bytes();
        if self.parser.options.allow_abbrev && bytes.starts_with(b"--") {
            return self.parse_optional_prefix_abbreviation(prefix, explicit);
        }
        None
    }
    fn parse_optional_exact(&self, token: &str) -> Option<usize> {
        self.parser
            .arguments
            .iter()
            .zip(&self.parser.names)
            .position(|(a, n)| !a.positional && n == token)
    }
    fn parse_optional_prefix_abbreviation(
        &self,
        prefix: &std::ffi::OsStr,
        explicit: Option<Token>,
    ) -> Option<Optional> {
        let prefix = prefix.to_str()?;
        let mut found = Optional {
            explicit,
            ..Optional::default()
        };
        for (i, (arg, name)) in self
            .parser
            .arguments
            .iter()
            .zip(&self.parser.names)
            .enumerate()
        {
            if !arg.positional && name.starts_with(prefix) {
                found.matches.push(name.clone());
                found.index = Some(i);
            }
        }
        found.index.is_some().then_some(found)
    }
    fn parse(&mut self) -> Result<(), ParseFailure> {
        if self.parser.options.help_sentinel && self.args == ["help"] {
            self.namespace = Namespace::default();
            self.namespace.put("help", "help".into(), true);
            return Ok(());
        }
        let mut start = 0;
        if let Some(last) = self.parse_known_args_classify() {
            start = self.parse_known_args_options(last)?;
        }
        if self.version {
            return Ok(());
        }
        start = self.consume_positionals(start)?;
        self.extras.extend_from_slice(&self.args[start..]);
        self.parse_known_args_required()
    }
    fn parse_known_args_classify(&mut self) -> Option<usize> {
        let mut separated = false;
        let mut last = None;
        for (i, arg) in self.args.iter().enumerate() {
            let mut option = Optional::default();
            let kind = if separated {
                Kind::Argument
            } else if arg == "--" {
                separated = true;
                Kind::Separator
            } else if let Some(found) = self.parse_optional(arg) {
                option = found;
                last = Some(i);
                Kind::Option
            } else {
                Kind::Argument
            };
            self.kinds.push(kind);
            self.options.push(option);
        }
        last
    }
    fn parse_known_args_options(&mut self, last: usize) -> Result<usize, ParseFailure> {
        let mut start = 0;
        while start <= last && !self.version {
            let next = self.parse_known_args_options_next(start, last);
            if start != next {
                let end = self.consume_positionals(start)?;
                if end > start {
                    start = end;
                    continue;
                }
            }
            self.extras.extend_from_slice(&self.args[start..next]);
            start = self.consume_optional(next)?;
        }
        Ok(start)
    }
    fn parse_known_args_options_next(&self, start: usize, last: usize) -> usize {
        (start..=last)
            .find(|i| self.kinds[*i] == Kind::Option)
            .unwrap_or(start)
    }
    fn parse_known_args_required(&self) -> Result<(), ParseFailure> {
        let missing = self
            .parser
            .arguments
            .iter()
            .zip(&self.seen)
            .enumerate()
            .filter(|(_, (a, seen))| {
                !**seen && a.is_required() && (a.positional || !self.parser.options.ignore_required)
            })
            .map(|(i, _)| self.parser.names[i].clone())
            .collect::<Vec<_>>();
        if missing.is_empty() {
            Ok(())
        } else {
            Err(self.failure(None, ParseFailureKind::RequiredMissing(missing)))
        }
    }
    fn match_argument(&self, index: usize, kinds: &[Kind]) -> Result<usize, ParseFailure> {
        let arg = self.parser.arguments[index];
        pattern::match_argument(arg, kinds).ok_or_else(|| {
            self.failure(
                Some(index),
                match arg.arity() {
                    None => ParseFailureKind::ExpectedOneArgument,
                    Some(Nargs::Optional) => ParseFailureKind::ExpectedAtMostOneArgument,
                    Some(Nargs::ZeroOrMore | Nargs::OneOrMore) => {
                        ParseFailureKind::ExpectedAtLeastOneArgument
                    }
                    Some(Nargs::Count(n)) => ParseFailureKind::ExpectedCount(n),
                },
            )
        })
    }
    fn consume_optional(&mut self, start: usize) -> Result<usize, ParseFailure> {
        debug_assert!(self.kinds[start] == Kind::Option);
        let option = self.options[start].clone();
        if option.matches.len() > 1 {
            return Err(self.failure(
                None,
                ParseFailureKind::AmbiguousOption {
                    token: self.args[start].value.clone(),
                    matches: option.matches,
                },
            ));
        }
        let Some(index) = option.index else {
            self.extras.push(self.args[start].clone());
            return Ok(start + 1);
        };
        if let Some(explicit) = option.explicit {
            let count = self.match_argument(index, &[Kind::Argument])?;
            if count != 1 {
                return Err(self.failure(
                    Some(index),
                    ParseFailureKind::IgnoredExplicitArgument(explicit.value),
                ));
            }
            self.take_action(index, &[explicit])?;
            return Ok(start + 1);
        }
        let count = self.match_argument(index, &self.kinds[start + 1..])?;
        self.take_action(index, &self.args[start + 1..start + 1 + count])?;
        Ok(start + 1 + count)
    }
    fn consume_positionals(&mut self, start: usize) -> Result<usize, ParseFailure> {
        debug_assert!(start <= self.args.len());
        let indices = self.positionals[self.positional_index..].to_vec();
        let arguments = indices
            .iter()
            .map(|i| self.parser.arguments[*i])
            .collect::<Vec<_>>();
        let counts = pattern::match_arguments_partial(&arguments, &self.kinds[start..]);
        let mut end = start;
        for (index, count) in indices.iter().zip(&counts) {
            let values = self.args[end..end + count]
                .iter()
                .zip(&self.kinds[end..end + count])
                .filter(|(_, k)| **k != Kind::Separator)
                .map(|(s, _)| s.clone())
                .collect::<Vec<_>>();
            self.take_action(*index, &values)?;
            end += count;
        }
        self.positional_index += counts.len();
        debug_assert!(self.positional_index <= self.positionals.len());
        Ok(end)
    }
    fn values(&self, index: usize, strings: &[Token]) -> Result<Value, ParseFailure> {
        let arg = self.parser.arguments[index];
        if strings.is_empty()
            && let Some(value) = get_values_default(arg)
        {
            return Ok(value);
        }
        for value in strings {
            self.check_value(index, value)?;
        }
        // argparse stores a bare string for nargs None and OPTIONAL only.
        if strings.len() == 1 && matches!(arg.arity(), None | Some(Nargs::Optional)) {
            Ok(strings[0].clone().into())
        } else {
            Ok(strings.to_vec().into())
        }
    }
    fn check_value(&self, index: usize, value: &Token) -> Result<(), ParseFailure> {
        let arg = self.parser.arguments[index];
        let choices = if arg.action == Action::Command {
            self.parser
                .options
                .command_choices
                .as_deref()
                .unwrap_or(arg.choices)
        } else {
            arg.choices
        };
        if choices.is_empty() {
            return Ok(());
        }
        if value.as_str().is_some_and(|value| choices.contains(&value)) {
            return Ok(());
        }
        let suggestions =
            crate::close_matches::close_matches(value.as_os_str().as_encoded_bytes(), choices)
                .into_iter()
                .map(str::to_owned)
                .collect();
        Err(self.failure(
            Some(index),
            ParseFailureKind::InvalidChoice {
                value: value.value.clone(),
                suggestions,
            },
        ))
    }
    fn take_action(&mut self, index: usize, strings: &[Token]) -> Result<(), ParseFailure> {
        debug_assert!(index < self.parser.arguments.len());
        self.seen[index] = true;
        let arg = self.parser.arguments[index];
        let mut value = self.values(index, strings)?;
        let dest = &self.parser.dests[index];
        match arg.action {
            Action::Version => {
                self.version = true;
                return Ok(());
            }
            Action::StoreTrue => value = true.into(),
            Action::StoreFalse => value = false.into(),
            Action::Append | Action::AppendNamed => {
                if arg.action == Action::AppendNamed {
                    assert!(!strings.is_empty());
                    value = vec![
                        Value::from(self.parser.names[index].clone()),
                        Value::from(strings[0].clone()),
                    ]
                    .into();
                }
                assert!(value.depth() < VALUE_DEPTH_MAX);
                self.namespace.append(dest, value);
                return Ok(());
            }
            Action::Store | Action::Command => {}
        }
        assert!(value.depth() <= VALUE_DEPTH_MAX);
        self.namespace.put(dest, value, true);
        Ok(())
    }
}
/// The value _get_values gives an action that consumed no tokens, when its
/// nargs supplies one: OPTIONAL's default or const, and a positional
/// ZERO_OR_MORE's explicit default.
fn get_values_default(arg: Argument) -> Option<Value> {
    match arg.arity()? {
        Nargs::Optional => Some(if arg.positional {
            arg.default.value()
        } else {
            arg.constant.unwrap_or_default().value()
        }),
        Nargs::ZeroOrMore if arg.positional && arg.default != DefaultValue::None => {
            Some(arg.default.value())
        }
        Nargs::ZeroOrMore | Nargs::OneOrMore | Nargs::Count(_) => None,
    }
}
fn init_validate_argument(arg: Argument) -> Result<(), InitError> {
    if arg.constant.is_some() && arg.nargs != Some(Nargs::Optional) {
        return Err(InitError::ConstWithoutOptionalNargs);
    }
    if arg.nargs == Some(Nargs::Count(0)) {
        return Err(InitError::ZeroNargs);
    }
    Ok(())
}
fn init_validate_command(arg: Argument, options: &Options) -> Result<(), InitError> {
    if arg.action == Action::Command && options.command_choices.is_none() {
        return Err(InitError::CommandWithoutChoices);
    }
    Ok(())
}
fn init_option_replaced(arg: Argument, later_arguments: &[Argument]) -> bool {
    later_arguments
        .iter()
        .any(|later| !later.positional && later.name == arg.name)
}
/// Argparse's ASCII negative-number recognition.
pub fn is_negative_number(token: &str) -> bool {
    is_negative_number_bytes(token.as_bytes())
}
fn is_negative_number_bytes(b: &[u8]) -> bool {
    if b.len() < 2 || b[0] != b'-' {
        return false;
    }
    let i = if b[1] == b'.' { 2 } else { 1 };
    b.get(i).is_some_and(u8::is_ascii_digit)
}
#[cfg(test)]
mod tests;
