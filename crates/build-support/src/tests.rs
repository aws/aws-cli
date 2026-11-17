use super::*;

#[test]
fn native_linux_allows_musl_and_glibc_on_the_same_architecture() -> io::Result<()> {
    for arch in ["x86_64", "aarch64"] {
        assert_eq!(
            NativeTarget::from_triples(
                &format!("{arch}-unknown-linux-gnu"),
                &format!("{arch}-unknown-linux-musl"),
            )?,
            NativeTarget::LinuxMusl
        );
    }
    Ok(())
}

#[test]
fn cross_platform_cross_architecture_and_unsupported_abis_are_rejected() {
    for (host, target) in [
        ("x86_64-unknown-linux-gnu", "aarch64-unknown-linux-musl"),
        ("aarch64-apple-darwin", "aarch64-unknown-linux-musl"),
        ("x86_64-unknown-linux-gnu", "x86_64-pc-windows-msvc"),
        ("x86_64-pc-windows-msvc", "x86_64-pc-windows-gnu"),
        ("i686-unknown-linux-musl", "i686-unknown-linux-musl"),
        ("s390x-unknown-linux-gnu", "s390x-unknown-linux-musl"),
        ("x86_64-unknown-linux-gnu", "s390x-unknown-linux-gnu"),
        ("riscv64gc-unknown-linux-gnu", "riscv64gc-apple-darwin"),
        ("x86_64-unknown-linux-gnux32", "x86_64-unknown-linux-gnux32"),
    ] {
        assert!(
            NativeTarget::from_triples(host, target).is_err(),
            "{host} -> {target}"
        );
    }
}

#[test]
fn native_glibc_system_builds_accept_the_64_bit_little_endian_architectures() -> io::Result<()> {
    for triple in [
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "riscv64gc-unknown-linux-gnu",
        "powerpc64le-unknown-linux-gnu",
        "loongarch64-unknown-linux-gnu",
    ] {
        assert_eq!(
            NativeTarget::from_triples(triple, triple)?,
            NativeTarget::LinuxGnu
        );
    }
    Ok(())
}

#[test]
fn native_glibc_system_builds_reject_32_bit_and_big_endian_architectures() {
    for triple in [
        "i686-unknown-linux-gnu",
        "i586-unknown-linux-gnu",
        "s390x-unknown-linux-gnu",
        "powerpc64-unknown-linux-gnu",
        "aarch64_be-unknown-linux-gnu",
        "sparc64-unknown-linux-gnu",
    ] {
        let error = NativeTarget::from_triples(triple, triple)
            .err()
            .map(|error| error.to_string());
        assert_eq!(
            error,
            Some(format!(
                "unsupported architecture: {triple}; Linux/glibc builds support only \
                 the 64-bit little-endian x86_64, aarch64, riscv64gc, powerpc64le and \
                 loongarch64"
            ))
        );
    }
}

#[test]
fn python_glue_is_a_builtin_core_module_only_for_static_python() {
    assert_eq!(python_linkage_c_flags(false), ["-DPy_BUILD_CORE_BUILTIN=1"]);
    assert!(python_linkage_c_flags(true).is_empty());
}

#[test]
fn needed_libraries_stay_in_dt_needed_under_rustc_as_needed() -> io::Result<()> {
    assert_eq!(
        needed_libraries_link_arg(["aws-c-s3", "python3.14"])?,
        "-Wl,--push-state,--no-as-needed,-laws-c-s3,-lpython3.14,--pop-state"
    );
    let all = needed_libraries_link_arg(CRT_LIBRARIES)?;
    for library in CRT_LIBRARIES {
        assert!(all.contains(&format!(",-l{library},")));
    }
    for invalid in ["", "a,b"] {
        assert!(needed_libraries_link_arg([invalid]).is_err());
    }
    Ok(())
}

#[test]
fn crt_libraries_are_the_aws_group_of_the_link_inventory() -> io::Result<()> {
    let inventory = std::fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../deps/crt-libraries.txt"),
    )?;
    let aws: Vec<_> = inventory
        .lines()
        .map(str::trim)
        .filter(|line| line.starts_with("aws-"))
        .collect();
    assert_eq!(aws, CRT_LIBRARIES);
    Ok(())
}

#[test]
fn object_formats_have_read_only_payloads_and_native_symbol_names() -> io::Result<()> {
    for (target, section, symbol, retention) in [
        (
            NativeTarget::LinuxMusl,
            ".section .pyload,\"a\"",
            "awscli",
            "-Wl,--undefined=",
        ),
        (
            NativeTarget::LinuxGnu,
            ".section .pyload,\"a\"",
            "awscli",
            "-Wl,--undefined=",
        ),
        (
            NativeTarget::Macos,
            ".section __DATA_CONST,__pyload",
            "_awscli",
            "-Wl,-u,_",
        ),
        (
            NativeTarget::WindowsMsvc,
            ".section .pyload,\"dr\"",
            "awscli",
            "/INCLUDE:",
        ),
    ] {
        let assembly = target.payload_assembly(Path::new("/work/payload.blob"))?;
        assert!(assembly.starts_with(section));
        assert!(assembly.contains(&format!(".global {symbol}_payload_start\n")));
        assert_eq!(assembly.matches(".incbin").count(), 1);
        assert!(target.payload_retention_flag().starts_with(retention));
        assert!(
            target
                .undefined_symbol_flag("PyOS_getsig")
                .starts_with(retention)
        );
    }
    assert_eq!(
        NativeTarget::Macos.undefined_symbol_flag("PyOS_getsig"),
        "-Wl,-u,_PyOS_getsig"
    );
    assert_eq!(
        NativeTarget::LinuxGnu.undefined_symbol_flag("PyOS_setsig"),
        "-Wl,--undefined=PyOS_setsig"
    );
    Ok(())
}

#[test]
fn payload_assembly_rejects_injected_directives_and_accepts_windows_separators() -> io::Result<()> {
    for path in ["a\"\n.incbin \"b", "a\r", "a\0b"] {
        assert!(
            NativeTarget::LinuxMusl
                .payload_assembly(Path::new(path))
                .is_err()
        );
    }
    assert!(
        NativeTarget::WindowsMsvc
            .payload_assembly(Path::new(r"C:\work\payload.blob"))?
            .contains(".incbin \"C:/work/payload.blob\"")
    );
    Ok(())
}
