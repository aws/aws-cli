use super::*;
use crate::deps::Pins;
use crate::deps::tests::test_root;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

/// Every label `stage_files` accepts.
const STAGES: &[&str] = &[
    "openssl",
    "zlib-xz",
    "crt",
    "toolchain",
    "profile",
    "python-support",
    "cpython",
    "fallback-archive",
    "fallback-payload",
    "fallback-runtime",
    "fallback",
];

/// Every native host a stage builds on, as `std::env::consts` names it.
const HOSTS: &[(&str, &str)] = &[
    ("linux", "x86_64"),
    ("linux", "aarch64"),
    ("macos", "x86_64"),
    ("macos", "aarch64"),
    ("windows", "x86_64"),
];

/// The files that key `label` on any host.
fn all_files(label: &str) -> Result<BTreeSet<&'static str>> {
    let parts = parts(label)?;
    Ok(HOSTS
        .iter()
        .flat_map(|(os, arch)| host_inputs(parts, os, arch))
        .collect())
}

/// The pins that key `label` on any host.
fn all_pins(label: &str) -> Result<BTreeSet<&'static str>> {
    let parts = pin_parts(label)?;
    Ok(HOSTS
        .iter()
        .flat_map(|(os, arch)| host_inputs(parts, os, arch))
        .collect())
}

fn verify_inventory(label: &str, required: &[&str]) -> Result<()> {
    let files = stage_files(label)?;
    let root = test_root()?;
    assert_eq!(
        files.len(),
        files.iter().copied().collect::<BTreeSet<_>>().len()
    );
    for file in &all_files(label)? {
        assert!(root.join(file).is_file(), "{label}: missing input {file}");
        assert!(
            !file.ends_with("/tests.rs"),
            "test code is not a build input"
        );
    }
    for expected in required {
        assert!(files.contains(expected), "{label}: missing {expected}");
    }
    Ok(())
}

/// The drivers' shared modules, which every stage that runs one covers.
const PYTHON_SHARED: &[&str] = &[
    "xtask/src/python/stage.rs",
    "deps/scripts/build_environ.py",
    "deps/scripts/build_guard.py",
    "deps/scripts/native_target.py",
    "deps/scripts/tool_environ.txt",
];

/// The inputs the OpenSSL, zlib/xz, and CRT stages cover: the commands
/// they run and the compiler-side code they share.
const CRT_SHARED: &[&str] = &[
    "xtask/src/deps/crt/source_paths.rs",
    "xtask/src/deps/command.rs",
    "xtask/src/deps/files.rs",
    "xtask/src/deps/platform.rs",
    "deps/scripts/tool_environ.txt",
];

#[test]
fn crt_inventory_covers_its_builder_and_libraries() -> Result<()> {
    verify_inventory(
        "crt",
        &[
            CRT_SHARED,
            &[
                "xtask/src/deps/crt.rs",
                "xtask/src/deps/crt/cmake.rs",
                "deps/crt-libraries.txt",
            ],
        ]
        .concat(),
    )?;
    // The CRT follows the toolchain's code through the toolchain digest,
    // and OpenSSL's and zlib/xz's through their keys.
    let files = all_files("crt")?;
    for excluded in [
        "xtask/src/deps/toolchain.rs",
        "xtask/src/deps/crt/openssl.rs",
        "xtask/src/deps/crt/zlib_xz.rs",
    ] {
        assert!(!files.contains(excluded), "crt: {excluded}");
    }
    assert!(
        !files
            .iter()
            .any(|file| file.starts_with("xtask/src/python"))
    );
    Ok(())
}

#[test]
fn openssl_inventory_covers_its_builder_without_the_crt() -> Result<()> {
    verify_inventory(
        "openssl",
        &[CRT_SHARED, &["xtask/src/deps/crt/openssl.rs"]].concat(),
    )?;
    // An AWS C library, zlib/xz, CMake driver, or CRT inventory edit never
    // rebuilds OpenSSL.
    let files = all_files("openssl")?;
    for excluded in [
        "xtask/src/deps/crt.rs",
        "xtask/src/deps/crt/cmake.rs",
        "xtask/src/deps/crt/zlib_xz.rs",
        "deps/crt-libraries.txt",
        "xtask/src/deps/toolchain.rs",
    ] {
        assert!(!files.contains(excluded), "openssl: {excluded}");
    }
    Ok(())
}

#[test]
fn zlib_xz_inventory_covers_its_builder_without_the_crt() -> Result<()> {
    verify_inventory(
        "zlib-xz",
        &[
            CRT_SHARED,
            &[
                "xtask/src/deps/crt/cmake.rs",
                "xtask/src/deps/crt/zlib_xz.rs",
            ],
        ]
        .concat(),
    )?;
    // An AWS C library, OpenSSL, or CRT inventory edit never rebuilds
    // zlib/xz, and so never reaches CPython through it.
    let files = all_files("zlib-xz")?;
    for excluded in [
        "xtask/src/deps/crt.rs",
        "xtask/src/deps/crt/openssl.rs",
        "deps/crt-libraries.txt",
        "xtask/src/deps/toolchain.rs",
    ] {
        assert!(!files.contains(excluded), "zlib-xz: {excluded}");
    }
    Ok(())
}

#[test]
fn toolchain_inventory_covers_compiler_runtime_builder() -> Result<()> {
    let linux: &[&str] = if cfg!(target_os = "linux") {
        &[
            "xtask/src/deps/toolchain/compiler_runtime.rs",
            "xtask/src/deps/llvm.rs",
        ]
    } else {
        &["xtask/src/deps/toolchain/native.rs"]
    };
    verify_inventory(
        "toolchain",
        &[
            &[
                "xtask/src/deps/toolchain.rs",
                "xtask/src/deps/command.rs",
                "xtask/src/deps/files.rs",
            ],
            linux,
        ]
        .concat(),
    )
}

/// Assert whether each of `inputs` is `listed`, naming `host` on failure.
fn assert_lists(listed: &[&str], inputs: &[&str], expected: bool, host: &str) {
    for input in inputs {
        assert_eq!(listed.contains(input), expected, "{host}: {input}");
    }
}

#[test]
fn the_linux_toolchain_keys_on_the_profile_runtime_it_installs() -> Result<()> {
    let linux = host_inputs(parts("toolchain")?, "linux", "x86_64");
    assert_lists(
        &linux,
        &[PROFILE, PYTHON_SHARED, LINUX_TOOLCHAIN].concat(),
        true,
        "linux",
    );
    assert_lists(&linux, &[MSVC, NATIVE_TOOLCHAIN].concat(), false, "linux");
    // The CPython, support, and fallback code never keys the toolchain.
    let python: Vec<&str> = [SUPPORT, CPYTHON, FALLBACK, FALLBACK_DRIVER]
        .concat()
        .into_iter()
        .filter(|file| !COMMANDS.contains(file))
        .collect();
    assert_lists(&linux, &python, false, "linux");
    Ok(())
}

#[test]
fn the_other_toolchains_key_only_on_tool_discovery() -> Result<()> {
    for (os, arch) in [("macos", "aarch64"), ("windows", "x86_64")] {
        let files = host_inputs(parts("toolchain")?, os, arch);
        assert_lists(&files, NATIVE_TOOLCHAIN, true, os);
        assert_lists(&files, MSVC, os == "windows", os);
        assert_lists(&files, &[PROFILE, LINUX_TOOLCHAIN].concat(), false, os);
    }
    Ok(())
}

#[test]
fn cpython_inventory_covers_interpreter_and_support_builders() -> Result<()> {
    verify_inventory(
        "cpython",
        &[
            PYTHON_SHARED,
            &[
                "xtask/src/python/interpreter.rs",
                "xtask/src/python/support.rs",
                "xtask/src/deps/files.rs",
                "deps/scripts/build_cpython.py",
                "deps/scripts/build_cpython_windows.py",
                "deps/scripts/build_python_deps.py",
                "deps/scripts/payload_sysconfig.py",
                "deps/scripts/profile_aws.py",
                "deps/cpython-linux-pyconfig.h",
            ],
        ]
        .concat(),
    )?;
    // Only Linux PGO builds the managed profile runtime for the interpreter.
    let parts = parts("cpython")?;
    assert!(host_inputs(parts, "linux", "aarch64").contains(&"deps/scripts/build_pgo_tools.py"));
    assert!(!host_inputs(parts, "macos", "aarch64").contains(&"deps/scripts/build_pgo_tools.py"));
    verify_inventory(
        "python-support",
        &[
            PYTHON_SHARED,
            &[
                "xtask/src/python/support.rs",
                "deps/scripts/build_python_deps.py",
            ],
        ]
        .concat(),
    )?;
    assert!(!all_files("python-support")?.contains("xtask/src/python/interpreter.rs"));
    Ok(())
}

#[test]
fn profile_inventory_covers_its_driver_and_shared_inputs() -> Result<()> {
    verify_inventory(
        "profile",
        &[
            PYTHON_SHARED,
            &[
                "xtask/src/python/profile.rs",
                "deps/scripts/build_pgo_tools.py",
            ],
        ]
        .concat(),
    )
}

/// The inputs every fallback phase covers.
const FALLBACK_SHARED: &[&str] = &[
    "xtask/src/python/stage.rs",
    "xtask/src/python/fallback.rs",
    "deps/scripts/prepare_python_fallback.py",
    "deps/scripts/build_environ.py",
    "deps/scripts/build_guard.py",
    "deps/scripts/tool_environ.txt",
];

const RUNTIME_SOURCE: &str = "crates/python-fallback/python/runtime.py";
const RUNTIME_LOCKS: &[&str] = &[
    "aws-cli/requirements/download-deps/system-sandbox-lock.txt",
    "aws-cli/requirements/download-deps/system-sandbox-win-lock.txt",
];

#[test]
fn fallback_archive_inventory_covers_generators_without_payload_or_runtime() -> Result<()> {
    verify_inventory(
        "fallback-archive",
        &[
            FALLBACK_SHARED,
            &[
                "deps/scripts/gen_inittab.py",
                "deps/scripts/gen_frozen_bootstrap.py",
            ],
        ]
        .concat(),
    )?;
    let files = stage_files("fallback-archive")?;
    for excluded in RUNTIME_LOCKS.iter().chain([&RUNTIME_SOURCE]) {
        assert!(!files.contains(excluded), "archive: {excluded}");
    }
    Ok(())
}

#[test]
fn fallback_payload_inventory_covers_packer_and_locks_without_runtime() -> Result<()> {
    verify_inventory(
        "fallback-payload",
        &[
            FALLBACK_SHARED,
            RUNTIME_LOCKS,
            &["deps/scripts/gen_ac_index.py", "deps/scripts/pack.py"],
        ]
        .concat(),
    )?;
    assert!(!stage_files("fallback-payload")?.contains(&RUNTIME_SOURCE));
    Ok(())
}

#[test]
fn fallback_runtime_inventory_covers_bootstrap_without_payload_inputs() -> Result<()> {
    verify_inventory(
        "fallback-runtime",
        &[FALLBACK_SHARED, &[RUNTIME_SOURCE]].concat(),
    )?;
    let files = stage_files("fallback-runtime")?;
    for excluded in RUNTIME_LOCKS.iter().chain(&["deps/scripts/pack.py"]) {
        assert!(!files.contains(excluded), "runtime: {excluded}");
    }
    Ok(())
}

#[test]
fn published_fallback_inventory_covers_only_its_linking_code() -> Result<()> {
    verify_inventory(
        "fallback",
        &["xtask/src/python/stage.rs", "xtask/src/python/fallback.rs"],
    )?;
    assert!(!stage_files("fallback")?.contains(&RUNTIME_SOURCE));
    Ok(())
}

#[test]
fn fallback_stages_follow_the_interpreter_through_its_prefix() -> Result<()> {
    // The interpreter prefix in their keys carries CPython's own key, and a
    // caller-supplied prefix is keyed by its path.
    for label in [
        "fallback-archive",
        "fallback-payload",
        "fallback-runtime",
        "fallback",
    ] {
        let files = all_files(label)?;
        for file in CPYTHON.iter().chain(SUPPORT).chain(PROFILE) {
            if !COMMANDS.contains(file) {
                assert!(!files.contains(file), "{label}: {file}");
            }
        }
    }
    Ok(())
}

/// Files under the dependency build's directories that key no stage, and why.
const UNKEYED_FILES: &[&str] = &[
    // Sequences the stages, checks and fetches the pins, and computes the
    // keys. Sources are identified by their pinned digests.
    "xtask/src/deps/mod.rs",
    // This inventory; the tests here check it instead.
    "xtask/src/deps/inputs.rs",
    // Names the prefixes the stages compute and prunes the others.
    "xtask/src/deps/roots.rs",
    // Locates the store the prefixes live in and removes unused entries. A
    // prefix's location is its path, never an input of its key.
    "xtask/src/deps/store.rs",
    // The system-mode CRT is not a stage; `system_crt::build` keys itself.
    "xtask/src/deps/system_crt.rs",
    // Sequences the Python stages.
    "xtask/src/python.rs",
    // The checks tests/deps/test_build_checks.py stages beside the drivers.
    "deps/scripts/check_build_environ.py",
    "deps/scripts/check_build_guard.py",
    // Package, system-mode, and consumer tools that no stage runs.
    "deps/scripts/prepare_system_python.py",
    "deps/scripts/probe_system_python.py",
    "deps/scripts/validate_bytecode_metadata.py",
];

/// Every non-test file below `directory`, relative to `root`.
fn tree_files(root: &Path, directory: &str, files: &mut Vec<String>) -> Result<()> {
    for entry in fs::read_dir(root.join(directory))? {
        let entry = entry?;
        let relative = format!("{directory}/{}", entry.file_name().to_string_lossy());
        if entry.file_type()?.is_dir() {
            if entry.file_name() != "__pycache__" {
                tree_files(root, &relative, files)?;
            }
        } else if !relative.ends_with("/tests.rs") && !relative.ends_with(".pyc") {
            files.push(relative);
        }
    }
    Ok(())
}

#[test]
fn every_build_module_and_driver_keys_a_stage_or_is_named_unkeyed() -> Result<()> {
    let root = test_root()?;
    let mut files = vec!["xtask/src/python.rs".to_owned()];
    for directory in ["xtask/src/deps", "xtask/src/python", "deps/scripts"] {
        tree_files(root, directory, &mut files)?;
    }
    let mut keyed = BTreeSet::new();
    for label in STAGES {
        keyed.extend(all_files(label)?);
    }
    for file in &files {
        let unkeyed = UNKEYED_FILES.contains(&file.as_str());
        assert!(
            keyed.contains(file.as_str()) != unkeyed,
            "{file} must key a stage or be named in UNKEYED_FILES, not both"
        );
    }
    for file in UNKEYED_FILES {
        assert!(root.join(file).is_file(), "unkeyed {file} does not exist");
    }
    Ok(())
}

#[test]
fn orchestration_keys_no_stage_on_any_host() -> Result<()> {
    for label in STAGES {
        let files = all_files(label)?;
        for orchestration in [
            "deps/pins.toml",
            "xtask/src/deps/mod.rs",
            "xtask/src/deps/inputs.rs",
            "xtask/src/python.rs",
            "xtask/src/process.rs",
            "xtask/src/file_lock.rs",
        ] {
            assert!(!files.contains(orchestration), "{label}: {orchestration}");
        }
    }
    Ok(())
}

/// The file each module name a stage's code can spell refers to. The
/// command helpers are re-exported through `deps`, so their names stand for
/// their module too.
const MODULES: &[(&str, &str)] = &[
    ("command::", "xtask/src/deps/command.rs"),
    ("tool_command", "xtask/src/deps/command.rs"),
    ("write_executable", "xtask/src/deps/command.rs"),
    ("shell_quote", "xtask/src/deps/command.rs"),
    ("ninja_program", "xtask/src/deps/command.rs"),
    ("files::", "xtask/src/deps/files.rs"),
    ("copy_tree", "xtask/src/deps/files.rs"),
    ("CopyMode", "xtask/src/deps/files.rs"),
    ("platform::", "xtask/src/deps/platform.rs"),
    ("llvm::", "xtask/src/deps/llvm.rs"),
    ("msvc::", "xtask/src/deps/msvc.rs"),
    ("capture::", "xtask/src/deps/msvc/capture.rs"),
    ("source_paths::", "xtask/src/deps/crt/source_paths.rs"),
    ("openssl::", "xtask/src/deps/crt/openssl.rs"),
    ("cmake::", "xtask/src/deps/crt/cmake.rs"),
    ("zlib_xz::", "xtask/src/deps/crt/zlib_xz.rs"),
    ("toolchain::", "xtask/src/deps/toolchain.rs"),
    (
        "compiler_runtime::",
        "xtask/src/deps/toolchain/compiler_runtime.rs",
    ),
    ("native::", "xtask/src/deps/toolchain/native.rs"),
    ("stage::", "xtask/src/python/stage.rs"),
    ("DRIVER_TARGET", "xtask/src/python/stage.rs"),
    ("profile::", "xtask/src/python/profile.rs"),
    ("python::profile", "xtask/src/python/profile.rs"),
    ("support::", "xtask/src/python/support.rs"),
    ("interpreter::", "xtask/src/python/interpreter.rs"),
    ("PYTHON_ABI", "xtask/src/python/interpreter.rs"),
    ("fallback::", "xtask/src/python/fallback.rs"),
];

/// The module references a stage's code makes without keying on the module,
/// and why.
const FOLLOWED_MODULES: &[(&str, &str)] = &[
    // The CRT runs the toolchain's `jobs`, which never changes an output,
    // and its tools, whose code reaches it through the toolchain digest.
    ("crt", "xtask/src/deps/toolchain.rs"),
    ("openssl", "xtask/src/deps/toolchain.rs"),
    ("zlib-xz", "xtask/src/deps/toolchain.rs"),
    // The CRT builds the OpenSSL and zlib/xz stages and keys on their keys,
    // which an edit to either changes.
    ("crt", "xtask/src/deps/crt/openssl.rs"),
    ("crt", "xtask/src/deps/crt/zlib_xz.rs"),
    // The fallback phases pass `PYTHON_ABI` to their driver. `check_pins`
    // ties it to `python_version`, which keys the managed CPython prefix
    // each phase keys on, so an ABI change already rekeys them.
    ("fallback-archive", "xtask/src/python/interpreter.rs"),
    ("fallback-payload", "xtask/src/python/interpreter.rs"),
    ("fallback-runtime", "xtask/src/python/interpreter.rs"),
    ("fallback", "xtask/src/python/interpreter.rs"),
];

/// Whether `text` uses `name`, as a whole identifier or path prefix.
fn mentions(text: &str, name: &str) -> bool {
    text.match_indices(name).any(|(index, _)| {
        !text[..index]
            .chars()
            .next_back()
            .is_some_and(|before| before.is_alphanumeric() || before == '_')
    })
}

#[test]
fn every_module_a_stage_runs_is_in_its_inventory() -> Result<()> {
    let root = test_root()?;
    for label in STAGES {
        let files = all_files(label)?;
        for file in files.iter().filter(|file| file.ends_with(".rs")) {
            let text = fs::read_to_string(root.join(file))?;
            for (name, module) in MODULES {
                if mentions(&text, name) && !FOLLOWED_MODULES.contains(&(label, module)) {
                    assert!(
                        files.contains(module),
                        "{label}: {file} uses {name} from unlisted {module}"
                    );
                }
            }
        }
    }
    Ok(())
}

/// The sibling modules a driver imports.
fn script_imports(text: &str) -> Vec<String> {
    text.lines()
        .filter_map(|line| {
            let line = line.trim_start();
            let rest = line
                .strip_prefix("from ")
                .or_else(|| line.strip_prefix("import "))?;
            let module = rest.split([' ', ',', '.']).next()?;
            Some(format!("deps/scripts/{module}.py"))
        })
        .collect()
}

/// The scripts the `.rs` files among `files` run through `driver`.
fn driver_scripts(root: &Path, files: &BTreeSet<&str>) -> Result<Vec<String>> {
    let call = "driver(root, \"";
    let mut scripts = Vec::new();
    for file in files.iter().filter(|file| file.ends_with(".rs")) {
        let text = fs::read_to_string(root.join(file))?;
        for (index, _) in text.match_indices(call) {
            let name = text[index + call.len()..].split('"').next();
            scripts.push(format!("deps/scripts/{}", name.unwrap_or_default()));
        }
    }
    Ok(scripts)
}

#[test]
fn every_driver_a_stage_runs_is_in_its_inventory() -> Result<()> {
    let root = test_root()?;
    // The published stage only links the phases' outputs.
    for label in STAGES.iter().filter(|label| **label != "fallback") {
        let files = all_files(label)?;
        for script in driver_scripts(root, &files)? {
            assert!(files.contains(script.as_str()), "{label}: {script}");
        }
    }
    Ok(())
}

#[test]
fn every_module_a_listed_driver_imports_is_in_its_inventory() -> Result<()> {
    let root = test_root()?;
    for label in STAGES {
        let files = all_files(label)?;
        let drivers = files
            .iter()
            .filter(|file| file.starts_with("deps/scripts/") && file.ends_with(".py"));
        for file in drivers {
            let imports = script_imports(&fs::read_to_string(root.join(file))?);
            for import in imports.iter().filter(|import| root.join(import).is_file()) {
                assert!(
                    files.contains(import.as_str()),
                    "{label}: {file} imports unlisted {import}"
                );
            }
        }
    }
    Ok(())
}

#[test]
fn script_imports_name_sibling_modules() {
    let text = "import argparse\nfrom build_environ import tool_environ\n\
                import build_cpython_windows\nfrom payload_sysconfig import (\n";
    assert_eq!(
        script_imports(text),
        [
            "deps/scripts/argparse.py",
            "deps/scripts/build_environ.py",
            "deps/scripts/build_cpython_windows.py",
            "deps/scripts/payload_sysconfig.py",
        ]
    );
}

/// Pins no stage keys on, and why.
const UNKEYED_PINS: &[&str] = &[
    // The product's crt-sys build compiles it; its unpacked path, which
    // names its digest, reaches that build through the toolchain.
    "mimalloc_source",
    // A fetch-only source no stage builds from.
    "llvm_source",
    // Versions `check_pins` matches against the URLs of sources that key
    // the stages built from them.
    "awscrt_commit",
    "musl_version",
    "linux_version",
];

/// The pin names a stage's code spells without keying on them, and why.
const MENTIONED_PINS: &[(&str, &str)] = &[
    // The toolchain hands the mimalloc source on, unbuilt.
    ("toolchain", "mimalloc_source"),
    // The runtime and published stages share fallback.rs with the phases
    // that compile and pack awscrt.
    ("fallback-runtime", "awscrt"),
    ("fallback-runtime", "awscrt_version"),
    ("fallback", "awscrt"),
    ("fallback", "awscrt_version"),
];

#[test]
fn every_pin_keys_a_stage_or_is_named_unkeyed() -> Result<()> {
    let pins = Pins::load(test_root()?)?;
    let names: BTreeSet<&str> = pins
        .sources
        .keys()
        .chain(pins.versions.keys())
        .map(String::as_str)
        .collect();
    assert_eq!(
        names.len(),
        pins.sources.len() + pins.versions.len(),
        "a source and a version share a name"
    );
    let mut keyed = BTreeSet::new();
    for label in STAGES {
        for pin in all_pins(label)? {
            assert!(names.contains(pin), "{label}: unknown pin {pin}");
            keyed.insert(pin);
        }
    }
    for name in &names {
        assert!(
            keyed.contains(name) != UNKEYED_PINS.contains(name),
            "{name} must key a stage or be named in UNKEYED_PINS, not both"
        );
    }
    for name in UNKEYED_PINS {
        assert!(names.contains(name), "unkeyed pin {name} does not exist");
    }
    Ok(())
}

#[test]
fn every_pin_a_stage_names_is_one_of_its_pins() -> Result<()> {
    let root = test_root()?;
    let pins = Pins::load(root)?;
    let names: Vec<&str> = pins
        .sources
        .keys()
        .chain(pins.versions.keys())
        .map(String::as_str)
        .collect();
    for label in STAGES {
        let stage_pins = all_pins(label)?;
        for file in all_files(label)?
            .iter()
            .filter(|file| file.ends_with(".rs"))
        {
            let text = fs::read_to_string(root.join(file))?;
            for name in &names {
                if text.contains(&format!("\"{name}\"")) && !MENTIONED_PINS.contains(&(label, name))
                {
                    assert!(
                        stage_pins.contains(name),
                        "{label}: {file} names pin {name}, which does not key it"
                    );
                }
            }
        }
    }
    Ok(())
}

#[test]
fn each_linux_toolchain_keys_only_the_llvm_it_selects() -> Result<()> {
    let toolchain = pin_parts("toolchain")?;
    let x86_64 = host_inputs(toolchain, "linux", "x86_64");
    assert_lists(&x86_64, &["llvm_binary", "musl"], true, "x86_64");
    assert_lists(&x86_64, AARCH64_LLVM_PINS, false, "x86_64");
    let aarch64 = host_inputs(toolchain, "linux", "aarch64");
    assert_lists(&aarch64, &["llvm_binary_aarch64", "musl"], true, "aarch64");
    assert_lists(&aarch64, X86_64_LLVM_PINS, false, "aarch64");
    // The other toolchains only discover the host's tools.
    assert!(host_inputs(toolchain, "macos", "aarch64").is_empty());
    assert!(host_inputs(toolchain, "windows", "x86_64").is_empty());
    Ok(())
}

#[test]
fn openssl_alone_keys_on_the_openssl_pin() -> Result<()> {
    for label in STAGES {
        let keyed = all_pins(label)?.contains("openssl");
        assert_eq!(keyed, *label == "openssl", "{label}");
    }
    assert_eq!(stage_pins("openssl")?, ["openssl"]);
    Ok(())
}

#[test]
fn zlib_xz_alone_keys_on_the_zlib_and_xz_pins() -> Result<()> {
    for label in STAGES {
        for pin in ["zlib", "xz"] {
            let keyed = all_pins(label)?.contains(pin);
            assert_eq!(keyed, *label == "zlib-xz", "{label}: {pin}");
        }
    }
    assert_eq!(stage_pins("zlib-xz")?, ["zlib", "xz"]);
    Ok(())
}

#[test]
fn each_host_keys_only_the_crt_and_interpreter_pins_it_builds() -> Result<()> {
    let crt = pin_parts("crt")?;
    assert_lists(
        &host_inputs(crt, "linux", "x86_64"),
        S2N_PINS,
        true,
        "linux",
    );
    assert_lists(
        &host_inputs(crt, "windows", "x86_64"),
        S2N_PINS,
        false,
        "windows",
    );
    // Only Linux PGO builds the managed profile runtime for the interpreter.
    let cpython = pin_parts("cpython")?;
    let profile = PROFILE_PINS;
    assert_lists(
        &host_inputs(cpython, "linux", "aarch64"),
        profile,
        true,
        "linux",
    );
    assert_lists(
        &host_inputs(cpython, "macos", "x86_64"),
        profile,
        false,
        "macos",
    );
    Ok(())
}

#[test]
fn every_stage_has_a_tool_inventory() -> Result<()> {
    for label in STAGES {
        stage_files(label)?;
        stage_pins(label)?;
        stage_tools(label)?;
    }
    assert!(stage_files("unknown").is_err());
    assert!(stage_pins("unknown").is_err());
    assert!(stage_tools("unknown").is_err());
    Ok(())
}

#[test]
fn only_output_changing_tools_key_a_stage() -> Result<()> {
    for label in STAGES {
        for tool in stage_tools(label)? {
            assert!(["cmake", "perl"].contains(tool), "{label}: {tool}");
        }
    }
    Ok(())
}

#[test]
fn only_the_cmake_and_openssl_builds_key_on_their_tools() -> Result<()> {
    let native = !cfg!(windows);
    // Perl generates OpenSSL's build; the CMake projects never run it.
    let openssl: &[&str] = if native { &["perl"] } else { &[] };
    assert_eq!(stage_tools("openssl")?, openssl);
    let cmake: &[&str] = if native { &["cmake"] } else { &[] };
    assert_eq!(stage_tools("zlib-xz")?, cmake);
    assert_eq!(stage_tools("crt")?, cmake);
    let toolchain: &[&str] = if cfg!(target_os = "linux") {
        &["cmake"]
    } else {
        &[]
    };
    assert_eq!(stage_tools("toolchain")?, toolchain);
    // The Python stages run only the drivers and the project-built interpreter.
    for label in STAGES
        .iter()
        .filter(|label| !["openssl", "zlib-xz", "crt", "toolchain"].contains(label))
    {
        assert!(stage_tools(label)?.is_empty(), "{label}");
    }
    Ok(())
}
