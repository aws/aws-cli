use super::*;

#[test]
fn upstream_source_and_version_are_owned_by_the_tracked_tree() -> Result<()> {
    let root = test_root()?;
    let pins = Pins::load(root)?;
    assert_eq!(aws_cli_source(root)?, root.join("aws-cli"));
    assert!(!aws_cli_version(root)?.is_empty());
    assert!(!pins.sources.contains_key("aws_cli"));
    assert!(!pins.versions.contains_key("aws_cli_version"));
    assert!(aws_cli_runtime_lock(root)?.is_file());
    Ok(())
}

#[test]
fn source_digest_detects_edits_additions_deletions_and_lock_updates() -> Result<()> {
    let directory = Directory::new()?;
    let source = directory.0.join("aws-cli");
    fs::create_dir_all(source.join("awscli"))?;
    fs::create_dir_all(source.join("requirements/download-deps"))?;
    fs::write(source.join("awscli/__init__.py"), "__version__ = '1.2.3'\n")?;
    for lock in ["system-sandbox-lock.txt", "system-sandbox-win-lock.txt"] {
        fs::write(
            source.join("requirements/download-deps").join(lock),
            "first\n",
        )?;
    }
    assert_eq!(aws_cli_version(&directory.0)?, "1.2.3");
    let initial = aws_cli_digest(&directory.0)?;
    fs::write(source.join("awscli/new.py"), "first\n")?;
    let added = aws_cli_digest(&directory.0)?;
    assert_ne!(added, initial);
    fs::write(source.join("awscli/new.py"), "other\n")?;
    assert_ne!(aws_cli_digest(&directory.0)?, added);
    fs::remove_file(source.join("awscli/new.py"))?;
    assert_eq!(aws_cli_digest(&directory.0)?, initial);
    fs::write(
        source.join("requirements/download-deps/system-sandbox-lock.txt"),
        "other\n",
    )?;
    assert_ne!(aws_cli_digest(&directory.0)?, initial);
    Ok(())
}

#[cfg(unix)]
#[test]
fn source_digest_ignores_generated_bytecode_and_rejects_symlinks() -> Result<()> {
    let directory = Directory::new()?;
    let source = directory.0.join("aws-cli");
    fs::create_dir_all(source.join("awscli"))?;
    fs::create_dir_all(source.join("requirements/download-deps"))?;
    fs::write(source.join("awscli/__init__.py"), "__version__ = '1'\n")?;
    for lock in ["system-sandbox-lock.txt", "system-sandbox-win-lock.txt"] {
        fs::write(source.join("requirements/download-deps").join(lock), "")?;
    }
    let initial = aws_cli_digest(&directory.0)?;
    fs::create_dir(source.join("awscli/__pycache__"))?;
    fs::write(source.join("awscli/__pycache__/cache.py"), "ignored")?;
    fs::write(source.join("awscli/cache.pyc"), "ignored")?;
    assert_eq!(aws_cli_digest(&directory.0)?, initial);
    std::os::unix::fs::symlink("__init__.py", source.join("awscli/link.py"))?;
    assert!(aws_cli_digest(&directory.0).is_err());
    Ok(())
}

#[test]
fn tree_digest_bounds_all_enumerated_entries_and_skips_cache_contents() -> Result<()> {
    let directory = Directory::new()?;
    fs::write(directory.0.join("first.py"), "first")?;
    fs::write(directory.0.join("second.py"), "second")?;
    assert!(tree_digest_with_entry_limit(&directory.0, 2).is_err());
    let initial = tree_digest_with_entry_limit(&directory.0, 3)?;
    fs::create_dir(directory.0.join("package"))?;
    fs::write(directory.0.join("package/module.py"), "module")?;
    assert!(tree_digest_with_entry_limit(&directory.0, 4).is_err());
    let expanded = tree_digest_with_entry_limit(&directory.0, 5)?;
    assert_ne!(expanded, initial);
    fs::create_dir(directory.0.join("__pycache__"))?;
    fs::write(directory.0.join("__pycache__/ignored.py"), "ignored")?;
    fs::write(directory.0.join("ignored.pyc"), "ignored")?;
    assert!(tree_digest_with_entry_limit(&directory.0, 6).is_err());
    assert_eq!(tree_digest_with_entry_limit(&directory.0, 7)?, expanded);
    Ok(())
}

#[test]
fn pin_mismatch_is_rejected() -> Result<()> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("missing workspace parent"))?;
    let mut pins = Pins::load(root)?;
    // Keep the pinned major.minor so the URL rule, not the ABI rule, rejects it.
    let major_minor =
        major_minor(pins.version("python_version")?).ok_or_else(|| error("no major.minor"))?;
    pins.versions
        .insert("python_version".into(), format!("{major_minor}.999"));
    assert_eq!(
        failure(check_pins(root, &pins)),
        "cpython: URL disagrees with python_version"
    );
    Ok(())
}

#[test]
fn revision_mismatch_is_rejected() -> Result<()> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("missing workspace parent"))?;
    let mut pins = Pins::load(root)?;
    pins.sources
        .get_mut("aws_c_common")
        .ok_or_else(|| error("missing CRT pin"))?
        .url
        .push_str("wrong");
    assert!(check_pins(root, &pins).is_err());
    Ok(())
}

fn failure(result: Result<()>) -> String {
    result
        .err()
        .map(|failure| failure.to_string())
        .unwrap_or_default()
}

#[test]
fn tracked_pins_pass_every_check() -> Result<()> {
    let root = test_root()?;
    check_pins(root, &Pins::load(root)?)
}

#[test]
fn cli_awscrt_requirement_must_equal_the_awscrt_pin() {
    let project =
        "dependencies = [\n    \"colorama>=0.2.5,<0.4.7\",\n    \"awscrt==0.37.0\",\r\n]\n";
    assert!(check_cli_awscrt(project, "0.37.0").is_ok());
    assert!(check_cli_awscrt("\t'awscrt==0.37.0'\n", "0.37.0").is_ok());
    assert_eq!(
        failure(check_cli_awscrt(project, "0.38.0")),
        "aws-cli/pyproject.toml requires awscrt==0.37.0, but deps/pins.toml pins \
         awscrt==0.38.0; update the aws-crt-python version and package pin together"
    );
    // The first requirement decides.
    let twice = "\"awscrt>=0.37.0\",\n\"awscrt==0.37.0\",\n";
    assert!(
        failure(check_cli_awscrt(twice, "0.37.0"))
            .starts_with("aws-cli/pyproject.toml requires awscrt>=0.37.0, ")
    );
}

#[test]
fn cli_awscrt_requirement_must_be_present_and_quoted() {
    for project in ["", "dependencies = []\n", "    awscrt==0.37.0,\n"] {
        assert_eq!(
            failure(check_cli_awscrt(project, "0.37.0")),
            "aws-cli/pyproject.toml: missing awscrt requirement",
            "{project:?}"
        );
    }
    for (project, found) in [
        ("    \"awscrt==0.37.0',\n", "\"awscrt==0.37.0'"),
        ("    \"awscrt==0.37.0\n", "\"awscrt==0.37.0"),
    ] {
        assert_eq!(
            failure(check_cli_awscrt(project, "0.37.0")),
            format!("AWS CLI metadata: expected a quoted value, found {found}")
        );
    }
}

#[test]
fn check_pins_rejects_an_awscrt_pin_the_cli_does_not_require() -> Result<()> {
    let root = test_root()?;
    let mut pins = Pins::load(root)?;
    pins.versions
        .insert("awscrt_version".into(), "0.0.0".into());
    let message = failure(check_pins(root, &pins));
    assert!(
        message.starts_with("aws-cli/pyproject.toml requires awscrt=="),
        "{message}"
    );
    assert!(
        message.contains(", but deps/pins.toml pins awscrt==0.0.0;"),
        "{message}"
    );
    Ok(())
}

#[test]
fn python_abi_must_name_the_pinned_major_minor() {
    assert!(check_python_abi("3.14.8", "python3.14").is_ok());
    assert!(check_python_abi("3.14.0", "python3.14").is_ok());
    assert_eq!(
        failure(check_python_abi("3.15.0", "python3.14")),
        "xtask/src/python/interpreter.rs: PYTHON_ABI = python3.14, but deps/pins.toml pins \
         Python 3.15.0; update them together"
    );
    assert_eq!(
        failure(check_python_abi("3", "python3.14")),
        "deps/pins.toml: python_version must be MAJOR.MINOR.MICRO, found 3"
    );
}

#[test]
fn check_pins_rejects_a_python_pin_beyond_the_abi() -> Result<()> {
    let root = test_root()?;
    let mut pins = Pins::load(root)?;
    pins.versions
        .insert("python_version".into(), "3.99.0".into());
    assert_eq!(
        failure(check_pins(root, &pins)),
        format!(
            "xtask/src/python/interpreter.rs: PYTHON_ABI = {}, but deps/pins.toml pins \
             Python 3.99.0; update them together",
            crate::python::PYTHON_ABI
        )
    );
    Ok(())
}

#[test]
fn python_fallback_build_script_repeats_the_python_abi() -> Result<()> {
    let script = fs::read_to_string(test_root()?.join("crates/python-fallback/build.rs"))?;
    let declaration = format!(
        "const PYTHON_ABI: &str = \"{}\";",
        crate::python::PYTHON_ABI
    );
    assert!(
        script.contains(&declaration),
        "crates/python-fallback/build.rs must declare {declaration}"
    );
    Ok(())
}

const TOOLCHAIN: &str = "[toolchain]\nchannel = \"1.96.0\"\nprofile = \"minimal\"\n";
const MISE: &str = "[tools]\ncmake = \"3.25.1\"\nninja = \"1.11.1\"\nrust = \"1.96.0\"\n";
const MANIFEST: &str =
    "[workspace]\nmembers = []\n\n[workspace.package]\nrust-version = \"1.96\"\n";

fn rust_copies<'a>(toolchain: &'a str, mise: &'a str, manifest: &'a str) -> RustPinCopies<'a> {
    RustPinCopies {
        toolchain,
        mise,
        manifest,
    }
}

#[test]
fn rust_version_copies_agree_with_the_pin() {
    assert!(check_rust_version("1.96.0", &rust_copies(TOOLCHAIN, MISE, MANIFEST)).is_ok());
    let full = MANIFEST.replace("\"1.96\"", "\"1.96.0\"");
    assert!(check_rust_version("1.96.0", &rust_copies(TOOLCHAIN, MISE, &full)).is_ok());
}

#[test]
fn each_drifted_rust_version_copy_is_named() {
    let toolchain = TOOLCHAIN.replace("1.96.0", "1.97.0");
    let mise = MISE.replace("1.96.0", "1.95.0");
    for (copies, message) in [
        (
            rust_copies(&toolchain, MISE, MANIFEST),
            "rust-toolchain.toml: channel = 1.97.0, but deps/pins.toml pins 1.96.0",
        ),
        (
            rust_copies(TOOLCHAIN, &mise, MANIFEST),
            "mise.toml: rust = 1.95.0, but deps/pins.toml pins 1.96.0",
        ),
    ] {
        assert_eq!(failure(check_rust_version("1.96.0", &copies)), message);
    }
    for minimum in ["1.95", "1.9", "1.96.1", "1"] {
        let manifest = MANIFEST.replace("\"1.96\"", &format!("\"{minimum}\""));
        assert_eq!(
            failure(check_rust_version(
                "1.96.0",
                &rust_copies(TOOLCHAIN, MISE, &manifest)
            )),
            format!("Cargo.toml: rust-version = {minimum}, but deps/pins.toml pins 1.96.0")
        );
    }
}

#[test]
fn missing_or_invalid_rust_version_copies_are_named() {
    let mise = "[tools]\ncmake = \"3.25.1\"\n";
    assert_eq!(
        failure(check_rust_version(
            "1.96.0",
            &rust_copies(TOOLCHAIN, mise, MANIFEST)
        )),
        "mise.toml: missing tools.rust"
    );
    assert_eq!(
        failure(check_rust_version(
            "1.96.0",
            &rust_copies(TOOLCHAIN, MISE, "[workspace]\n")
        )),
        "Cargo.toml: missing workspace.package.rust-version"
    );
    assert!(
        failure(check_rust_version(
            "1.96.0",
            &rust_copies("[toolchain", MISE, MANIFEST)
        ))
        .starts_with("invalid rust-toolchain.toml: ")
    );
}

#[test]
fn check_pins_rejects_a_rust_pin_the_toolchain_files_do_not_select() -> Result<()> {
    let root = test_root()?;
    let mut pins = Pins::load(root)?;
    pins.versions.insert("rust_version".into(), "0.0.0".into());
    let message = failure(check_pins(root, &pins));
    assert!(
        message.starts_with("rust-toolchain.toml: channel = "),
        "{message}"
    );
    assert!(
        message.ends_with(", but deps/pins.toml pins 0.0.0"),
        "{message}"
    );
    Ok(())
}

/// A root holding the `labels` stage inventories and the pins copied from
/// this checkout, and a minimal AWS CLI tree.
fn stage_root(labels: &[&str]) -> Result<Directory> {
    let directory = Directory::new()?;
    let pins = "deps/pins.toml";
    for label in labels {
        for relative in inputs::stage_files(label)?.into_iter().chain([pins]) {
            let target = directory.0.join(relative);
            if let Some(parent) = target.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(test_root()?.join(relative), target)?;
        }
    }
    let source = directory.0.join("aws-cli");
    fs::create_dir_all(source.join("awscli"))?;
    fs::create_dir_all(source.join("requirements/download-deps"))?;
    fs::write(source.join("awscli/__init__.py"), "__version__ = '1'\n")?;
    for lock in ["system-sandbox-lock.txt", "system-sandbox-win-lock.txt"] {
        let lock = source.join("requirements/download-deps").join(lock);
        if !lock.is_file() {
            fs::write(lock, "")?;
        }
    }
    Ok(directory)
}

#[test]
fn cli_edits_never_change_the_interpreter_key() -> Result<()> {
    let root = stage_root(&["cpython"])?;
    let versions = [b"tool 1.0\n".to_vec()];
    // Linux PGO trains on the CLI; the key still covers only its path.
    for pgo in [true, false] {
        let libraries = [Path::new("openssl"), Path::new("zlib-xz")];
        let key = crate::python::interpreter_key(pgo, libraries, None);
        let initial = stage_key(&root.0, "cpython", &versions, &key)?;
        fs::write(root.0.join("aws-cli/awscli/new.py"), "edited\n")?;
        assert_eq!(stage_key(&root.0, "cpython", &versions, &key)?, initial);
        fs::remove_file(root.0.join("aws-cli/awscli/new.py"))?;
    }
    Ok(())
}

/// The CRT and interpreter keys of `root`, chained as the stages chain
/// them: the CRT on the OpenSSL and zlib/xz keys, and the interpreter on
/// their prefixes, with OpenSSL's perl at `perl`.
fn chained_keys(root: &Path, perl: &[u8]) -> Result<(String, String)> {
    let cmake = [b"cmake 1.0\n".to_vec()];
    let openssl = stage_key(root, "openssl", &[perl.to_vec()], &[])?;
    let zlib_xz = stage_key(root, "zlib-xz", &cmake, &[])?;
    let crt = stage_key(
        root,
        "crt",
        &cmake,
        &crt::crt_key("toolchain", &openssl, &zlib_xz),
    )?;
    let stages = PathBuf::from(format!("target/deps/{TARGET}"));
    let libraries = [
        stages.join(format!("openssl-{openssl}")),
        stages.join(format!("zlib-xz-{zlib_xz}")),
    ];
    let key = crate::python::interpreter_key(true, [&libraries[0], &libraries[1]], None);
    Ok((crt, stage_key(root, "cpython", &[], &key)?))
}

#[test]
fn a_perl_upgrade_reaches_the_crt_and_interpreter_through_openssl() -> Result<()> {
    let root = stage_root(&["openssl", "zlib-xz", "crt", "cpython"])?;
    // Only OpenSSL runs perl, and CPython has no tools of its own, so the
    // OpenSSL key in the CRT's key, and its prefix in CPython's, carry the
    // perl upgrade to both.
    let (old_crt, old_interpreter) = chained_keys(&root.0, b"perl 5.32\n")?;
    let (new_crt, new_interpreter) = chained_keys(&root.0, b"perl 5.40\n")?;
    assert_ne!(old_crt, new_crt);
    assert_ne!(old_interpreter, new_interpreter);
    Ok(())
}

#[test]
fn the_interpreter_follows_only_the_crt_libraries_it_links() -> Result<()> {
    let root = stage_root(&["openssl", "zlib-xz", "crt", "cpython"])?;
    let perl = b"perl 5.40\n";
    let mut previous = chained_keys(&root.0, perl)?;
    // CPython links no AWS C library, so their bumps rebuild only the CRT.
    for (pin, linked) in [
        ("aws_c_common", false),
        ("aws_c_s3", false),
        ("zlib", true),
        ("xz", true),
        ("openssl", true),
    ] {
        bump_pin(pin)(&root.0)?;
        let keys = chained_keys(&root.0, perl)?;
        assert_ne!(keys.0, previous.0, "{pin}");
        assert_eq!(keys.1 != previous.1, linked, "{pin}");
        previous = keys;
    }
    Ok(())
}

const FALLBACK_STAGES: [&str; 3] = ["fallback-archive", "fallback-payload", "fallback-runtime"];

/// The archive, payload, and runtime keys of `root` under fixed tool versions.
fn fallback_keys(root: &Path) -> Result<Vec<String>> {
    let versions = [b"tool 1.0\n".to_vec()];
    FALLBACK_STAGES
        .iter()
        .map(|label| stage_key(root, label, &versions, &[b"pgo"]))
        .collect()
}

#[test]
fn cli_edits_change_only_the_payload_key() -> Result<()> {
    let root = stage_root(&FALLBACK_STAGES)?;
    let initial = fallback_keys(&root.0)?;
    fs::write(root.0.join("aws-cli/awscli/new.py"), "edited\n")?;
    let edited = fallback_keys(&root.0)?;
    // The runtime follows the payload through its prefix, not the CLI tree.
    assert_eq!(edited[0], initial[0], "archive");
    assert_ne!(edited[1], initial[1], "payload");
    assert_eq!(edited[2], initial[2], "runtime");
    Ok(())
}

#[test]
fn runtime_bootstrap_edits_change_only_the_runtime_key() -> Result<()> {
    let root = stage_root(&FALLBACK_STAGES)?;
    let initial = fallback_keys(&root.0)?;
    let runtime = root.0.join("crates/python-fallback/python/runtime.py");
    let mut source = fs::read(&runtime)?;
    source.extend_from_slice(b"# edited\n");
    fs::write(&runtime, source)?;
    let edited = fallback_keys(&root.0)?;
    assert_eq!(edited[0], initial[0], "archive");
    assert_eq!(edited[1], initial[1], "payload");
    assert_ne!(edited[2], initial[2], "runtime");
    Ok(())
}

/// Every stage label `stage_key` accepts.
const STAGES: [&str; 11] = [
    "toolchain",
    "openssl",
    "zlib-xz",
    "crt",
    "profile",
    "python-support",
    "cpython",
    "fallback-archive",
    "fallback-payload",
    "fallback-runtime",
    "fallback",
];

/// The Python stages, which all build through python/stage.rs.
const PYTHON_STAGES: [&str; 7] = [
    "profile",
    "python-support",
    "cpython",
    "fallback-archive",
    "fallback-payload",
    "fallback-runtime",
    "fallback",
];

/// Every stage's key in `root` under fixed tool versions and no extra
/// inputs. A stage built from another's output also keys on its prefix,
/// which `extra` carries; these keys show only the stage's own inputs.
fn stage_keys(root: &Path) -> Result<BTreeMap<&'static str, String>> {
    let versions = [b"tool 1.0\n".to_vec()];
    STAGES
        .iter()
        .map(|label| Ok((*label, stage_key(root, label, &versions, &[])?)))
        .collect()
}

/// The stages whose keys `change` alters, in `STAGES` order.
fn rekeyed(root: &Path, change: impl FnOnce(&Path) -> Result<()>) -> Result<Vec<&'static str>> {
    let before = stage_keys(root)?;
    change(root)?;
    let after = stage_keys(root)?;
    Ok(STAGES
        .into_iter()
        .filter(|label| before[label] != after[label])
        .collect())
}

/// Append a comment to the inventory file `relative`.
fn edit(relative: &'static str) -> impl FnOnce(&Path) -> Result<()> {
    move |root| {
        let path = root.join(relative);
        let mut contents = fs::read(&path)?;
        contents.extend_from_slice(b"\n# edited\n");
        Ok(fs::write(path, contents)?)
    }
}

/// Change the pin `name` in deps/pins.toml: a source's digest, or a
/// version's value.
fn bump_pin(name: &'static str) -> impl FnOnce(&Path) -> Result<()> {
    move |root| {
        let path = root.join("deps/pins.toml");
        let text = fs::read_to_string(&path)?;
        let mut section = String::new();
        let mut bumped = false;
        let lines: Vec<String> = text
            .lines()
            .map(|line| {
                if line.starts_with('[') {
                    section = line.to_owned();
                }
                let source = section == format!("[sources.{name}]");
                if source && let Some(digest) = line.strip_prefix("sha256 = \"") {
                    bumped = true;
                    let first = if digest.starts_with('0') { '1' } else { '0' };
                    return format!("sha256 = \"{first}{}", &digest[1..]);
                }
                let prefix = format!("{name} = \"");
                if section == "[versions]" && line.starts_with(&prefix) {
                    bumped = true;
                    return line.replacen(&prefix, &format!("{prefix}0.0.0-"), 1);
                }
                line.to_owned()
            })
            .collect();
        if !bumped {
            return Err(error(format!("no pin {name} to bump")));
        }
        Ok(fs::write(path, lines.join("\n") + "\n")?)
    }
}

/// `labels`, and `linux` too on Linux, in `STAGES` order.
fn on_linux(linux: &[&'static str], labels: &[&'static str]) -> Vec<&'static str> {
    STAGES
        .into_iter()
        .filter(|label| {
            labels.contains(label) || (cfg!(target_os = "linux") && linux.contains(label))
        })
        .collect()
}

#[test]
fn a_fallback_edit_rekeys_neither_the_toolchain_nor_the_crt_nor_the_interpreter() -> Result<()> {
    let root = stage_root(&STAGES)?;
    let fallback = [
        "fallback-archive",
        "fallback-payload",
        "fallback-runtime",
        "fallback",
    ];
    assert_eq!(
        rekeyed(&root.0, edit("xtask/src/python/fallback.rs"))?,
        fallback
    );
    assert_eq!(
        rekeyed(&root.0, edit("deps/scripts/prepare_python_fallback.py"))?,
        fallback[..3]
    );
    assert_eq!(
        rekeyed(&root.0, edit("deps/scripts/gen_inittab.py"))?,
        ["fallback-archive"]
    );
    assert_eq!(
        rekeyed(&root.0, edit("deps/scripts/pack.py"))?,
        ["fallback-payload"]
    );
    Ok(())
}

#[test]
fn an_interpreter_edit_rekeys_only_the_interpreter() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for file in [
        "xtask/src/python/interpreter.rs",
        "deps/scripts/build_cpython.py",
        "deps/scripts/payload_sysconfig.py",
        "deps/cpython-linux-pyconfig.h",
    ] {
        assert_eq!(rekeyed(&root.0, edit(file))?, ["cpython"], "{file}");
    }
    for file in [
        "xtask/src/python/support.rs",
        "deps/scripts/build_python_deps.py",
    ] {
        assert_eq!(
            rekeyed(&root.0, edit(file))?,
            ["python-support", "cpython"],
            "{file}"
        );
    }
    Ok(())
}

#[test]
fn a_profile_edit_rekeys_the_linux_toolchain_that_installs_its_runtime() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for file in [
        "xtask/src/python/profile.rs",
        "deps/scripts/build_pgo_tools.py",
    ] {
        assert_eq!(
            rekeyed(&root.0, edit(file))?,
            on_linux(&["toolchain", "cpython"], &["profile"]),
            "{file}"
        );
    }
    // Every Python stage and the Linux toolchain's profile build run the
    // shared stage helpers and driver modules.
    for file in ["xtask/src/python/stage.rs", "deps/scripts/build_guard.py"] {
        let mut expected = on_linux(&["toolchain"], &PYTHON_STAGES);
        if file.ends_with(".py") {
            // The published stage runs no driver.
            expected.retain(|label| *label != "fallback");
        }
        assert_eq!(rekeyed(&root.0, edit(file))?, expected, "{file}");
    }
    Ok(())
}

#[test]
fn a_native_builder_edit_rekeys_only_the_stages_it_builds() -> Result<()> {
    let root = stage_root(&STAGES)?;
    let cases: [(&str, &[&str]); 10] = [
        ("xtask/src/deps/crt.rs", &["crt"]),
        ("deps/crt-libraries.txt", &["crt"]),
        // The CRT follows an OpenSSL or zlib/xz edit through the stage's
        // key, and CPython through its prefix.
        ("xtask/src/deps/crt/openssl.rs", &["openssl"]),
        ("xtask/src/deps/crt/zlib_xz.rs", &["zlib-xz"]),
        ("xtask/src/deps/crt/cmake.rs", &["zlib-xz", "crt"]),
        (
            "xtask/src/deps/crt/source_paths.rs",
            &["openssl", "zlib-xz", "crt"],
        ),
        ("xtask/src/deps/platform.rs", &["openssl", "zlib-xz", "crt"]),
        ("xtask/src/deps/toolchain.rs", &["toolchain"]),
        (
            "xtask/src/deps/command.rs",
            &["toolchain", "openssl", "zlib-xz", "crt"],
        ),
        // CPython merges the support prefix into its own with copy_tree.
        (
            "xtask/src/deps/files.rs",
            &["toolchain", "openssl", "zlib-xz", "crt", "cpython"],
        ),
    ];
    for (file, expected) in cases {
        assert_eq!(rekeyed(&root.0, edit(file))?, expected, "{file}");
    }
    Ok(())
}

#[test]
fn a_support_pin_rekeys_the_support_and_interpreter_stages_only() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for pin in ["sqlite", "bzip2", "libffi", "zstd"] {
        assert_eq!(
            rekeyed(&root.0, bump_pin(pin))?,
            ["python-support", "cpython"],
            "{pin}"
        );
    }
    for pin in ["cpython", "python_version"] {
        assert_eq!(rekeyed(&root.0, bump_pin(pin))?, ["cpython"], "{pin}");
    }
    Ok(())
}

#[test]
fn a_crt_pin_rekeys_only_the_crt() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for pin in ["aws_c_common", "aws_c_s3", "aws_checksums"] {
        assert_eq!(rekeyed(&root.0, bump_pin(pin))?, ["crt"], "{pin}");
    }
    // The CRT and CPython follow an OpenSSL, zlib, or xz bump through the
    // stage that builds it.
    assert_eq!(rekeyed(&root.0, bump_pin("openssl"))?, ["openssl"]);
    for pin in ["zlib", "xz"] {
        assert_eq!(rekeyed(&root.0, bump_pin(pin))?, ["zlib-xz"], "{pin}");
    }
    // Windows uses Schannel and never builds s2n-tls.
    let s2n: &[&str] = if cfg!(windows) { &[] } else { &["crt"] };
    assert_eq!(rekeyed(&root.0, bump_pin("s2n_tls"))?, s2n);
    Ok(())
}

#[test]
fn a_toolchain_pin_rekeys_only_the_stages_built_from_it() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for pin in ["musl", "linux_headers", "cmake_source", "rust_version"] {
        assert_eq!(
            rekeyed(&root.0, bump_pin(pin))?,
            on_linux(&["toolchain"], &[]),
            "{pin}"
        );
    }
    let llvm = if cfg!(target_arch = "aarch64") {
        "llvm_binary_aarch64"
    } else {
        "llvm_binary"
    };
    assert_eq!(
        rekeyed(&root.0, bump_pin(llvm))?,
        on_linux(&["toolchain"], &[])
    );
    // The profile runtime builds from compiler-rt too.
    assert_eq!(
        rekeyed(&root.0, bump_pin("compiler_rt_source"))?,
        on_linux(&["toolchain", "cpython"], &["profile"])
    );
    Ok(())
}

#[test]
fn the_awscrt_pins_rekey_the_archive_and_payload_only() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for pin in ["awscrt", "awscrt_version"] {
        assert_eq!(
            rekeyed(&root.0, bump_pin(pin))?,
            ["fallback-archive", "fallback-payload"],
            "{pin}"
        );
    }
    Ok(())
}

#[test]
fn pins_and_pin_fields_no_build_reads_rekey_nothing() -> Result<()> {
    let root = stage_root(&STAGES)?;
    for pin in ["mimalloc_source", "llvm_source", "awscrt_commit"] {
        assert!(rekeyed(&root.0, bump_pin(pin))?.is_empty(), "{pin}");
    }
    // A source's original URL only records where its archive came from.
    let rekeyed = rekeyed(&root.0, |root| {
        let path = root.join("deps/pins.toml");
        let text = fs::read_to_string(&path)?;
        Ok(fs::write(
            path,
            text.replace("original_url = \"git+", "original_url = \"git+edited-"),
        )?)
    })?;
    assert!(rekeyed.is_empty(), "{rekeyed:?}");
    Ok(())
}

#[test]
fn a_stage_key_naming_a_missing_pin_is_an_error() -> Result<()> {
    let root = stage_root(&STAGES)?;
    let path = root.0.join("deps/pins.toml");
    let text = fs::read_to_string(&path)?;
    fs::write(
        &path,
        text.replace("[sources.zlib]", "[sources.zlib_renamed]"),
    )?;
    assert_eq!(
        failure(stage_key(&root.0, "zlib-xz", &[], &[]).map(drop)),
        "stage key names missing pin zlib"
    );
    // A stage that does not key on the pin is unaffected.
    stage_key(&root.0, "python-support", &[], &[])?;
    Ok(())
}

#[test]
fn every_stage_keys_on_the_tracked_checkout() -> Result<()> {
    for label in STAGES {
        stage_key(test_root()?, label, &[], &[])?;
    }
    Ok(())
}

#[test]
fn only_the_payload_is_keyed_on_cli_contents() {
    assert!(hashes_cli_source("fallback-payload"));
    for label in [
        "fallback",
        "fallback-archive",
        "fallback-runtime",
        "cpython",
        "toolchain",
        "profile",
        "python-support",
        "openssl",
        "zlib-xz",
        "crt",
    ] {
        assert!(!hashes_cli_source(label), "{label}");
    }
}

#[test]
fn native_environment_applies_only_project_dependency_paths() {
    let environment = NativeEnvironment {
        crt: "/managed/crt".into(),
        cpython: "/managed/cpython".into(),
        fallback: "/managed/fallback".into(),
        cc: "/managed/tools/clang".into(),
        clang: "/managed/tools/clang".into(),
        ar: "/managed/tools/llvm-ar".into(),
        ranlib: "/managed/tools/llvm-ranlib".into(),
        mimalloc: Some("/managed/sources/mimalloc".into()),
        msvc: None,
        link: Some("/managed/tools/link".into()),
    };
    let mut command = Command::new("cargo");
    environment.apply(&mut command);

    let actual: BTreeMap<_, _> = command
        .get_envs()
        .map(|(name, value)| (name.to_owned(), value.map(std::ffi::OsStr::to_owned)))
        .collect();
    let expected = BTreeMap::from([
        ("AR".into(), Some("/managed/tools/llvm-ar".into())),
        ("AWS_NATIVE_LINK_MODE".into(), Some("static".into())),
        ("AWS_NATIVE_PYTHON_LINK".into(), Some("static".into())),
        ("AWS_NATIVE_PYTHON_PAYLOAD".into(), Some("embedded".into())),
        (
            "AWS_NATIVE_CPYTHON_PREFIX".into(),
            Some("/managed/cpython".into()),
        ),
        ("AWS_NATIVE_CRT_PREFIX".into(), Some("/managed/crt".into())),
        (
            "AWS_NATIVE_FALLBACK_PREFIX".into(),
            Some("/managed/fallback".into()),
        ),
        (
            "AWS_NATIVE_MIMALLOC_SOURCE".into(),
            Some("/managed/sources/mimalloc".into()),
        ),
        ("CC".into(), Some("/managed/tools/clang".into())),
        ("RANLIB".into(), Some("/managed/tools/llvm-ranlib".into())),
    ]);
    assert_eq!(actual, expected);
    assert!(!actual.contains_key(std::ffi::OsStr::new("HOME")));
    // The link driver is the test command's own step, after its flags.
    let mut linked = Command::new("cargo");
    environment.apply_link(&mut linked);
    assert!(
        linked
            .get_envs()
            .any(|(_, value)| value == Some(std::ffi::OsStr::new("/managed/tools/link")))
    );
}

pub(super) fn test_root() -> Result<&'static Path> {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("missing workspace parent"))
}

#[derive(Debug)]
pub(super) struct Directory(pub(super) PathBuf);

impl Directory {
    pub(super) fn new() -> Result<Self> {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "awscli-deps-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path)?;
        Ok(Self(path))
    }
}

impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn guard_proceeds_without_controls() -> Result<()> {
    guard_controls("unused", None, None)
}

#[test]
fn stage_lock_excludes_other_handles_and_releases_on_drop() -> Result<()> {
    let directory = Directory::new()?;
    let prefix = directory.0.join("native-stage");
    let lock = lock_stage(&prefix)?;
    let second = File::options()
        .read(true)
        .write(true)
        .open(prefix.with_extension("lock"))?;
    assert!(second.try_lock().is_err());
    drop(lock);
    second
        .try_lock()
        .map_err(|failure| error(failure.to_string()))?;
    Ok(())
}

#[test]
fn guard_forbid_wins_and_accepts_any_nonempty_value() -> Result<()> {
    let directory = Directory::new()?;
    let marker = directory.0.join("markers");
    for value in ["1", "yes", "0"] {
        assert!(guard_controls("builder", Some(value.as_ref()), Some(marker.as_os_str())).is_err());
        assert!(!marker.exists());
    }
    guard_controls("builder", None, Some(marker.as_os_str()))?;
    assert_eq!(fs::read_to_string(marker.join("builder"))?, "ran\n");
    Ok(())
}

#[test]
fn guard_empty_controls_are_unset() -> Result<()> {
    guard_controls("unused", Some("".as_ref()), Some("".as_ref()))
}

#[test]
fn guard_appends_one_line_per_invocation() -> Result<()> {
    let directory = Directory::new()?;
    let marker = directory.0.join("markers");
    guard_controls("buildkit-check", None, Some(marker.as_os_str()))?;
    guard_controls("buildkit-check", None, Some(marker.as_os_str()))?;
    assert_eq!(
        fs::read_to_string(marker.join("buildkit-check"))?,
        "ran\nran\n"
    );
    Ok(())
}

#[test]
fn tool_allowlist_has_only_discovery_and_host_state() -> Result<()> {
    let text = fs::read_to_string(test_root()?.join("deps/scripts/tool_environ.txt"))?;
    let names: Vec<_> = text
        .lines()
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .collect();
    assert!(names.contains(&"PATH"));
    for name in names {
        assert!(!name.contains(['=', '#', ' ', '\t']));
        for forbidden in [
            "CPATH",
            "C_INCLUDE_PATH",
            "CFLAGS",
            "CXXFLAGS",
            "CPPFLAGS",
            "LDFLAGS",
            "LIBRARY_PATH",
            "PYTHONPATH",
            "PERL5OPT",
            "MAKEFLAGS",
            "LC_ALL",
            "LANG",
            "SDKROOT",
            "CC",
            "INCLUDE",
            "LIB",
            "LIBPATH",
            "CL",
            "_CL_",
        ] {
            assert_ne!(name, forbidden);
        }
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn executable_wrapper_preserves_exact_script_and_mode() -> Result<()> {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new()?;
    let wrapper = directory.0.join("tools/ar");
    let script = "#!/bin/sh\nexec '/opt/llvm/bin/llvm-ar' \"$@\"\n";
    write_executable(&wrapper, script)?;
    assert_eq!(fs::read_to_string(&wrapper)?, script);
    assert_ne!(fs::metadata(wrapper)?.permissions().mode() & 0o100, 0);
    Ok(())
}

#[test]
fn direct_tool_commands_preserve_hostile_paths_and_argument_boundaries() -> Result<()> {
    use std::ffi::OsStr;
    for directory in ["tools with spaces", "100%pure", "tools-日本語-é"] {
        let program = PathBuf::from(directory).join("llvm-ar.exe");
        let mut command = tool_command(test_root()?, &program)?;
        let arguments = ["rcs", "a b", "", "'\"$()`;*\\", "a\nb"];
        command.args(arguments);
        assert_eq!(command.get_program(), program.as_os_str());
        assert_eq!(
            command.get_args().collect::<Vec<_>>(),
            arguments.map(OsStr::new),
        );
    }
    Ok(())
}

/// Writes an executable this process then runs. Tests fork concurrently, and
/// a child forked while this process holds the file open for writing keeps
/// that descriptor until it execs, so running the file can fail with ETXTBSY.
/// A separate process writes it instead, so no descriptor this process could
/// pass to a forked child ever has the file open for writing.
#[cfg(unix)]
fn write_executable_out_of_process(path: &Path, content: &str) -> Result<()> {
    let mut child = Command::new("/bin/sh")
        .args(["-c", "cat > \"$1\" && chmod 755 \"$1\"", "sh"])
        .arg(path)
        .stdin(std::process::Stdio::piped())
        .spawn()?;
    child
        .stdin
        .take()
        .ok_or_else(|| error("writer stdin is missing"))?
        .write_all(content.as_bytes())?;
    if !child.wait()?.success() {
        return Err(error(format!("cannot write {}", path.display())));
    }
    Ok(())
}

#[test]
#[cfg(unix)]
fn shell_quoting_preserves_metacharacters_and_arguments() -> Result<()> {
    let directory = Directory::new()?;
    let names = [
        "tool",
        "tool with spaces",
        "tool%literal",
        "tool-λ-雪",
        "tool'; printf INJECTED; #''$(printf expanded)`printf expanded`\"\\\n",
    ];
    for (index, name) in names.into_iter().enumerate() {
        let tool = directory.0.join(name);
        write_executable_out_of_process(&tool, "#!/bin/sh\nprintf '<%s>\\n' \"$@\"\n")?;
        for argument in ["ar", "ranlib"] {
            let wrapper = directory.0.join(format!("wrapper-{index}-{argument}"));
            write_executable_out_of_process(
                &wrapper,
                &format!(
                    "#!/bin/sh\nexec {} {argument} \"$@\"\n",
                    shell_quote(&tool)?
                ),
            )?;
            let output =
                process::output(Command::new(wrapper).args(["", "a b", "'\"$()`;*\\", "a\nb"]))?;
            assert_eq!(
                String::from_utf8_lossy(&output.stdout),
                format!("<{argument}>\n<>\n<a b>\n<'\"$()`;*\\>\n<a\nb>\n")
            );
            assert!(output.stderr.is_empty());
        }
    }
    Ok(())
}

#[test]
fn corrupted_cached_archive_fails_before_network_or_tools() -> Result<()> {
    let pins = Pins::load(test_root()?)?;
    let pin = pins
        .sources
        .get("cmake_source")
        .ok_or_else(|| error("missing CMake pin"))?;
    let directory = Directory::new()?;
    let downloads = directory.0.join("target/downloads");
    fs::create_dir_all(&downloads)?;
    fs::write(downloads.join(format!("{}.tar.xz", pin.sha256)), "corrupt")?;
    let result = download(&directory.0, &pins, "cmake_source");
    assert!(
        matches!(result, Err(TaskError::Message(message)) if message.contains("SHA-256 mismatch"))
    );
    Ok(())
}

#[test]
fn member_paths_name_members_below_the_stripped_directory() -> Result<()> {
    let listing = "LLVM-21/libexec/\nLLVM-21/bin/clang\n";
    assert_eq!(
        member_paths(listing, 1, &["bin/clang", "lib/clang/21"])?,
        ["LLVM-21/bin/clang", "LLVM-21/lib/clang/21"]
    );
    assert_eq!(
        member_paths("bin/clang\n", 0, &["bin/clang"])?,
        ["bin/clang"]
    );
    assert!(member_paths(listing, 1, &[])?.is_empty());
    assert!(member_paths("", 1, &["bin/clang"]).is_err());
    assert!(member_paths("LLVM-21/\n", 2, &["bin/clang"]).is_err());
    Ok(())
}

#[test]
fn unpacked_marker_records_the_members_of_a_partial_unpack() {
    assert_eq!(unpacked_marker("abc", &[]), "abc");
    assert_eq!(
        unpacked_marker("abc", &["bin/clang", "lib"]),
        "abc\nbin/clang\nlib"
    );
}

/// A root holding a fake LLVM release archive, which contains every release
/// member and the unused `bin/flang`, and pins naming it `llvm_binary`.
#[cfg(unix)]
fn llvm_release_fixture(root: &Path) -> Result<(PathBuf, Pins)> {
    fs::create_dir_all(root.join("deps/scripts"))?;
    fs::copy(
        test_root()?.join("deps/scripts/tool_environ.txt"),
        root.join("deps/scripts/tool_environ.txt"),
    )?;
    let release = root.join("fixture/LLVM-test");
    for member in llvm::RELEASE_MEMBERS {
        let path = release.join(member);
        if member.starts_with("lib/") {
            fs::create_dir_all(path.join("include"))?;
            fs::write(path.join("include/stddef.h"), "header\n")?;
        } else {
            fs::create_dir_all(path.parent().ok_or_else(|| error("member has no parent"))?)?;
            fs::write(&path, member)?;
        }
    }
    fs::write(release.join("bin/flang"), "unused\n")?;
    let fixture = root.join("fixture.tar.gz");
    process::run(
        Command::new("tar")
            .arg("-czf")
            .arg(&fixture)
            .arg("-C")
            .arg(root.join("fixture"))
            .arg("LLVM-test"),
    )?;
    let pin = Source {
        url: "https://example.invalid/llvm.tar.gz".to_owned(),
        sha256: file_hash(&fixture)?,
        original_url: None,
        strip_components: 1,
    };
    let pins = Pins {
        versions: BTreeMap::new(),
        sources: BTreeMap::from([("llvm_binary".to_owned(), pin)]),
    };
    Ok((fixture, pins))
}

#[cfg(unix)]
#[test]
fn llvm_release_unpacks_only_its_members_and_drops_the_archive() -> Result<()> {
    let directory = Directory::new()?;
    let root = &directory.0;
    let (fixture, pins) = llvm_release_fixture(root)?;
    let sha256 = &pins.sources["llvm_binary"].sha256;
    let archive = root
        .join("target/downloads")
        .join(format!("{sha256}.tar.gz"));
    fs::create_dir_all(root.join("target/downloads"))?;
    fs::copy(&fixture, &archive)?;

    let prefix = source(root, &pins, "llvm_binary")?;
    assert_eq!(
        prefix,
        source_dir(root, "llvm_binary", &pins.sources["llvm_binary"])
    );
    assert!(prefix.starts_with(root.join("target/toolchain")));
    assert_eq!(
        fs::read_to_string(prefix.join("bin/clang-21"))?,
        "bin/clang-21"
    );
    assert!(prefix.join("lib/clang/21/include/stddef.h").is_file());
    assert!(!prefix.join("bin/flang").exists());
    assert!(!archive.exists());
    assert_eq!(source(root, &pins, "llvm_binary")?, prefix);

    // A full unpack records only the digest; its tree is replaced.
    fs::write(prefix.join(".unpacked"), sha256)?;
    fs::write(prefix.join("bin/flang"), "unused\n")?;
    fs::copy(&fixture, &archive)?;
    source(root, &pins, "llvm_binary")?;
    assert!(!prefix.join("bin/flang").exists());
    assert!(!archive.exists());
    Ok(())
}

#[test]
fn dependency_options_accept_alias_print_roots_and_reject_unknown_arguments() -> Result<()> {
    let args = ["--print-roots", "python-fallback", "--python-pgo=false"].map(String::from);
    assert_eq!(dependency_options(&args)?, ("python-fallback", false, true));
    assert_eq!(dependency_options(&[])?, ("all", !cfg!(windows), false));
    for args in [vec!["crt", "all"], vec!["--unknown"]] {
        let args: Vec<_> = args.into_iter().map(String::from).collect();
        assert!(dependency_options(&args).is_err());
    }
    Ok(())
}

#[test]
fn work_dirs_sit_beside_the_prefixes_of_their_target_not_inside_one() {
    let root = Path::new("/checkout");
    let work = work_dir(root, TARGET, "crt");
    assert_eq!(work, root.join("target/deps").join(TARGET).join("work/crt"));
    // Every prefix is `<label>-<digest>`, so no prefix is named `work`.
    let prefix = root.join("target/deps").join(TARGET).join("crt-0123");
    assert!(!work.starts_with(&prefix));
    assert_ne!(
        work_dir(root, "x86_64-unknown-linux-gnu", "crt"),
        work_dir(root, TARGET, "crt")
    );
    assert_ne!(work_dir(root, TARGET, "toolchain"), work);
}

#[test]
fn claimed_work_survives_its_own_key_and_is_emptied_for_another() -> Result<()> {
    let directory = Directory::new()?;
    let work = directory.0.join("work/crt");
    drop(claim_work(&work, Path::new("first"))?);
    fs::write(work.join("openssl.o"), "first")?;
    drop(claim_work(&work, Path::new("first"))?);
    assert_eq!(fs::read_to_string(work.join("openssl.o"))?, "first");
    drop(claim_work(&work, Path::new("second"))?);
    assert!(!work.join("openssl.o").exists());
    assert_eq!(fs::read_to_string(work.join(WORK_KEY))?, "second");
    Ok(())
}

#[test]
fn unmarked_work_is_emptied_before_it_is_claimed() -> Result<()> {
    let directory = Directory::new()?;
    let work = directory.0.join("work/toolchain");
    fs::create_dir_all(work.join("musl"))?;
    fs::write(work.join("musl/stale.o"), "stale")?;
    drop(claim_work(&work, Path::new("key"))?);
    assert!(!work.join("musl").exists());
    Ok(())
}

#[test]
fn claimed_work_excludes_other_handles_until_dropped() -> Result<()> {
    let directory = Directory::new()?;
    let work = directory.0.join("work/crt");
    let lock = claim_work(&work, Path::new("key"))?;
    let second = File::options()
        .read(true)
        .write(true)
        .open(work.with_extension("lock"))?;
    assert!(second.try_lock().is_err());
    drop(lock);
    second
        .try_lock()
        .map_err(|failure| error(failure.to_string()))?;
    Ok(())
}

#[test]
fn toolchain_roots_name_the_linux_scratch_and_the_profile_stage_it_builds() -> Result<()> {
    let root = stage_root(&["profile"])?;
    let mut tools = keying_toolchain();
    tools.prefix = root.0.join("target/toolchain/llvm");
    let roots = toolchain_roots(&root.0, &tools)?;
    let stages = root.0.join("target/deps").join(TARGET);
    let mut expected = Roots::default();
    expected.insert("toolchain", tools.prefix.clone());
    if cfg!(target_os = "linux") {
        let profile = stage_key(&root.0, "profile", &[], &[tools.digest.as_bytes()])?;
        expected.insert("profile", stages.join(format!("profile-{profile}")));
        expected.insert_work(&root.0, stages.join("work/profile"));
        expected.insert_work(&root.0, stages.join("work/toolchain"));
    }
    assert_eq!(roots, expected);
    Ok(())
}
