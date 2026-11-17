//! botocore's `InstanceMetadataProvider`.
//!
//! The provider asks the instance metadata service for the credentials of
//! the role attached to the instance. They expire, so they are refreshable,
//! and a refresh asks the service again (`InstanceMetadataProvider.load`).
//!
//! botocore hands its provider a fetcher, and this one is handed a
//! [`RoleFetcher`], which stands for
//! `InstanceMetadataFetcher.retrieve_iam_role_credentials`.
//! [`Fetcher`] is that fetcher: the requests, the retries and the errors
//! are botocore's, and it sends each request through a [`Transport`] the
//! caller supplies, so this crate still reaches no network itself.
use crate::{Credentials, LoadError, Loaded, Provider, Refreshable};
use cli_core::EnvMap;
use std::fmt;
use std::sync::Arc;
use std::time::SystemTime;

mod expiration;
mod fetch;
mod location;
mod repr;
mod settings;

pub(crate) use fetch::raised;
#[doc(inline)]
pub use fetch::{Fetcher, Request, Response, Transport, TransportError};
#[doc(inline)]
pub use location::Location;
pub(crate) use repr::text as repr_text;
#[doc(inline)]
pub use settings::{InstanceMetadataSettings, Timeout};
pub(crate) use settings::{VARIABLES, masked};

const METHOD: &str = "iam-role";
const DISABLED: &str = "AWS_EC2_METADATA_DISABLED";

/// What the service returned for the instance's role: botocore's metadata
/// without the role's name, which it only logs.
#[derive(Clone, PartialEq, Eq)]
pub struct RoleCredentials {
    pub access_key: String,
    pub secret_key: String,
    pub token: String,
    pub expiry: SystemTime,
}

/// Names the access key, never the secret or the token.
impl fmt::Debug for RoleCredentials {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RoleCredentials")
            .field("access_key", &self.access_key)
            .field("expiry", &self.expiry)
            .finish_non_exhaustive()
    }
}

impl From<RoleCredentials> for Credentials {
    fn from(role: RoleCredentials) -> Self {
        Self::new(METHOD, role.access_key, role.secret_key)
            .with_session_token(Some(role.token))
            .with_expiry(Some(role.expiry))
    }
}

/// How the service is asked, botocore's `retrieve_iam_role_credentials`:
/// `Ok(None)` is its empty answer, which it gives for a service that
/// cannot be reached or that has no usable credentials, and an error is
/// an exception it lets through. [`Fetcher`] is the one that asks the
/// service.
///
/// The provider's refresh operation keeps a copy, so it is shared.
#[derive(Clone)]
pub struct RoleFetcher(Arc<Fetch>);

type Fetch = dyn Fn() -> Result<Option<RoleCredentials>, LoadError> + Send + Sync;

impl RoleFetcher {
    pub fn new(
        fetch: impl Fn() -> Result<Option<RoleCredentials>, LoadError> + Send + Sync + 'static,
    ) -> Self {
        Self(Arc::new(fetch))
    }
    /// What botocore's provider returns once it asks the service
    /// (`InstanceMetadataProvider.load`): nothing for the fetcher's empty
    /// answer, else credentials that a refresh asks the service for again.
    ///
    /// # Errors
    /// What the fetcher raises, which stops the chain.
    pub fn load(&self) -> Result<Option<Loaded>, LoadError> {
        let Some(found) = (self.0)()? else {
            return Ok(None);
        };
        // The refresh outlives the chain, so it owns the fetcher it asks.
        // botocore refuses a refresh's empty answer once its refresh
        // callable has returned (`RefreshableCredentials._protected_refresh`
        // and `_set_from_data`); what the fetcher raises, it raises inside
        // the callable.
        let fetcher = self.clone();
        let refresh = move || {
            let found = (fetcher.0)()?.ok_or(LoadError::EmptyRefresh { provider: METHOD })?;
            Ok(found.into())
        };
        Ok(Some(Refreshable::new(found.into(), refresh).into()))
    }
}

impl From<Fetcher> for RoleFetcher {
    fn from(fetcher: Fetcher) -> Self {
        Self::new(move || fetcher.retrieve())
    }
}

impl fmt::Debug for RoleFetcher {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RoleFetcher").finish_non_exhaustive()
    }
}

/// Credentials of the role attached to the instance.
pub struct InstanceMetadataProvider<'a, E> {
    env: &'a E,
    fetcher: RoleFetcher,
}

impl<'a, E: EnvMap> InstanceMetadataProvider<'a, E> {
    pub fn new(env: &'a E, fetcher: RoleFetcher) -> Self {
        Self { env, fetcher }
    }
}

/// Omits the environment, which holds the secret key.
impl<E> fmt::Debug for InstanceMetadataProvider<'_, E> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("InstanceMetadataProvider")
            .finish_non_exhaustive()
    }
}

impl<E: EnvMap> Provider for InstanceMetadataProvider<'_, E> {
    fn method(&self) -> &'static str {
        METHOD
    }
    /// A service that is disabled, cannot be reached or has no credentials
    /// passes to the next provider (`InstanceMetadataProvider.load`).
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        // botocore's fetcher answers nothing, without a request, when the
        // variable is `true` in any case (`IMDSFetcher._assert_enabled`).
        let disabled = self
            .env
            .var(DISABLED)
            .is_some_and(|value| value.eq_ignore_ascii_case("true"));
        if disabled {
            return Ok(None);
        }
        self.fetcher.load()
    }
}

#[cfg(test)]
mod tests;
