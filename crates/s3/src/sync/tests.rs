use super::*;

fn args(source: &str, destination: &str) -> Args {
    Args {
        paths: [source.into(), destination.into()],
        ..Args::default()
    }
}

#[test]
fn admits_syncs_between_a_local_directory_and_s3_in_either_direction() {
    for (source, destination) in [
        ("site", "s3://bucket/www/"),
        ("site", "s3://bucket/www"),
        ("site", "s3://bucket"),
        ("s3://bucket/www/", "site"),
        ("s3://bucket/www", "."),
        ("s3://bucket", "site"),
    ] {
        assert_eq!(
            admit(&args(source, destination)),
            None,
            "{source} {destination}"
        );
    }
}

#[test]
fn refuses_operands_a_recursive_copy_leaves_to_python() {
    for (source, destination) in [
        ("s3://bucket/www/", "s3://other/www/"),
        ("site", "copy"),
        ("-", "s3://bucket/www/"),
        ("s3://bucket/www/", "-"),
        ("site", "s3://bucket-s3alias/www/"),
        ("site", "s3://bucket--usw2-az1--x-s3/www/"),
        ("s3://bucket--usw2-az1--x-s3/www/", "site"),
        (
            "site",
            "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/ap/www/",
        ),
    ] {
        assert_eq!(
            admit(&args(source, destination)),
            Some(AdmissionReason::UnsupportedOperand),
            "{source} {destination}"
        );
    }
}

#[test]
fn copies_recursively_with_every_option_at_its_default() {
    let copy = args("site", "s3://bucket/www/").to_copy_args();
    assert_eq!(
        copy,
        cp_args::Args {
            paths: ["site".into(), "s3://bucket/www/".into()],
            dir_op: true,
            dryrun: false,
            quiet: false,
            no_overwrite: false,
            page_size: None,
            only_show_errors: false,
            progress: true,
            progress_frequency: None,
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
            case_conflict: OnCaseConflict::Ignore,
        }
    );
}

#[test]
fn hands_the_copy_every_option_but_no_overwrite() {
    let sync = Args {
        dryrun: true,
        quiet: true,
        no_overwrite: true,
        page_size: Some(5),
        filters: vec![(FilterKind::Exclude, "*.log".to_owned())],
        follow_symlinks: false,
        content_type: Some("text/plain".to_owned()),
        request_payer: Some("requester".to_owned()),
        ..args("site", "s3://bucket/www/")
    };
    let copy = sync.to_copy_args();
    assert!(!copy.no_overwrite);
    assert_eq!(
        (copy.dryrun, copy.quiet, copy.page_size, copy.dir_op),
        (true, true, Some(5), true)
    );
    assert_eq!(copy.filters, sync.filters);
    assert!(!copy.follow_symlinks);
    assert_eq!(copy.content_type.as_deref(), Some("text/plain"));
    assert_eq!(copy.request_payer.as_deref(), Some("requester"));
}

#[test]
fn the_strategy_registered_last_wins_as_upstream_s_does() {
    let strategies = |no_overwrite, exact_timestamps, size_only| {
        Args {
            no_overwrite,
            exact_timestamps,
            size_only,
            ..args("site", "s3://bucket/www/")
        }
        .strategies()
        .both
    };
    for (flags, both) in [
        ((false, false, false), BothSides::SizeAndLastModified),
        ((false, false, true), BothSides::SizeOnly),
        ((false, true, false), BothSides::ExactTimestamps),
        ((false, true, true), BothSides::ExactTimestamps),
        ((true, false, true), BothSides::Never),
        ((true, true, true), BothSides::Never),
    ] {
        assert_eq!(strategies(flags.0, flags.1, flags.2), both, "{flags:?}");
    }
}

#[test]
fn case_conflict_and_delete_choose_their_cases_strategies() {
    for (mode, source_only) in [
        (OnCaseConflict::Ignore, SourceOnly::Transfer),
        (
            OnCaseConflict::Skip,
            SourceOnly::CaseConflict(CaseConflict::Skip),
        ),
        (
            OnCaseConflict::Warn,
            SourceOnly::CaseConflict(CaseConflict::Warn),
        ),
        (
            OnCaseConflict::Error,
            SourceOnly::CaseConflict(CaseConflict::Error),
        ),
    ] {
        let sync = Args {
            case_conflict: mode,
            delete: true,
            ..args("s3://bucket/www/", "site")
        };
        assert_eq!(
            sync.strategies(),
            Strategies {
                both: BothSides::SizeAndLastModified,
                source_only,
                destination_only: DestinationOnly::Delete,
            },
            "{mode:?}"
        );
    }
    assert_eq!(
        args("site", "s3://bucket/www/").strategies(),
        Strategies::default()
    );
}
