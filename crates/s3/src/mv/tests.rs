use super::*;
use crate::filter::FilterKind::{Exclude, Include};

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
        progress_frequency: None,
        progress_multiline: false,
        ignore_glacier_warnings: false,
        force_glacier_transfer: false,
        validate_same_s3_paths: false,
        filters: Vec::new(),
        follow_symlinks: true,
        case_conflict: OnCaseConflict::Ignore,
    }
}

#[test]
fn admits_moves_between_a_local_path_and_s3_in_either_direction() {
    for (source, destination) in [
        ("file.txt", "s3://bucket/key"),
        ("file.txt", "s3://bucket/"),
        ("s3://bucket/key", "file.txt"),
        ("s3://bucket/key", "."),
    ] {
        for recursive in [false, true] {
            assert_eq!(
                admit(&args(source, destination, recursive)),
                None,
                "{source} {destination} recursive={recursive}"
            );
        }
    }
}

#[test]
fn admits_path_validation_off_a_move_between_s3_paths() {
    let mut args = args("file.txt", "s3://bucket/key", false);
    args.validate_same_s3_paths = true;
    assert_eq!(admit(&args), None);
}

#[test]
fn refuses_operands_a_copy_leaves_to_python() {
    for (source, destination) in [
        ("s3://bucket/key", "s3://bucket/other"),
        ("s3://bucket/key", "s3://bucket/key"),
        ("a.txt", "b.txt"),
        ("-", "s3://bucket/key"),
        ("s3://bucket/key", "-"),
        ("file.txt", "s3://bucket-s3alias/key"),
        (
            "file.txt",
            "s3://arn:aws:s3:us-east-1:123456789012:accesspoint/ap",
        ),
    ] {
        assert_eq!(
            admit(&args(source, destination, false)),
            Some(AdmissionReason::UnsupportedOperand),
            "{source} {destination}"
        );
    }
}

#[test]
fn refuses_a_page_size_outside_the_listing_range() {
    for page_size in [0, -1, i64::from(u32::MAX) + 1] {
        let mut args = args("s3://bucket/prefix", "dir", true);
        args.page_size = Some(page_size);
        assert_eq!(
            admit(&args),
            Some(AdmissionReason::UnsupportedValue),
            "{page_size}"
        );
    }
}

#[test]
fn the_copy_keeps_every_option_but_path_validation() {
    let args = Args {
        paths: ["s3://bucket/prefix".into(), "dir".into()],
        dir_op: true,
        dryrun: true,
        quiet: true,
        no_overwrite: true,
        page_size: Some(7),
        only_show_errors: true,
        progress: false,
        progress_frequency: Some(3),
        progress_multiline: true,
        ignore_glacier_warnings: true,
        force_glacier_transfer: true,
        validate_same_s3_paths: true,
        filters: vec![(Exclude, "*".into()), (Include, "*.txt".into())],
        follow_symlinks: false,
        case_conflict: OnCaseConflict::Warn,
    };
    assert_eq!(
        args.to_copy_args(),
        cp_args::Args {
            paths: ["s3://bucket/prefix".into(), "dir".into()],
            dir_op: true,
            dryrun: true,
            quiet: true,
            no_overwrite: true,
            page_size: Some(7),
            only_show_errors: true,
            progress: false,
            progress_frequency: Some(3),
            progress_multiline: true,
            ignore_glacier_warnings: true,
            force_glacier_transfer: true,
            filters: vec![(Exclude, "*".into()), (Include, "*.txt".into())],
            follow_symlinks: false,
            content_type: None,
            cache_control: None,
            content_disposition: None,
            content_encoding: None,
            content_language: None,
            expires: None,
            website_redirect: None,
            metadata: awscli_argparse::bind::StringMap::default(),
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
            case_conflict: OnCaseConflict::Warn,
        }
    );
}
