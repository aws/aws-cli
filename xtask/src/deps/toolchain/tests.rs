use super::*;
use std::ffi::OsStr;

#[test]
fn jobs_default_to_available_parallelism_capped_at_sixteen() -> Result<()> {
    assert_eq!(jobs_from(None, 4)?, 4);
    assert_eq!(jobs_from(None, 64)?, DEFAULT_JOBS_MAX);
    assert_eq!(
        jobs_from(Some(OsStr::new("default")), 64)?,
        DEFAULT_JOBS_MAX
    );
    Ok(())
}

#[test]
fn cargo_build_jobs_sets_an_explicit_limit() -> Result<()> {
    assert_eq!(jobs_from(Some(OsStr::new("2")), 64)?, 2);
    // An explicit limit is used as given, even above the available parallelism.
    assert_eq!(jobs_from(Some(OsStr::new("32")), 4)?, 32);
    // Negative counts leave processors idle, as in Cargo.
    assert_eq!(jobs_from(Some(OsStr::new("-1")), 8)?, 7);
    assert_eq!(jobs_from(Some(OsStr::new("-9")), 8)?, 1);
    Ok(())
}

#[test]
fn cargo_build_jobs_rejects_zero_and_text() {
    let failure = |value: &str| {
        jobs_from(Some(OsStr::new(value)), 8)
            .err()
            .map(|failure| failure.to_string())
            .unwrap_or_default()
    };
    assert_eq!(failure("0"), "CARGO_BUILD_JOBS may not be 0");
    for value in ["x", "", " 2", "2.5"] {
        assert!(
            failure(value).starts_with(&format!("could not parse CARGO_BUILD_JOBS `{value}`")),
            "{value}: {}",
            failure(value)
        );
    }
}

#[test]
fn missing_rust_runtime_names_the_pinned_rust_version() {
    let root = std::env::temp_dir().join(format!("awscli-missing-rust-{}", std::process::id()));
    let message = copy_rust_runtime(&root, "9.8.7", &root.join("prefix"))
        .err()
        .map(|failure| failure.to_string())
        .unwrap_or_default();
    let _ = fs::remove_dir_all(&root);
    assert!(
        message.starts_with("cannot copy Rust 9.8.7 libunwind "),
        "{message}"
    );
    assert!(
        message.ends_with(&format!("; install its {TARGET} target")),
        "{message}"
    );
}

/// A clang that prints each argument it gets on its own line.
#[cfg(unix)]
const PRINT_ARGUMENTS: &str = "#!/bin/sh\nprintf '%s\\n' \"$@\"\n";

/// A `bin/link` in a fresh `name` directory, whose clang is the shell
/// script `clang`. Its allowlist keeps `PATH` and `TMPDIR`, and names a
/// Windows variable sh can't read.
#[cfg(unix)]
fn stub_link_driver(name: &str, clang: &str) -> Result<(PathBuf, PathBuf)> {
    let directory = std::env::temp_dir().join(format!("awscli-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&directory);
    fs::create_dir_all(&directory)?;
    let mut tools = crate::deps::keying_toolchain();
    tools.prefix.clone_from(&directory);
    tools.clang = directory.join("clang");
    write_executable(&tools.clang, clang)?;
    let link = link_driver(&directory);
    let allowlist = "# Tool discovery.\nPATH\n\nTMPDIR\nProgramFiles(x86)\n";
    write_executable(&link, &link_script(&tools, allowlist)?)?;
    Ok((directory, link))
}

/// `bin/link` refuses Rust's bundled musl, named directly or on any line of
/// an `@file`, and hands every other argument to clang.
#[cfg(unix)]
#[test]
fn link_driver_refuses_rusts_bundled_musl() -> Result<()> {
    let (directory, link) = stub_link_driver("link-driver", PRINT_ARGUMENTS)?;
    // The last line has no newline, as an `@file` need not end in one.
    let bundled = directory.join("bundled");
    fs::write(&bundled, "-lc\n/rust/lib/self-contained/libc.a")?;
    let managed = directory.join("managed");
    fs::write(&managed, "-lunwind\n-lc\n")?;
    let run = |argument: &str| Command::new(&link).arg(argument).output();
    for refused in [
        "/rust/lib/self-contained/rcrt1.o".to_owned(),
        format!("@{}", bundled.display()),
    ] {
        let output = run(&refused)?;
        assert!(!output.status.success(), "{refused}");
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("names Rust's bundled musl"),
            "{refused}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let output = run(&format!("@{}", managed.display()))?;
    assert!(output.status.success());
    let forwarded = String::from_utf8_lossy(&output.stdout);
    let copy = format!("{}.static-pie", managed.display());
    assert!(
        forwarded.lines().any(|line| line == format!("@{copy}")),
        "{forwarded}"
    );
    assert_eq!(fs::read_to_string(&copy)?, "-lunwind\n-lc\n");
    assert!(forwarded.contains("--sysroot="), "{forwarded}");
    fs::remove_dir_all(&directory)?;
    Ok(())
}

/// `bin/link` replaces the `-no-pie` rustc passes for a fixed-address link,
/// directly or on a line of an `@file`, with `-static-pie`, and keeps every
/// other argument as it is.
#[cfg(unix)]
#[test]
fn link_driver_links_a_static_pie_where_rustc_asks_for_a_fixed_address() -> Result<()> {
    let (directory, link) = stub_link_driver("link-driver-pie", PRINT_ARGUMENTS)?;
    // rustc escapes spaces in an `@file`, and its last line need not end in
    // a newline.
    let arguments = directory.join("linker-arguments");
    fs::write(&arguments, "-static\n-no-pie\nwith\\ space.o\n-no-pie")?;
    let output = Command::new(&link)
        .args(["-static", "-no-pie", "-o", "hello"])
        .arg(format!("@{}", arguments.display()))
        .output()?;
    assert!(output.status.success());
    let forwarded = String::from_utf8_lossy(&output.stdout);
    let copy = format!("{}.static-pie", arguments.display());
    let copy_argument = format!("@{copy}");
    let lines: Vec<&str> = forwarded.lines().collect();
    assert!(
        lines.ends_with(&["-static", "-static-pie", "-o", "hello", &copy_argument]),
        "{forwarded}"
    );
    assert!(!lines.contains(&"-no-pie"), "{forwarded}");
    assert_eq!(
        fs::read_to_string(&copy)?,
        "-static\n-static-pie\nwith\\ space.o\n-static-pie\n"
    );
    fs::remove_dir_all(&directory)?;
    Ok(())
}

/// `bin/link` runs clang with only the allowlist's variables and
/// `LC_ALL=C`, so a caller's `COMPILER_PATH` or `LIBRARY_PATH` can't pick
/// its linker or libraries.
#[cfg(unix)]
#[test]
fn link_driver_runs_clang_in_the_tool_environment() -> Result<()> {
    let (directory, link) = stub_link_driver(
        "link-driver-environment",
        concat!(
            "#!/bin/sh\nprintf '%s=%s\\n' ",
            "COMPILER_PATH \"${COMPILER_PATH-unset}\" LIBRARY_PATH \"${LIBRARY_PATH-unset}\" ",
            "TMPDIR \"${TMPDIR-unset}\" LC_ALL \"${LC_ALL-unset}\"\n",
        ),
    )?;
    let output = Command::new(&link)
        .env("COMPILER_PATH", &directory)
        .env("LIBRARY_PATH", &directory)
        .env("TMPDIR", &directory)
        .env("LC_ALL", "en_US.UTF-8")
        .output()?;
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        format!(
            "COMPILER_PATH=unset\nLIBRARY_PATH=unset\nTMPDIR={}\nLC_ALL=C\n",
            directory.display()
        )
    );
    fs::remove_dir_all(&directory)?;
    Ok(())
}

#[test]
fn static_elf_check_rejects_needed_libraries_before_the_dynamic_end() {
    let entry = |tag: u64| [tag.to_le_bytes(), 0_u64.to_le_bytes()].concat();
    let needed = [entry(5), entry(DT_NEEDED), entry(DT_NULL)].concat();
    assert!(assert_no_needed(&needed, 0, 48).is_err());
    let ended = [entry(5), entry(DT_NULL), entry(DT_NEEDED)].concat();
    assert!(assert_no_needed(&ended, 0, 48).is_ok());
    // A dynamic section past the end of the file is truncated.
    assert!(assert_no_needed(&ended, 1024, 48).is_err());
}

/// The value `command` sets for `name`, if it sets one.
fn set_variable(command: &Command, name: &str) -> Option<String> {
    command
        .get_envs()
        .find(|(key, _)| *key == name)
        .and_then(|(_, value)| value)
        .map(|value| value.to_string_lossy().into_owned())
}

#[test]
fn apply_link_appends_the_link_flags_to_the_flags_cargo_reads() {
    let mut tools = crate::deps::keying_toolchain();
    tools.link = Some(PathBuf::from("/managed/bin/link"));
    let link_flags = RUST_LINK_FLAGS.join("\x1f");

    // Without the encoded variables, Cargo splits the plain ones on
    // whitespace.
    let mut command = Command::new("cargo");
    command
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env("RUSTFLAGS", " -Ctarget-cpu=x86-64  -Cdebuginfo=1 ")
        .env_remove("CARGO_ENCODED_RUSTDOCFLAGS")
        .env_remove("RUSTDOCFLAGS");
    tools.apply_link(&mut command);
    assert_eq!(
        set_variable(&command, "CARGO_ENCODED_RUSTFLAGS"),
        Some(format!(
            "-Ctarget-cpu=x86-64\x1f-Cdebuginfo=1\x1f{link_flags}"
        ))
    );
    // Doctests link with the rustdocflags.
    assert_eq!(
        set_variable(&command, "CARGO_ENCODED_RUSTDOCFLAGS"),
        Some(link_flags.clone())
    );
    assert_eq!(
        set_variable(&command, &linker_variable()).as_deref(),
        Some("/managed/bin/link")
    );

    // An encoded variable wins over its plain one, as it does for Cargo.
    let mut command = Command::new("cargo");
    command
        .env("CARGO_ENCODED_RUSTFLAGS", "-Cforce-frame-pointers=yes")
        .env("RUSTFLAGS", "-Cignored")
        .env("CARGO_ENCODED_RUSTDOCFLAGS", "")
        .env("RUSTDOCFLAGS", "-Cignored");
    tools.apply_link(&mut command);
    assert_eq!(
        set_variable(&command, "CARGO_ENCODED_RUSTFLAGS"),
        Some(format!("-Cforce-frame-pointers=yes\x1f{link_flags}"))
    );
    assert_eq!(
        set_variable(&command, "CARGO_ENCODED_RUSTDOCFLAGS"),
        Some(link_flags)
    );
}

#[test]
fn apply_link_leaves_a_toolchain_without_a_link_driver_alone() {
    let tools = crate::deps::keying_toolchain();
    let mut command = Command::new("cargo");
    tools.apply_link(&mut command);
    assert_eq!(command.get_envs().count(), 0);
}

#[cfg(target_os = "linux")]
#[test]
fn the_linker_variable_names_the_musl_target() {
    assert_eq!(
        linker_variable(),
        format!(
            "CARGO_TARGET_{}_UNKNOWN_LINUX_MUSL_LINKER",
            std::env::consts::ARCH.to_uppercase()
        )
    );
}
