use std::collections::BTreeMap;

use super::*;
use crate::deps::tests::Directory;

/// An environment of only `variables`.
fn environment(variables: &[(&str, &Path)]) -> impl Fn(&str) -> Option<OsString> + use<> {
    let variables: BTreeMap<String, OsString> = variables
        .iter()
        .map(|(name, value)| ((*name).to_owned(), value.as_os_str().to_owned()))
        .collect();
    move |name| variables.get(name).cloned()
}

fn message(result: Result<Store>) -> String {
    result
        .err()
        .map(|failure| failure.to_string())
        .unwrap_or_default()
}

/// The shared store `locate` should select in `directory`, once created.
fn shared_in(directory: &Path) -> Result<Store> {
    let directory = canonical(directory).ok_or_else(|| error("unresolved test directory"))?;
    Ok(Store {
        directory: directory.join("v1"),
        lock: directory.join("v1.lock"),
        kind: Kind::Shared,
    })
}

#[cfg(not(windows))]
#[test]
fn the_default_directory_is_in_the_xdg_cache_else_home_cache() {
    let (xdg, home) = (Path::new("/xdg"), Path::new("/home/user"));
    assert_eq!(
        cache_directory(environment(&[("XDG_CACHE_HOME", xdg), ("HOME", home)])),
        Some(PathBuf::from("/xdg/aws-cli-native/build"))
    );
    assert_eq!(
        cache_directory(environment(&[("HOME", home)])),
        Some(PathBuf::from("/home/user/.cache/aws-cli-native/build"))
    );
    // The XDG specification ignores a relative XDG_CACHE_HOME.
    assert_eq!(
        cache_directory(environment(&[
            ("XDG_CACHE_HOME", Path::new("relative")),
            ("HOME", home)
        ])),
        Some(PathBuf::from("/home/user/.cache/aws-cli-native/build"))
    );
    assert_eq!(
        cache_directory(environment(&[("HOME", Path::new("relative"))])),
        None
    );
    assert_eq!(cache_directory(environment(&[])), None);
}

#[cfg(windows)]
#[test]
fn the_default_directory_is_in_local_app_data() {
    let local = Path::new(r"C:\Users\user\AppData\Local");
    assert_eq!(
        cache_directory(environment(&[
            ("LOCALAPPDATA", local),
            ("XDG_CACHE_HOME", Path::new(r"C:\xdg"))
        ])),
        Some(local.join("aws-cli-native").join("build"))
    );
    assert_eq!(
        cache_directory(environment(&[("LOCALAPPDATA", Path::new("relative"))])),
        None
    );
    assert_eq!(cache_directory(environment(&[])), None);
}

#[test]
fn the_default_shared_store_is_created_in_the_cache_directory() -> Result<()> {
    let (checkout, cache) = (Directory::new()?, Directory::new()?);
    let variable = if cfg!(windows) {
        "LOCALAPPDATA"
    } else {
        "XDG_CACHE_HOME"
    };
    let store = locate(&checkout.0, environment(&[(variable, &cache.0)]))?;
    let directory = cache.0.join("aws-cli-native").join("build");
    assert!(directory.is_dir());
    assert_eq!(store, shared_in(&directory)?);
    // An explicit `shared` and an empty directory select the same store.
    let explicit = environment(&[
        (variable, &cache.0),
        (MODE, Path::new("shared")),
        (DIRECTORY, Path::new("")),
    ]);
    assert_eq!(locate(&checkout.0, explicit)?, store);
    Ok(())
}

#[test]
fn the_cache_directory_variable_replaces_the_default() -> Result<()> {
    let (checkout, cache, store) = (Directory::new()?, Directory::new()?, Directory::new()?);
    let directory = store.0.join("nested");
    let variables = environment(&[
        ("XDG_CACHE_HOME", &cache.0),
        ("LOCALAPPDATA", &cache.0),
        (DIRECTORY, &directory),
    ]);
    assert_eq!(locate(&checkout.0, variables)?, shared_in(&directory)?);
    assert!(fs::read_dir(&cache.0)?.next().is_none());
    Ok(())
}

#[cfg(unix)]
#[test]
fn a_linked_cache_directory_resolves_to_its_target() -> Result<()> {
    let (checkout, store) = (Directory::new()?, Directory::new()?);
    let link = checkout.0.join("link");
    std::os::unix::fs::symlink(&store.0, &link)?;
    assert_eq!(
        locate(&checkout.0, environment(&[(DIRECTORY, &link)]))?,
        shared_in(&store.0)?
    );
    Ok(())
}

#[test]
fn a_relative_cache_directory_is_rejected() -> Result<()> {
    let checkout = Directory::new()?;
    let variables = environment(&[(DIRECTORY, Path::new("relative"))]);
    assert_eq!(
        message(locate(&checkout.0, variables)),
        "AWS_NATIVE_CACHE_DIR must be an absolute path, not relative"
    );
    Ok(())
}

#[test]
fn the_local_mode_keeps_the_store_in_target() -> Result<()> {
    let (checkout, cache) = (Directory::new()?, Directory::new()?);
    let variables = environment(&[
        ("XDG_CACHE_HOME", &cache.0),
        ("LOCALAPPDATA", &cache.0),
        (MODE, Path::new("local")),
    ]);
    assert_eq!(locate(&checkout.0, variables)?, local(&checkout.0));
    assert_eq!(local(&checkout.0).directory, checkout.0.join("target"));
    assert!(fs::read_dir(&cache.0)?.next().is_none());
    Ok(())
}

#[test]
fn the_local_mode_rejects_a_cache_directory() -> Result<()> {
    let (checkout, store) = (Directory::new()?, Directory::new()?);
    let variables = environment(&[(MODE, Path::new("local")), (DIRECTORY, &store.0)]);
    assert_eq!(
        message(locate(&checkout.0, variables)),
        "AWS_NATIVE_CACHE=local keeps dependencies in target, so AWS_NATIVE_CACHE_DIR \
         must be unset"
    );
    Ok(())
}

#[test]
fn an_unknown_mode_is_rejected() -> Result<()> {
    let checkout = Directory::new()?;
    let variables = environment(&[(MODE, Path::new("everywhere"))]);
    assert_eq!(
        message(locate(&checkout.0, variables)),
        "AWS_NATIVE_CACHE must be `shared` or `local`, not `everywhere`"
    );
    Ok(())
}

#[test]
fn a_host_without_a_cache_directory_keeps_the_local_store() -> Result<()> {
    let checkout = Directory::new()?;
    assert_eq!(locate(&checkout.0, environment(&[]))?, local(&checkout.0));
    Ok(())
}

#[cfg(unix)]
#[test]
fn an_uncreatable_cache_directory_is_reported() -> Result<()> {
    let (checkout, store) = (Directory::new()?, Directory::new()?);
    let file = store.0.join("file");
    fs::write(&file, "")?;
    let directory = file.join("store");
    let found = message(locate(&checkout.0, environment(&[(DIRECTORY, &directory)])));
    assert!(
        found.starts_with(&format!(
            "cannot open the dependency store {}: ",
            directory.display()
        )),
        "{found}"
    );
    assert!(
        found.ends_with(
            "; set AWS_NATIVE_CACHE_DIR to another directory, or AWS_NATIVE_CACHE=local \
             to keep dependencies in target"
        ),
        "{found}"
    );
    Ok(())
}

#[test]
fn unit_tests_keep_every_store_in_the_checkout() -> Result<()> {
    let checkout = Directory::new()?;
    assert_eq!(resolve(&checkout.0), local(&checkout.0));
    assert!(!is_shared(&checkout.0));
    Ok(())
}
