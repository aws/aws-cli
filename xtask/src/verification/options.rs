//! Explicit test modes; unsupported combinations fail before building.
use super::error;
use crate::{TaskError, sanitizers::CMode};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum Mode {
    Workspace,
    Miri,
    ThreadSanitizer,
    Coverage,
    C(CMode),
}
#[derive(Debug, Eq, PartialEq)]
pub(super) struct Options {
    pub mode: Mode,
    pub packages: Vec<String>,
    pub profile: String,
    /// The libtest name filter every test command of the mode receives.
    pub filter: Option<String>,
}

pub(super) fn options(args: &[String]) -> Result<Options, TaskError> {
    let mut result = Options {
        mode: Mode::Workspace,
        packages: Vec::new(),
        profile: "dev".into(),
        filter: None,
    };
    let mut args = args.iter();
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "-p" | "--package" => result.packages.push(value(&mut args, flag)?.into()),
            "--profile" => result.profile = value(&mut args, flag)?.into(),
            "--filter" => {
                if result.filter.is_some() {
                    return Err(error("--filter may be given once"));
                }
                result.filter = Some(value(&mut args, flag)?.into());
            }
            _ => {
                if result.mode != Mode::Workspace {
                    return Err(error("select one test mode"));
                }
                result.mode = mode(flag, &mut args)?;
            }
        }
    }
    validate(&result)?;
    Ok(result)
}

fn mode(flag: &str, args: &mut std::slice::Iter<'_, String>) -> Result<Mode, TaskError> {
    match flag {
        "--miri" => Ok(Mode::Miri),
        "--sanitize-thread" => Ok(Mode::ThreadSanitizer),
        "--coverage" => Ok(Mode::Coverage),
        "--sanitize-c" => match value(args, flag)? {
            "trap" => Ok(Mode::C(CMode::Trap)),
            "full" => Ok(Mode::C(CMode::Full)),
            other => Err(error(format!("unknown C sanitizer mode: {other}"))),
        },
        _ => Err(error(format!("unknown test option: {flag}"))),
    }
}

fn value<'a>(args: &mut std::slice::Iter<'a, String>, flag: &str) -> Result<&'a str, TaskError> {
    args.next()
        .map(String::as_str)
        .ok_or_else(|| error(format!("{flag} requires a value")))
}

fn validate(options: &Options) -> Result<(), TaskError> {
    if !matches!(
        options.profile.as_str(),
        "dev" | "release" | "release-safe" | "release-small"
    ) {
        return Err(error(format!("unknown test profile: {}", options.profile)));
    }
    if !options.packages.is_empty()
        && !matches!(
            options.mode,
            Mode::Workspace | Mode::Miri | Mode::ThreadSanitizer
        )
    {
        return Err(error(
            "--package applies to workspace, Miri, and TSan tests",
        ));
    }
    if options.profile != "dev"
        && matches!(
            options.mode,
            Mode::Miri | Mode::ThreadSanitizer | Mode::Coverage
        )
    {
        return Err(error(
            "--profile applies to workspace and C sanitizer tests",
        ));
    }
    Ok(())
}
