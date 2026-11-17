use super::*;
use crate::deps::tests::Directory;

/// A prefix holding every file `validate` requires, its markers, and its
/// completion marker.
fn complete_prefix() -> Result<Directory> {
    let directory = Directory::new()?;
    let mut files = vec![
        "include/zlib.h".to_owned(),
        "include/lzma.h".to_owned(),
        "share/pkgconfig/zlib.pc".to_owned(),
        format!("{MARKERS}/zlib.complete"),
        ".complete".to_owned(),
    ];
    for name in ["z", "lzma"] {
        files.push(format!(
            "lib/{}",
            platform::archive_name(std::env::consts::OS, name)
        ));
    }
    for file in files {
        let path = directory.0.join(file);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, "")?;
    }
    Ok(directory)
}

#[test]
fn a_complete_prefix_is_reused() -> Result<()> {
    let prefix = complete_prefix()?;
    assert!(cached(&prefix.0)?);
    fs::remove_file(prefix.0.join(".complete"))?;
    assert!(!cached(&prefix.0)?);
    Ok(())
}

#[test]
fn a_prefix_missing_an_archive_or_header_is_rejected() -> Result<()> {
    // Joined as `validate` joins them, so the message's separators match on
    // Windows.
    for missing in [
        PathBuf::from("include/zlib.h"),
        PathBuf::from("include/lzma.h"),
        Path::new("lib").join(platform::archive_name(std::env::consts::OS, "z")),
        Path::new("lib").join(platform::archive_name(std::env::consts::OS, "lzma")),
    ] {
        let prefix = complete_prefix()?;
        let path = prefix.0.join(&missing);
        fs::remove_file(&path)?;
        assert_eq!(
            validate(&prefix.0).err().map(|failure| failure.to_string()),
            Some(format!("zlib/xz prefix lacks {}", path.display())),
            "{}",
            missing.display()
        );
    }
    Ok(())
}

#[test]
fn a_prefix_with_a_tree_the_crt_does_not_link_is_rejected() -> Result<()> {
    let prefix = complete_prefix()?;
    fs::create_dir(prefix.0.join("bin"))?;
    assert_eq!(
        validate(&prefix.0).err().map(|failure| failure.to_string()),
        Some(format!(
            "zlib/xz prefix {} has bin, which the CRT does not publish",
            prefix.0.display()
        ))
    );
    Ok(())
}

#[test]
fn roots_name_the_prefix_and_its_scratch_tree() {
    let root = Path::new("/checkout");
    let stages = root.join("target/deps").join(TARGET);
    let prefix = stages.join("zlib-xz-1");
    let mut expected = Roots::default();
    expected.insert("zlib-xz", prefix.clone());
    expected.insert("work/zlib-xz", stages.join("work/zlib-xz"));
    assert_eq!(roots(root, &prefix), expected);
}
