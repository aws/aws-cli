use crate::chain::{Level, Outcome, ParseResult, Stage};
use crate::failure::Color;
use crate::tables::{self, Command, CommandKind};
use crate::{Action, Argument, CliType, DefaultValue, Nargs, Value};
/// The `dump-tables` document: the global table and the S3 command tree in
/// the field order the drift checks compare.
pub fn dump_tables() -> Value {
    Value::object([
        ("globals", table_json(tables::GLOBALS)),
        ("s3", command_json(&tables::S3, 0)),
    ])
}
fn table_json(table: &[Argument]) -> Value {
    table.iter().map(argument_json).collect::<Vec<_>>().into()
}
fn argument_json(arg: &Argument) -> Value {
    let nargs = match arg.nargs {
        None => Value::Null,
        Some(Nargs::Optional) => "?".into(),
        Some(Nargs::ZeroOrMore) => "*".into(),
        Some(Nargs::OneOrMore) => "+".into(),
        Some(Nargs::Count(n)) => n.into(),
    };
    let action = match arg.action {
        Action::Store => "store",
        Action::StoreTrue => "store_true",
        Action::StoreFalse => "store_false",
        Action::Append => "append",
        Action::AppendNamed => "append_named",
        Action::Command => "command",
        Action::Version => "version",
    };
    let cli_type = arg.cli_type.map(|t| match t {
        CliType::Integer => "integer",
        CliType::Blob => "blob",
        CliType::Map => "map",
    });
    Value::object([
        ("name", arg.name.into()),
        ("positional", arg.positional.into()),
        ("action", action.into()),
        ("nargs", nargs),
        (
            "const",
            arg.constant.map(DefaultValue::value).unwrap_or(Value::Null),
        ),
        ("default", arg.default_value()),
        ("choices", arg.choices.to_vec().into()),
        ("dest", arg.destination().into()),
        ("required", arg.is_required().into()),
        ("cli_type", cli_type.into()),
    ])
}
fn command_json(command: &Command, depth: usize) -> Value {
    assert!(depth < crate::LINEAGE_DEPTH_MAX);
    let kind = match command.kind {
        CommandKind::Basic => "basic",
        CommandKind::Service => "service",
        CommandKind::Operation => "operation",
    };
    let subcommands = command.subcommands.map(|children| {
        children
            .iter()
            .map(|child| command_json(child, depth + 1))
            .collect::<Vec<_>>()
    });
    Value::object([
        ("name", command.name.into()),
        ("kind", kind.into()),
        ("usage", command.usage.into()),
        ("arguments", table_json(command.arguments)),
        ("subcommands", subcommands.into()),
    ])
}
fn seen_json(level: &Level) -> Value {
    level
        .table
        .iter()
        .zip(&level.seen)
        .filter_map(|(a, s)| s.then_some(a.name))
        .collect::<Vec<_>>()
        .into()
}
/// One complete result object, every oracle comparison field in the
/// canonical order. `unsupported` says value processing handed the
/// invocation to Python; `color` renders the failure text with color.
pub fn result_json(result: &ParseResult, unsupported: bool, color: bool) -> Value {
    let raw = result_raw_fields(result);
    let chain = result_chain_fields(result, unsupported, color);
    Value::Object(
        raw.into_iter()
            .chain(chain)
            .map(|(name, value)| (name.to_owned(), value))
            .collect(),
    )
}
fn result_raw_fields(result: &ParseResult) -> [(&'static str, Value); 10] {
    let version = result.outcome == Outcome::Version;
    let remaining = if let Outcome::Unresolved { remaining, .. } = &result.outcome {
        remaining
    } else {
        &result.args.remaining
    };
    let lineage: Vec<_> = result.lineage.iter().map(|c| c.name).collect();
    let skipped: Vec<&str> = if result.query_syntax_skipped {
        vec!["query_syntax"]
    } else {
        Vec::new()
    };
    [
        ("stage", result.stage.name().into()),
        ("lineage", lineage.into()),
        ("first_pass", result.first_pass.namespace.json()),
        ("first_pass_seen", seen_json(&result.first_pass)),
        (
            "globals",
            if version {
                Value::Object(crate::json::Object::new())
            } else {
                result.globals.namespace.json()
            },
        ),
        (
            "globals_seen",
            if version {
                Vec::<String>::new().into()
            } else {
                seen_json(&result.globals)
            },
        ),
        ("args", result.args.namespace.json()),
        ("args_seen", seen_json(&result.args)),
        ("remaining", remaining.clone().into()),
        ("skipped", skipped.into()),
    ]
}
fn result_chain_fields(
    result: &ParseResult,
    unsupported: bool,
    color: bool,
) -> [(&'static str, Value); 4] {
    let values = if result.stage == Stage::Leftover {
        result.values.json()
    } else {
        Value::Null
    };
    let unsupported_dest = if unsupported {
        result.stopped_dest.as_deref()
    } else {
        None
    };
    [
        ("outcome", outcome_name(result, unsupported).into()),
        ("values", values),
        ("unsupported", unsupported_dest.into()),
        ("error", error_json(result, color)),
    ]
}
fn outcome_name(result: &ParseResult, unsupported: bool) -> &'static str {
    if unsupported {
        return "unsupported";
    }
    match result.outcome {
        Outcome::Parsed => "parsed",
        Outcome::Help => "help",
        Outcome::Version => "version",
        Outcome::UnsupportedOsValue => "unsupported",
        Outcome::Unresolved { .. } => "unresolved",
        Outcome::Failure(_) => "reject",
    }
}
fn error_json(result: &ParseResult, color: bool) -> Value {
    let Outcome::Failure(failure) = &result.outcome else {
        return Value::Null;
    };
    let text = failure.error_text(Color {
        force_color: color,
        ..Color::default()
    });
    Value::object([
        ("class", failure.class.name().into()),
        ("text", text.into()),
        ("dest", result.stopped_dest.clone().into()),
        ("kind", failure.kind.name().into()),
        ("parameter", failure.parameter().map(str::to_owned).into()),
    ])
}
