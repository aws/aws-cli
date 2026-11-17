use super::*;
use std::path::PathBuf;
use std::process::Command;

/// The CRT's layout: the work tree `work/crt` beside the install prefix
/// `crt-<hash>`, which shares its `crt` stem.
fn roots(base: &Path) -> (PathBuf, PathBuf, PathBuf, PathBuf) {
    (
        base.join("sources/package it's"),
        base.join("work/crt/cmake/aws-c-common"),
        base.join("work/crt"),
        base.join("crt-0123"),
    )
}

#[test]
fn maps_are_ordered_broad_to_specific_with_separator_boundaries() -> Result<()> {
    let (source, build, work, install) = roots(Path::new("/store"));
    let flags = flags(&Roots {
        name: "aws-c-common",
        source: &source,
        build: &build,
        work: &work,
        install: &install,
    })?;
    assert_eq!(
        flags,
        [
            "-ffile-prefix-map=/store/work/crt/=crt-work/",
            "-ffile-prefix-map=/store/crt-0123/=crt-install/",
            "-ffile-prefix-map=/store/sources/package it's/=aws-c-common/",
            "-ffile-prefix-map=/store/work/crt/cmake/aws-c-common/=crt-build/aws-c-common/",
        ]
    );
    Ok(())
}

#[cfg(unix)]
#[test]
fn wrapper_preserves_each_map_argument_and_the_callers_arguments() -> Result<()> {
    // `printf` stands in for the compiler; its format is the first fixed argument.
    let fixed = [
        "<%s>\n".to_owned(),
        "-ffile-prefix-map=/a b/it's/=x/".to_owned(),
    ];
    let script = wrapper(Path::new("printf"), &fixed)?;
    assert!(script.starts_with("#!/bin/sh\nexec 'printf' "));
    let output = Command::new("sh")
        .arg("-c")
        .arg(script)
        .args(["sh", "-c", "$HOME"])
        .output()?;
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        "<-ffile-prefix-map=/a b/it's/=x/>\n<-c>\n<$HOME>\n"
    );
    Ok(())
}

// Compile real `__FILE__` expansions through the generated wrapper, with
// nested roots and a space, an apostrophe, and a literal backslash in the
// physical paths. The
// native suite supplies the managed compiler and must not skip this check.
#[cfg(target_os = "linux")]
#[test]
fn wrapper_maps_actual_compiler_filenames_for_every_root() -> Result<()> {
    let Some(compiler) = std::env::var_os("AWS_NATIVE_TEST_CC") else {
        assert!(
            std::env::var_os("AWS_NATIVE_CRT_PREFIX").is_none(),
            "the native suite must supply AWS_NATIVE_TEST_CC"
        );
        return Ok(());
    };
    let base = std::env::temp_dir().join(format!("crt-file-maps-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    let (source, build, work, install) = roots(&base.join("store it's\\x"));
    let maps = flags(&Roots {
        name: "aws-c-common",
        source: &source,
        build: &build,
        work: &work,
        install: &install,
    })?;
    let script = base.join("cc");
    std::fs::create_dir_all(&base)?;
    std::fs::write(&script, wrapper(Path::new(&compiler), &maps)?)?;
    let cases = [
        (&source, "aws-c-common"),
        (&build, "crt-build/aws-c-common"),
        (&work, "crt-work"),
        (&install.join("include"), "crt-install/include"),
    ];
    for (directory, logical) in cases {
        std::fs::create_dir_all(directory)?;
        let probe = directory.join("probe.c");
        std::fs::write(&probe, "__FILE__\n")?;
        // `sh` reads the wrapper, so no freshly written file is executed.
        let output = Command::new("sh")
            .arg(&script)
            .args(["-E", "-P", "-x", "c"])
            .arg(&probe)
            .output()?;
        assert!(output.status.success(), "{output:?}");
        assert_eq!(
            String::from_utf8_lossy(&output.stdout).trim(),
            format!("\"{logical}/probe.c\"")
        );
    }
    std::fs::remove_dir_all(&base)?;
    Ok(())
}

#[test]
fn posix_maps_keep_a_backslash_in_a_directory_name() -> Result<()> {
    if cfg!(windows) {
        return Ok(());
    }
    let source = Path::new("/tmp/a\\b/source\\");
    let maps = flags(&Roots {
        name: "aws-c-common",
        source,
        build: Path::new("/tmp/a\\b/build/"),
        work: Path::new("/tmp/a\\b"),
        install: Path::new("/tmp/a\\b"),
    })?;
    assert_eq!(
        maps,
        [
            "-ffile-prefix-map=/tmp/a\\b/=crt-work/",
            "-ffile-prefix-map=/tmp/a\\b/=crt-install/",
            "-ffile-prefix-map=/tmp/a\\b/build/=crt-build/aws-c-common/",
            "-ffile-prefix-map=/tmp/a\\b/source\\/=aws-c-common/",
        ]
    );
    Ok(())
}

#[test]
fn windows_maps_cover_both_separator_spellings_broadest_first() -> Result<()> {
    let source = Path::new("C:\\work tree\\crt\\work\\openssl\\source");
    let build = Path::new("C:\\work tree\\crt\\work\\openssl");
    let work = Path::new("C:\\work tree\\crt\\work");
    let install = Path::new("C:/work tree/crt");
    let maps = clang_cl_flags(&Roots {
        name: "openssl",
        source,
        build,
        work,
        install,
    })?;
    assert_eq!(
        maps,
        [
            "-ffile-prefix-map=C:\\work tree\\crt\\=crt-install/",
            "-ffile-prefix-map=C:/work tree/crt/=crt-install/",
            "-ffile-prefix-map=C:\\work tree\\crt\\work\\=crt-work/",
            "-ffile-prefix-map=C:/work tree/crt/work/=crt-work/",
            "-ffile-prefix-map=C:\\work tree\\crt\\work\\openssl\\=crt-build/openssl/",
            "-ffile-prefix-map=C:/work tree/crt/work/openssl/=crt-build/openssl/",
            "-ffile-prefix-map=C:\\work tree\\crt\\work\\openssl\\source\\=openssl/",
            "-ffile-prefix-map=C:/work tree/crt/work/openssl/source/=openssl/",
        ]
    );
    Ok(())
}

/// The options clang-cl derives from a `_CL_` value: quoted tokens, each
/// with its first `#` replaced by `=` (clang's `getCLEnvVarOptions`).
fn clang_cl_options(variable: &str) -> Vec<String> {
    variable
        .split('"')
        .skip(1)
        .step_by(2)
        .map(|option| option.replacen('#', "=", 1))
        .collect()
}

#[test]
fn windows_map_flags_retain_spaces_and_percent_signs() {
    let map = "-ffile-prefix-map=C:/package store/100%/=aws-c-common/";
    assert_eq!(windows_flags(&[map.to_owned()]), format!("\"{map}\""));
    assert_eq!(
        windows_flags(&[
            map.to_owned(),
            "-ffile-prefix-map=C:/w/=crt-work/".to_owned()
        ]),
        format!("\"{map}\" \"-ffile-prefix-map=C:/w/=crt-work/\"")
    );
}

#[test]
fn clang_cl_variable_survives_the_drivers_quoting_and_hash_rules() {
    let maps = [
        "-ffile-prefix-map=C:\\work #1 tree\\=crt-work/".to_owned(),
        "-ffile-prefix-map=C:/work #1 tree/=crt-work/".to_owned(),
        "-ffile-prefix-map=C:/package store/100%/=aws-c-common/".to_owned(),
    ];
    let variable = clang_cl_variable(&maps);
    assert_eq!(
        variable,
        "\"/clang:-ffile-prefix-map#C:\\work #1 tree\\=crt-work/\" \
         \"/clang:-ffile-prefix-map#C:/work #1 tree/=crt-work/\" \
         \"/clang:-ffile-prefix-map#C:/package store/100%/=aws-c-common/\""
    );
    assert_eq!(
        clang_cl_options(&variable),
        maps.iter()
            .map(|map| format!("/clang:{map}"))
            .collect::<Vec<_>>()
    );
}

// The `_CL_` maps must reach clang-cl's real `__FILE__` expansion. This
// regression can run only on a native Windows host.
#[cfg(windows)]
#[test]
fn clang_cl_variable_maps_actual_compiler_filenames() -> Result<()> {
    let Some(clang) = std::env::var_os("AWS_NATIVE_TEST_CLANG") else {
        assert!(
            std::env::var_os("AWS_NATIVE_CRT_PREFIX").is_none(),
            "the native suite must supply AWS_NATIVE_TEST_CLANG"
        );
        return Ok(());
    };
    let base = std::env::temp_dir().join(format!("openssl file #maps {}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    let source = base.join("openssl").join("source");
    std::fs::create_dir_all(&source)?;
    let probe = source.join("probe.c");
    std::fs::write(&probe, "__FILE__\n")?;
    let maps = clang_cl_flags(&Roots {
        name: "openssl",
        source: &source,
        build: &base.join("openssl"),
        work: &base,
        install: &base.join("install"),
    })?;
    let output = Command::new(Path::new(&clang).with_file_name("clang-cl.exe"))
        .env("_CL_", clang_cl_variable(&maps))
        .args(["/nologo", "/EP"])
        .arg(&probe)
        .output()?;
    std::fs::remove_dir_all(&base)?;
    assert!(output.status.success(), "{output:?}");
    // Clang spells a Windows filename with escaped backslashes.
    assert_eq!(
        String::from_utf8_lossy(&output.stdout)
            .trim()
            .replace("\\\\", "/"),
        "\"openssl/probe.c\""
    );
    Ok(())
}
