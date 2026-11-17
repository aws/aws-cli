use super::*;

fn name_rendering_to(length: usize, package: bool) -> Vec<u8> {
    let suffix = if package { "/__init__.py" } else { ".py" };
    let fixed = SYNTHETIC_ROOT.len() + 1 + suffix.len();
    let mut name = b"awscli.".to_vec();
    name.resize(length - fixed, b'm');
    name
}

#[test]
fn synthetic_paths_render_dotted_names_under_the_synthetic_root() {
    for (name, package, path) in [
        (
            &b"awscli.clidriver"[..],
            false,
            &b"/<zippy>/awscli/clidriver.py"[..],
        ),
        (
            b"awscli.botocore",
            true,
            b"/<zippy>/awscli/botocore/__init__.py",
        ),
        (b"plain", false, b"/<zippy>/plain.py"),
    ] {
        assert_eq!(synthetic_path(name, package).as_deref(), Some(path));
    }
}

#[test]
fn synthetic_paths_fill_the_path_limit_and_overflow_one_byte_past_it() {
    for package in [false, true] {
        let name = name_rendering_to(SYNTHETIC_PATH_MAX, package);
        let path = synthetic_path(&name, package);
        assert_eq!(path.as_ref().map(Vec::len), Some(SYNTHETIC_PATH_MAX));
        assert!(path.is_some_and(|path| path.starts_with(b"/<zippy>/awscli/mmm")));
        let name = name_rendering_to(SYNTHETIC_PATH_MAX + 1, package);
        assert_eq!(synthetic_path(&name, package), None);
    }
}
