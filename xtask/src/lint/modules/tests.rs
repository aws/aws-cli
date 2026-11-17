use super::*;

#[test]
fn path_attributes_survive_other_attributes_and_visibility() -> Result<(), TaskError> {
    let source = r#"
        #[path = "../../src/bootstrap/sequence.rs"]
        #[cfg(test)]
        pub(crate) mod startup;
        mod ordinary;
    "#;
    assert_eq!(
        declarations(source)?,
        [
            Declaration {
                name: "startup",
                path: Some(PathBuf::from("../../src/bootstrap/sequence.rs")),
            },
            Declaration {
                name: "ordinary",
                path: None,
            },
        ]
    );
    Ok(())
}

#[test]
fn attributes_inside_comments_and_strings_do_not_declare_modules() -> Result<(), TaskError> {
    let source = r###"
        // #[path = "absent.rs"] mod absent;
        const TEXT: &str = r#"#[path = "absent.rs"] mod absent;"#;
        #[path = "unused.rs"] fn unrelated() {}
        mod ordinary;
    "###;
    assert_eq!(
        declarations(source)?,
        [Declaration {
            name: "ordinary",
            path: None,
        }]
    );
    Ok(())
}

#[test]
fn module_paths_decode_raw_and_escaped_rust_strings() -> Result<(), TaskError> {
    for (literal, expected) in [
        (r##"r#"windows\tests.rs"#"##, "windows\\tests.rs"),
        (r#""windows\\tests.rs""#, "windows\\tests.rs"),
        (r#""caf\u{e9}/\x74ests.rs""#, "café/tests.rs"),
        ("\"nested/\\\n    tests.rs\"", "nested/tests.rs"),
    ] {
        assert_eq!(path_literal(literal)?, PathBuf::from(expected));
    }
    Ok(())
}

#[test]
fn invalid_module_path_attributes_fail_explicitly() {
    for source in [
        "#[path = include_str!(\"path\")] mod other;",
        "#[path = b\"other.rs\"] mod other;",
        "#[path = \"\\xFF.rs\"] mod other;",
        "#[path = \"\\u{110000}.rs\"] mod other;",
        "#[path = \"other.rs\"",
    ] {
        assert!(declarations(source).is_err(), "{source}");
    }
}
