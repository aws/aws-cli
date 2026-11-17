#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
use std::path::Path;

#[test]
fn shared_config_and_credentials_paths_follow_the_platform_home() {
    use cli_core::{SnapshotEnv, shared_config};
    for (variable, filename) in [
        ("AWS_CONFIG_FILE", "config"),
        ("AWS_SHARED_CREDENTIALS_FILE", "credentials"),
    ] {
        let env = SnapshotEnv::from_pairs([("HOME", "/home/test"), ("USERPROFILE", "/home/test")]);
        assert_eq!(
            shared_config::locate(&env, variable, filename),
            Some(Path::new("/home/test").join(".aws").join(filename))
        );
        let env = SnapshotEnv::from_pairs([
            ("HOME", "/home/test"),
            ("USERPROFILE", "/home/test"),
            (variable, "~/.aws/alternate"),
        ]);
        assert_eq!(
            shared_config::locate(&env, variable, filename),
            Some(Path::new("/home/test/.aws/alternate").to_owned())
        );
        // Every home variable set empty names no home directory; an unset
        // HOME would reach the passwd entry instead.
        for override_value in [None, Some(""), Some("~/file")] {
            let env = SnapshotEnv::from_pairs(
                override_value
                    .map(|value| (variable, value))
                    .into_iter()
                    .chain(NO_HOME),
            );
            assert_eq!(shared_config::locate(&env, variable, filename), None);
        }
    }
}
use awscli_config::{Contents, Inputs, Status};
use cli_core::SnapshotEnv;
/// Every home variable either platform reads, set empty.
const NO_HOME: [(&str, &str); 4] = [
    ("HOME", ""),
    ("USERPROFILE", ""),
    ("HOMEDRIVE", ""),
    ("HOMEPATH", ""),
];
fn files(text: &str) -> ParsedFiles {
    ParsedFiles::parse(Inputs {
        config: Some(Contents {
            bytes: text.as_bytes(),
            source: "config",
        }),
        ..Inputs::default()
    })
}
fn parse(text: &str, operation: Operation) -> Result<Settings, LoadError> {
    load(&SnapshotEnv::default(), &files(text), operation, None)
}
fn nested_default(files: &ParsedFiles) -> &Nested {
    files
        .profiles
        .as_ref()
        .and_then(|profiles| profiles.get("default"))
        .and_then(|profile| profile.get("s3"))
        .and_then(|entry| entry.value.as_nested())
        .unwrap()
}
fn setting(key: &str, value: &str) -> Result<Settings, LoadError> {
    parse(
        &format!("[default]\ns3 =\n {key} = {value}"),
        Operation::SingleDownload,
    )
}
#[test]
fn loads_nested_default_profile() {
    let settings = parse(
        "[default]\ns3 =\n target_bandwidth = 100Gb/s\n max_in_flight = 32\n \
        io_workers = 4\n download_writer = mmap\n download_writer_copy = memcpy\n \
        download_writer_prefault = disabled\n download_writer_numa = all-nodes\n \
        download_writer_node = 0,2",
        Operation::SingleDownload,
    )
    .unwrap();
    assert_eq!(settings.in_flight_max, Some(32));
    assert_eq!(settings.io_workers, Some(4));
    assert_eq!(settings.download_writer, Some(WriterMode::Mmap));
    assert_eq!(settings.download_writer_copy, Some(CopyMode::Memcpy));
    assert_eq!(
        settings.download_writer_prefault,
        Some(PrefaultMode::Disabled)
    );
    assert_eq!(settings.download_writer_numa, Some(NumaMode::AllNodes));
    assert_eq!(settings.download_writer_node, Some(vec![0, 2]));
}
#[test]
fn loads_direct_writer() {
    assert_eq!(
        setting("download_writer", "direct")
            .unwrap()
            .download_writer,
        Some(WriterMode::Direct)
    );
}
#[test]
fn named_profile_preserves_explicit_settings() {
    let files = files("[profile named]\ns3 =\n max_in_flight = 3\n download_writer = pwrite");
    let settings = load(
        &SnapshotEnv::default(),
        &files,
        Operation::SingleDownload,
        Some("named"),
    )
    .unwrap();
    assert_eq!(settings.resolve_in_flight_max(), 3);
    assert_eq!(
        settings.resolve_download().writer.requirement,
        Requirement::Required
    );
}
#[test]
fn missing_profile_or_s3_uses_defaults() {
    for text in [
        "",
        "[default]\nregion=us-east-1",
        "[profile other]\ns3 =\n io_workers = 3",
        "[default]\ns3 = string",
    ] {
        assert_eq!(
            parse(text, Operation::SingleDownload).unwrap(),
            Settings::default()
        );
    }
}
#[test]
fn download_tuning_retains_each_explicit_requirement() {
    let default = Settings::default().resolve_download();
    assert!(!default.custom_writer_required);
    assert_eq!(default.writer.requirement, Requirement::Preferred);
    for (key, value) in [
        ("io_workers", "1"),
        ("download_writer", "mmap"),
        ("download_writer_copy", "memcpy"),
        ("download_writer_prefault", "disabled"),
        ("download_writer_numa", "disabled"),
        ("download_writer", "crt"),
    ] {
        assert!(
            setting(key, value)
                .unwrap()
                .resolve_download()
                .custom_writer_required
        );
    }
}
#[test]
fn empty_config_override_omits_file() {
    let env = SnapshotEnv::from_pairs([("AWS_CONFIG_FILE", "")]);
    assert!(cli_core::shared_config::locate(&env, "AWS_CONFIG_FILE", "config").is_none());
    assert!(load(&env, &ParsedFiles::default(), Operation::SingleUpload, None).is_ok());
}
#[test]
fn cli_profile_precedes_environment() {
    let files =
        files("[profile cli]\ns3 =\n max_in_flight=3\n[profile env]\ns3 =\n max_in_flight=7");
    let env = SnapshotEnv::from_pairs([("AWS_PROFILE", "env")]);
    assert_eq!(
        load(&env, &files, Operation::SingleDownload, Some("cli"))
            .unwrap()
            .in_flight_max,
        Some(3)
    );
}
#[test]
fn missing_implicit_config_and_no_home_directory_are_empty() {
    let mut files = ParsedFiles::default();
    files.config.status = Status::Missing;
    assert!(
        load(
            &SnapshotEnv::default(),
            &files,
            Operation::SingleDownload,
            None
        )
        .is_ok()
    );
    let no_home = SnapshotEnv::from_pairs(NO_HOME);
    assert!(cli_core::shared_config::locate(&no_home, "AWS_CONFIG_FILE", "config").is_none());
}
#[test]
fn credentials_s3_block_replaces_whole_config_block() {
    let files = ParsedFiles::parse(Inputs {
        config: Some(Contents {
            bytes: b"[default]\ns3 =\n max_in_flight=3\n io_workers=7",
            source: "c",
        }),
        credentials: Some(Contents {
            bytes: b"[default]\ns3 =\n max_in_flight=5",
            source: "k",
        }),
        ..Inputs::default()
    });
    let settings = load(
        &SnapshotEnv::default(),
        &files,
        Operation::SingleDownload,
        None,
    )
    .unwrap();
    assert_eq!(settings.in_flight_max, Some(5));
    assert_eq!(settings.io_workers, None);
}
/// The failure the parser and validation report for a download of `block`.
fn download_error(block: &str) -> ParseError {
    let values = files(&format!("[default]\ns3 =\n {block}"));
    parse_settings(nested_default(&values), Operation::SingleDownload).unwrap_err()
}
#[test]
fn invalid_settings_fail_without_topology_probes() {
    for (key, value, expected) in [
        ("max_in_flight", "0", ParseError::InvalidMaxInFlight),
        ("io_workers", "-1", ParseError::InvalidIoWorkers),
        (
            "download_writer",
            "PWRITE",
            ParseError::InvalidDownloadWriter,
        ),
        (
            "download_writer_copy",
            "invalid",
            ParseError::InvalidDownloadWriterCopy,
        ),
        (
            "download_writer_prefault",
            "yes",
            ParseError::InvalidDownloadWriterPrefault,
        ),
        (
            "download_writer_numa",
            "same_node",
            ParseError::InvalidDownloadWriterNuma,
        ),
        (
            "download_writer_node",
            "16",
            ParseError::InvalidDownloadWriterNode,
        ),
        (
            "download_numa_pool",
            "on",
            ParseError::InvalidDownloadNumaPool,
        ),
    ] {
        assert_eq!(download_error(&format!("{key} = {value}")), expected);
    }
}
const POSITIVE: &str = "expected a positive integer";
const TOGGLE: &str = "expected 'enabled' or 'disabled'";
const MMAP: &str = "requires s3.download_writer = mmap";
const NATIVE: &str = "requires s3.download_writer = mmap, pwrite, or direct";
/// Every failure with the key and message its diagnostic names.
const FAILURES: [(ParseError, &str, &str); 16] = [
    (ParseError::InvalidMaxInFlight, "max_in_flight", POSITIVE),
    (ParseError::InvalidIoWorkers, "io_workers", POSITIVE),
    (
        ParseError::InvalidDownloadWriter,
        "download_writer",
        "expected 'pwrite', 'mmap', 'direct', or 'crt'",
    ),
    (
        ParseError::InvalidDownloadWriterCopy,
        "download_writer_copy",
        "expected 'memcpy', 'nt', or 'rep'",
    ),
    (
        ParseError::UnsupportedDownloadWriterCopy,
        "download_writer_copy",
        "'nt' and 'rep' require an optimized x86_64 build",
    ),
    (
        ParseError::InvalidDownloadWriterPrefault,
        "download_writer_prefault",
        TOGGLE,
    ),
    (
        ParseError::InvalidDownloadWriterNuma,
        "download_writer_numa",
        "expected 'disabled', 'same-node', or 'all-nodes'",
    ),
    (
        ParseError::InvalidDownloadWriterNode,
        "download_writer_node",
        "expected 'auto' or a node list like '0', '0,2', or '0-3'",
    ),
    (
        ParseError::InvalidDownloadNumaPool,
        "download_numa_pool",
        TOGGLE,
    ),
    (
        ParseError::UnsupportedDownloadNumaPool,
        "download_numa_pool",
        "'enabled' requires Linux NUMA support",
    ),
    (
        ParseError::DownloadWriterCopyRequiresMmap,
        "download_writer_copy",
        MMAP,
    ),
    (
        ParseError::DownloadWriterPrefaultRequiresMmap,
        "download_writer_prefault",
        MMAP,
    ),
    (
        ParseError::DownloadWriterNodeRequiresNuma,
        "download_writer_node",
        "requires s3.download_writer_numa = same-node or all-nodes",
    ),
    (
        ParseError::SameNodeRequiresSingleNode,
        "download_writer_node",
        "same-node mode accepts only one node id",
    ),
    (
        ParseError::IoWorkersRequiresNativeWriter,
        "io_workers",
        NATIVE,
    ),
    (
        ParseError::DownloadWriterNumaRequiresNativeWriter,
        "download_writer_numa",
        NATIVE,
    ),
];
#[test]
fn every_failure_names_its_key_and_message() {
    for (index, (error, ..)) in FAILURES.iter().enumerate() {
        assert!(
            FAILURES[index + 1..]
                .iter()
                .all(|(other, ..)| other != error)
        );
    }
    for (error, key, message) in FAILURES {
        assert_eq!((error.key(), error.message()), (key, message), "{error:?}");
        assert_eq!(error.to_string(), format!("invalid s3.{key}: {message}"));
    }
}
#[test]
fn conversion_order_precedes_relationship_validation() {
    let error = parse(
        "[default]\ns3 =\n target_bandwidth = bad\n io_workers = nope\n \
        download_writer = direct\n download_writer_copy = memcpy",
        Operation::SingleDownload,
    )
    .unwrap_err();
    assert!(error.message.contains("s3.io_workers"));
    assert_eq!(
        download_error(
            "download_writer = pwrite\n download_writer_copy = memcpy\n \
            download_writer_node = bad"
        ),
        ParseError::InvalidDownloadWriterNode
    );
}
/// Uploads skip the download settings, even ones a download rejects, and
/// still read max_in_flight.
fn assert_uploads_ignore_download_settings(contents: &str) {
    for operation in [Operation::SingleUpload, Operation::RecursiveUpload] {
        assert_eq!(
            parse(contents, operation).unwrap(),
            Settings {
                in_flight_max: Some(7),
                ..Settings::default()
            }
        );
    }
}
#[test]
fn download_settings_accepted_recursively_and_ignored_for_uploads() {
    let invalid = "[default]\ns3 =\n io_workers = 0\n download_writer = bogus\n max_in_flight = 7";
    assert_uploads_ignore_download_settings(invalid);
    assert!(
        parse(invalid, Operation::SingleDownload)
            .unwrap_err()
            .message
            .contains("s3.io_workers")
    );
    let unsupported_pool = (!cfg!(target_os = "linux")).then_some("requires Linux NUMA support");
    for (text, recursive_error) in [
        ("io_workers = 2", None),
        ("download_writer = mmap", None),
        ("download_writer_copy = memcpy", None),
        ("download_writer_prefault = disabled", None),
        ("download_writer_numa = disabled", None),
        (
            "download_writer_node = auto",
            Some("requires s3.download_writer_numa"),
        ),
        ("download_writer = crt", None),
        ("download_numa_pool = enabled", unsupported_pool),
        ("download_numa_pool = disabled", None),
    ] {
        let contents = format!("[default]\ns3 =\n {text}\n max_in_flight = 7");
        assert_uploads_ignore_download_settings(&contents);
        let recursive = parse(&contents, Operation::RecursiveDownload);
        // A download still rejects what only it reads.
        let matched = recursive
            .err()
            .map(|error| recursive_error.is_some_and(|message| error.message.contains(message)));
        assert_eq!(matched, recursive_error.map(|_| true), "{text}");
    }
}
#[test]
fn unknown_s3_properties_are_ignored() {
    assert_eq!(
        parse(
            "[default]\ns3 =\n future=value\n max_in_flight=5",
            Operation::SingleDownload
        )
        .unwrap()
        .in_flight_max,
        Some(5)
    );
}
#[test]
fn positive_integer_boundaries() {
    assert_eq!(
        setting("max_in_flight", &u32::MAX.to_string())
            .unwrap()
            .in_flight_max,
        Some(u32::MAX)
    );
    assert_eq!(
        setting("io_workers", &usize::MAX.to_string())
            .unwrap()
            .io_workers,
        Some(usize::MAX)
    );
    // Interior underscores are skipped, however many.
    for (value, expected) in [("1_000", 1000), (" 1__0 ", 10), ("0_1", 1)] {
        assert_eq!(
            setting("max_in_flight", value).unwrap().in_flight_max,
            Some(expected),
            "{value}"
        );
    }
    assert_eq!(setting("io_workers", "1_6").unwrap().io_workers, Some(16));
    for value in [
        "",
        " ",
        "0",
        "-1",
        "+1",
        "1.5",
        "nope",
        "4294967296",
        "_1",
        "1_",
        "_",
        "0_0",
        "4_294_967_296",
    ] {
        assert!(setting("max_in_flight", value).is_err(), "{value}");
    }
}
#[test]
fn numa_pool_parser_covers_every_value() {
    for (value, mode) in [
        ("enabled", NumaPoolMode::Enabled),
        ("disabled", NumaPoolMode::Disabled),
    ] {
        let values = files(&format!("[default]\ns3 =\n download_numa_pool = {value}"));
        let nested = nested_default(&values);
        assert_eq!(
            parse::download_settings(nested).unwrap().download_numa_pool,
            Some(mode)
        );
    }
}
/// One key's value through the download parser alone, before validation.
fn parsed(key: &str, value: &str) -> Result<Settings, ParseError> {
    let values = files(&format!("[default]\ns3 =\n {key} = {value}"));
    parse::download_settings(nested_default(&values))
}
/// Each value parses to its variant in the field `field` reads.
fn assert_values<T: Copy + PartialEq + std::fmt::Debug>(
    key: &str,
    cases: &[(&str, T)],
    field: impl Fn(Settings) -> Option<T>,
) {
    for (value, expected) in cases {
        let settings = parsed(key, value).unwrap();
        assert_eq!(field(settings), Some(*expected), "{key} = {value}");
    }
}
#[test]
fn mode_parsers_cover_all_variants() {
    assert_values(
        "download_writer",
        &[
            ("pwrite", WriterMode::Pwrite),
            ("mmap", WriterMode::Mmap),
            ("direct", WriterMode::Direct),
            ("crt", WriterMode::Crt),
        ],
        |settings| settings.download_writer,
    );
    assert_values(
        "download_numa_pool",
        &[
            ("enabled", NumaPoolMode::Enabled),
            ("disabled", NumaPoolMode::Disabled),
        ],
        |settings| settings.download_numa_pool,
    );
    assert_values(
        "download_writer_copy",
        &[
            ("memcpy", CopyMode::Memcpy),
            ("nt", CopyMode::Nt),
            ("rep", CopyMode::RepMovsb),
        ],
        |settings| settings.download_writer_copy,
    );
    assert_values(
        "download_writer_prefault",
        &[
            ("enabled", PrefaultMode::Enabled),
            ("disabled", PrefaultMode::Disabled),
        ],
        |settings| settings.download_writer_prefault,
    );
    assert_values(
        "download_writer_numa",
        &[
            ("disabled", NumaMode::Disabled),
            ("same-node", NumaMode::SameNode),
            ("all-nodes", NumaMode::AllNodes),
        ],
        |settings| settings.download_writer_numa,
    );
}
#[test]
fn mode_parsers_reject_near_misses() {
    // Values match exactly, and `recv_filepath`, the CRT option the `crt`
    // writer uses, is not an alias for `crt`.
    for (key, value, error) in [
        (
            "download_writer",
            "PWRITE",
            ParseError::InvalidDownloadWriter,
        ),
        (
            "download_writer",
            "recv_filepath",
            ParseError::InvalidDownloadWriter,
        ),
        (
            "download_numa_pool",
            "on",
            ParseError::InvalidDownloadNumaPool,
        ),
        (
            "download_writer_copy",
            "other",
            ParseError::InvalidDownloadWriterCopy,
        ),
        (
            "download_writer_prefault",
            "on",
            ParseError::InvalidDownloadWriterPrefault,
        ),
        (
            "download_writer_numa",
            "same_node",
            ParseError::InvalidDownloadWriterNuma,
        ),
    ] {
        assert_eq!(parsed(key, value), Err(error), "{key} = {value}");
    }
}
#[test]
fn node_parser_retains_order_and_rejects_invalid_ranges() {
    for (value, expected) in [
        ("auto", vec![]),
        ("0", vec![0]),
        ("0,2", vec![0, 2]),
        ("0-3", vec![0, 1, 2, 3]),
        (" 1 , 3-4 ", vec![1, 3, 4]),
        ("15", vec![15]),
        ("1_0", vec![10]),
        ("0_1-0_3", vec![1, 2, 3]),
    ] {
        assert_eq!(parse_node_selection(value).unwrap(), expected);
    }
    for value in [
        "",
        " ",
        ",",
        "0,",
        ",0",
        "0,,1",
        "2-1",
        "0,0",
        "0-2,2-3",
        "4294967296",
        "nope",
        "16",
        "0-16",
        "1024",
        "0 -1",
        "0- 1",
        "_1",
        "1_",
        "_1-2",
        "1-2_",
        "1_6",
    ] {
        assert!(parse_node_selection(value).is_err(), "{value}");
    }
}
#[test]
fn node_parser_capacity_and_extra_part() {
    let expected: Vec<_> = (0..16).collect();
    assert_eq!(parse_node_selection("0-15").unwrap(), expected);
    let value = expected
        .iter()
        .map(u32::to_string)
        .collect::<Vec<_>>()
        .join(",");
    assert_eq!(parse_node_selection(&value).unwrap(), expected);
    assert!(parse_node_selection(&format!("{value},0")).is_err());
}
#[test]
fn download_cross_setting_relationships() {
    for block in [
        "download_writer=pwrite\n download_writer_copy=memcpy",
        "download_writer=direct\n download_writer_prefault=enabled",
        "download_writer=direct\n download_writer_prefault=disabled",
        "download_writer=direct\n download_writer_copy=memcpy",
        "download_writer=pwrite\n download_writer_prefault=enabled",
        "download_writer_node=auto",
        "download_writer_numa=disabled\n download_writer_node=0",
        "download_writer_numa=same-node\n download_writer_node=0,1",
    ] {
        assert!(
            parse(
                &format!("[default]\ns3 =\n {block}"),
                Operation::SingleDownload
            )
            .is_err()
        );
    }
    for block in [
        "download_writer_copy=memcpy",
        "download_writer=mmap\n download_writer_copy=memcpy\n download_writer_prefault=enabled",
        "download_writer=direct",
        "download_writer_numa=same-node",
        "download_writer_numa=same-node\n download_writer_node=auto",
        "download_writer_numa=all-nodes\n download_writer_node=0,1",
    ] {
        assert!(
            parse(
                &format!("[default]\ns3 =\n {block}"),
                Operation::SingleDownload
            )
            .is_ok()
        );
    }
}
#[test]
fn shared_parser_handles_comments_crlf_and_repeated_keys() {
    let settings = parse(
        "# comment\r\n[default]\r\ns3 =\r\n max_in_flight=3\r\n \
        max_in_flight=8\r\n unknown=ignored\r\n",
        Operation::SingleDownload,
    )
    .unwrap();
    assert_eq!(settings.in_flight_max, Some(8));
}
// Botocore reads a config file it can't read as a regular file as empty, and
// so does cp. A file that fails to parse never gets here: the router sends that
// invocation to Python.
#[test]
fn unusable_config_file_reads_as_empty() {
    for status in [
        Status::Missing,
        Status::Directory,
        Status::Unreadable(awscli_config::ReadError::AccessDenied),
    ] {
        let mut files = ParsedFiles::default();
        files.config.status = status;
        files.config.source = "chosen".into();
        for operation in [
            Operation::SingleDownload,
            Operation::SingleUpload,
            Operation::RecursiveDownload,
            Operation::RecursiveUpload,
        ] {
            let env = SnapshotEnv::from_pairs([("AWS_CONFIG_FILE", "chosen")]);
            assert_eq!(
                load(&env, &files, operation, None).unwrap(),
                Settings::default()
            );
        }
    }
}

#[test]
fn explicit_missing_config_uses_defaults_without_home_fallback() {
    let mut files = ParsedFiles::default();
    files.config.status = Status::Missing;
    files.config.source = "chosen".into();
    let env = SnapshotEnv::from_pairs([("AWS_CONFIG_FILE", "chosen"), ("HOME", "/unused")]);
    assert_eq!(
        load(&env, &files, Operation::SingleDownload, None).unwrap(),
        Settings::default()
    );
}
#[test]
fn client_transfer_settings_are_not_reparsed_as_writer_settings() {
    for value in ["+1_000", "invalid", "100Gb/s", "0"] {
        assert_eq!(
            setting("target_bandwidth", value).unwrap(),
            Settings::default()
        );
    }
}

#[test]
fn direct_io_preference_preserves_explicit_writer_requirements() {
    let settings = Settings::default();
    assert_eq!(
        settings
            .resolve_download()
            .with_direct_io(false)
            .writer
            .mode,
        WriterMode::Mmap
    );
    let writer = |mode| Settings {
        download_writer: Some(mode),
        ..Settings::default()
    };
    for (settings, mode, requirement) in [
        (settings, WriterMode::Direct, Requirement::Preferred),
        // A worker count alone names no writer, so direct_io still applies.
        (
            Settings {
                io_workers: Some(4),
                ..Settings::default()
            },
            WriterMode::Direct,
            Requirement::Preferred,
        ),
        (
            writer(WriterMode::Pwrite),
            WriterMode::Pwrite,
            Requirement::Required,
        ),
        (
            writer(WriterMode::Mmap),
            WriterMode::Mmap,
            Requirement::Required,
        ),
        (
            writer(WriterMode::Direct),
            WriterMode::Direct,
            Requirement::Required,
        ),
        // A copy mode alone requires the mapped writer it configures.
        (
            Settings {
                download_writer_copy: Some(CopyMode::Memcpy),
                ..Settings::default()
            },
            WriterMode::Mmap,
            Requirement::Required,
        ),
    ] {
        let selected = settings.resolve_download().with_direct_io(true);
        assert_eq!(
            (selected.writer.mode, selected.writer.requirement),
            (mode, requirement)
        );
    }
}

#[test]
fn first_invalid_setting_precedes_relationship_failures() {
    for (properties, key, message) in [
        (
            "max_in_flight = 0\n download_writer = invalid",
            "max_in_flight",
            "expected a positive integer",
        ),
        (
            "download_writer = invalid\n download_writer_copy = invalid",
            "download_writer",
            "expected 'pwrite', 'mmap', 'direct', or 'crt'",
        ),
        (
            "download_writer_prefault = on\n download_writer_numa = invalid",
            "download_writer_prefault",
            "expected 'enabled' or 'disabled'",
        ),
        (
            "download_writer = pwrite\n download_writer_copy = memcpy\n \
            download_writer_prefault = enabled\n download_writer_node = auto",
            "download_writer_copy",
            "requires s3.download_writer = mmap",
        ),
        (
            "download_writer = pwrite\n download_writer_prefault = enabled\n \
            download_writer_node = auto",
            "download_writer_prefault",
            "requires s3.download_writer = mmap",
        ),
        (
            "download_numa_pool = on\n download_writer = crt\n io_workers = 2",
            "download_numa_pool",
            "expected 'enabled' or 'disabled'",
        ),
    ] {
        let error = parse(
            &format!("[default]\ns3 =\n {properties}"),
            Operation::SingleDownload,
        )
        .unwrap_err();
        assert_eq!(
            error.message,
            format!("error: invalid s3.{key} in AWS config profile \"default\": {message}\n")
        );
    }
}
#[test]
fn crt_writer_rejects_settings_only_a_native_writer_honors() {
    for operation in [Operation::SingleDownload, Operation::RecursiveDownload] {
        for (properties, key, message) in crt_writer_rejections() {
            let error = parse(
                &format!("[default]\ns3 =\n download_writer = crt\n {properties}"),
                operation,
            )
            .unwrap_err();
            assert_eq!(
                error.message,
                format!("error: invalid s3.{key} in AWS config profile \"default\": {message}\n")
            );
        }
    }
    // A crt writer accepts disabled placement, the pool key, and direct_io.
    let accepted = parse(
        "[default]\ns3 =\n download_writer = crt\n download_writer_numa = disabled\n \
        download_numa_pool = disabled\n direct_io = true",
        Operation::SingleDownload,
    )
    .unwrap();
    assert_eq!(accepted.download_writer, Some(WriterMode::Crt));
    assert_eq!(accepted.download_numa_pool, Some(NumaPoolMode::Disabled));
}
/// The settings a crt writer rejects, each with the key and message reported
/// next to `download_writer = crt`.
fn crt_writer_rejections() -> Vec<(&'static str, &'static str, &'static str)> {
    let mut cases = vec![
        // A portable copy mode reaches the mmap rule on every platform.
        (
            "download_writer_copy = memcpy",
            "download_writer_copy",
            "requires s3.download_writer = mmap",
        ),
        (
            "download_writer_prefault = enabled",
            "download_writer_prefault",
            "requires s3.download_writer = mmap",
        ),
        (
            "download_writer_prefault = disabled",
            "download_writer_prefault",
            "requires s3.download_writer = mmap",
        ),
        ("io_workers = 4", "io_workers", NATIVE),
        (
            "download_writer_numa = same-node",
            "download_writer_numa",
            NATIVE,
        ),
        (
            "download_writer_numa = all-nodes",
            "download_writer_numa",
            NATIVE,
        ),
        // Without a positive NUMA mode the node rule fires; with one, the
        // writer rule fires first because writer validation runs first.
        (
            "download_writer_node = auto",
            "download_writer_node",
            "requires s3.download_writer_numa = same-node or all-nodes",
        ),
        (
            "download_writer_numa = same-node\n download_writer_node = 0",
            "download_writer_numa",
            NATIVE,
        ),
    ];
    // The unavailable fast copy modes keep their precedence over the mmap rule.
    if !COPY_FAST_MODES_AVAILABLE {
        cases.push((
            "download_writer_copy = nt",
            "download_writer_copy",
            "'nt' and 'rep' require an optimized x86_64 build",
        ));
    }
    cases
}
#[test]
fn numa_pool_key_parses_and_needs_numa_discovery_to_enable() {
    assert_eq!(
        setting("download_numa_pool", "on").unwrap_err().message,
        "error: invalid s3.download_numa_pool in AWS config profile \"default\": \
        expected 'enabled' or 'disabled'\n"
    );
    assert_eq!(
        setting("download_numa_pool", "disabled")
            .unwrap()
            .download_numa_pool,
        Some(NumaPoolMode::Disabled)
    );
    // Enabling the pool with placement disabled is valid where discovery exists.
    let enabled = parse(
        "[default]\ns3 =\n download_numa_pool = enabled\n download_writer_numa = disabled",
        Operation::SingleDownload,
    );
    if cfg!(target_os = "linux") {
        assert_eq!(
            enabled.unwrap().download_numa_pool,
            Some(NumaPoolMode::Enabled)
        );
    } else {
        assert_eq!(
            enabled.unwrap_err().message,
            "error: invalid s3.download_numa_pool in AWS config profile \"default\": \
            'enabled' requires Linux NUMA support\n"
        );
    }
    let error = validate_numa_pool(&Settings {
        download_numa_pool: Some(NumaPoolMode::Enabled),
        ..Settings::default()
    });
    assert_eq!(error.is_err(), !cfg!(target_os = "linux"));
}
#[test]
fn crt_writer_resolves_required_with_the_pool_unset() {
    // An explicit crt writer is required and sets the explicit-setting flag,
    // which the writer routing overrides for crt.
    let crt = Settings {
        download_writer: Some(WriterMode::Crt),
        ..Settings::default()
    }
    .resolve_download();
    assert_eq!(crt.writer.mode, WriterMode::Crt);
    assert_eq!(crt.writer.requirement, Requirement::Required);
    assert!(crt.custom_writer_required);
    assert_eq!(
        crt.clone().with_direct_io(true).writer.mode,
        WriterMode::Crt
    );
    assert_eq!(crt.numa_pool, None);
    // Unset keys resolve exactly as before.
    let unset = Settings::default().resolve_download();
    assert!(!unset.custom_writer_required);
    assert_eq!(unset.writer.mode, WriterMode::Mmap);
    assert_eq!(unset.numa_pool, None);
}
#[test]
fn pool_key_alone_changes_neither_the_writer_nor_the_explicit_flag() {
    for mode in [NumaPoolMode::Enabled, NumaPoolMode::Disabled] {
        let pooled = Settings {
            download_numa_pool: Some(mode),
            ..Settings::default()
        }
        .resolve_download();
        assert!(!pooled.custom_writer_required);
        assert_eq!(pooled.writer.mode, WriterMode::Mmap);
        assert_eq!(pooled.writer.requirement, Requirement::Preferred);
        assert_eq!(pooled.writer.numa.requirement, Requirement::Preferred);
        assert_eq!(pooled.numa_pool, Some(mode));
        assert_eq!(pooled.with_direct_io(true).numa_pool, Some(mode));
    }
}

#[test]
fn an_invalid_node_id_is_reported_before_crt_writer_relationships() {
    let error = parse(
        "[default]\ns3 =\n  download_writer = crt\n  io_workers = 1\n  download_writer_node = 16\n",
        Operation::SingleDownload,
    )
    .unwrap_err();
    assert_eq!(
        error.message,
        "error: invalid s3.download_writer_node in AWS config profile \"default\": \
         expected 'auto' or a node list like '0', '0,2', or '0-3'\n"
    );
}
#[test]
fn numa_struct_default_places_nothing_while_settings_prefer_same_node() {
    assert_eq!(
        NumaConfig::default(),
        NumaConfig {
            mode: NumaMode::Disabled,
            nodes: Vec::new(),
            requirement: Requirement::Required,
        }
    );
    assert_eq!(
        Settings::default().resolve_download().writer.numa,
        NumaConfig {
            mode: NumaMode::SameNode,
            nodes: Vec::new(),
            requirement: Requirement::Preferred,
        }
    );
}
#[test]
fn fast_copy_modes_follow_one_build_predicate() {
    let default = Settings::default().resolve_download().writer.copy_mode;
    let expected = if COPY_FAST_MODES_AVAILABLE {
        CopyMode::Nt
    } else {
        CopyMode::Memcpy
    };
    assert_eq!(default, expected);
    assert_eq!(WriterConfig::default().copy_mode, CopyMode::Memcpy);
    for value in ["nt", "rep"] {
        let parsed = parse_settings(
            nested_default(&files(&format!(
                "[default]\ns3 =\n download_writer_copy = {value}"
            ))),
            Operation::SingleDownload,
        );
        assert_eq!(
            parsed.err(),
            (!COPY_FAST_MODES_AVAILABLE).then_some(ParseError::UnsupportedDownloadWriterCopy),
            "{value}"
        );
    }
}
