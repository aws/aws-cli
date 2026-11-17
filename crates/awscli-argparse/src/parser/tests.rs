#![expect(clippy::unwrap_used, reason = "pinned test fixtures and assertions")]
use super::*;
use crate::DefaultValue;
#[test]
fn shared_destinations_and_duplicate_options_preserve_insertion_order() {
    let args = [
        Argument {
            dest: Some("shared"),
            default: DefaultValue::String("first"),
            ..Argument::new("old")
        },
        Argument {
            action: Action::StoreTrue,
            ..Argument::new("same")
        },
        Argument {
            dest: Some("shared"),
            default: DefaultValue::String("ignored"),
            ..Argument::new("new")
        },
        Argument {
            action: Action::StoreFalse,
            ..Argument::new("same")
        },
    ];
    let parser = Parser::new(&args, Options::new("aws")).unwrap();
    assert_eq!(parser.arguments[2].name, "same");
    let parsed = parser
        .parse_known_args(&["--new", "second", "--old", "last", "--same"].map(str::to_owned))
        .unwrap();
    assert_eq!(parsed.namespace.string("shared"), Some("last"));
    assert!(!parsed.namespace.boolean("same"));
    assert!(parsed.namespace.is_explicit("shared"));
    assert_eq!(parsed.seen, [true, true, true]);
}
#[test]
fn repeated_append_values_keep_a_linear_memory_budget() {
    let table = [
        Argument {
            dest: Some("filters"),
            action: Action::AppendNamed,
            ..Argument::new("include")
        },
        Argument {
            dest: Some("filters"),
            action: Action::AppendNamed,
            ..Argument::new("exclude")
        },
        Argument {
            action: Action::Append,
            nargs: Some(Nargs::Count(1)),
            ..Argument::new("tags")
        },
    ];
    let parser = Parser::new(&table, Options::new("aws")).unwrap();
    let argv = (0..800)
        .flat_map(|i| {
            [
                if i % 2 == 0 { "--include" } else { "--exclude" },
                "*.txt",
                "--tags",
                "key=value",
            ]
            .map(str::to_owned)
        })
        .collect::<Vec<_>>();
    let result = parser.parse_known_args(&argv).unwrap();
    let filters = result
        .namespace
        .value("filters")
        .unwrap()
        .as_array()
        .unwrap();
    let tags = result.namespace.value("tags").unwrap().as_array().unwrap();
    assert_eq!(filters.len(), 800);
    assert_eq!(tags.len(), 800);
    for (i, (filter, tag)) in filters.iter().zip(tags).enumerate() {
        assert_eq!(
            filter[0],
            if i % 2 == 0 { "--include" } else { "--exclude" }
        );
        assert_eq!(filter[1], "*.txt");
        assert_eq!(tag[0], "key=value");
    }
    let total = retained(&result);
    assert!(total < argv.len() * 640, "{total} retained bytes");
}
fn retained_value(value: &Value) -> usize {
    match value {
        Value::Null | Value::Bool(_) => 0,
        Value::Number(text) | Value::String(text) => text.capacity(),
        Value::OsString(text) => text.capacity(),
        Value::Bytes(bytes) => bytes.capacity(),
        Value::Array(values) => {
            values.capacity() * size_of::<Value>()
                + values.iter().map(retained_value).sum::<usize>()
        }
        Value::Object(pairs) => pairs
            .iter()
            .map(|(key, value)| {
                size_of::<(String, Value)>() + key.capacity() + retained_value(value)
            })
            .sum(),
    }
}
fn retained(parsed: &Parsed) -> usize {
    let entries = &parsed.namespace.entries;
    let namespace = entries.capacity() * size_of::<crate::namespace::Entry>()
        + entries
            .iter()
            .map(|entry| entry.dest.capacity() + retained_value(&entry.value))
            .sum::<usize>();
    let remaining = parsed.remaining.capacity() * size_of::<Token>()
        + parsed
            .remaining
            .iter()
            .map(|token| token.value.capacity())
            .sum::<usize>();
    namespace + parsed.seen.capacity() * size_of::<bool>() + remaining
}
#[test]
fn appended_pairs_reach_but_do_not_exceed_the_value_depth_bound() {
    let table = [
        Argument {
            dest: Some("filters"),
            action: Action::AppendNamed,
            ..Argument::new("include")
        },
        Argument {
            dest: Some("filters"),
            action: Action::AppendNamed,
            ..Argument::new("exclude")
        },
    ];
    let parser = Parser::new(&table, Options::new("aws")).unwrap();
    let result = parser
        .parse_known_args(&["--include", "*.txt", "--exclude", "*.log"].map(str::to_owned))
        .unwrap();
    let filters = result.namespace.value("filters").unwrap();
    assert_eq!(filters.depth(), 2);
    assert_eq!(filters.depth(), VALUE_DEPTH_MAX);
    assert_eq!(filters[1][0], "--exclude");
    assert_eq!(Value::from("scalar").depth(), 0);
}
#[test]
fn default_options_name_aws_and_allow_abbreviations() {
    let options = Options::default();
    assert!(options.allow_abbrev);
    assert_eq!(options.prog, "aws");
    assert_eq!(Options::new("usage").usage, "usage");
    let table = [Argument {
        action: Action::StoreTrue,
        ..Argument::new("recursive")
    }];
    let parser = Parser::new(&table, options).unwrap();
    let result = parser.parse_known_args(&["--rec".to_owned()]).unwrap();
    assert!(result.namespace.boolean("recursive"));
    assert!(result.remaining.is_empty());
}
#[test]
fn command_arguments_require_runtime_choices() {
    let table = [Argument {
        positional: true,
        action: Action::Command,
        nargs: Some(Nargs::Optional),
        ..Argument::new("subcommand")
    }];
    assert_eq!(
        Parser::new(&table, Options::new("aws")).unwrap_err(),
        InitError::CommandWithoutChoices
    );
    let mut options = Options::new("aws");
    options.command_choices = Some(vec!["ls", "cp"]);
    let parser = Parser::new(&table, options).unwrap();
    let result = parser.parse_known_args(&["ls".to_owned()]).unwrap();
    assert_eq!(result.namespace.string("subcommand"), Some("ls"));
    let rejected = parser.parse_known_args(&["lss".to_owned()]).unwrap_err();
    assert_eq!(
        *rejected.failure.kind,
        ParseFailureKind::InvalidChoice {
            value: "lss".into(),
            suggestions: vec!["ls".into()],
        }
    );
}
#[test]
fn invalid_table_definitions_are_rejected() {
    let config = Options::new("aws");
    assert_eq!(
        Parser::new(
            &[Argument {
                constant: Some(DefaultValue::String("v")),
                ..Argument::new("x")
            }],
            config.clone()
        )
        .unwrap_err(),
        InitError::ConstWithoutOptionalNargs
    );
    assert_eq!(
        Parser::new(
            &[Argument {
                nargs: Some(Nargs::Count(0)),
                ..Argument::new("x")
            }],
            config.clone()
        )
        .unwrap_err(),
        InitError::ZeroNargs
    );
    assert_eq!(
        Parser::new(
            &vec![Argument::new("x"); ARGUMENT_COUNT_MAX + 1],
            config.clone()
        )
        .unwrap_err(),
        InitError::TableTooLarge
    );
    assert_eq!(
        Parser::new(
            &[Argument {
                positional: true,
                ..Argument::new("x")
            }; POSITIONAL_COUNT_MAX + 1],
            config
        )
        .unwrap_err(),
        InitError::TableTooLarge
    );
}
#[test]
fn exact_match_precedes_equals_and_negative_numbers_are_values() {
    let table = [Argument::new("name=x"), Argument::new("name")];
    let parser = Parser::new(&table, Options::new("aws")).unwrap();
    let result =
        parser.parse_known_args(&["--name=x", "ok", "-5", "-.4", "--na"].map(str::to_owned));
    assert!(result.is_err());
    for text in ["-5", "-.4", "-5suffix"] {
        assert!(is_negative_number(text));
    }
    for text in ["-", "-.", "--5"] {
        assert!(!is_negative_number(text));
    }
}

#[test]
#[cfg(unix)]
fn inline_os_values_are_bound_to_the_option_without_changing_remaining_arguments() {
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;
    let parser = Parser::new(&[Argument::new("name")], Options::new("aws")).unwrap();
    let value = OsString::from_vec(b"value-\xff".to_vec());
    let mut argument = OsString::from("--name=");
    argument.push(&value);
    let raw_extra = OsString::from_vec(b"extra-\xfe".to_vec());
    let result = parser
        .parse_known_os_args(&[argument, raw_extra.clone()])
        .unwrap();
    assert_eq!(result.namespace.os_string("name"), Some(value.as_os_str()));
    assert_eq!(result.namespace.string("name"), None);
    assert_eq!(result.remaining[0].original_index, 1);
    assert_eq!(result.remaining[0].value, raw_extra);
}
