use super::*;

#[test]
fn product_filter_rejects_test_sources_and_tools() {
    let root = Path::new("/repo");
    for file in [
        "crates/s3/src/tests.rs",
        "crates/s3/src/testing/fakes.rs",
        "crates/s3/src/scheduler/model.rs",
        "crates/s3/src/download/tests/linux.rs",
        "crates/build-support/src/lib.rs",
        "crates/build-support/src/allocation.rs",
        "xtask/src/main.rs",
        "fuzz/fuzz_targets/writer_retries.rs",
        "crates/s3/build.rs",
    ] {
        assert_eq!(product_file(root, &root.join(file)), None, "{file}");
    }
    let runtime = Path::new("crates/s3/src/download/service.rs");
    assert_eq!(
        product_file(root, &root.join(runtime)),
        Some(runtime.to_path_buf())
    );
    assert_eq!(
        product_file(root, Path::new("/elsewhere/crates/s3/src/lib.rs")),
        None
    );
}

fn lcov(records: &[(&str, &[(u32, u64)])]) -> Vec<u8> {
    let mut text = String::from("TN:\n");
    for (file, lines) in records {
        text.push_str(&format!("SF:/repo/{file}\nFN:1,example\nFNDA:1,example\n"));
        for (number, count) in *lines {
            text.push_str(&format!("DA:{number},{count}\n"));
        }
        text.push_str(&format!("LF:{}\nLH:0\nend_of_record\n", lines.len()));
    }
    text.into_bytes()
}

#[test]
fn projection_baseline_intersection_preserves_omitted_files_and_lines() -> Result<(), TaskError> {
    let root = Path::new("/repo");
    let mut baseline = parse_lcov(
        root,
        &lcov(&[
            ("crates/s3/src/a.rs", &[(1, 0), (2, 0)]),
            ("crates/s3/src/b.rs", &[(8, 0)]),
        ]),
    )?;
    let union = parse_lcov(
        root,
        &lcov(&[
            ("crates/s3/src/a.rs", &[(2, 1), (99, 1)]),
            ("crates/s3/src/test_only.rs", &[(1, 9), (2, 0)]),
        ]),
    )?;
    let projection = project(&mut baseline, &union);
    assert_eq!(
        totals(&baseline),
        Totals {
            covered: 1,
            counted: 3
        }
    );
    assert_eq!(
        projection.outside,
        Totals {
            covered: 2,
            counted: 3
        }
    );
    assert_eq!(
        projection.test,
        Totals {
            covered: 3,
            counted: 4
        }
    );
    Ok(())
}

#[test]
fn filters_remove_test_hits_without_changing_baseline_denominator() -> Result<(), TaskError> {
    let root = Path::new("/repo");
    let application = lcov(&[("crates/s3/src/a.rs", &[(1, 0), (2, 0)])]);
    let union = lcov(&[
        ("crates/s3/src/a.rs", &[(1, 4), (3, 1)]),
        ("crates/s3/src/tests.rs", &[(1, 100)]),
        ("xtask/src/main.rs", &[(1, 100)]),
    ]);
    let summary = summary(root, &application, &union)?;
    assert_eq!(
        summary,
        "Test-executable diagnostic: 2/2 lines (not application coverage)\n\
        Test lines outside application baseline: 1/1\n\
        Product file\tCovered lines\tTotal lines\tCoverage\n\
        crates/s3/src/a.rs\t1\t2\t50.00%\n\
        TOTAL\t1\t2\t50.00%\n\
        Application coverage: 1/2 (50.00%)\n"
    );
    Ok(())
}

#[test]
fn duplicate_records_or_their_hits() -> Result<(), TaskError> {
    let root = Path::new("/repo");
    let files = parse_lcov(
        root,
        &lcov(&[
            ("crates/s3/src/a.rs", &[(4, 0), (5, 0)]),
            ("crates/s3/src/a.rs", &[(4, 2)]),
        ]),
    )?;
    assert_eq!(files.len(), 1);
    assert_eq!(
        totals(&files),
        Totals {
            covered: 1,
            counted: 2
        }
    );
    Ok(())
}

#[test]
fn rejects_malformed_records_and_empty_baselines() {
    let root = Path::new("/repo");
    for text in [
        "DA:1,0\n",
        "SF:/repo/crates/s3/src/a.rs\nDA:1\nend_of_record\n",
        "SF:/repo/crates/s3/src/a.rs\nDA:0,1\nend_of_record\n",
        "SF:/repo/crates/s3/src/a.rs\nDA:x,1\nend_of_record\n",
        "SF:/repo/crates/s3/src/a.rs\nDA:1,-1\nend_of_record\n",
        "SF:/repo/crates/s3/src/a.rs\nDA:1,0\n",
        "SF:/repo/crates/s3/src/a.rs\nSF:/repo/crates/s3/src/b.rs\nend_of_record\n",
        "end_of_record\n",
    ] {
        assert!(parse_lcov(root, text.as_bytes()).is_err(), "{text:?}");
    }
    assert!(parse_lcov(root, b"\xff").is_err());
    let union = lcov(&[("crates/s3/src/a.rs", &[(1, 1)])]);
    for application in [
        lcov(&[]),
        lcov(&[("crates/s3/src/tests.rs", &[(1, 0)])]),
        lcov(&[("crates/s3/src/a.rs", &[])]),
    ] {
        assert!(summary(root, &application, &union).is_err());
    }
}

#[test]
fn zero_line_rows_and_totals_have_no_percentage() -> Result<(), TaskError> {
    let mut files = Files::new();
    files.insert(PathBuf::from("crates/s3/src/zero.rs"), BTreeMap::new());
    let rendered = render(&files, &Projection::default())?;
    assert!(rendered.contains("\ncrates/s3/src/zero.rs\t0\t0\tn/a\n"));
    assert!(rendered.contains("\nTOTAL\t0\t0\tn/a\n"));
    assert!(rendered.ends_with("\nApplication coverage: 0/0 (unavailable)\n"));
    files.insert(
        PathBuf::from("crates/s3/src/unhit.rs"),
        BTreeMap::from([(1, false), (2, false), (3, true)]),
    );
    let rendered = render(&files, &Projection::default())?;
    let zero = rendered.find("\ncrates/s3/src/zero.rs\t0\t0\tn/a\n");
    let unhit = rendered.find("\ncrates/s3/src/unhit.rs\t1\t3\t33.33%\n");
    // Rows sort by path, not by insertion.
    assert!(
        zero.is_some() && unhit.is_some() && unhit < zero,
        "{rendered}"
    );
    assert!(rendered.ends_with("\nTOTAL\t1\t3\t33.33%\nApplication coverage: 1/3 (33.33%)\n"));
    Ok(())
}
