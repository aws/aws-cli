use super::*;
use std::ffi::OsString;

fn args(operand: &str) -> Args {
    Args {
        paths: [OsString::from(operand)],
        dir_op: false,
        dryrun: false,
        quiet: false,
        only_show_errors: false,
        page_size: None,
        request_payer: None,
        filters: Vec::new(),
    }
}

#[test]
fn admits_an_s3_uri_of_a_supported_bucket() {
    for operand in [
        "s3://bucket/key",
        "s3://bucket",
        "s3://bucket/",
        "s3://b/p/",
    ] {
        assert_eq!(admit(&args(operand)), None, "{operand}");
    }
}

#[test]
fn refuses_operands_only_python_takes() {
    for operand in [
        "local.txt",
        "-",
        "s3:bucket/key",
        "s3://",
        "s3:///key",
        "s3://bucket-s3alias/key",
        "s3://arn:aws:s3:us-east-1:123456789012:accesspoint/ap/key",
        "s3://bucket/a\0b",
    ] {
        assert_eq!(
            admit(&args(operand)),
            Some(AdmissionReason::UnsupportedOperand),
            "{operand}"
        );
    }
}

#[cfg(unix)]
#[test]
fn refuses_an_operand_that_is_not_utf8() {
    use std::os::unix::ffi::OsStringExt;
    let mut args = args("");
    args.paths = [OsString::from_vec(b"s3://bucket/\xff".to_vec())];
    assert_eq!(admit(&args), Some(AdmissionReason::UnsupportedOperand));
}

#[test]
fn refuses_a_page_size_outside_the_listing_range() {
    for page_size in [0, -1, i64::from(u32::MAX) + 1] {
        let mut args = args("s3://bucket/");
        args.page_size = Some(page_size);
        assert_eq!(admit(&args), Some(AdmissionReason::UnsupportedValue));
    }
    let mut args = args("s3://bucket/");
    args.page_size = Some(1);
    assert_eq!(admit(&args), None);
}

fn recursive(operand: &str) -> Args {
    Args {
        dir_op: true,
        ..args(operand)
    }
}

#[test]
fn plans_one_object_a_listing_or_the_folder_markers() {
    let single = args("s3://bucket/dir/key.txt");
    let plan = make_delete_plan(&single);
    assert_eq!(
        (plan.bucket, plan.key, plan.selection),
        ("bucket", b"dir/key.txt".as_slice(), Selection::Object)
    );
    let marker = args("s3://bucket/dir/");
    assert_eq!(make_delete_plan(&marker).selection, Selection::Object);
    for operand in ["s3://bucket", "s3://bucket/"] {
        let bucket = args(operand);
        let plan = make_delete_plan(&bucket);
        assert_eq!(plan.selection, Selection::FolderMarkers, "{operand}");
        assert_eq!(plan.listing_prefix(), b"", "{operand}");
    }
    for (operand, prefix) in [
        ("s3://bucket/tree", b"tree/".as_slice()),
        ("s3://bucket/tree/", b"tree/"),
        ("s3://bucket", b""),
    ] {
        let listed = recursive(operand);
        let plan = make_delete_plan(&listed);
        assert_eq!(plan.selection, Selection::Prefix, "{operand}");
        assert_eq!(plan.listing_prefix(), prefix, "{operand}");
    }
}

#[test]
fn plans_the_admitted_page_size() {
    let mut listed = recursive("s3://bucket/tree");
    assert_eq!(make_delete_plan(&listed).page_size, 0);
    listed.page_size = Some(2);
    assert_eq!(make_delete_plan(&listed).page_size, 2);
}

#[test]
fn plans_the_request_payer_argparse_bound() {
    let mut listed = recursive("s3://bucket/tree");
    assert_eq!(make_delete_plan(&listed).request_payer, None);
    listed.request_payer = Some("requester".into());
    assert_eq!(admit(&listed), None);
    assert_eq!(
        make_delete_plan(&listed).request_payer,
        Some(RequestPayer::Requester)
    );
    assert_eq!(RequestPayer::Requester.header_value(), b"requester");
}

#[test]
fn refuses_a_request_payer_native_does_not_know() {
    let mut listed = recursive("s3://bucket/tree");
    listed.request_payer = Some("owner".into());
    assert_eq!(admit(&listed), Some(AdmissionReason::UnsupportedValue));
}

fn filtered(mut args: Args, filters: &[(FilterKind, &str)]) -> Filter {
    args.filters = filters
        .iter()
        .map(|(kind, pattern)| (*kind, (*pattern).to_owned()))
        .collect();
    let plan = make_delete_plan(&args);
    make_delete_filter(&args, &plan)
}

#[test]
fn a_single_delete_roots_its_patterns_at_the_keys_directory() {
    let operand = "s3://bucket/tree/a.txt";
    let excluded = filtered(args(operand), &[(FilterKind::Exclude, "*")]);
    assert!(!excluded.includes(b"tree/a.txt"));
    let rooted = filtered(args(operand), &[(FilterKind::Exclude, "tree/a.txt")]);
    assert!(rooted.includes(b"tree/a.txt"));
    let included = filtered(
        args(operand),
        &[(FilterKind::Exclude, "*"), (FilterKind::Include, "a.txt")],
    );
    assert!(included.includes(b"tree/a.txt"));
}

#[test]
fn a_recursive_delete_roots_its_patterns_at_the_operand() {
    let filter = filtered(
        recursive("s3://bucket/tree"),
        &[(FilterKind::Exclude, "*/")],
    );
    assert!(!filter.includes(b"tree/folder/"));
    assert!(filter.includes(b"tree/"));
    assert!(filter.includes(b"tree/a.txt"));
}

#[test]
fn no_patterns_include_every_object() {
    let plan_args = recursive("s3://bucket/tree");
    let plan = make_delete_plan(&plan_args);
    assert_eq!(make_delete_filter(&plan_args, &plan), Filter::default());
}
