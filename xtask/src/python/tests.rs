use super::*;
use crate::deps;
use std::collections::BTreeMap;
use std::fs;

/// A checkout of only the pins and the `labels` stage inventories, with a
/// one-file AWS CLI, so a payload key need not hash the whole tracked tree.
pub(super) fn keying_checkout(directory: &Path, labels: &[&str]) -> Result<(), TaskError> {
    let checkout = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| TaskError::Message("missing workspace parent".into()))?;
    let mut files = vec!["deps/pins.toml"];
    for label in labels {
        files.extend(deps::inputs::stage_files(label)?);
    }
    for file in files {
        fs::create_dir_all(directory.join(file).parent().unwrap_or(directory))?;
        fs::copy(checkout.join(file), directory.join(file))?;
    }
    fs::create_dir_all(directory.join("aws-cli/awscli"))?;
    fs::write(
        directory.join("aws-cli/awscli/__init__.py"),
        "__version__ = '2.0.0'\n",
    )?;
    Ok(())
}

/// Roots by name, as `--print-roots` prints them.
type Printed = BTreeMap<String, PathBuf>;

fn printed(roots: &Roots) -> Result<Printed, TaskError> {
    let mut json = Vec::new();
    roots.write(&mut json)?;
    serde_json::from_slice(&json).map_err(|failure| TaskError::Message(failure.to_string()))
}

/// A minimal checkout holding the Python stage inventories.
fn python_checkout(name: &str) -> Result<PathBuf, TaskError> {
    let directory =
        std::env::temp_dir().join(format!("awscli-python-test-{}-{name}", std::process::id()));
    keying_checkout(
        &directory,
        &[
            "profile",
            "python-support",
            "fallback-archive",
            "fallback-payload",
            "fallback-runtime",
            "fallback",
        ],
    )?;
    Ok(directory)
}

/// The Python roots of `directory` in PGO mode `pgo`, for an interpreter
/// built at `cpython`.
fn python_roots(directory: &Path, cpython: &Path, pgo: bool) -> Result<Printed, TaskError> {
    let outputs = PythonOutputs {
        cpython: cpython.to_owned(),
        fallback: directory.join("unused"),
    };
    printed(&roots(
        directory,
        &deps::keying_toolchain(),
        Path::new("/deps/crt-1"),
        pgo,
        &outputs,
    )?)
}

/// Check that `roots` name the support and interpreter stages and the
/// scratch of `mode`, each where `stages` keeps it.
fn check_mode(roots: &Printed, stages: &Path, cpython: &Path, mode: &str) {
    assert_eq!(roots["cpython"], cpython, "{mode}");
    for name in [
        "python-support".to_owned(),
        "work/python-support".to_owned(),
        format!("work/cpython/{mode}"),
        "fallback".to_owned(),
        format!("work/fallback-payload/{mode}"),
    ] {
        assert!(roots.contains_key(&name), "{mode}: {name} in {roots:?}");
    }
    assert_eq!(roots.len(), 10, "{mode}: {roots:?}");
    for (name, path) in roots {
        if name.starts_with("work/") {
            assert_eq!(path, &stages.join(name));
        } else {
            assert_eq!(path.parent(), Some(stages), "{name}");
        }
    }
}

#[test]
fn roots_name_the_support_and_interpreter_stages_and_one_modes_scratch() -> Result<(), TaskError> {
    let directory = python_checkout("python-roots")?;
    let stages = directory.join("target/deps").join(deps::TARGET);
    let cpython = stages.join("cpython-1");
    let roots = python_roots(&directory, &cpython, true)
        .and_then(|pgo| Ok((pgo, python_roots(&directory, &cpython, false)?)));
    fs::remove_dir_all(&directory)?;
    let (pgo, no_pgo) = roots?;
    check_mode(&pgo, &stages, &cpython, "pgo");
    check_mode(&no_pgo, &stages, &cpython, "no-pgo");
    // Support keys only on the toolchain, so both modes keep one prefix.
    assert_eq!(pgo["python-support"], no_pgo["python-support"]);
    let support = pgo["python-support"]
        .file_name()
        .and_then(|file| file.to_str());
    assert!(support.is_some_and(|file| file.starts_with("python-support-")));
    Ok(())
}

#[test]
fn profile_roots_name_the_stage_and_its_scratch() -> Result<(), TaskError> {
    let directory = python_checkout("profile-roots")?;
    let roots =
        profile_roots(&directory, &deps::keying_toolchain()).and_then(|roots| printed(&roots));
    fs::remove_dir_all(&directory)?;
    let roots = roots?;
    let stages = directory.join("target/deps").join(deps::TARGET);
    assert!(roots.keys().eq(["profile", "work/profile"]), "{roots:?}");
    assert_eq!(roots["work/profile"], stages.join("work/profile"));
    assert_eq!(roots["profile"].parent(), Some(stages.as_path()));
    let profile = roots["profile"].file_name().and_then(|file| file.to_str());
    assert!(profile.is_some_and(|file| file.starts_with("profile-")));
    Ok(())
}
