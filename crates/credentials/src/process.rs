//! botocore's `ProcessProvider`.
//!
//! A profile's `credential_process` names a command that prints credentials
//! as JSON. Output with an `Expiration` makes the credentials refreshable,
//! and a refresh runs the same command again (`ProcessProvider.load`).
//!
//! The command is split into words as botocore's `compat_shell_split`
//! splits it: by Windows' own rules there, by `shlex`'s elsewhere.
//!
//! Not ported: the PyInstaller environment botocore restores for the child
//! (`original_ld_library_path`).
use crate::profile::text;
use crate::{Credentials, LoadError, Loaded, Provider, Refreshable, expiry};
use awscli_config::{ParsedFiles, Status};
use serde_json::{Map, Value};
#[cfg(unix)]
use std::ffi::OsStr;
use std::fmt;
use std::io;
use std::iter;
use std::mem;
use std::process::Output;
#[cfg(not(unix))]
use std::process::{Command, Stdio};
use std::sync::Arc;

const METHOD: &str = "custom-process";
const CREDENTIAL_PROCESS: &str = "credential_process";
const ACCOUNT_ID: &str = "aws_account_id";

/// What one run of a credential process left: whether it exited with
/// status zero, and what it wrote.
#[derive(Clone, Default, PartialEq, Eq)]
pub struct ProcessOutput {
    pub success: bool,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

/// Omits the output, which holds the secret key.
impl fmt::Debug for ProcessOutput {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ProcessOutput")
            .field("success", &self.success)
            .finish_non_exhaustive()
    }
}

/// How a credential process is run, botocore's `popen`.
///
/// The provider's refresh operation keeps a copy, so it is shared.
#[derive(Clone)]
pub struct Runner(Arc<Run>);

type Run = dyn Fn(&[String]) -> io::Result<ProcessOutput> + Send + Sync;

impl Runner {
    /// Runs the command as a child of this process and waits for it. The
    /// child reads this process's standard input, as botocore's does, so a
    /// command may prompt.
    pub fn system() -> Self {
        Self::new(|command| {
            let (program, arguments) = command
                .split_first()
                .ok_or_else(|| io::Error::other("the command is empty"))?;
            let output = started(program, arguments)?;
            Ok(ProcessOutput {
                success: output.status.success(),
                stdout: output.stdout,
                stderr: output.stderr,
            })
        })
    }
    /// Runs the command's words through `run`, for a test that stands in
    /// for the process.
    pub fn new(
        run: impl Fn(&[String]) -> io::Result<ProcessOutput> + Send + Sync + 'static,
    ) -> Self {
        Self(Arc::new(run))
    }
}

/// Finds `program` as the system does for its own `Command`.
#[cfg(not(unix))]
fn started(program: &str, arguments: &[String]) -> io::Result<Output> {
    Command::new(program)
        .args(arguments)
        .stdin(Stdio::inherit())
        .output()
}

/// CPython's default search path, `os.defpath`.
#[cfg(unix)]
const DEFAULT_PATH: &str = "/bin:/usr/bin";

/// Finds `program` as CPython's `subprocess` does (`Popen._execute_child`
/// and `_posixsubprocess`'s `child_exec`): a name with a directory
/// is run as given, and any other from each directory of `PATH` in turn,
/// an empty one being the working directory, until one starts. A candidate
/// the kernel cannot start moves the search on, and none is run through
/// `/bin/sh` as `Command` would run it.
///
/// # Errors
/// As [`cli_core::subprocess::output`]: when no candidate starts, the
/// failure `subprocess` raises.
#[cfg(unix)]
fn started(program: &str, arguments: &[String]) -> io::Result<Output> {
    if program.contains('/') {
        return cli_core::subprocess::output(&[program], program, arguments);
    }
    let path = std::env::var_os("PATH").unwrap_or_else(|| DEFAULT_PATH.into());
    searched(&path, program, arguments)
}

/// [`started`] for a bare `program`, searching `path`.
#[cfg(unix)]
fn searched(path: &OsStr, program: &str, arguments: &[String]) -> io::Result<Output> {
    // An empty directory joins to the bare name, which `execv` finds in the
    // working directory, as `os.path.join` builds it.
    let candidates: Vec<_> = std::env::split_paths(path)
        .map(|directory| directory.join(program))
        .collect();
    cli_core::subprocess::output(&candidates, program, arguments)
}

impl fmt::Debug for Runner {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Runner").finish_non_exhaustive()
    }
}

/// Credentials from the command the profile's `credential_process` names.
pub struct ProcessProvider<'a> {
    files: &'a ParsedFiles,
    profile: &'a str,
    runner: Runner,
}

impl<'a> ProcessProvider<'a> {
    /// The provider for `profile`, which runs its command with
    /// [`Runner::system`].
    pub fn new(files: &'a ParsedFiles, profile: &'a str) -> Self {
        Self::new_with_runner(files, profile, Runner::system())
    }
    pub fn new_with_runner(files: &'a ParsedFiles, profile: &'a str, runner: Runner) -> Self {
        Self {
            files,
            profile,
            runner,
        }
    }
}

/// Names the profile and omits the files, which hold secret keys.
impl fmt::Debug for ProcessProvider<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ProcessProvider")
            .field("profile", &self.profile)
            .finish_non_exhaustive()
    }
}

impl Provider for ProcessProvider<'_> {
    fn method(&self) -> &'static str {
        METHOD
    }
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        // The provider reads the session's `full_config`: the config file's
        // profiles with the credentials file's values laid over them
        // (`Session.full_config`). Either file failing to parse is an error.
        let Some(profiles) = &self.files.profiles else {
            return Err(parse_failure(self.files));
        };
        let Some(command) = profiles
            .get(self.profile)
            .and_then(|entries| text(entries, CREDENTIAL_PROCESS))
        else {
            return Ok(None);
        };
        let account_id = profiles
            .get(self.profile)
            .and_then(|entries| text(entries, ACCOUNT_ID));
        let process = Process {
            command: command.to_owned(),
            account_id: account_id.map(str::to_owned),
            runner: self.runner.clone(),
        };
        let found = process.retrieve()?;
        if found.expiry().is_none() {
            return Ok(Some(found.into()));
        }
        // The refresh outlives this provider and the chain, so it owns the
        // command it runs.
        Ok(Some(
            Refreshable::new(found, move || process.retrieve()).into(),
        ))
    }
}

/// The file whose failure left no merged profiles: the config file is read
/// first.
pub(crate) fn parse_failure(files: &ParsedFiles) -> LoadError {
    let failed =
        |status: &Status| matches!(status, Status::ParseFailure(_) | Status::ResourceLimit);
    let file = if failed(&files.config.status) {
        &files.config
    } else {
        &files.credentials
    };
    LoadError::ConfigParse {
        path: file.source.clone(),
    }
}

/// One profile's command, which the first load and every refresh run.
struct Process {
    command: String,
    /// The profile's `aws_account_id`, for output that names no account
    /// (`ProcessProvider._get_account_id`).
    account_id: Option<String>,
    runner: Runner,
}

impl Process {
    /// botocore's `_retrieve_credentials_using`.
    fn retrieve(&self) -> Result<Credentials, LoadError> {
        let command = if cfg!(windows) {
            windows_shell_split(&self.command)
        } else {
            shell_split(&self.command).map_err(str::to_owned)
        }
        .map_err(unusable)?;
        let output = (self.runner.0)(&command).map_err(|error| unusable(error.to_string()))?;
        if !output.success {
            return Err(LoadError::CredentialRetrieval {
                provider: METHOD,
                error_msg: String::from_utf8_lossy(&output.stderr).into_owned(),
            });
        }
        let parsed: Value =
            serde_json::from_slice(&output.stdout).map_err(|error| unusable(error.to_string()))?;
        let Value::Object(parsed) = parsed else {
            return Err(unusable("the output is not a JSON object".to_owned()));
        };
        self.credentials(&parsed)
    }

    /// The values botocore's refresh callable returns
    /// (`_retrieve_credentials_using`), read in botocore's order.
    fn credentials(&self, parsed: &Map<String, Value>) -> Result<Credentials, LoadError> {
        check_version(parsed.get("Version"))?;
        // Inside the callable only a required key that is absent fails
        // (`_retrieve_credentials_using`), and botocore looks for both
        // before anything reads a value. An advisory refresh forgives it.
        let access_key = required(parsed, "AccessKeyId")?;
        let secret_key = required(parsed, "SecretAccessKey")?;
        // The values are returned as they are and fail later, so each is
        // a fault in what the provider returned, which no refresh window
        // forgives. The expiry is the first that botocore reads
        // (`RefreshableCredentials`); the rest fail as it signs.
        let expiry = match parsed.get("Expiration") {
            None | Some(Value::Null) => None,
            Some(Value::String(text)) => Some(expiry::parse(METHOD, text)?),
            // dateutil's `parse` raises `TypeError` for anything else.
            Some(other) => {
                return Err(LoadError::Expiry {
                    provider: METHOD,
                    value: other.to_string(),
                });
            }
        };
        let access_key = string(access_key, "AccessKeyId")?;
        let secret_key = string(secret_key, "SecretAccessKey")?;
        let token = session_token(parsed)?;
        Ok(Credentials::new(METHOD, access_key, secret_key)
            .with_session_token(token.map(str::to_owned))
            .with_account_id(self.account_id(parsed).map(str::to_owned))
            .with_expiry(expiry))
    }

    /// botocore's `_get_account_id`: the output's `AccountId`, or the
    /// profile's when Python counts the output's as false.
    fn account_id<'a>(&'a self, parsed: &'a Map<String, Value>) -> Option<&'a str> {
        match parsed.get("AccountId") {
            Some(Value::String(account_id)) if !account_id.is_empty() => Some(account_id),
            // botocore keeps any other value Python counts as true, and
            // nothing checks it or signs with it. `Credentials` cannot
            // hold it, so no account is named.
            Some(other) if truthy(other) => None,
            _ => self.account_id.as_deref(),
        }
    }
}

fn unusable(reason: String) -> LoadError {
    LoadError::CredentialProcess { reason }
}

/// A member botocore reads with `parsed[key]`: one that is absent raises
/// `KeyError` inside the refresh callable. One that is there is returned
/// whatever it is, `null` included.
fn required<'a>(parsed: &'a Map<String, Value>, key: &'static str) -> Result<&'a Value, LoadError> {
    parsed
        .get(key)
        .ok_or_else(|| LoadError::CredentialRetrieval {
            provider: METHOD,
            error_msg: format!("Missing required key in response: '{key}'"),
        })
}

/// A value botocore stores unchecked
/// (`RefreshableCredentials._set_from_data`) and cannot sign with unless
/// it is a string.
fn string<'a>(value: &'a Value, key: &'static str) -> Result<&'a str, LoadError> {
    value.as_str().ok_or(LoadError::Metadata {
        provider: METHOD,
        key,
    })
}

/// botocore's `parsed.get('SessionToken')`, which it stores unchecked and
/// signs with only when Python counts it as true. So `null`, `false`, zero
/// and anything empty leave the header out, as an absent token does. Any
/// other value that is not a string cannot be signed with.
fn session_token(parsed: &Map<String, Value>) -> Result<Option<&str>, LoadError> {
    match parsed.get("SessionToken").filter(|token| truthy(token)) {
        None => Ok(None),
        Some(token) => string(token, "SessionToken").map(Some),
    }
}

/// Whether Python counts a JSON value as true.
fn truthy(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Bool(flag) => *flag,
        Value::Number(number) => number.as_f64() != Some(0.0),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(members) => !members.is_empty(),
    }
}

/// Only version 1 is supported (`_retrieve_credentials_using`). Python
/// compares with `!= 1`, which `1.0` and `true` pass as well.
fn check_version(version: Option<&Value>) -> Result<(), LoadError> {
    let shown = match version {
        Some(Value::Number(number)) if number.as_f64() == Some(1.0) => return Ok(()),
        Some(Value::Bool(true)) => return Ok(()),
        None => "<Version key not provided>".to_owned(),
        Some(Value::String(text)) => text.clone(),
        Some(Value::Null) => "None".to_owned(),
        Some(Value::Bool(false)) => "False".to_owned(),
        Some(other) => other.to_string(),
    };
    Err(LoadError::CredentialRetrieval {
        provider: METHOD,
        error_msg: format!(
            "Unsupported version '{shown}' for credential process provider, \
             supported versions: 1"
        ),
    })
}

/// Python's `shlex.split`, which botocore splits the command with off
/// Windows (`compat_shell_split`): POSIX quoting, whitespace between words,
/// no comments.
///
/// # Errors
/// The text `shlex` raises `ValueError` with: a quotation that is never
/// closed, or a backslash that ends the command.
fn shell_split(command: &str) -> Result<Vec<String>, &'static str> {
    const NO_CLOSING_QUOTATION: &str = "No closing quotation";
    const NO_ESCAPED_CHARACTER: &str = "No escaped character";
    let mut words = Vec::new();
    // `Some` from a word's first character or quote, so `''` is a word.
    let mut word: Option<String> = None;
    let mut characters = command.chars();
    while let Some(character) = characters.next() {
        match character {
            ' ' | '\t' | '\r' | '\n' => words.extend(word.take()),
            '\\' => word
                .get_or_insert_default()
                .push(characters.next().ok_or(NO_ESCAPED_CHARACTER)?),
            '\'' => {
                let word = word.get_or_insert_default();
                loop {
                    match characters.next().ok_or(NO_CLOSING_QUOTATION)? {
                        '\'' => break,
                        quoted => word.push(quoted),
                    }
                }
            }
            '"' => {
                let word = word.get_or_insert_default();
                loop {
                    match characters.next().ok_or(NO_CLOSING_QUOTATION)? {
                        '"' => break,
                        '\\' => {
                            // Inside double quotes a backslash escapes only
                            // itself and the quote; before anything else it
                            // stays.
                            let escaped = characters.next().ok_or(NO_ESCAPED_CHARACTER)?;
                            if !matches!(escaped, '\\' | '"') {
                                word.push('\\');
                            }
                            word.push(escaped);
                        }
                        quoted => word.push(quoted),
                    }
                }
            }
            plain => word.get_or_insert_default().push(plain),
        }
    }
    words.extend(word);
    Ok(words)
}

/// botocore's `_windows_shell_split`, which it splits the command with on
/// Windows: the C runtime's rules, where only space and tab part words,
/// the double quote is the only quote, and backslashes are literal unless
/// a run of them leads up to a double quote.
///
/// # Errors
/// The text botocore raises `ValueError` with when a quotation is never
/// closed.
fn windows_shell_split(command: &str) -> Result<Vec<String>, String> {
    let mut words = Vec::new();
    // `Some` from a word's first character or quote, so `""` is a word.
    let mut word: Option<String> = None;
    let mut quoted = false;
    // A run of backslashes waits for the character after it to say what
    // the run means.
    let mut backslashes = 0;
    for character in command.chars() {
        match character {
            '\\' => backslashes += 1,
            '"' => {
                // Before a quote each pair is one backslash, and one left
                // over makes the quote part of the word.
                let word = word.get_or_insert_default();
                word.extend(iter::repeat_n('\\', backslashes / 2));
                if mem::take(&mut backslashes) % 2 == 1 {
                    word.push('"');
                } else {
                    quoted = !quoted;
                }
            }
            ' ' | '\t' if !quoted => {
                keep_backslashes(&mut word, &mut backslashes);
                words.extend(word.take());
            }
            other => {
                keep_backslashes(&mut word, &mut backslashes);
                word.get_or_insert_default().push(other);
            }
        }
    }
    if quoted {
        return Err(format!("No closing quotation in string: {command}"));
    }
    keep_backslashes(&mut word, &mut backslashes);
    words.extend(word);
    Ok(words)
}

/// Ends a run of backslashes that leads up to no quote: each one stays.
fn keep_backslashes(word: &mut Option<String>, backslashes: &mut usize) {
    if *backslashes > 0 {
        word.get_or_insert_default()
            .extend(iter::repeat_n('\\', mem::take(backslashes)));
    }
}

#[cfg(test)]
mod tests;
