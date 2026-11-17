use crate::{TaskError, deps};
use std::path::{Path, PathBuf};

#[derive(Debug)]
pub(super) struct Options {
    pub crt: Option<PathBuf>,
    pub cpython: Option<PathBuf>,
    pub fallback: Option<PathBuf>,
    pub profile: Option<PathBuf>,
    pub pgo: bool,
}

/// Whether CPython is built with PGO when nothing asks either way, on the
/// host `os` as `std::env::consts::OS` names it. Matches the default of
/// `cargo xtask build`'s `--python-pgo`: CPython's Windows build has no
/// `make profile-opt`, so PGO is refused there, and a Windows consumer runs
/// without `--pgo=false`.
pub(super) fn default_pgo(os: &str) -> bool {
    os != "windows"
}

impl Options {
    pub(super) fn parse(root: &Path, args: &[String]) -> Result<Self, TaskError> {
        let mut options = Self {
            crt: None,
            cpython: None,
            fallback: None,
            profile: None,
            pgo: default_pgo(std::env::consts::OS),
        };
        let mut args = args.iter();
        while let Some(argument) = args.next() {
            let (flag, value) = if let Some(pair) = argument.split_once('=') {
                pair
            } else {
                (
                    argument.as_str(),
                    args.next()
                        .ok_or_else(|| deps::error(format!("{argument} needs a value")))?
                        .as_str(),
                )
            };
            // `--python-pgo` is `cargo xtask build`'s spelling of `--pgo`,
            // kept as an alias.
            if flag == "--pgo" || flag == "--python-pgo" {
                options.pgo = match value {
                    "true" => true,
                    "false" => false,
                    _ => return Err(deps::error(format!("{flag} requires true or false"))),
                };
                continue;
            }
            let destination = match flag {
                "--crt-prefix" => &mut options.crt,
                "--cpython-prefix" => &mut options.cpython,
                "--fallback-prefix" => &mut options.fallback,
                "--pgo-prefix" => &mut options.profile,
                _ => return Err(deps::error(format!("unknown consumer option {flag}"))),
            };
            let path = root.join(value).canonicalize()?;
            if !path.is_dir() {
                return Err(deps::error(format!(
                    "invalid prepared prefix {}",
                    path.display()
                )));
            }
            deps::register_input(root, &path)?;
            *destination = Some(path);
        }
        if cfg!(windows) && options.pgo {
            return Err(deps::error("CPython PGO is unsupported on Windows"));
        }
        if !cfg!(target_os = "linux") && options.profile.is_some() {
            return Err(deps::error(
                "the standalone PGO consumer requires native Linux",
            ));
        }
        Ok(options)
    }
}
