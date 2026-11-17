//! Blackbox runner options: one AWS CLI per run, with pytest selection passed through.

use std::path::PathBuf;

use crate::product::options::{LinkMode, PythonPayload};
use crate::{TaskError, deps};

/// The AWS CLI the run tests.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(super) enum Binary {
    /// The default-profile product, which `harness::binary` checks
    /// the host for.
    #[default]
    Built,
    /// A built binary at this path, which `ci product` tests.
    Explicit(String),
    /// Another AWS CLI, such as the public one of the in-tree version, which
    /// must pass every test but the upstream failures and upstream issues.
    External(String),
}

impl Binary {
    /// Whether the binary is this repository's, whose known native gaps the
    /// run applies.
    pub(super) fn is_built(&self) -> bool {
        !matches!(self, Self::External(_))
    }

    /// The name of the directory that holds the run's reports.
    pub(super) fn report_name(&self) -> &'static str {
        if self.is_built() { "built" } else { "external" }
    }
}

/// The pytest sessions the run runs.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) enum Suite {
    /// Upstream's tests and then the repository's.
    #[default]
    All,
    /// Upstream's tests alone.
    Upstream,
    /// The repository's tests, under `tests/blackbox/tests`, alone.
    Repo,
}

impl Suite {
    /// The names of the sessions the suite runs, in run.py's order.
    pub(super) fn sessions(self) -> &'static [&'static str] {
        match self {
            Self::All => &["upstream", "repo"],
            Self::Upstream => &["upstream"],
            Self::Repo => &["repo"],
        }
    }

    /// The `--suite` value run.py takes, or `None` for every session.
    pub(super) fn runner_arg(self) -> Option<&'static str> {
        match self {
            Self::All => None,
            Self::Upstream => Some("upstream"),
            Self::Repo => Some("repo"),
        }
    }
}

/// How a system build links the CRT.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum CrtLink {
    Static,
    Shared,
}

/// The build options that made the built binary, as far as its executable
/// and payload tests depend on them: by default the static build.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Build {
    pub link_mode: LinkMode,
    pub crt_link: CrtLink,
    pub payload: PythonPayload,
    /// The system Python a system build linked, whose ABI the dynamic link
    /// check requires; the pinned ABI when absent.
    pub python_exe: Option<PathBuf>,
}

impl Default for Build {
    fn default() -> Self {
        Self {
            link_mode: LinkMode::Static,
            crt_link: CrtLink::Static,
            payload: PythonPayload::Embedded,
            python_exe: None,
        }
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
pub(super) struct Options {
    pub binary: Binary,
    pub build: Build,
    pub suite: Suite,
    pub run_all: bool,
    /// Variables set in the environment of every command of the AWS CLI,
    /// in the order given, as name and value.
    pub env: Vec<(String, String)>,
    /// Arguments after `--`, forwarded unchanged to the shared runner and pytest.
    pub forwarded: Vec<String>,
}

impl Options {
    /// The artifact selection in the form `harness::binary` accepts. An
    /// external AWS CLI is no artifact, so it selects none.
    pub(super) fn artifact_args(&self) -> Vec<String> {
        match &self.binary {
            Binary::Explicit(path) => vec!["--aws-binary".to_owned(), path.clone()],
            Binary::Built | Binary::External(_) => Vec::new(),
        }
    }
}

pub(super) fn parse(args: &[String]) -> Result<Options, TaskError> {
    let (own, forwarded) = args
        .iter()
        .position(|arg| arg == "--")
        .map_or((args, &[][..]), |index| {
            (&args[..index], &args[index + 1..])
        });
    let mut options = Options::default();
    let mut given = BuildOptions::default();
    let mut own = own.iter();
    while let Some(arg) = own.next() {
        match arg.as_str() {
            "--aws-binary" if options.binary == Binary::Built => {
                options.binary = Binary::Explicit(value(&mut own, arg)?.to_owned());
            }
            "--external-binary" if options.binary == Binary::Built => {
                options.binary = Binary::External(value(&mut own, arg)?.to_owned());
            }
            "--suite" if options.suite == Suite::All => {
                options.suite = match value(&mut own, arg)? {
                    "upstream" => Suite::Upstream,
                    "repo" => Suite::Repo,
                    other => {
                        return Err(deps::error(format!(
                            "--suite takes upstream or repo, not {other:?}"
                        )));
                    }
                };
            }
            "--run-all" if !options.run_all => options.run_all = true,
            "--env" => {
                let assignment = value(&mut own, arg)?;
                let (name, value) = assignment.split_once('=').ok_or_else(|| {
                    deps::error(format!("--env requires NAME=VALUE, not {assignment:?}"))
                })?;
                options.env.push((name.to_owned(), value.to_owned()));
            }
            _ => {
                if !given.take(arg, &mut own)? {
                    return Err(usage(arg));
                }
            }
        }
    }
    if given.any_given() && !options.binary.is_built() {
        return Err(deps::error(
            "another AWS CLI has no build options; --link-mode, --crt-link, \
             --python-payload, and --python-exe describe the built binary",
        ));
    }
    options.build = given.build()?;
    if let Some(arg) = forwarded.iter().find(|arg| runner_owned(arg)) {
        return Err(deps::error(format!(
            "blackbox argument {arg:?} after -- is set by xtask; pass \
             xtask's own options, such as --aws-binary, --suite, or --env, \
             before --"
        )));
    }
    options.forwarded = forwarded.to_vec();
    Ok(options)
}

/// The build options as given, each at most once.
#[derive(Default)]
struct BuildOptions {
    link_mode: Option<LinkMode>,
    crt_link: Option<CrtLink>,
    payload: Option<PythonPayload>,
    python_exe: Option<PathBuf>,
}

impl BuildOptions {
    /// Take the value of `arg`, a build option not given before, from
    /// `args`; false when `arg` is no such option.
    fn take(
        &mut self,
        arg: &str,
        args: &mut std::slice::Iter<'_, String>,
    ) -> Result<bool, TaskError> {
        match arg {
            "--link-mode" if self.link_mode.is_none() => {
                self.link_mode = Some(match value(args, arg)? {
                    "static" => LinkMode::Static,
                    "system" => LinkMode::System,
                    other => return Err(choice(arg, "static or system", other)),
                });
            }
            "--crt-link" if self.crt_link.is_none() => {
                self.crt_link = Some(match value(args, arg)? {
                    "static" => CrtLink::Static,
                    "shared" => CrtLink::Shared,
                    other => return Err(choice(arg, "static or shared", other)),
                });
            }
            "--python-payload" if self.payload.is_none() => {
                self.payload = Some(match value(args, arg)? {
                    "embedded" => PythonPayload::Embedded,
                    "system" => PythonPayload::System,
                    other => return Err(choice(arg, "embedded or system", other)),
                });
            }
            "--python-exe" if self.python_exe.is_none() => {
                self.python_exe = Some(PathBuf::from(value(args, arg)?));
            }
            _ => return Ok(false),
        }
        Ok(true)
    }

    fn any_given(&self) -> bool {
        self.link_mode.is_some()
            || self.crt_link.is_some()
            || self.payload.is_some()
            || self.python_exe.is_some()
    }

    /// The build the options describe, with `cargo xtask build`'s rules: a
    /// system build links the CRT shared unless told otherwise, and the
    /// static build has neither a shared CRT, the system payload, nor a
    /// system Python.
    fn build(self) -> Result<Build, TaskError> {
        let link_mode = self.link_mode.unwrap_or(LinkMode::Static);
        let payload = self.payload.unwrap_or(PythonPayload::Embedded);
        let crt_link = self.crt_link.unwrap_or(match link_mode {
            LinkMode::Static => CrtLink::Static,
            LinkMode::System => CrtLink::Shared,
        });
        if link_mode == LinkMode::Static {
            if crt_link == CrtLink::Shared {
                return Err(deps::error("shared CRT requires --link-mode system"));
            }
            if payload == PythonPayload::System {
                return Err(deps::error(
                    "system Python payload requires --link-mode system",
                ));
            }
            if self.python_exe.is_some() {
                return Err(deps::error("--python-exe requires --link-mode system"));
            }
        }
        Ok(Build {
            link_mode,
            crt_link,
            payload,
            python_exe: self.python_exe,
        })
    }
}

fn choice(flag: &str, choices: &str, value: &str) -> TaskError {
    deps::error(format!("{flag} takes {choices}, not {value:?}"))
}

fn value<'a>(args: &mut std::slice::Iter<'a, String>, flag: &str) -> Result<&'a str, TaskError> {
    args.next()
        .map(String::as_str)
        .ok_or_else(|| deps::error(format!("{flag} requires a value")))
}

fn usage(arg: &str) -> TaskError {
    deps::error(format!(
        "unsupported blackbox argument {arg:?}; usage: cargo xtask blackbox \
         [--aws-binary PATH | --external-binary PATH] \
         [--link-mode static|system] [--crt-link static|shared] \
         [--python-payload embedded|system] [--python-exe PATH] \
         [--suite upstream|repo] [--run-all] \
         [--env NAME=VALUE]... [-- PYTEST_ARGS...]"
    ))
}

/// Options whose value xtask supplies, so a forwarded copy would contradict it.
fn runner_owned(arg: &str) -> bool {
    [
        "--aws-binary",
        "--aws-cli-source",
        "--cache-dir",
        "--known-gaps",
        "--upstream-failures",
        "--link-mode",
        "--crt-link",
        "--python-payload",
        "--python-abi",
        "--suite",
        "--run-all",
        "--env",
        "--junit-dir",
        "--junitxml",
        "--junit-xml",
    ]
    .iter()
    .any(|flag| {
        arg.strip_prefix(flag)
            .is_some_and(|rest| rest.is_empty() || rest.starts_with('='))
    })
}

#[cfg(test)]
mod tests;
