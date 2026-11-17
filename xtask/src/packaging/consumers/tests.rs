use super::*;

#[derive(Debug)]
struct Directory(PathBuf);

impl Directory {
    fn new(name: &str) -> Result<Self, TaskError> {
        let path = std::env::temp_dir().join(format!(
            "awscli-consumers-test-{}-{name}",
            std::process::id()
        ));
        if path.exists() {
            fs::remove_dir_all(&path)?;
        }
        fs::create_dir_all(&path)?;
        Ok(Self(path))
    }
}

impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn workspace_root() -> Result<&'static Path, TaskError> {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| deps::error("workspace root missing"))
}

fn arguments(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

#[cfg(feature = "package-consumers")]
#[test]
fn generated_fallback_files_and_archive_agree() -> Result<(), TaskError> {
    run(workspace_root()?, &[])
}

#[test]
fn pgo_is_on_by_default_except_on_windows() -> Result<(), TaskError> {
    assert!(options::default_pgo("linux"));
    assert!(options::default_pgo("macos"));
    assert!(!options::default_pgo("windows"));
    assert_eq!(Options::parse(workspace_root()?, &[])?.pgo, !cfg!(windows));
    Ok(())
}

#[test]
fn pgo_option_takes_pgo_and_the_python_pgo_alias() -> Result<(), TaskError> {
    let root = workspace_root()?;
    for values in [
        &["--pgo", "false"][..],
        &["--pgo=false"],
        &["--python-pgo", "false"],
        &["--python-pgo=false"],
    ] {
        assert!(!Options::parse(root, &arguments(values))?.pgo, "{values:?}");
    }
    for flag in ["--pgo", "--python-pgo"] {
        let failure = Options::parse(root, &arguments(&[flag, "maybe"]))
            .err()
            .map(|failure| failure.to_string());
        assert_eq!(
            failure.as_deref(),
            Some(format!("{flag} requires true or false").as_str())
        );
    }
    Ok(())
}

#[test]
fn prepared_pgo_prefix_names_its_merger_and_runtime() -> Result<(), TaskError> {
    let prefix = Directory::new("pgo-prefix")?;
    fs::create_dir_all(prefix.0.join("bin"))?;
    fs::create_dir_all(prefix.0.join("lib"))?;
    fs::write(prefix.0.join("bin/llvm-profdata"), "")?;
    let failure = prefix_tools(&prefix.0)
        .err()
        .map(|failure| failure.to_string());
    assert_eq!(
        failure.as_deref(),
        Some("prepared PGO prefix has no profile runtime")
    );
    fs::write(prefix.0.join("lib/libclang_rt.profile-musl.a"), "")?;
    assert_eq!(
        prefix_tools(&prefix.0)?,
        ProfileTools {
            llvm_profdata: prefix.0.join("bin/llvm-profdata"),
            profile_runtime: prefix.0.join("lib/libclang_rt.profile-musl.a"),
        }
    );
    Ok(())
}

#[test]
fn crt_archives_follow_the_library_inventory() -> Result<(), TaskError> {
    let root = workspace_root()?;
    let prefix = Directory::new("crt-prefix")?;
    let directory = prefix.0.join("lib");
    fs::create_dir_all(&directory)?;
    let inventory = fs::read_to_string(root.join("deps/crt-libraries.txt"))?;
    let mut expected = Vec::new();
    for name in inventory
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .filter(|name| !cfg!(windows) || *name != "s2n")
    {
        let archive = directory.join(platform::archive(name));
        fs::write(&archive, "")?;
        expected.push(archive);
    }
    // An archive the inventory does not name is never linked.
    fs::write(directory.join(platform::archive("foo")), "")?;
    assert_eq!(deps::crt_archives(root, &prefix.0)?, expected);
    let missing = directory.join(platform::archive("aws-c-mqtt"));
    fs::remove_file(&missing)?;
    let failure = deps::crt_archives(root, &prefix.0)
        .err()
        .map(|failure| failure.to_string())
        .unwrap_or_default();
    assert!(
        failure.starts_with(&format!("missing CRT archive {}", missing.display())),
        "{failure}"
    );
    Ok(())
}

fn fake_python() -> python::PythonOutputs {
    python::PythonOutputs {
        cpython: PathBuf::from("/cpython"),
        fallback: PathBuf::from("/fallback"),
    }
}

fn fake_inputs<'a>(python: &'a python::PythonOutputs, crt_archives: &'a [PathBuf]) -> Inputs<'a> {
    Inputs {
        root: Path::new("/root"),
        crt: Path::new("/crt"),
        crt_archives,
        python,
        output: Path::new("/output"),
    }
}

fn includes(consumer: &Consumer) -> Vec<&Path> {
    consumer.includes.iter().map(PathBuf::as_path).collect()
}

fn defined(consumer: &Consumer) -> Vec<(&Path, &[&str])> {
    consumer
        .sources
        .iter()
        .map(|source| (source.path.as_path(), source.defines))
        .collect()
}

fn support() -> Vec<PathBuf> {
    SUPPORT_LIBRARIES
        .iter()
        .map(|name| Path::new("/cpython/lib").join(platform::archive(name)))
        .collect()
}

const CRT_INCLUDE: &str = "/crt/include";
const CPYTHON_INCLUDE: &str = "/cpython/include/python3.14";

#[test]
fn crt_and_pgo_consumers_attach_only_their_own_package() {
    let python = fake_python();
    let crt_archives = [PathBuf::from("/crt/lib/libaws-c-s3.a")];
    let inputs = fake_inputs(&python, &crt_archives);
    let consumer = crt_consumer(&inputs);
    assert_eq!(includes(&consumer), [Path::new(CRT_INCLUDE)]);
    let fixture = Path::new("/root/tests/packages/crt.c");
    assert_eq!(defined(&consumer), [(fixture, &[][..])]);
    assert_eq!(consumer.archives, crt_archives);

    let tools = ProfileTools {
        llvm_profdata: PathBuf::from("/pgo/bin/llvm-profdata"),
        profile_runtime: PathBuf::from("/pgo/lib/libclang_rt.profile-musl.a"),
    };
    let consumer = pgo_consumer(&inputs, &tools);
    assert!(consumer.includes.is_empty());
    let fixture = Path::new("/root/tests/packages/pgo.c");
    assert_eq!(defined(&consumer), [(fixture, &[][..])]);
    assert_eq!(consumer.archives, [tools.profile_runtime]);
}

#[test]
fn cpython_consumers_scope_the_core_define_to_fallback_glue() {
    let python = fake_python();
    let crt_archives = [PathBuf::from("/crt/lib/libaws-c-s3.a")];
    let inputs = fake_inputs(&python, &crt_archives);
    let both = [Path::new(CPYTHON_INCLUDE), Path::new(CRT_INCLUDE)];

    let consumer = cpython_consumer(&inputs);
    assert_eq!(includes(&consumer), both);
    let none: &[&str] = &[];
    assert_eq!(
        defined(&consumer),
        [
            (Path::new("/root/tests/packages/cpython.c"), none),
            (Path::new("/cpython/lib/python3.14-inittab.c"), none),
        ]
    );
    let mut archives = vec![PathBuf::from("/cpython/lib/libpython3.14.a")];
    archives.extend(support());
    archives.extend(crt_archives.iter().cloned());
    assert_eq!(consumer.archives, archives);

    let consumer = fallback_consumer(&inputs);
    assert_eq!(includes(&consumer), both);
    let core: &[&str] = &[BUILD_CORE_BUILTIN];
    assert_eq!(
        defined(&consumer),
        [
            (Path::new("/root/tests/packages/fallback.c"), none),
            (Path::new("/fallback/inittab.c"), core),
            (Path::new("/fallback/frozen_bootstrap.c"), core),
        ]
    );
    let mut archives = vec![PathBuf::from("/fallback/python-fallback.a")];
    archives.extend(support());
    archives.extend(crt_archives.iter().cloned());
    assert_eq!(consumer.archives, archives);
}

fn os_strings(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}

#[test]
fn consumer_arguments_optimize_for_size_and_name_fallback_consumer_outputs() {
    let python = fake_python();
    let inputs = fake_inputs(&python, &[]);
    let consumer = fallback_consumer(&inputs);
    // Joined like the builder, so the separators match on every host.
    let cpython_include = Path::new("/cpython")
        .join("include")
        .join(python::PYTHON_ABI);
    let crt_include = Path::new("/crt").join("include");
    let mut shared = os_strings(&["-Os", "-ffunction-sections", "-fdata-sections"]);
    for include in [&cpython_include, &crt_include] {
        shared.push("-I".into());
        shared.push(include.into());
    }
    assert_eq!(consumer.compile_arguments(), shared);
    let object = inputs.output.join("fallback-consumer-inittab.o");
    let (path, arguments) = consumer.object(&consumer.sources[1], inputs.output);
    assert_eq!(path, object);
    let mut expected = shared;
    expected.extend(os_strings(&[BUILD_CORE_BUILTIN, "-c"]));
    expected.push(Path::new("/fallback").join("inittab.c").into());
    expected.push("-o".into());
    expected.push(object.into());
    assert_eq!(arguments, expected);
    let binary = format!("fallback-consumer{}", std::env::consts::EXE_SUFFIX);
    assert_eq!(consumer.binary(inputs.output), inputs.output.join(binary));
}
