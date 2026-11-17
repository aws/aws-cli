#![expect(clippy::unwrap_used, reason = "test assertions require fixture values")]
mod filesystem;
use super::*;
use serde_json::{Value as Json, json};

fn sections_json(sections: &Sections) -> Json {
    sections
        .iter()
        .map(|(name, entries)| {
            (
                name.to_owned(),
                entries
                    .iter()
                    .map(|(key, entry)| {
                        let value = match &entry.value {
                            Value::String(value) => Json::String(value.clone()),
                            Value::Nested(nested) => nested
                                .iter()
                                .map(|(key, value)| (key.to_owned(), Json::String(value.clone())))
                                .collect(),
                        };
                        (key.to_owned(), value)
                    })
                    .collect::<Json>(),
            )
        })
        .collect()
}
fn result_json(parsed: &ParsedFiles) -> Json {
    let mut organized = sections_json(&parsed.organized.ordinary);
    organized["profiles"] = sections_json(&parsed.organized.profiles);
    organized["services"] = sections_json(&parsed.organized.services);
    organized["sso_sessions"] = sections_json(&parsed.organized.sso_sessions);
    let file = |file: &File| {
        json!({
            "status": file.status.name(), "sections": sections_json(&file.sections)
        })
    };
    json!({
        "config": file(&parsed.config), "credentials": file(&parsed.credentials),
        "aliases": file(&parsed.aliases), "organized": organized,
        "profiles": parsed.profiles.as_ref().map(sections_json)
    })
}
#[derive(Debug)]
struct Fixture {
    inputs: [Option<Vec<u8>>; 3],
    expected: Json,
}
impl Fixture {
    fn inputs(&self) -> Inputs<'_> {
        let contents = |index: usize, source| {
            self.inputs[index]
                .as_deref()
                .map(|bytes| Contents { bytes, source })
        };
        Inputs {
            config: contents(0, "config"),
            credentials: contents(1, "credentials"),
            aliases: contents(2, "aliases"),
        }
    }
}
fn fixture(mut remaining: &str) -> Result<Fixture, &'static str> {
    let mut inputs = [None, None, None];
    for _ in 0..4 {
        let (header, body) = remaining.split_once('\n').ok_or("invalid fixture header")?;
        if header == "=== EXPECTED ===" {
            return Ok(Fixture {
                inputs,
                expected: serde_json::from_str(body).map_err(|_| "invalid expected JSON")?,
            });
        }
        let end = if body.starts_with("=== ") {
            0
        } else {
            body.find("\n=== ").ok_or("missing expected block")? + 1
        };
        remaining = &body[end..];
        let body = &body[..end];
        let labels = ["CONFIG", "CREDENTIALS", "ALIASES"];
        let index = labels
            .iter()
            .position(|label| {
                header == format!("=== {label} ===") || header == format!("=== {label} JSON ===")
            })
            .ok_or("invalid fixture header")?;
        if inputs[index].is_some() {
            return Err("duplicate input");
        }
        inputs[index] = Some(if header.ends_with(" JSON ===") {
            let spec: Json = serde_json::from_str(body).map_err(|_| "invalid input JSON")?;
            match (spec.get("text"), spec.get("bytes")) {
                (Some(text), None) => text.as_str().ok_or("invalid input")?.as_bytes().to_vec(),
                (None, Some(bytes)) => bytes
                    .as_array()
                    .ok_or("invalid input")?
                    .iter()
                    .map(|byte| {
                        byte.as_u64()
                            .and_then(|byte| u8::try_from(byte).ok())
                            .ok_or("invalid input")
                    })
                    .collect::<Result<Vec<_>, _>>()?,
                _ => return Err("invalid input"),
            }
        } else {
            body.as_bytes().to_vec()
        });
    }
    Err("missing expected block")
}
fn collect_cases(directory: &std::path::Path, prefix: &str, cases: &mut Vec<(String, String)>) {
    for entry in std::fs::read_dir(directory).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        let name = format!("{prefix}{}", entry.file_name().to_str().unwrap());
        if entry.file_type().unwrap().is_dir() {
            collect_cases(&path, &format!("{name}/"), cases);
        } else if path
            .extension()
            .is_some_and(|extension| extension == "case")
        {
            cases.push((name, std::fs::read_to_string(&path).unwrap()));
        }
    }
}
#[test]
fn pinned_aws_cli_golden_corpus_bytes_and_files() {
    let mut cases = Vec::new();
    collect_cases(
        std::path::Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/testdata")),
        "",
        &mut cases,
    );
    cases.sort();
    assert!(!cases.is_empty(), "no .case files found");
    for (name, text) in &cases {
        let case = fixture(text)
            .map_err(|error| format!("{name}: {error}"))
            .unwrap();
        let parsed = ParsedFiles::parse(case.inputs());
        assert_eq!(
            result_json(&parsed),
            case.expected,
            "byte entrypoint: {name}"
        );
        let loaded = filesystem::load_fixture(&case);
        assert_eq!(
            result_json(&loaded),
            case.expected,
            "file entrypoint: {name}"
        );
    }
}
#[test]
fn declaration_origins_survive_inheritance_and_shallow_merge() {
    let parsed = ParsedFiles::parse(Inputs {
        config: Some(Contents {
            source: "config",
            bytes: b"[DEFAULT]\nInherited=yes\n[profile work]\nx=\n nested=one\nkeep=v\n",
        }),
        credentials: Some(Contents {
            source: "credentials",
            bytes: b"[work]\nx=replaced\n",
        }),
        ..Inputs::default()
    });
    let profile = parsed.profiles.as_ref().unwrap().get("work").unwrap();
    assert_eq!(
        profile.keys().collect::<Vec<_>>(),
        ["x", "keep", "inherited"]
    );
    let inherited = profile.get("inherited").unwrap();
    assert_eq!(
        inherited.origin,
        Origin {
            source: "config".into(),
            section: "DEFAULT".into(),
            key: "inherited".into(),
            line: 2
        }
    );
    assert_eq!(profile.get("x").unwrap().origin.source, "credentials");
    assert_eq!(profile.get("x").unwrap().value.as_str(), Some("replaced"));
}
#[test]
fn shallow_merge_retains_both_files_and_winning_origins() {
    let parsed = ParsedFiles::parse(Inputs {
        config: Some(Contents {
            source: "shared",
            bytes: concat!(
                "[DEFAULT]\noutput=json\n[profile dev]\nregion=west\n",
                "s3=\n first=config\n second=config\n"
            )
            .as_bytes(),
        }),
        credentials: Some(Contents {
            source: "creds",
            bytes: b"[dev]\nregion=\ns3=\n first=credentials\n",
        }),
        aliases: None,
    });
    let merged = parsed.profiles.as_ref().unwrap().get("dev").unwrap();
    assert_eq!(merged.get("region").unwrap().value.as_str(), Some(""));
    assert_eq!(
        merged.get("region").unwrap().origin,
        Origin {
            source: "creds".into(),
            section: "dev".into(),
            key: "region".into(),
            line: 2
        }
    );
    assert_eq!(
        merged.get("output").unwrap().origin,
        Origin {
            source: "shared".into(),
            section: "DEFAULT".into(),
            key: "output".into(),
            line: 2
        }
    );
    assert_eq!(
        merged.get("s3").unwrap().value.as_nested().unwrap().len(),
        1
    );
    let original = parsed.config.sections.get("profile dev").unwrap();
    assert_eq!(
        original.get("s3").unwrap().value.as_nested().unwrap().len(),
        2
    );
    assert_eq!(original.get("region").unwrap().value.as_str(), Some("west"));
    assert_eq!(
        parsed
            .credentials
            .sections
            .get("dev")
            .unwrap()
            .get("s3")
            .unwrap()
            .value
            .as_nested()
            .unwrap()
            .get("first")
            .map(String::as_str),
        Some("credentials")
    );
}
#[test]
fn owned_inputs_and_labels_survive_mutation_and_move() {
    let mut bytes = b"[default]\nkey=value".to_vec();
    let mut source = String::from("config-path");
    let parsed = ParsedFiles::parse(Inputs {
        config: Some(Contents {
            bytes: &bytes,
            source: &source,
        }),
        ..Inputs::default()
    });
    bytes.fill(b'x');
    source.clear();
    let moved = parsed;
    let entry = moved
        .profiles
        .as_ref()
        .unwrap()
        .get("default")
        .unwrap()
        .get("key")
        .unwrap();
    assert_eq!(entry.value.as_str(), Some("value"));
    assert_eq!(
        entry.origin,
        Origin {
            source: "config-path".into(),
            section: "default".into(),
            key: "key".into(),
            line: 2
        }
    );
}
#[test]
fn diagnostics_discard_partial_data() {
    for (bytes, syntax, line) in [
        (b"orphan=yes".as_slice(), Syntax::MissingSection, Some(1)),
        (
            b"[default]\nx=1\n[default]",
            Syntax::DuplicateSection,
            Some(3),
        ),
        (b"[default]\nX=1\nx=2", Syntax::DuplicateOption, Some(3)),
        (b"[default]\ninvalid", Syntax::InvalidOption, Some(2)),
        (b"[default]\nx=\n bad", Syntax::InvalidNested, Some(2)),
        (b"\xff", Syntax::Decoding, None),
    ] {
        let parsed = ParsedFiles::parse(Inputs {
            config: Some(Contents {
                bytes,
                source: "broken",
            }),
            ..Inputs::default()
        });
        assert_eq!(
            parsed.config.status,
            Status::ParseFailure(Diagnostic {
                source: "broken".into(),
                line,
                syntax
            })
        );
        assert!(parsed.config.sections.is_empty());
        assert!(parsed.profiles.is_none());
    }
}
#[test]
fn fixture_blocks_preserve_bytes_and_empty_inputs() {
    let case = fixture("=== CONFIG ===\n=== CREDENTIALS ===\n[dev]\n  x=1\n\n=== EXPECTED ===\n{}")
        .unwrap();
    assert_eq!(case.inputs[0], Some(vec![]));
    assert_eq!(
        case.inputs[1].as_deref(),
        Some(b"[dev]\n  x=1\n\n".as_slice())
    );
    assert!(case.inputs[2].is_none());
    let case = fixture(concat!(
        "=== CONFIG JSON ===\n{\"text\":\"[default]\\r\\nx=\\u0000\"}\n",
        "=== CREDENTIALS JSON ===\n{\"bytes\":[255,10]}\n=== EXPECTED ===\n{}"
    ))
    .unwrap();
    assert_eq!(
        case.inputs[0].as_deref(),
        Some(b"[default]\r\nx=\0".as_slice())
    );
    assert_eq!(case.inputs[1], Some(vec![255, 10]));
}
#[test]
fn malformed_fixture_structure_is_rejected() {
    for input in [
        "[default]\n=== EXPECTED ===\n{}",
        "=== CONFIG ===\n=== CONFIG ===\n=== EXPECTED ===\n{}",
        "=== CONFIG ===\nx=1\n",
        "=== UNKNOWN ===\n=== EXPECTED ===\n{}",
        "=== CONFIG JSON ===\n{\"text\":\"\",\"bytes\":[]}\n=== EXPECTED ===\n{}",
    ] {
        assert!(fixture(input).is_err());
    }
}
