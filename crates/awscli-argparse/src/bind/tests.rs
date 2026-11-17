#![expect(clippy::unwrap_used, reason = "pinned test fixtures and assertions")]
use super::*;
use crate::{Options, chain, tables};
crate::native_args! {
    struct ListArgs for tables::LS_ARGUMENTS {
        paths: String, dir_op: bool, page_size: Option<i64>, human_readable: bool,
        request_payer: Option<String>, bucket_region: Option<String>
    }
}
crate::native_args! {
    struct CopyArgs for tables::CP_ARGUMENTS {
        paths: [String;2], dir_op: bool, quiet: bool, page_size: Option<i64>,
        guess_mime_type: bool, progress: bool, progress_frequency: Option<i64>,
        sse: Option<String>, copy_props: String, filters: Vec<(String, String)>,
        grants: Vec<String>
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
struct Included;
impl TryFrom<&str> for Included {
    type Error = ();
    fn try_from(name: &str) -> Result<Self, ()> {
        (name == "--include").then_some(Self).ok_or(())
    }
}
crate::native_args! {
    struct IncludedArgs for tables::CP_ARGUMENTS { filters: Vec<(Included, String)> }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "binds every ls and cp field shape in one test"
)]
fn handler_views_bind_every_shape_from_s3_tables() {
    let result = chain::parse(
        &["s3", "ls", "--recursive", "--page-size", "10"].map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    let mut values = result.args.namespace;
    values.put("page_size", 10.into(), true);
    let args = ListArgs::bind(&values).unwrap();
    assert_eq!(args.paths, "s3://");
    assert!(args.dir_op);
    assert_eq!(args.page_size, Some(10));
    assert_eq!(args.bucket_region, None);
    let result = chain::parse(
        &["s3", "cp", "a", "b"].map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    let args = CopyArgs::bind(&result.args.namespace).unwrap();
    assert_eq!(args.paths, ["a", "b"]);
    assert!(args.guess_mime_type);
    assert!(args.progress);
    assert_eq!(args.progress_frequency, Some(0));
    assert_eq!(args.sse, None);
    assert_eq!(args.copy_props, "default");
    assert_eq!(args.filters, []);
    assert_eq!(args.grants, Vec::<String>::new());
    let result = chain::parse(
        &["s3", "cp", "--exc=*", "a", "b", "--include", "*.txt"].map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    let args = CopyArgs::bind(&result.args.namespace).unwrap();
    assert_eq!(
        args.filters,
        [("--exclude", "*"), ("--include", "*.txt")]
            .map(|(name, value)| (name.into(), value.into()))
    );
    let result = chain::parse(
        &[
            "s3",
            "cp",
            "a",
            "b",
            "--grants",
            "read=id=x",
            "--grants",
            "full=id=y",
            "read=id=z",
        ]
        .map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    let args = CopyArgs::bind(&result.args.namespace).unwrap();
    assert_eq!(args.grants, ["full=id=y", "read=id=z"]);
    assert_eq!(ListArgs::FIELD_NAMES.len(), ListArgs::SHAPES.len());
    assert_eq!(CopyArgs::FIELD_NAMES.len(), CopyArgs::SHAPES.len());
}
#[test]
fn misnamed_fields_and_mismatched_shapes_are_rejected() {
    for (name, shape) in ListArgs::SHAPES {
        assert_eq!(check(tables::LS_ARGUMENTS, name, *shape), Ok(()), "{name}");
    }
    for (name, shape) in CopyArgs::SHAPES {
        assert_eq!(check(tables::CP_ARGUMENTS, name, *shape), Ok(()), "{name}");
    }
    let mismatch = |argument| Err(ShapeError::ShapeMismatch { argument });
    for (table, dest, shape, expected) in [
        (
            tables::LS_ARGUMENTS,
            "page_sizes",
            Shape::Integer,
            Err(ShapeError::MissingDest),
        ),
        (
            tables::LS_ARGUMENTS,
            "recursive",
            Shape::Flag,
            Err(ShapeError::MissingDest),
        ),
        (
            tables::LS_ARGUMENTS,
            "page_size",
            Shape::Flag,
            mismatch("page-size"),
        ),
        (
            tables::LS_ARGUMENTS,
            "dir_op",
            Shape::Integer,
            mismatch("recursive"),
        ),
        (
            tables::LS_ARGUMENTS,
            "bucket_region",
            Shape::StringDefault,
            mismatch("bucket-region"),
        ),
        (
            tables::CP_ARGUMENTS,
            "paths",
            Shape::Strings(3),
            mismatch("paths"),
        ),
        (
            tables::CP_ARGUMENTS,
            "paths",
            Shape::StringDefault,
            mismatch("paths"),
        ),
        (
            tables::CP_ARGUMENTS,
            "filters",
            Shape::String,
            mismatch("include"),
        ),
        (
            tables::CP_ARGUMENTS,
            "paths",
            Shape::NamedValues,
            mismatch("paths"),
        ),
    ] {
        assert_eq!(check(table, dest, shape), expected, "{dest}");
        assert!(!accepts(table, dest, shape), "{dest}");
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "checks null and missing fields of the ls and cp views in one test"
)]
fn handler_views_preserve_null_and_missing_field_assertions() {
    let mut list = Namespace::default();
    for (dest, value) in [
        ("paths", "s3://b".into()),
        ("dir_op", true.into()),
        ("page_size", 10.into()),
        ("human_readable", Value::Null),
        ("request_payer", "requester".into()),
        ("bucket_region", Value::Null),
    ] {
        list.put(dest, value, false);
    }
    let list = ListArgs::bind(&list).unwrap();
    assert_eq!(list.paths, "s3://b");
    assert!(list.dir_op);
    assert_eq!(list.page_size, Some(10));
    assert!(!list.human_readable);
    assert_eq!(list.request_payer.as_deref(), Some("requester"));
    assert_eq!(list.bucket_region, None);
    let mut copy = Namespace::default();
    copy.put("paths", vec!["./a", "s3://b/k"].into(), false);
    copy.put("dir_op", false.into(), false);
    copy.put("page_size", Value::Null, false);
    copy.put("copy_props", "default".into(), false);
    let copy = CopyArgs::bind(&copy).unwrap();
    assert_eq!(copy.paths, ["./a", "s3://b/k"]);
    assert!(!copy.dir_op);
    assert!(!copy.quiet);
    assert_eq!(copy.page_size, None);
    assert_eq!(copy.filters, []);
    let mut filters = Namespace::default();
    filters.put("paths", vec!["./a", "s3://b/k"].into(), false);
    filters.put("copy_props", "default".into(), false);
    filters.put("filters", Value::Null, false);
    assert_eq!(
        CopyArgs::bind(&filters).map(|copy| copy.filters),
        Ok(Vec::new())
    );
    for value in [
        Value::from("*"),
        Value::Array(vec!["--exclude".into(), "*".into()]),
        Value::Array(vec![Value::Array(vec!["--exclude".into()])]),
    ] {
        filters.put("filters", value, true);
        assert_eq!(
            CopyArgs::bind(&filters).map(|copy| copy.filters),
            Err(BindError {
                destination: "filters".into(),
                shape: Shape::NamedValues,
            })
        );
    }
}
#[test]
fn named_values_bind_only_names_their_type_converts() {
    assert_eq!(IncludedArgs::FIELD_NAMES, ["filters"]);
    for (name, shape) in IncludedArgs::SHAPES {
        assert_eq!(check(tables::CP_ARGUMENTS, name, *shape), Ok(()), "{name}");
    }
    let pair = |name: &str| Value::Array(vec![Value::Array(vec![name.into(), "*".into()])]);
    let mut namespace = Namespace::default();
    namespace.put("filters", pair("--include"), false);
    assert_eq!(
        IncludedArgs::bind(&namespace).map(|args| args.filters),
        Ok(vec![(Included, "*".to_owned())])
    );
    namespace.put("filters", pair("--exclude"), true);
    assert_eq!(
        IncludedArgs::bind(&namespace),
        Err(BindError {
            destination: "filters".into(),
            shape: Shape::NamedValues,
        })
    );
}
#[test]
fn lists_bind_their_values_or_a_parameter_files_characters() {
    let mismatch = |argument| Err(ShapeError::ShapeMismatch { argument });
    for (dest, shape, expected) in [
        ("grants", Shape::List, Ok(())),
        ("paths", Shape::List, mismatch("paths")),
        ("content_type", Shape::List, mismatch("content-type")),
        ("grants", Shape::Strings(1), mismatch("grants")),
        ("grants", Shape::String, mismatch("grants")),
    ] {
        assert_eq!(check(tables::CP_ARGUMENTS, dest, shape), expected, "{dest}");
    }
    let mut namespace = Namespace::default();
    namespace.put("paths", vec!["./a", "s3://b/k"].into(), false);
    namespace.put("copy_props", "default".into(), false);
    let grants = |namespace: &Namespace| CopyArgs::bind(namespace).map(|args| args.grants);
    namespace.put("grants", Value::Null, false);
    assert_eq!(grants(&namespace), Ok(Vec::new()));
    namespace.put("grants", vec!["read=id=x", "full=id=y"].into(), true);
    assert_eq!(
        grants(&namespace),
        Ok(vec!["read=id=x".to_owned(), "full=id=y".to_owned()])
    );
    namespace.put("grants", "r=é".into(), true);
    assert_eq!(
        grants(&namespace),
        Ok(["r", "=", "é"].map(str::to_owned).to_vec())
    );
    namespace.put("grants", "".into(), true);
    assert_eq!(grants(&namespace), Ok(Vec::new()));
    for value in [Value::from(1), Value::Array(vec![Value::from(1)])] {
        namespace.put("grants", value, true);
        assert_eq!(
            grants(&namespace),
            Err(BindError {
                destination: "grants".into(),
                shape: Shape::List,
            })
        );
    }
}
