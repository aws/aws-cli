use super::*;
use crate::deps::Source;
use crate::deps::tests::Directory;

fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

/// Create each of `files` below `root`, with any missing parents; a name
/// ending in `/` is created as a directory.
fn create(root: &Path, files: &[&str]) -> Result<()> {
    for file in files {
        let path = root.join(file);
        if file.ends_with('/') {
            fs::create_dir_all(path)?;
        } else {
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(path, "")?;
        }
    }
    Ok(())
}

/// The first path of each of `stale`, relative to `base`.
/// Each entry's first path under `base`, with `/` separators on every host
/// so one expectation serves Windows too.
fn first_paths(stale: &[Stale], base: &Path) -> Vec<String> {
    stale
        .iter()
        .map(|entry| {
            let path = entry.paths[0].strip_prefix(base).unwrap_or(&entry.paths[0]);
            path.components()
                .map(|component| component.as_os_str().to_string_lossy())
                .collect::<Vec<_>>()
                .join("/")
        })
        .collect()
}

#[test]
fn prune_options_take_repeated_roots_and_reject_unknown_or_duplicate_flags() -> Result<()> {
    let options = prune_options(&args(&[
        "--roots=a.json",
        "--dry-run",
        "--roots=b.json",
        "--sources",
    ]))?;
    assert_eq!(
        options,
        PruneOptions {
            roots: vec![PathBuf::from("a.json"), PathBuf::from("b.json")],
            sources: true,
            dry_run: true,
        }
    );
    for rejected in [
        vec![],
        vec!["--dry-run"],
        vec!["--roots="],
        vec!["--roots", "a.json"],
        vec!["--roots=a.json", "--sources", "--sources"],
        vec!["--roots=a.json", "--python-pgo=false"],
    ] {
        assert!(prune_options(&args(&rejected)).is_err(), "{rejected:?}");
    }
    Ok(())
}

#[test]
fn roots_name_scratch_by_its_path_and_round_trip_as_print_roots_json() -> Result<()> {
    let root = Path::new("/checkout");
    let stages = stage_dir(root);
    let mut roots = Roots::default();
    roots.insert("toolchain", stages.join("toolchain-0123"));
    roots.insert_work(root, stages.join("work/cpython/pgo"));
    let mut text = Vec::new();
    roots.write(&mut text)?;
    let text = String::from_utf8(text).map_err(|failure| error(failure.to_string()))?;
    // CI reads the toolchain from the same object `deps toolchain` printed.
    let value: serde_json::Value =
        serde_json::from_str(&text).map_err(|failure| error(failure.to_string()))?;
    assert_eq!(
        value["toolchain"].as_str().map(PathBuf::from),
        Some(stages.join("toolchain-0123"))
    );
    assert_eq!(
        value["work/cpython/pgo"].as_str().map(PathBuf::from),
        Some(stages.join("work/cpython/pgo"))
    );
    assert!(text.ends_with("}\n"));

    let directory = Directory::new()?;
    let file = directory.0.join("nested/roots.json");
    roots.save(&file)?;
    assert_eq!(Roots::read(&file)?, roots);
    Ok(())
}

#[test]
fn live_paths_reject_roots_of_another_checkout_or_none_in_the_stage_directory() -> Result<()> {
    let root = Path::new("/checkout");
    let mut roots = Roots::default();
    roots.insert("crt", stage_dir(root).join("crt-0123"));
    assert_eq!(
        live_paths(root, std::slice::from_ref(&roots))?,
        BTreeSet::from([stage_dir(root).join("crt-0123")])
    );

    let mut elsewhere = roots.clone();
    elsewhere.insert("cpython", PathBuf::from("/other/target/deps/cpython-4567"));
    assert!(live_paths(root, &[elsewhere]).is_err());

    // The system CRT's roots name another target's directory.
    let mut system = Roots::default();
    system.insert(
        "crt",
        root.join("target/deps/x86_64-unknown-linux-gnu/crt-0123"),
    );
    assert!(live_paths(root, &[system]).is_err());
    Ok(())
}

#[test]
fn stale_entries_keep_live_roots_their_locks_and_their_ancestors() -> Result<()> {
    let directory = Directory::new()?;
    let stages = directory.0.join("deps");
    create(
        &stages,
        &[
            "toolchain-new/bin/cc",
            "toolchain-new.lock",
            "toolchain-old/bin/cc",
            "toolchain-old.lock",
            "ubsan-minimal-old/lib/libclang_rt.ubsan_minimal-musl.a",
            "cpython-gone.lock",
            "openssl-new.lock",
            "work/crt/.key",
            "work/crt.lock",
            "work/cpython/pgo/build",
            "work/cpython/pgo.lock",
            "work/cpython/no-pgo/build",
            "work/cpython/no-pgo.lock",
            "work/cpython.lock",
            "work/renamed/",
        ],
    )?;
    let live = BTreeSet::from([
        stages.join("toolchain-new"),
        // A root whose prefix is gone still keeps its lock.
        stages.join("openssl-new"),
        stages.join("work/crt"),
        stages.join("work/cpython/pgo"),
    ]);
    let stale = stale_entries(&stages, &live)?;
    assert_eq!(
        first_paths(&stale, &stages),
        [
            "cpython-gone.lock",
            "toolchain-old",
            "ubsan-minimal-old",
            "work/cpython/no-pgo",
            "work/cpython.lock",
            "work/renamed",
        ]
    );
    let lock = stages.join("toolchain-old.lock");
    assert!(stale.contains(&Stale {
        lock: Some(lock.clone()),
        paths: vec![stages.join("toolchain-old"), lock],
    }));
    assert!(stale.contains(&Stale {
        lock: None,
        paths: vec![stages.join("ubsan-minimal-old")],
    }));
    let lone = stages.join("cpython-gone.lock");
    assert!(stale.contains(&Stale {
        lock: Some(lone.clone()),
        paths: vec![lone],
    }));
    assert!(stale_entries(&directory.0.join("missing"), &live)?.is_empty());
    Ok(())
}

#[test]
fn removal_takes_the_lock_and_skips_an_entry_a_build_holds() -> Result<()> {
    let directory = Directory::new()?;
    create(&directory.0, &["crt-old/lib/libz.a", "crt-old.lock"])?;
    let prefix = directory.0.join("crt-old");
    let lock = directory.0.join("crt-old.lock");
    let stale = Stale {
        lock: Some(lock.clone()),
        paths: vec![prefix.clone(), lock.clone()],
    };
    {
        let _held = FileLock::lock(&lock)?;
        assert!(!remove(&stale)?);
        assert!(prefix.join("lib/libz.a").is_file());
    }
    assert!(remove(&stale)?);
    assert!(!prefix.exists());
    assert!(!lock.exists());
    // An entry removed since it was listed is not an error.
    assert!(remove(&stale)?);
    Ok(())
}

#[test]
fn removal_skips_a_directory_holding_the_lock_of_a_build_below_it() -> Result<()> {
    let directory = Directory::new()?;
    let stages = directory.0.join("deps");
    create(
        &stages,
        &[
            "work/crt/.key",
            "work/crt.lock",
            "work/cpython/pgo/build",
            "work/cpython/pgo.lock",
        ],
    )?;
    // Roots naming only the CRT's scratch leave `work/cpython` stale whole,
    // with no lock of its own.
    let stale = stale_entries(&stages, &BTreeSet::from([stages.join("work/crt")]))?;
    let scratch = stages.join("work/cpython");
    let entry = Stale {
        lock: None,
        paths: vec![scratch.clone()],
    };
    assert_eq!(stale, std::slice::from_ref(&entry));
    {
        let _held = FileLock::lock(&scratch.join("pgo.lock"))?;
        assert!(!remove(&entry)?);
        assert!(scratch.join("pgo/build").is_file());
    }
    assert!(remove(&entry)?);
    assert!(!scratch.exists());
    Ok(())
}

#[cfg(unix)]
#[test]
fn removal_unlinks_a_link_without_following_it() -> Result<()> {
    let directory = Directory::new()?;
    create(&directory.0, &["outside/kept"])?;
    let link = directory.0.join("cpython-old");
    std::os::unix::fs::symlink(directory.0.join("outside"), &link)?;
    let live = BTreeSet::from([link.join("kept")]);
    // A link is never searched, even toward a live path.
    let stale = stale_entries(&directory.0, &BTreeSet::new())?;
    assert!(stale.iter().any(|entry| entry.paths[0] == link));
    assert!(!contains_live(&link, &live)?);
    assert!(remove(&Stale {
        lock: None,
        paths: vec![link.clone()],
    })?);
    assert!(fs::symlink_metadata(&link).is_err());
    assert!(directory.0.join("outside/kept").is_file());
    Ok(())
}

fn pins(sources: &[(&str, &str, &str)]) -> Pins {
    Pins {
        versions: BTreeMap::new(),
        sources: sources
            .iter()
            .map(|(name, sha256, url)| {
                (
                    (*name).to_owned(),
                    Source {
                        url: (*url).to_owned(),
                        sha256: (*sha256).to_owned(),
                        original_url: None,
                        strip_components: 1,
                    },
                )
            })
            .collect(),
    }
}

#[test]
fn stale_sources_keep_what_the_pins_name_and_guard_downloads_by_digest() -> Result<()> {
    let directory = Directory::new()?;
    let root = &directory.0;
    let (live, old) = ("a".repeat(64), "b".repeat(64));
    let (release, distro) = ("d".repeat(64), "e".repeat(64));
    let pins = pins(&[
        ("zlib", &live, "https://example.com/zlib.tar.gz"),
        ("llvm_binary", &old, "https://example.com/llvm.tar.xz"),
    ]);
    // The unpacks the pins name, by recipe.
    let unpacked = |name: &str| {
        source_dir(root, name, &pins.sources[name])
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .ok_or_else(|| error("unnamed source directory"))
    };
    let (zlib, llvm) = (unpacked("zlib")?, unpacked("llvm_binary")?);
    create(
        root,
        &[
            &format!("target/sources/{zlib}/configure"),
            &format!("target/sources/{zlib}.lock"),
            &format!("target/sources/zlib-{old}/configure"),
            &format!("target/sources/zlib-{old}.lock"),
            &format!("target/downloads/{live}.tar.gz"),
            &format!("target/downloads/{old}.tar.xz"),
            "target/downloads/zlib.tar.gz",
            &format!("target/downloads/{live}.42.part"),
            &format!("target/downloads/{old}.tar.gz"),
            &format!("target/download-locks/{live}.lock"),
            &format!("target/download-locks/{old}.lock"),
            &format!("target/download-locks/{}.lock", "c".repeat(64)),
            // The LLVM release unpacks outside target/sources, beside the
            // distro fallback earlier builds assembled, which no pin names.
            &format!("target/toolchain/{llvm}/bin/clang"),
            &format!("target/toolchain/{llvm}.lock"),
            &format!("target/toolchain/llvm_binary-{release}/bin/clang"),
            &format!("target/toolchain/llvm_binary-{release}.lock"),
            &format!("target/toolchain/distro-{distro}/bin/clang"),
            &format!("target/toolchain/distro-{distro}.lock"),
        ],
    )?;
    let stale = stale_sources(root, &pins)?;
    assert_eq!(
        first_paths(&stale, root),
        [
            format!("target/sources/zlib-{old}"),
            format!("target/toolchain/distro-{distro}"),
            format!("target/toolchain/llvm_binary-{release}"),
            format!("target/downloads/{live}.42.part"),
            format!("target/downloads/{old}.tar.gz"),
            format!("target/download-locks/{}.lock", "c".repeat(64)),
        ]
    );
    // A superseded release goes with its lock.
    assert_eq!(
        stale[2].paths,
        [
            root.join(format!("target/toolchain/llvm_binary-{release}")),
            root.join(format!("target/toolchain/llvm_binary-{release}.lock")),
        ]
    );
    // A `.part` file is a download in progress until its digest's lock is free.
    let part = &stale[3];
    let download_lock = root.join(format!("target/download-locks/{live}.lock"));
    assert_eq!(part.lock.as_ref(), Some(&download_lock));
    assert_eq!(part.paths.len(), 1);
    {
        let _held = FileLock::lock(&download_lock)?;
        assert!(!remove(part)?);
    }
    assert!(remove(part)?);
    assert!(download_lock.is_file());
    Ok(())
}

/// A checkout whose stage directory holds a current and a superseded CRT
/// and both PGO modes' interpreter scratch, with the roots of each mode.
struct PruneFixture {
    directory: Directory,
    pgo: PathBuf,
    no_pgo: PathBuf,
}

impl PruneFixture {
    fn new() -> Result<Self> {
        let directory = Directory::new()?;
        let root = &directory.0;
        let stages = stage_dir(root);
        create(
            &stages,
            &[
                "crt-new/lib/libz.a",
                "crt-new.lock",
                "crt-old/lib/libz.a",
                "crt-old.lock",
                "cpython-pgo/bin/python3",
                "cpython-pgo.lock",
                "cpython-no-pgo/bin/python3",
                "cpython-no-pgo.lock",
                "work/cpython/pgo/build",
                "work/cpython/no-pgo/build",
            ],
        )?;
        create(root, &["target/deps/x86_64-unknown-linux-gnu/crt-old/"])?;
        let (mut pgo, mut no_pgo) = (Roots::default(), Roots::default());
        pgo.insert("crt", stages.join("crt-new"));
        pgo.insert("cpython", stages.join("cpython-pgo"));
        pgo.insert_work(root, stages.join("work/cpython/pgo"));
        // Both modes name their interpreter under the same label.
        no_pgo.insert("cpython", stages.join("cpython-no-pgo"));
        no_pgo.insert_work(root, stages.join("work/cpython/no-pgo"));
        let fixture = Self {
            pgo: root.join("pgo.json"),
            no_pgo: root.join("no-pgo.json"),
            directory,
        };
        pgo.save(&fixture.pgo)?;
        no_pgo.save(&fixture.no_pgo)?;
        Ok(fixture)
    }

    fn stages(&self) -> PathBuf {
        stage_dir(&self.directory.0)
    }

    /// Prune with `roots` and `extra` options, and return the report.
    fn prune(&self, roots: &[&Path], extra: &[&str]) -> Result<String> {
        let mut args: Vec<_> = roots
            .iter()
            .map(|file| format!("--roots={}", file.display()))
            .collect();
        args.extend(extra.iter().map(|option| (*option).to_owned()));
        let mut output = Vec::new();
        prune_reporting(&self.directory.0, &pins(&[]), &args, &mut output)?;
        String::from_utf8(output).map_err(|failure| error(failure.to_string()))
    }
}

#[test]
fn prune_removes_only_entries_the_roots_files_neither_name_nor_contain() -> Result<()> {
    let fixture = PruneFixture::new()?;
    let stages = fixture.stages();
    let both = [fixture.pgo.as_path(), fixture.no_pgo.as_path()];
    let old = stages.join("crt-old");
    assert_eq!(
        fixture.prune(&both, &["--dry-run"])?,
        format!("would remove {}\n", old.display())
    );
    assert!(old.is_dir() && stages.join("crt-old.lock").is_file());
    assert_eq!(
        fixture.prune(&both, &[])?,
        format!("removed {}\npruned 1 of 1 stale entries\n", old.display())
    );
    assert!(!old.exists() && !stages.join("crt-old.lock").exists());
    for kept in [
        "crt-new/lib/libz.a",
        "crt-new.lock",
        "cpython-pgo/bin/python3",
        "cpython-pgo.lock",
        "cpython-no-pgo/bin/python3",
        "cpython-no-pgo.lock",
        "work/cpython/pgo/build",
        "work/cpython/no-pgo/build",
    ] {
        assert!(stages.join(kept).exists(), "{kept}");
    }
    // Another target's prefixes are never pruned.
    let system = fixture
        .directory
        .0
        .join("target/deps/x86_64-unknown-linux-gnu");
    assert!(system.join("crt-old").is_dir());
    Ok(())
}

#[test]
fn prune_with_one_pgo_modes_roots_removes_the_other_modes_scratch() -> Result<()> {
    let fixture = PruneFixture::new()?;
    let stages = fixture.stages();
    fixture.prune(&[&fixture.pgo], &[])?;
    assert!(!stages.join("work/cpython/no-pgo").exists());
    assert!(!stages.join("cpython-no-pgo").exists());
    assert!(stages.join("cpython-pgo/bin/python3").is_file());
    assert!(stages.join("work/cpython/pgo/build").is_file());
    assert!(stages.join("crt-new/lib/libz.a").is_file());
    Ok(())
}
