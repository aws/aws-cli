#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
use std::fs;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT: AtomicU64 = AtomicU64::new(0);
struct Directory(PathBuf);
impl Directory {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "s3-links-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn skip(root: &Path) -> LinkPolicy {
    LinkPolicy::from_flag(false, root)
}

#[test]
fn the_policy_roots_at_the_operand_without_its_separator() {
    let operand = std::env::temp_dir().join("dest");
    let mut separated = operand.clone().into_os_string();
    separated.push(std::path::MAIN_SEPARATOR_STR);
    assert_eq!(
        LinkPolicy::from_flag(false, Path::new(&separated)),
        LinkPolicy::Skip {
            root: operand.clone()
        }
    );
    assert_eq!(LinkPolicy::from_flag(true, &operand), LinkPolicy::Follow);
    assert_eq!(LinkPolicy::default(), LinkPolicy::Follow);
    #[cfg(windows)]
    assert_eq!(
        LinkPolicy::from_flag(false, Path::new(r"\\server\share\dir\dest\")),
        LinkPolicy::Skip {
            root: PathBuf::from(r"\\server\share\dir\dest")
        }
    );
}

#[test]
fn parents_stop_at_the_root_as_upstream_s_dirname_loop_does() {
    let root = std::env::temp_dir().join("dest");
    let destination = root.join("a").join("..").join("b").join("c.txt");
    assert_eq!(
        parents_below(&root, &destination),
        [
            root.join("a").join("..").join("b"),
            root.join("a").join(".."),
            root.join("a"),
        ]
    );
    assert_eq!(parents_below(&root, &root.join("c.txt")), [] as [&Path; 0]);
}

#[cfg(unix)]
#[test]
fn parents_stop_at_a_path_that_is_its_own_directory() {
    // `sync s3://bucket /` names `//key`, whose `dirname` stays `//`, which
    // never reaches the root `/`.
    assert_eq!(
        parents_below(Path::new("/"), Path::new("//a/b")),
        [Path::new("//a"), Path::new("//")]
    );
}

#[test]
fn only_a_destination_below_the_root_and_a_separator_is_checked() {
    let root = std::env::temp_dir().join("dest");
    let separator = std::path::MAIN_SEPARATOR_STR;
    let below = |rest: &str| {
        let mut path = root.clone().into_os_string();
        path.push(rest);
        lies_below(&root, Path::new(&path))
    };
    assert!(below(&format!("{separator}a")));
    assert!(below(separator));
    assert!(!below(""));
    assert!(!below("-sibling"));
    #[cfg(unix)]
    assert!(lies_below(Path::new("/"), Path::new("/a")));
}

#[test]
fn following_skips_nothing() {
    let directory = Directory::new();
    let missing = directory.0.join("missing").join("..").join("a.txt");
    let follow = LinkPolicy::from_flag(true, &directory.0);
    assert!(!follow.skips_download(&missing));
    assert!(!follow.drops_root() && !follow.drops_operand());
    assert!(!follow.drops(&directory.0));
}

#[test]
fn a_parent_reference_below_the_root_is_never_followed() {
    let directory = Directory::new();
    fs::create_dir(directory.0.join("plain")).unwrap();
    let policy = skip(&directory.0);
    for parts in [&["plain", "..", "a.txt"][..], &["missing", "..", "a.txt"]] {
        let destination = parts.iter().fold(directory.0.clone(), |p, c| p.join(c));
        assert!(policy.skips_download(&destination), "{parts:?}");
    }
    assert!(!policy.skips_download(&directory.0.join("..")));
    assert!(!policy.skips_download(&directory.0.join("plain").join("a.txt")));
    assert!(!policy.skips_download(&directory.0.join("absent").join("a.txt")));
}

#[cfg(unix)]
#[test]
fn a_download_skips_a_link_at_or_below_the_root_and_follows_one_above_it() {
    use std::os::unix::fs::symlink;
    let directory = Directory::new();
    let outside = directory.0.join("outside");
    let dest = directory.0.join("dest");
    fs::create_dir_all(dest.join("a").join("b")).unwrap();
    fs::create_dir(&outside).unwrap();
    fs::write(outside.join("target.txt"), b"target").unwrap();
    symlink(&outside, dest.join("a").join("sub")).unwrap();
    symlink(outside.join("target.txt"), dest.join("link.txt")).unwrap();
    symlink(&dest, directory.0.join("dest-link")).unwrap();
    let policy = skip(&dest);
    assert!(policy.skips_download(&dest.join("link.txt")));
    assert!(policy.skips_download(&dest.join("a").join("sub").join("x.txt")));
    assert!(!policy.skips_download(&dest.join("a").join("b").join("x.txt")));
    let through = directory.0.join("dest-link").join("x.txt");
    assert!(!skip(&through).skips_download(&through));
    assert!(skip(&dest.join("link.txt")).skips_download(&dest.join("link.txt")));
    let linked = skip(&directory.0.join("dest-link"));
    assert!(linked.skips_download(&directory.0.join("elsewhere.txt")));
    assert!(linked.skips_download(&directory.0.join("dest-link").join("x.txt")));
}

#[cfg(unix)]
#[test]
fn a_walk_drops_links_and_a_root_that_links_to_a_directory() {
    use std::os::unix::fs::symlink;
    let directory = Directory::new();
    let real = directory.0.join("real");
    fs::create_dir(&real).unwrap();
    fs::write(directory.0.join("file.txt"), b"file").unwrap();
    symlink(&real, directory.0.join("dir-link")).unwrap();
    symlink(directory.0.join("file.txt"), directory.0.join("file-link")).unwrap();
    symlink(directory.0.join("absent"), directory.0.join("broken")).unwrap();
    let policy = skip(&real);
    for name in ["dir-link", "file-link", "broken"] {
        assert!(policy.drops(&directory.0.join(name)), "{name}");
    }
    assert!(!policy.drops(&real) && !policy.drops(&directory.0.join("file.txt")));
    assert!(!policy.drops_root() && !policy.drops_operand());
    assert!(skip(&directory.0.join("dir-link")).drops_root());
    for name in ["file-link", "broken"] {
        let policy = skip(&directory.0.join(name));
        assert!(!policy.drops_root() && policy.drops_operand(), "{name}");
    }
}
