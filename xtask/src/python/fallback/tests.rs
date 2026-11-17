use super::*;
use crate::python::tests::keying_checkout;

#[test]
fn linked_outputs_replace_a_stale_destination() -> Result<(), TaskError> {
    let directory = std::env::temp_dir().join(format!(
        "awscli-python-test-{}-link-output",
        std::process::id()
    ));
    fs::create_dir_all(&directory)?;
    let (output, destination) = (directory.join("output"), directory.join("destination"));
    fs::write(&output, "fresh")?;
    fs::write(&destination, "stale")?;
    link_output(&output, &destination)?;
    let linked = fs::read_to_string(&destination)?;
    fs::remove_dir_all(&directory)?;
    assert_eq!(linked, "fresh");
    Ok(())
}

#[test]
fn published_fallback_outputs_are_each_stage_output_once() {
    let outputs = fallback_outputs();
    let unique: std::collections::BTreeSet<_> = outputs.iter().collect();
    assert_eq!(unique.len(), outputs.len());
    assert_eq!(
        outputs.len(),
        ARCHIVE_OUTPUTS.len() + 1 + RUNTIME_OUTPUTS.len()
    );
}

/// The inputs of a fallback build against the CRT prefix `crt`.
fn inputs(crt: &Path) -> FallbackInputs<'_> {
    FallbackInputs {
        crt,
        cpython: Path::new("/deps/cpython-1"),
        runtime_source: Path::new("runtime.py"),
        pgo: true,
    }
}

#[test]
fn only_the_archive_is_keyed_on_the_crt_prefix() {
    // The archive compiles awscrt against the CRT headers; the payload and
    // runtime never read the CRT, and follow it through the interpreter
    // prefix when CPython relinks against a new one.
    let (first, second) = (Path::new("/deps/crt-1"), Path::new("/deps/crt-2"));
    assert_ne!(archive_key(&inputs(first)), archive_key(&inputs(second)));
    assert_eq!(fallback_key(&inputs(first)), fallback_key(&inputs(second)));
    let payload = Path::new("/deps/fallback-payload-1");
    assert_eq!(
        runtime_key(&inputs(first), payload, b"source"),
        runtime_key(&inputs(second), payload, b"source")
    );
    assert_eq!(
        archive_key(&inputs(first)),
        [b"pgo".as_slice(), b"/deps/cpython-1", b"/deps/crt-1"]
    );
}

#[test]
fn every_fallback_phase_is_keyed_on_the_interpreter_prefix_and_pgo_mode() {
    let crt = Path::new("/deps/crt-1");
    let other = FallbackInputs {
        cpython: Path::new("/deps/cpython-2"),
        ..inputs(crt)
    };
    let unoptimized = FallbackInputs {
        pgo: false,
        ..inputs(crt)
    };
    let payload = Path::new("/deps/fallback-payload-1");
    for changed in [&other, &unoptimized] {
        assert_ne!(archive_key(&inputs(crt)), archive_key(changed));
        assert_ne!(fallback_key(&inputs(crt)), fallback_key(changed));
        assert_ne!(
            runtime_key(&inputs(crt), payload, b"source"),
            runtime_key(changed, payload, b"source")
        );
    }
    // The runtime also follows the payload and its own bootstrap source.
    let managed = inputs(crt);
    let runtime = runtime_key(&managed, payload, b"source");
    assert_ne!(
        runtime,
        runtime_key(
            &inputs(crt),
            Path::new("/deps/fallback-payload-2"),
            b"source"
        )
    );
    assert_ne!(runtime, runtime_key(&inputs(crt), payload, b"edited"));
}

#[test]
fn python_scratch_sits_outside_every_prefix_and_splits_by_pgo_mode() {
    let root = Path::new("/checkout");
    let deps = root.join("target/deps").join(crate::deps::TARGET);
    // The payload's PGO scratch, which holds its venv, sits at a path no key determines.
    assert_eq!(
        pgo_work(root, "fallback-payload", true),
        deps.join("work/fallback-payload/pgo")
    );
    for label in ["fallback-archive", "fallback-payload", "cpython"] {
        let (pgo, plain) = (pgo_work(root, label, true), pgo_work(root, label, false));
        assert_ne!(pgo, plain, "{label}");
        for work in [pgo, plain] {
            assert!(work.starts_with(deps.join("work").join(label)), "{label}");
        }
    }
    assert_ne!(
        pgo_work(root, "fallback-archive", true),
        pgo_work(root, "fallback-payload", true)
    );
}

/// The fallback roots of `root` in PGO mode `pgo`, as `--print-roots` names them.
fn printed_roots(
    root: &Path,
    pgo: bool,
) -> Result<std::collections::BTreeMap<String, PathBuf>, TaskError> {
    let mut json = Vec::new();
    roots(
        root,
        &deps::keying_toolchain(),
        &FallbackInputs {
            crt: Path::new("/deps/crt-1"),
            cpython: Path::new("/deps/cpython-1"),
            runtime_source: &root.join("crates/python-fallback/python/runtime.py"),
            pgo,
        },
    )?
    .write(&mut json)?;
    serde_json::from_slice(&json).map_err(|failure| TaskError::Message(failure.to_string()))
}

#[test]
fn roots_name_every_stage_prefix_and_the_scratch_of_one_pgo_mode() -> Result<(), TaskError> {
    let directory = std::env::temp_dir().join(format!(
        "awscli-python-test-{}-fallback-roots",
        std::process::id()
    ));
    let roots = keying_checkout(
        &directory,
        &[
            "fallback-archive",
            "fallback-payload",
            "fallback-runtime",
            "fallback",
        ],
    )
    .and_then(|()| {
        Ok((
            printed_roots(&directory, true)?,
            printed_roots(&directory, false)?,
        ))
    });
    fs::remove_dir_all(&directory)?;
    let (pgo, no_pgo) = roots?;
    let stages = directory.join("target/deps").join(deps::TARGET);
    let phases = [
        "fallback",
        "fallback-archive",
        "fallback-payload",
        "fallback-runtime",
    ];
    for (mode, roots) in [("pgo", &pgo), ("no-pgo", &no_pgo)] {
        let mut names = phases.map(str::to_owned).to_vec();
        names.extend(["archive", "payload"].map(|phase| format!("work/fallback-{phase}/{mode}")));
        assert!(roots.keys().eq(names.iter()), "{mode}: {roots:?}");
        for (name, path) in roots {
            if name.starts_with("work/") {
                assert_eq!(path, &stages.join(name));
            } else {
                assert_eq!(path.parent(), Some(stages.as_path()), "{name}");
                let file = path.file_name().and_then(|file| file.to_str());
                assert!(file.is_some_and(|file| file.starts_with(&format!("{name}-"))));
            }
        }
    }
    // The mode keys every phase, so neither mode's roots keep the other's.
    for name in phases {
        assert_ne!(pgo[name], no_pgo[name], "{name}");
    }
    Ok(())
}
