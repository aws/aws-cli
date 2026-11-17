//! botocore's `EnvProvider`.
use crate::{Credentials, LoadError, Loaded, Provider, Refreshable, expiry};
use cli_core::EnvMap;

const METHOD: &str = "env";
const ACCESS_KEY: &str = "AWS_ACCESS_KEY_ID";
const SECRET_KEY: &str = "AWS_SECRET_ACCESS_KEY";
/// botocore reads the legacy name first, which the CRT does not read at all.
const TOKENS: [&str; 2] = ["AWS_SECURITY_TOKEN", "AWS_SESSION_TOKEN"];
const EXPIRY_TIME: &str = "AWS_CREDENTIAL_EXPIRATION";
const ACCOUNT_ID: &str = "AWS_ACCOUNT_ID";
/// Every variable the provider reads.
pub(crate) const VARIABLES: [&str; 6] = [
    ACCESS_KEY,
    SECRET_KEY,
    TOKENS[0],
    TOKENS[1],
    EXPIRY_TIME,
    ACCOUNT_ID,
];

/// Credentials from the environment.
///
/// `AWS_CREDENTIAL_EXPIRATION` makes them refreshable, and a refresh reads
/// the same variables again (`EnvProvider.load`). botocore reads the
/// process's live environment each time; the refresh here reads its own
/// clone of the environment the provider was given. A snapshot's clone
/// never changes, so its refresh returns what was loaded and fails once
/// that has expired, as botocore does in a process that leaves its own
/// environment alone.
pub struct EnvProvider<'a, E> {
    env: &'a E,
}

/// Omits the environment, which holds the secret key.
impl<E> std::fmt::Debug for EnvProvider<'_, E> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EnvProvider").finish_non_exhaustive()
    }
}

impl<'a, E: EnvMap> EnvProvider<'a, E> {
    pub fn new(env: &'a E) -> Self {
        Self { env }
    }
}

/// A variable's value; botocore treats an empty one as unset.
fn nonempty<'a>(env: &'a impl EnvMap, name: &str) -> Option<&'a str> {
    env.var(name).filter(|value| !value.is_empty())
}

/// botocore's `fetch_credentials`, which both the first load and every
/// refresh run. Only a refresh requires the expiry.
fn fetch(env: &impl EnvMap, require_expiry: bool) -> Result<Credentials, LoadError> {
    let require = |cred_var: &'static str| {
        nonempty(env, cred_var).ok_or(LoadError::PartialCredentials {
            provider: METHOD,
            cred_var,
        })
    };
    let access_key = require(ACCESS_KEY)?;
    let secret_key = require(SECRET_KEY)?;
    let token = TOKENS.iter().find_map(|name| nonempty(env, name));
    let expiry = if require_expiry {
        Some(require(EXPIRY_TIME)?)
    } else {
        nonempty(env, EXPIRY_TIME)
    };
    let expiry = expiry
        .map(|value| expiry::parse(METHOD, value))
        .transpose()?;
    Ok(Credentials::new(METHOD, access_key, secret_key)
        .with_session_token(token.map(str::to_owned))
        .with_account_id(nonempty(env, ACCOUNT_ID).map(str::to_owned))
        .with_expiry(expiry))
}

impl<E> Provider for EnvProvider<'_, E>
where
    E: EnvMap + Clone + Send + Sync + 'static,
{
    fn method(&self) -> &'static str {
        METHOD
    }
    /// An access key selects this provider (`EnvProvider.load`). A
    /// missing secret key is then an error, where the CRT's chain goes on
    /// to the next provider.
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        if nonempty(self.env, ACCESS_KEY).is_none() {
            return Ok(None);
        }
        let found = fetch(self.env, false)?;
        if found.expiry().is_none() {
            return Ok(Some(found.into()));
        }
        // The refresh outlives this provider and the chain, so it owns the
        // environment it reads.
        let env = self.env.clone();
        Ok(Some(
            Refreshable::new(found, move || fetch(&env, true)).into(),
        ))
    }
}

#[cfg(test)]
mod tests;
