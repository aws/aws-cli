use super::*;
use options::{PythonLink, PythonPayload};
use std::collections::BTreeMap;

#[test]
fn uses_static_release_safe_with_pgo_by_default() -> Result<(), TaskError> {
    let build = options::parse(&[])?;
    assert_eq!(build.profile, "release-safe");
    assert_eq!(build.python_pgo, !cfg!(windows));
    assert_eq!(build.link_mode, LinkMode::Static);
    assert_eq!(build.python_link, PythonLink::Static);
    assert_eq!(build.python_payload, PythonPayload::Embedded);
    assert!(!build.frame_pointers);
    assert_eq!(build.strip, Some(false));
    Ok(())
}

#[test]
fn selects_release_small_without_pgo_and_rejects_foreign_targets() -> Result<(), TaskError> {
    let selected = options::parse(&[
        "--profile".into(),
        "release-small".into(),
        "--python-pgo=false".into(),
    ])?;
    assert_eq!(selected.profile, "release-small");
    assert!(!selected.python_pgo);
    assert!(options::parse(&["--target".into(), "unsupported-target".into()]).is_err());
    Ok(())
}

#[test]
fn stripping_defaults_follow_profile_and_explicit_options_win_in_either_order()
-> Result<(), TaskError> {
    for profile in ["dev", "release", "release-safe", "release-small"] {
        let flag = format!("--profile={profile}");
        assert_eq!(
            options::parse(std::slice::from_ref(&flag))?.strip,
            Some(profile == "release-small")
        );
        for strip in [true, false] {
            let choice = format!("--strip={strip}");
            for args in [
                [flag.clone(), choice.clone()],
                [choice.clone(), flag.clone()],
            ] {
                assert_eq!(options::parse(&args)?.strip, Some(strip));
            }
        }
    }
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn system_mode_defaults_to_dynamic_python_on_the_native_gnu_target() -> Result<(), TaskError> {
    let build = options::parse(&[
        "--link-mode=system".into(),
        "--python-payload=system".into(),
    ])?;
    assert_eq!(build.python_link, PythonLink::Dynamic);
    assert_eq!(build.python_payload, PythonPayload::System);
    assert_eq!(
        build.python_exe,
        std::path::PathBuf::from("/usr/bin/python3.14")
    );
    assert_eq!(
        build.target,
        format!("{}-unknown-linux-gnu", std::env::consts::ARCH)
    );
    Ok(())
}

#[test]
fn rejects_mixed_abis_and_payload_contracts_before_dependency_work() {
    for args in [
        vec!["--python-link=dynamic"],
        vec!["--python-payload=system"],
        vec!["--link-mode=system", "--python-link=static"],
        vec!["--crt-static-prefix=/tmp/crt"],
        vec!["--awscrt-source=/tmp/awscrt"],
        vec![
            "--link-mode=system",
            "--python-payload=system",
            "--awscrt-source=/tmp/awscrt",
        ],
        vec!["--link-mode=system", "--target=x86_64-unknown-linux-musl"],
        vec!["--cpu=bad cpu"],
        vec!["--strip=maybe"],
    ] {
        let args: Vec<_> = args.into_iter().map(str::to_owned).collect();
        assert!(options::parse(&args).is_err(), "{args:?}");
    }
}

#[test]
fn applies_strip_cpu_and_frame_pointer_choices_to_cargo() -> Result<(), TaskError> {
    let options = options::parse(&[
        "--strip=false".into(),
        "--cpu=native".into(),
        "--frame-pointers=true".into(),
    ])?;
    let mut command = Command::new("cargo");
    apply_codegen(&mut command, &options);
    let environment: std::collections::BTreeMap<_, _> = command
        .get_envs()
        .map(|(key, value)| {
            (
                key.to_string_lossy().into_owned(),
                value.map(|value| value.to_string_lossy().into_owned()),
            )
        })
        .collect();
    assert_eq!(
        environment["CARGO_PROFILE_RELEASE_SAFE_STRIP"].as_deref(),
        Some("none")
    );
    let flags = environment["CARGO_ENCODED_RUSTFLAGS"]
        .as_deref()
        .ok_or_else(|| TaskError::Message("missing flags".into()))?;
    assert!(flags.contains("-Cforce-frame-pointers=yes"));
    assert!(flags.contains("-Ctarget-cpu=native"));
    Ok(())
}

/// The flags `apply_codegen` appends to the caller's own, which it inherits.
fn appended_codegen_flags(options: &options::Options) -> Result<Vec<String>, TaskError> {
    let inherited = std::env::var("CARGO_ENCODED_RUSTFLAGS").unwrap_or_else(|_| {
        std::env::var("RUSTFLAGS")
            .unwrap_or_default()
            .split_whitespace()
            .collect::<Vec<_>>()
            .join("\x1f")
    });
    let mut command = Command::new("cargo");
    apply_codegen(&mut command, options);
    let flags = command
        .get_envs()
        .find(|(key, _)| *key == "CARGO_ENCODED_RUSTFLAGS")
        .and_then(|(_, value)| value)
        .and_then(|value| value.to_str())
        .ok_or_else(|| TaskError::Message("missing flags".into()))?;
    let appended = flags
        .strip_prefix(inherited.as_str())
        .ok_or_else(|| TaskError::Message("the caller's flags do not come first".into()))?;
    Ok(appended
        .split('\x1f')
        .filter(|flag| !flag.is_empty())
        .map(str::to_owned)
        .collect())
}

/// A default build names no CPU, so rustc targets its architecture's
/// baseline, and `--cpu=baseline`, which the system build passes, names
/// that baseline as the distro packages do.
#[test]
fn the_default_build_uses_the_architectures_baseline_cpu() -> Result<(), TaskError> {
    let default = appended_codegen_flags(&options::parse(&[])?)?;
    assert!(
        !default.iter().any(|flag| flag.starts_with("-Ctarget-cpu=")),
        "{default:?}"
    );
    let baseline = appended_codegen_flags(&options::parse(&["--cpu=baseline".into()])?)?;
    let cpu = if cfg!(target_arch = "x86_64") {
        "-Ctarget-cpu=x86-64"
    } else {
        "-Ctarget-cpu=generic"
    };
    assert!(baseline.iter().any(|flag| flag == cpu), "{baseline:?}");
    Ok(())
}

#[test]
fn parser_capture_executable_stays_outside_installable_artifacts() -> Result<(), TaskError> {
    let options = options::parse(&["--profile".into(), "dev".into()])?;
    let root = Path::new("/workspace");
    let capture = capture_executable(root, &options);
    assert!(capture.starts_with("/workspace/target/argparse/capture"));
    assert!(!capture.starts_with(root.join("target").join(&options.target)));
    Ok(())
}

#[test]
fn system_targets_accept_the_native_64_bit_little_endian_glibc_architectures()
-> Result<(), TaskError> {
    for (host, target) in [
        ("x86_64-unknown-linux-gnu", "x86_64-unknown-linux-gnu"),
        ("aarch64-unknown-linux-gnu", "aarch64-unknown-linux-gnu"),
        ("riscv64gc-unknown-linux-gnu", "riscv64gc-unknown-linux-gnu"),
        (
            "powerpc64le-unknown-linux-gnu",
            "powerpc64le-unknown-linux-gnu",
        ),
        (
            "loongarch64-unknown-linux-gnu",
            "loongarch64-unknown-linux-gnu",
        ),
    ] {
        let version = format!("rustc 1.96.0\nbinary: rustc\nhost: {host}\nrelease: 1.96.0\n");
        assert_eq!(options::system_target_from(&version)?, target);
    }
    for version in [
        "rustc 1.96.0\nrelease: 1.96.0\n",
        "host: x86_64-unknown-linux-musl\n",
        "host: armv7-unknown-linux-gnueabihf\n",
        "host: aarch64-apple-darwin\n",
        "host: x86_64-pc-windows-msvc\n",
    ] {
        assert!(options::system_target_from(version).is_err(), "{version}");
    }
    // A glibc host whose architecture the 64-bit bindings, ABI checks and
    // blackbox ELF reader cannot serve is named, with the ones they can.
    for host in [
        "i686-unknown-linux-gnu",
        "s390x-unknown-linux-gnu",
        "powerpc64-unknown-linux-gnu",
        "sparc64-unknown-linux-gnu",
    ] {
        let error = options::system_target_from(&format!("host: {host}\n"))
            .err()
            .map(|error| error.to_string());
        assert_eq!(
            error,
            Some(format!(
                "unsupported architecture: {host}; Linux/glibc builds support only \
                 the 64-bit little-endian x86_64, aarch64, riscv64gc, powerpc64le and \
                 loongarch64"
            ))
        );
    }
    Ok(())
}

#[test]
fn system_crt_accepts_only_print_roots() -> Result<(), TaskError> {
    let args = |values: &[&str]| {
        values
            .iter()
            .map(|value| (*value).to_owned())
            .collect::<Vec<_>>()
    };
    assert!(!system::crt_options(&[])?);
    assert!(system::crt_options(&args(&["--print-roots"]))?);
    assert!(system::crt_options(&args(&[
        "--print-roots",
        "--print-roots"
    ]))?);
    for rejected in [
        args(&["crt"]),
        args(&["--print-roots", "all"]),
        args(&["--python-pgo=false"]),
    ] {
        assert_eq!(
            system::crt_options(&rejected)
                .err()
                .map(|error| error.to_string()),
            Some("system-crt accepts only --print-roots".into()),
            "{rejected:?}"
        );
    }
    Ok(())
}

fn codegen_environment(args: &[&str]) -> Result<BTreeMap<String, Option<String>>, TaskError> {
    let args: Vec<_> = args.iter().copied().map(str::to_owned).collect();
    let mut command = Command::new("cargo");
    apply_codegen(&mut command, &options::parse(&args)?);
    Ok(command
        .get_envs()
        .map(|(key, value)| {
            (
                key.to_string_lossy().into_owned(),
                value.map(|value| value.to_string_lossy().into_owned()),
            )
        })
        .collect())
}

#[test]
fn unstripped_release_artifacts_keep_full_debug_info() -> Result<(), TaskError> {
    for args in [&[][..], &["--profile=release-safe", "--strip=false"][..]] {
        let safe = codegen_environment(args)?;
        assert_eq!(
            safe.get("CARGO_PROFILE_RELEASE_SAFE_STRIP"),
            Some(&Some("none".into())),
            "{args:?}"
        );
        assert_eq!(
            safe.get("CARGO_PROFILE_RELEASE_SAFE_DEBUG"),
            Some(&Some("full".into())),
            "{args:?}"
        );
    }
    let release = codegen_environment(&["--profile=release"])?;
    assert_eq!(
        release.get("CARGO_PROFILE_RELEASE_DEBUG"),
        Some(&Some("full".into()))
    );
    for args in [
        &["--profile=release-safe", "--strip=true"][..],
        &["--profile=release-small"][..],
        &["--profile=release-small", "--strip=true"][..],
        &["--profile=release", "--strip=true"][..],
        &["--profile=dev", "--strip=false"][..],
        &["--profile=dev"][..],
    ] {
        let environment = codegen_environment(args)?;
        assert!(
            !environment.keys().any(|key| key.ends_with("_DEBUG")),
            "{args:?}: {environment:?}"
        );
    }
    Ok(())
}

#[test]
fn run_without_a_separator_builds_with_every_option_and_runs_aws_without_arguments() {
    let args =
        |values: &[&str]| -> Vec<String> { values.iter().copied().map(str::to_owned).collect() };
    let empty: &[String] = &[];
    assert_eq!(split_run_args(&[]), (empty, empty));
    let options = args(&["--profile", "dev"]);
    assert_eq!(split_run_args(&options), (&options[..], empty));
    let separated = args(&["--profile", "dev", "--", "s3", "ls"]);
    assert_eq!(
        split_run_args(&separated),
        (&separated[..2], &separated[3..])
    );
    let nested = args(&["--", "s3", "--", "ls"]);
    assert_eq!(split_run_args(&nested), (empty, &nested[1..]));
    assert_eq!(split_run_args(&nested).1, args(&["s3", "--", "ls"]));
}
