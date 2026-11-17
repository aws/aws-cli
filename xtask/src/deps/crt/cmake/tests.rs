use super::*;
use crate::deps::{TARGET, work_dir};

#[test]
fn installed_markers_live_in_the_prefix_they_describe() {
    let root = Path::new("/checkout");
    let deps = root.join("target/deps").join(TARGET);
    let marker = installed_marker(&deps.join("crt-1"), "aws-c-s3");
    assert_eq!(marker, deps.join("crt-1/.projects/aws-c-s3.complete"));
    // The work directory every CRT key claims in turn holds no marker.
    assert!(!marker.starts_with(work_dir(root, TARGET, "crt")));
    assert_ne!(installed_marker(&deps.join("crt-2"), "aws-c-s3"), marker);
}

#[test]
fn installed_markers_record_each_project_once_installed() -> Result<()> {
    let directory = crate::deps::tests::Directory::new()?;
    assert!(!installed_marker(&directory.0, "zlib").exists());
    mark_installed(&directory.0, "zlib")?;
    assert!(installed_marker(&directory.0, "zlib").is_file());
    assert!(!installed_marker(&directory.0, "xz").exists());
    Ok(())
}
