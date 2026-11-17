#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
use crate::sync::CaseConflict;
use FilterKind::Exclude;
fn args(source: &str, destination: &str, recursive: bool) -> Args {
    Args {
        paths: [source.into(), destination.into()],
        dir_op: recursive,
        dryrun: false,
        quiet: false,
        no_overwrite: false,
        page_size: None,
        only_show_errors: false,
        progress: true,
        progress_frequency: Some(0),
        progress_multiline: false,
        ignore_glacier_warnings: false,
        force_glacier_transfer: false,
        filters: Vec::new(),
        follow_symlinks: true,
        content_type: None,
        cache_control: None,
        content_disposition: None,
        content_encoding: None,
        content_language: None,
        expires: None,
        website_redirect: None,
        metadata: StringMap::default(),
        acl: None,
        storage_class: None,
        sse: None,
        sse_kms_key_id: None,
        sse_c: None,
        sse_c_key: None,
        request_payer: None,
        checksum_mode: None,
        checksum_algorithm: None,
        guess_mime_type: true,
        grants: Vec::new(),
        case_conflict: crate::sync::OnCaseConflict::Ignore,
    }
}
#[test]
fn upload_key_takes_basename_for_prefixes() {
    for (key, expected) in [("", "file"), ("dir/", "dir/file"), ("dir", "dir")] {
        assert_eq!(
            resolve_single_upload_key(key.as_bytes(), std::path::Path::new("a/file")),
            expected.as_bytes()
        );
    }
    let separator = std::path::MAIN_SEPARATOR;
    for (key, source, expected) in [
        ("", format!("nested{separator}dir{separator}"), ""),
        ("prefix/", format!("dir{separator}"), "prefix/"),
        ("fixed", format!("dir{separator}"), "fixed"),
        (
            "",
            format!(".{separator}nested{separator}file.txt"),
            "file.txt",
        ),
    ] {
        assert_eq!(
            resolve_single_upload_key(key.as_bytes(), std::path::Path::new(&source)),
            expected.as_bytes(),
            "{key:?} {source:?}"
        );
    }
}
#[test]
fn bucket_root_upload_retains_empty_key() {
    for destination in ["s3://b", "s3://b/"] {
        let args = args("file", destination, false);
        assert_eq!(
            make_copy_plan(&args).operation,
            Operation::SingleUpload(uri::S3Uri {
                bucket: "b",
                key: b""
            })
        );
    }
}
#[test]
fn copy_shapes_are_classified() {
    for recursive in [false, true] {
        for (source, destination) in [("a", "b"), ("s3://b/a", "s3://b/b")] {
            assert_eq!(
                admit(&args(source, destination, recursive)),
                Some(AdmissionReason::UnsupportedOperand)
            );
        }
        assert_eq!(admit(&args("s3://b/a", "b", recursive)), None);
        assert_eq!(admit(&args("a", "s3://b/b", recursive)), None);
    }
    for (source, destination, recursive, upload) in [
        ("s3://source-bucket/object.txt", "local.txt", false, false),
        (
            "local.txt",
            "s3://destination-bucket/object.txt",
            false,
            true,
        ),
        (
            "s3://source-bucket/source-prefix",
            "local-directory",
            true,
            false,
        ),
        (
            "local-directory",
            "s3://destination-bucket/prefix",
            true,
            true,
        ),
    ] {
        let input = args(source, destination, recursive);
        let operation = make_copy_plan(&input).operation;
        assert_eq!(operation.uploads(), upload);
        assert_eq!(
            matches!(
                operation,
                Operation::RecursiveDownload(_) | Operation::RecursiveUpload(_)
            ),
            recursive
        );
    }
}
#[test]
fn copy_plan_preserves_parsed_operands() {
    let input = args("s3://b/a//b", "local", false);
    assert_eq!(
        make_copy_plan(&input).operation,
        Operation::SingleDownload(uri::S3Uri {
            bucket: "b",
            key: b"a//b"
        })
    );
    let input = args("local", "s3://b/a//b", true);
    assert_eq!(
        make_copy_plan(&input).operation,
        Operation::RecursiveUpload(uri::S3PrefixUri {
            bucket: "b",
            prefix: b"a//b"
        })
    );
}
#[test]
fn admission_requires_one_remote_and_one_local() {
    for (source, dest) in [
        ("-", "s3://b/k"),
        ("a", "b"),
        ("s3://b/k", "s3://b/k"),
        ("arn:aws:s3:x", "file"),
        ("s3://bucket-s3alias/k", "file"),
        ("s3://", "file"),
    ] {
        assert_eq!(
            admit(&args(source, dest, false)),
            Some(AdmissionReason::UnsupportedOperand)
        );
    }
    assert_eq!(
        admit(&args("s3://b", "file", false)),
        Some(AdmissionReason::UnsupportedOperand)
    );
    assert_eq!(admit(&args("s3://b", "file", true)), None);
}
#[test]
fn only_a_recursive_download_checks_case_conflicts() {
    let checks = |source, destination, recursive, case_conflict| {
        Args {
            case_conflict,
            ..args(source, destination, recursive)
        }
        .case_conflict_strategies()
    };
    for (choice, conflict) in [
        (OnCaseConflict::Skip, CaseConflict::Skip),
        (OnCaseConflict::Warn, CaseConflict::Warn),
        (OnCaseConflict::Error, CaseConflict::Error),
    ] {
        assert_eq!(
            checks("s3://b/p/", "dir", true, choice),
            Some(Strategies {
                both: BothSides::Always,
                source_only: SourceOnly::CaseConflict(conflict),
                destination_only: DestinationOnly::Keep,
            }),
            "{choice:?}"
        );
        for (source, destination, recursive) in [
            ("s3://b/k", "file", false),
            ("dir", "s3://b/p/", true),
            ("file", "s3://b/k", false),
            ("s3://b/p/", "s3://c/p/", true),
        ] {
            assert_eq!(
                checks(source, destination, recursive, choice),
                None,
                "{source} {destination} {choice:?}"
            );
        }
    }
    assert_eq!(
        checks("s3://b/p/", "dir", true, OnCaseConflict::Ignore),
        None
    );
}
#[test]
fn page_size_admission_is_bounded() {
    let mut args = args("a", "s3://b", false);
    for n in [0, -1, i64::from(u32::MAX) + 1] {
        args.page_size = Some(n);
        assert_eq!(admit(&args), Some(AdmissionReason::UnsupportedValue));
    }
    for n in [1, i64::from(u32::MAX)] {
        args.page_size = Some(n);
        assert_eq!(admit(&args), None);
    }
}
#[test]
fn malformed_uris_belong_to_python() {
    for (source, destination, recursive) in [
        ("s3:/bucket/key", "destination", false),
        ("source", "s3://", false),
        ("s3://one/key", "s3://two", false),
        ("s3://bucket/key", "-", false),
        ("s3:/bucket/prefix", "dir", true),
        ("dir", "s3:///prefix", true),
        ("source", "destination", true),
        (
            "arn:aws:s3:us-east-1:123456789012:accesspoint/example/object/key",
            "d",
            false,
        ),
    ] {
        assert_eq!(
            admit(&args(source, destination, recursive)),
            Some(AdmissionReason::UnsupportedOperand),
            "{source:?} {destination:?}"
        );
    }
}

#[test]
fn windows_path_fallback_applies_only_to_the_local_operand() {
    let expected = cfg!(windows).then_some(AdmissionReason::UnsupportedOperand);
    for recursive in [false, true] {
        for path in [r"\\?\C:\..\out.txt", "D:foo", r"\foo", "dir/../file"] {
            assert_eq!(admit(&args(path, "s3://bucket/key", recursive)), expected);
            assert_eq!(admit(&args("s3://bucket/key", path, recursive)), expected);
        }
        assert_eq!(
            admit(&args("file", "s3://bucket/a/../key", recursive)),
            None
        );
    }
}

#[cfg(unix)]
#[test]
fn non_unicode_local_operands_and_upload_basenames_keep_the_original_bytes() {
    use std::os::unix::ffi::OsStrExt;
    let local = OsStr::from_bytes(b"directory-\xfe/file-\xff");
    for recursive in [false, true] {
        for upload in [false, true] {
            let mut input = args("s3://bucket/prefix/", "local", recursive);
            if upload {
                input.paths.swap(0, 1);
            }
            input.paths[usize::from(!upload)] = local.into();
            assert_eq!(admit(&input), None);
            let plan = make_copy_plan(&input);
            assert_eq!(
                if upload {
                    plan.source
                } else {
                    plan.destination
                },
                local
            );
        }
    }
    assert_eq!(
        resolve_single_upload_key(b"prefix/", std::path::Path::new(local)),
        b"prefix/file-\xff",
    );
    assert_eq!(
        resolve_single_upload_key(b"fixed", std::path::Path::new(local)),
        b"fixed",
    );
}

#[cfg(unix)]
#[test]
fn non_unicode_remote_keys_stay_remote_with_their_bytes() {
    use std::os::unix::ffi::OsStrExt;
    for recursive in [false, true] {
        let mut input = args("s3://bucket/key", "local", recursive);
        input.paths[0] = OsStr::from_bytes(b"s3://bucket/key-\xff").into();
        assert_eq!(admit(&input), None);
        let expected = uri::S3PrefixUri {
            bucket: "bucket",
            prefix: b"key-\xff",
        };
        assert_eq!(
            make_copy_plan(&input).operation,
            if recursive {
                Operation::RecursiveDownload(expected)
            } else {
                Operation::SingleDownload(uri::S3Uri {
                    bucket: "bucket",
                    key: b"key-\xff",
                })
            }
        );
        input.paths.swap(0, 1);
        assert_eq!(admit(&input), None);
        assert!(make_copy_plan(&input).operation.uploads());
    }
    for source in [false, true] {
        let mut input = args("local", "local", false);
        input.paths[usize::from(!source)] = OsStr::from_bytes(b"s3://bucket-\xff/key").into();
        assert_eq!(admit(&input), Some(AdmissionReason::UnsupportedOperand));
    }
}
#[test]
fn settings_admission_checks_only_what_an_upload_sends() {
    let upload = |edit: fn(&mut Args)| {
        let mut input = args("file", "s3://b/k", false);
        edit(&mut input);
        admit(&input)
    };
    let download = |edit: fn(&mut Args)| {
        let mut input = args("s3://b/k", "file", false);
        edit(&mut input);
        admit(&input)
    };
    let unsendable: [fn(&mut Args); 3] = [
        |input| input.cache_control = Some("a\nb".into()),
        |input| input.metadata = StringMap(vec![("k".into(), "na\u{ef}ve".into())]),
        |input| input.metadata = StringMap(vec![("a b".into(), "v".into())]),
    ];
    for edit in unsendable {
        assert_eq!(upload(edit), Some(AdmissionReason::UnsupportedValue));
        assert_eq!(download(edit), None);
    }
    let sendable: [fn(&mut Args); 3] = [
        |input| input.content_disposition = Some("attachment; filename=\"na\u{ef}ve\"".into()),
        |input| input.expires = Some("2037-10-21T07:28:00+05:30".into()),
        |input| input.metadata = StringMap(vec![(String::new(), "v".into())]),
    ];
    for edit in sendable {
        assert_eq!(upload(edit), None);
    }
    assert_eq!(
        upload(|input| input.acl = Some("everyone".into())),
        Some(AdmissionReason::UnsupportedValue)
    );
    assert_eq!(
        download(|input| input.request_payer = Some("owner".into())),
        Some(AdmissionReason::UnsupportedValue)
    );
}
#[test]
fn an_expires_native_does_not_read_stays_with_python() {
    for value in ["90", "tomorrow", "2023-02-29"] {
        for (source, destination) in [("file", "s3://b/k"), ("s3://b/k", "file")] {
            let mut input = args(source, destination, false);
            input.expires = Some(value.into());
            assert_eq!(admit(&input), Some(AdmissionReason::UnsupportedValue));
        }
    }
}
#[test]
fn plans_carry_the_object_settings() {
    let mut input = args("file", "s3://b/k", false);
    input.cache_control = Some("max-age=1".into());
    input.content_type = Some(String::new());
    input.request_payer = Some("requester".into());
    input.expires = Some("2037-10-21T07:28:00Z".into());
    input.checksum_algorithm = Some("XXHASH128".into());
    let settings = make_copy_plan(&input).settings;
    assert_eq!(
        settings.checksum_algorithm,
        Some(crate::object_settings::ChecksumAlgorithm::Xxhash128)
    );
    assert_eq!(settings.cache_control, Some("max-age=1"));
    assert_eq!(
        settings.expires.map(|date| date.to_string()),
        Some("Wed, 21 Oct 2037 07:28:00 GMT".into())
    );
    assert_eq!(settings.content_type, None);
    assert_eq!(
        settings.request_payer,
        Some(crate::transfer::RequestPayer::Requester)
    );
}
#[test]
fn plans_forward_page_size_and_flags() {
    let mut input = args("file", "s3://b/", false);
    assert_eq!(make_copy_plan(&input).page_size, 0);
    input.page_size = Some(23);
    input.quiet = true;
    input.no_overwrite = true;
    let plan = make_copy_plan(&input);
    assert_eq!(plan.page_size, 23);
    assert!(plan.quiet && plan.no_overwrite);
}
#[test]
fn plans_retain_selected_globals_and_quiet() {
    let mut input = args("file", "s3://bucket/", false);
    input.quiet = true;
    let globals = cli_core::command::Globals {
        region: Some("r".into()),
        profile: Some("p".into()),
        endpoint_url: Some("http://localhost".into()),
        ..Default::default()
    };
    let plan = make_copy_plan_with_globals(&input, &globals);
    assert_eq!(plan.selected_region, Some("r"));
    assert_eq!(plan.selected_profile, Some("p"));
    assert_eq!(plan.selected_endpoint_url, Some("http://localhost"));
    assert!(plan.quiet);
}

#[test]
fn glacier_flags_and_progress_selection_survive_copy_planning() {
    use crate::results::Mode;
    use crate::transfer::GlacierPolicy;
    for (ignore, force, policy) in [
        (false, false, GlacierPolicy::Warn),
        (true, false, GlacierPolicy::Skip),
        (false, true, GlacierPolicy::Transfer),
        (true, true, GlacierPolicy::Transfer),
    ] {
        let mut input = args("s3://bucket/key", "file", false);
        input.ignore_glacier_warnings = ignore;
        input.force_glacier_transfer = force;
        input.progress_frequency = Some(5);
        input.progress_multiline = true;
        let plan = make_copy_plan(&input);
        assert_eq!(
            GlacierPolicy::from_flags(plan.force_glacier_transfer, plan.ignore_glacier_warnings),
            policy
        );
        let printer = plan.printer.unwrap();
        assert_eq!(printer.frequency_s, 5);
        assert!(!printer.oneline);
        input.progress = false;
        assert_eq!(
            make_copy_plan(&input).printer.unwrap().mode,
            Mode::NoProgress
        );
        input.only_show_errors = true;
        assert_eq!(
            make_copy_plan(&input).printer.unwrap().mode,
            Mode::OnlyErrors
        );
        input.quiet = true;
        assert!(make_copy_plan(&input).printer.is_none());
    }
}

fn filtered(
    source: &str,
    destination: &str,
    recursive: bool,
    filters: &[(FilterKind, &str)],
) -> Filter {
    let mut input = args(source, destination, recursive);
    input.filters = filters
        .iter()
        .map(|&(kind, pattern)| (kind, pattern.to_owned()))
        .collect();
    make_copy_filter(&make_copy_plan(&input), Path::new("/cwd"))
}

#[test]
fn copy_filters_without_patterns_include_everything() {
    assert_eq!(
        filtered("src", "s3://bucket/", true, &[]),
        Filter::default()
    );
}

#[cfg(not(windows))]
#[test]
fn copy_filters_root_local_sources_as_upstream() {
    let walk = filtered(
        "src/../tree",
        "s3://bucket/prefix",
        true,
        &[(Exclude, "a.txt")],
    );
    assert!(!walk.includes(b"a.txt"));
    assert!(walk.includes(b"nested/a.txt"));
    for (pattern, excluded) in [("a.txt", true), ("dir/a.txt", false)] {
        let single = filtered("dir/a.txt", "s3://bucket/key", false, &[(Exclude, pattern)]);
        assert_eq!(single.includes(b"/cwd/dir/a.txt"), !excluded, "{pattern}");
    }
}

#[test]
fn copy_filters_root_s3_sources_as_upstream() {
    for (source, recursive, key, excluded) in [
        ("s3://bucket/tree", true, "tree/a.txt", true),
        ("s3://bucket/tree/", true, "tree/a.txt", true),
        ("s3://bucket", true, "a.txt", true),
        ("s3://bucket/tree", true, "tree/nested/a.txt", false),
        ("s3://bucket/tree/a.txt", false, "tree/a.txt", true),
        ("s3://bucket/a.txt", false, "a.txt", true),
    ] {
        let filter = filtered(source, "out", recursive, &[(Exclude, "a.txt")]);
        assert_eq!(filter.includes(key.as_bytes()), !excluded, "{source} {key}");
    }
}

#[cfg(not(windows))]
#[test]
fn copy_filters_also_root_patterns_at_the_destination() {
    for (destination, name, excluded) in [
        ("s3://bucket/key", "bucket/a.txt", true),
        ("s3://bucket/dir/key", "bucket/dir/a.txt", true),
        ("s3://bucket/dir/", "bucket/dir/a.txt", true),
        ("s3://bucket/dir/key", "bucket/a.txt", false),
    ] {
        let filter = filtered("file", destination, false, &[(Exclude, "a.txt")]);
        assert_eq!(
            filter.includes(name.as_bytes()),
            !excluded,
            "{destination} {name}"
        );
    }
}
