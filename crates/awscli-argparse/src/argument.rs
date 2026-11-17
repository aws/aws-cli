//! Argument definitions and destination normalization.
use crate::Value;
/// Namespace update performed by an action.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    Store,
    StoreTrue,
    StoreFalse,
    Append,
    AppendNamed,
    Command,
    Version,
}
/// Argument token cardinality.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Nargs {
    Optional,
    ZeroOrMore,
    OneOrMore,
    Count(u8),
}
/// Deferred modeled conversion.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CliType {
    Integer,
    Blob,
    Map,
}
/// Constant values representable in pinned tables.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum DefaultValue {
    #[default]
    None,
    Boolean(bool),
    Integer(i64),
    String(&'static str),
}
impl DefaultValue {
    /// Own the table default for a namespace.
    pub fn value(self) -> Value {
        match self {
            Self::None => Value::Null,
            Self::Boolean(v) => v.into(),
            Self::Integer(v) => v.into(),
            Self::String(v) => v.into(),
        }
    }
}
/// One action in an argparse table.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Argument {
    pub name: &'static str,
    pub dest: Option<&'static str>,
    pub positional: bool,
    pub action: Action,
    pub nargs: Option<Nargs>,
    pub constant: Option<DefaultValue>,
    pub default: DefaultValue,
    pub choices: &'static [&'static str],
    pub required: bool,
    pub cli_type: Option<CliType>,
}
impl Argument {
    /// Define a scalar argument with argparse defaults.
    pub const fn new(name: &'static str) -> Self {
        Self {
            name,
            dest: None,
            positional: false,
            action: Action::Store,
            nargs: None,
            constant: None,
            default: DefaultValue::None,
            choices: &[],
            required: false,
            cli_type: None,
        }
    }
    /// Destination after the default dash replacement.
    pub fn destination(self) -> String {
        self.dest
            .map_or_else(|| self.name.replace('-', "_"), str::to_owned)
    }
    /// Canonical diagnostic spelling.
    pub fn spelling(self) -> String {
        if self.positional {
            self.dest.unwrap_or(self.name).to_owned()
        } else {
            format!("--{}", self.name)
        }
    }
    /// Test a destination in const contexts.
    pub const fn matches_dest(self, dest: &str) -> bool {
        let source = match self.dest {
            Some(v) => v,
            None => self.name,
        }
        .as_bytes();
        let target = dest.as_bytes();
        if source.len() != target.len() {
            return false;
        }
        let mut i = 0;
        while i < source.len() {
            let c = if self.dest.is_none() && source[i] == b'-' {
                b'_'
            } else {
                source[i]
            };
            if c != target[i] {
                return false;
            }
            i += 1;
        }
        true
    }
    /// Whether missing this argument fails parsing.
    pub const fn is_required(self) -> bool {
        if !self.positional {
            return self.required;
        }
        !matches!(self.nargs, Some(Nargs::Optional | Nargs::ZeroOrMore))
    }
    /// Effective arity includes implicit zero operand flags.
    pub const fn arity(self) -> Option<Nargs> {
        match self.nargs {
            Some(v) => Some(v),
            None => match self.action {
                Action::StoreTrue | Action::StoreFalse | Action::Version => Some(Nargs::Count(0)),
                _ => None,
            },
        }
    }
    /// Default after boolean action defaults are applied.
    pub fn default_value(self) -> Value {
        match (self.default, self.action) {
            (DefaultValue::None, Action::StoreTrue) => false.into(),
            (DefaultValue::None, Action::StoreFalse) => true.into(),
            _ => self.default.value(),
        }
    }
}
#[cfg(test)]
mod tests;
