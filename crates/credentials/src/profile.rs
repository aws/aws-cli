//! botocore's `SharedCredentialProvider` and `ConfigProvider`.
//!
//! The two read the same keys from different files and never see each
//! other's values. The CRT's profile provider merges the two files first, so
//! a key pair split across them works there and fails here, as in botocore.
use crate::{Credentials, LoadError, Loaded, Provider};
use awscli_config::{Entries, File, ParsedFiles, Sections, Status};
use std::fmt;

const ACCESS_KEY: &str = "aws_access_key_id";
const SECRET_KEY: &str = "aws_secret_access_key";
/// botocore reads the legacy name first, which the CRT does not read at all.
const TOKENS: [&str; 2] = ["aws_security_token", "aws_session_token"];
const ACCOUNT_ID: &str = "aws_account_id";

/// Credentials from the profile's section of the shared credentials file.
pub struct SharedCredentialsProvider<'a> {
    file: &'a File,
    profile: &'a str,
}

impl<'a> SharedCredentialsProvider<'a> {
    const METHOD: &'static str = "shared-credentials-file";
    pub fn new(files: &'a ParsedFiles, profile: &'a str) -> Self {
        Self {
            file: &files.credentials,
            profile,
        }
    }
}

impl Provider for SharedCredentialsProvider<'_> {
    fn method(&self) -> &'static str {
        Self::METHOD
    }
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        // The credentials file has no `profile ` prefix: a section's header
        // is its profile's name.
        load(Self::METHOD, self.file, &self.file.sections, self.profile)
    }
}

/// Names the profile and omits the file, which holds secret keys.
impl fmt::Debug for SharedCredentialsProvider<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SharedCredentialsProvider")
            .field("profile", &self.profile)
            .finish_non_exhaustive()
    }
}

/// Credentials from the profile's section of the shared config file.
pub struct ConfigProvider<'a> {
    file: &'a File,
    profiles: &'a Sections,
    profile: &'a str,
}

impl<'a> ConfigProvider<'a> {
    const METHOD: &'static str = "config-file";
    pub fn new(files: &'a ParsedFiles, profile: &'a str) -> Self {
        Self {
            file: &files.config,
            profiles: &files.organized.profiles,
            profile,
        }
    }
}

/// Names the profile and omits the file, which holds secret keys.
impl fmt::Debug for ConfigProvider<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ConfigProvider")
            .field("profile", &self.profile)
            .finish_non_exhaustive()
    }
}

impl Provider for ConfigProvider<'_> {
    fn method(&self) -> &'static str {
        Self::METHOD
    }
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        load(Self::METHOD, self.file, self.profiles, self.profile)
    }
}

/// Both providers' `load`: `profiles` are the sections of `file` by profile
/// name. A file that is absent or unreadable has no credentials; one that
/// does not parse is an error.
fn load(
    method: &'static str,
    file: &File,
    profiles: &Sections,
    profile: &str,
) -> Result<Option<Loaded>, LoadError> {
    if matches!(file.status, Status::ParseFailure(_) | Status::ResourceLimit) {
        return Err(LoadError::ConfigParse {
            path: file.source.clone(),
        });
    }
    let Some(entries) = profiles.get(profile) else {
        return Ok(None);
    };
    // The access key's presence selects the provider, whatever its value.
    let Some(access_key) = text(entries, ACCESS_KEY) else {
        return Ok(None);
    };
    let secret_key = text(entries, SECRET_KEY).ok_or(LoadError::PartialCredentials {
        provider: method,
        cred_var: SECRET_KEY,
    })?;
    let token = TOKENS.iter().find_map(|name| text(entries, name));
    let found = Credentials::new(method, access_key, secret_key)
        .with_session_token(token.map(str::to_owned))
        .with_account_id(text(entries, ACCOUNT_ID).map(str::to_owned));
    Ok(Some(found.into()))
}

/// A present key's value. A nested value reads as empty: botocore would
/// hold a dict there, which no request can be signed with.
pub(crate) fn text<'a>(entries: &'a Entries, key: &str) -> Option<&'a str> {
    entries
        .get(key)
        .map(|entry| entry.value.as_str().unwrap_or_default())
}
