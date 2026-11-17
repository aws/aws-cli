//! botocore's `RefreshableCredentials` and `DeferredRefreshableCredentials`.
//!
//! The credentials hold the refresh operation of the provider that found
//! them and call nothing else. botocore's rules, kept as they are:
//!
//! * No refresh while at least fifteen minutes remain, the advisory window
//!   (`_DEFAULT_ADVISORY_REFRESH_TIMEOUT`).
//! * Inside the advisory window the first caller refreshes and waits for
//!   it. A caller that arrives meanwhile takes the current credentials
//!   without waiting, unless fewer than ten minutes remain, the mandatory
//!   window (`_DEFAULT_MANDATORY_REFRESH_TIMEOUT`), where it waits for the
//!   refresh and then refreshes again itself if that left the credentials
//!   inside the mandatory window (`RefreshableCredentials._refresh`).
//! * A provider that fails an advisory refresh leaves the current
//!   credentials in use; one that fails a mandatory refresh fails the
//!   caller (`RefreshableCredentials._protected_refresh`).
//! * Only a failure inside the provider's refresh operation is forgiven.
//!   What the provider returned is read after it, so an expiry that is
//!   missing or unreadable, or a value that is not text, fails the caller
//!   in either window (`_set_from_data`). The current
//!   credentials stay in place, as botocore's frozen ones do when the
//!   expiry fails to parse. A value that is not text botocore would keep,
//!   and fail to sign with, until its expiry came due.
//! * A refresh replaces the access key, secret key, token, expiry and
//!   account id together (`_set_from_data`), then fails the caller if the
//!   new credentials have expired already, in either window
//!   (`_protected_refresh`).
//! * Nothing backs off: every caller inside a window tries again.
//!
//! Not ported: windows other than the two defaults, which botocore lets a
//! provider choose (`RefreshableCredentials.__init__`).
use crate::{Credentials, LoadError};
use std::fmt;
use std::sync::{Arc, Mutex, MutexGuard, PoisonError, TryLockError};
use std::time::{Duration, SystemTime};

/// The time credentials are compared with, botocore's `time_fetcher`.
#[derive(Clone)]
pub struct Clock(Arc<dyn Fn() -> SystemTime + Send + Sync>);

impl Clock {
    /// The system's wall clock, as botocore's `_local_now` reads it.
    pub fn system() -> Self {
        Self::new(SystemTime::now)
    }
    /// A clock that reads `now`, for a test that moves time itself.
    pub fn new(now: impl Fn() -> SystemTime + Send + Sync + 'static) -> Self {
        Self(Arc::new(now))
    }
    pub(crate) fn now(&self) -> SystemTime {
        (self.0)()
    }
}

impl Default for Clock {
    fn default() -> Self {
        Self::system()
    }
}

impl fmt::Debug for Clock {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Clock").finish_non_exhaustive()
    }
}

/// A refresh that botocore raises to the caller that asked for credentials.
#[derive(Clone, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum RefreshError {
    /// The provider's refresh operation failed and the old credentials
    /// could not stand in; botocore raises the provider's own exception
    /// (`RefreshableCredentials._protected_refresh`).
    Provider(LoadError),
    /// The provider answered, with nothing, with an expiry that cannot be
    /// read or with a value that is not text. botocore meets these after
    /// its refresh callable has returned, so neither window forgives them
    /// (`RefreshableCredentials._set_from_data`).
    Metadata(LoadError),
    /// The refresh returned credentials that have expired already
    /// (`RefreshableCredentials._protected_refresh`).
    StillExpired,
    /// The refresh returned credentials without an expiry. botocore fails
    /// here inside dateutil, on `parse(None)`; the text is the one
    /// botocore's `_set_from_data` gives a refresh that lacks the key
    /// altogether.
    MissingExpiry { provider: &'static str },
}

impl fmt::Display for RefreshError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Provider(error) | Self::Metadata(error) => error.fmt(f),
            Self::StillExpired => f.write_str(
                "Credentials were refreshed, but the refreshed credentials are still expired.",
            ),
            Self::MissingExpiry { provider } => write!(
                f,
                "Error when retrieving credentials from {provider}: \
                 Credential refresh failed, response did not contain: expiry_time"
            ),
        }
    }
}

impl std::error::Error for RefreshError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Provider(error) | Self::Metadata(error) => Some(error),
            Self::StillExpired | Self::MissingExpiry { .. } => None,
        }
    }
}

type Refresh = Box<dyn Fn() -> Result<Credentials, LoadError> + Send + Sync>;

/// Credentials that replace themselves through the provider that found
/// them.
pub struct Refreshable {
    method: &'static str,
    /// botocore's `refresh_using`: the one provider's own operation.
    refresh: Refresh,
    clock: Clock,
    /// botocore's `_frozen_credentials`; `None` until a deferred set's
    /// first refresh.
    frozen: Mutex<Option<Credentials>>,
    /// botocore's `_refresh_lock`, held across a refresh.
    refreshing: Mutex<()>,
}

/// The advisory window: with less than this left a caller tries a refresh,
/// and does not wait for one another caller has under way
/// (`_DEFAULT_ADVISORY_REFRESH_TIMEOUT`).
const ADVISORY: Duration = Duration::from_secs(15 * 60);
/// The mandatory window: with less than this left every caller waits for
/// refreshed credentials (`_DEFAULT_MANDATORY_REFRESH_TIMEOUT`).
const MANDATORY: Duration = Duration::from_secs(10 * 60);

impl Refreshable {
    /// Credentials a provider found, with the operation that reads the same
    /// provider again. `initial` without an expiry never refreshes
    /// (`RefreshableCredentials.refresh_needed`).
    pub fn new(
        initial: Credentials,
        refresh: impl Fn() -> Result<Credentials, LoadError> + Send + Sync + 'static,
    ) -> Self {
        Self {
            method: initial.method(),
            refresh: Box::new(refresh),
            clock: Clock::system(),
            frozen: Mutex::new(Some(initial)),
            refreshing: Mutex::new(()),
        }
    }
    /// botocore's `DeferredRefreshableCredentials`: nothing to start with,
    /// so the first caller's refresh is a mandatory one.
    pub fn deferred(
        method: &'static str,
        refresh: impl Fn() -> Result<Credentials, LoadError> + Send + Sync + 'static,
    ) -> Self {
        Self {
            method,
            refresh: Box::new(refresh),
            clock: Clock::system(),
            frozen: Mutex::new(None),
            refreshing: Mutex::new(()),
        }
    }
    /// Reads the time from `clock` in place of the system's.
    #[must_use]
    pub fn with_clock(mut self, clock: Clock) -> Self {
        self.clock = clock;
        self
    }
    /// botocore's `method` of the provider that found the credentials.
    pub fn method(&self) -> &'static str {
        self.method
    }

    /// botocore's `get_frozen_credentials`: the
    /// credentials to sign one request with, refreshed first if they are
    /// due.
    ///
    /// It blocks while this caller refreshes, and while another caller's
    /// refresh runs if the credentials are inside the mandatory window.
    ///
    /// # Errors
    /// A failed mandatory refresh, or a refresh in either window that
    /// returned credentials which have expired already, carry no expiry
    /// that can be read, or hold a value that is not text.
    pub fn frozen(&self) -> Result<Credentials, RefreshError> {
        // `RefreshableCredentials._refresh`: the common case takes no
        // refresh lock.
        if let Some(current) = self.outside(ADVISORY) {
            return Ok(current);
        }
        let held = match self.refreshing.try_lock() {
            Ok(held) => Some(held),
            Err(TryLockError::Poisoned(poisoned)) => Some(poisoned.into_inner()),
            Err(TryLockError::WouldBlock) => None,
        };
        if let Some(_held) = held {
            // This caller refreshes.
            if let Some(current) = self.outside(ADVISORY) {
                return Ok(current);
            }
            return self.protected_refresh(self.outside(MANDATORY));
        }
        // Another caller is refreshing. Only the mandatory window makes
        // this one wait for it.
        match self.outside(MANDATORY) {
            Some(current) => Ok(current),
            None => self.frozen_after_waiting(),
        }
    }

    /// The rest of `get_frozen_credentials` for a caller that found
    /// another's refresh under way (`RefreshableCredentials._refresh`): it
    /// waits for that refresh, takes what it left if that is outside the
    /// mandatory window, and otherwise refreshes again itself, as a
    /// mandatory refresh. It never tries an advisory refresh of its own.
    ///
    /// [`Refreshable::frozen`] calls it when it finds the refresh lock
    /// held. A caller that must not block queues behind the refresh in
    /// place of blocking on that lock; it waited all the same, and calls
    /// this once the refresh ahead of it is done.
    ///
    /// # Errors
    /// As [`Refreshable::frozen`], for a refresh this caller runs itself.
    pub fn frozen_after_waiting(&self) -> Result<Credentials, RefreshError> {
        let _held = lock(&self.refreshing);
        match self.outside(MANDATORY) {
            Some(current) => Ok(current),
            None => self.protected_refresh(None),
        }
    }

    /// The current credentials while no refresh is due: at least the
    /// advisory window is left, where botocore returns them at once
    /// (`RefreshableCredentials._refresh`). It neither calls the provider
    /// nor waits.
    pub fn outside_advisory(&self) -> Option<Credentials> {
        self.outside(ADVISORY)
    }

    /// The current credentials while at least the mandatory window is
    /// left. A caller that finds another's refresh under way signs with
    /// them and does not wait for it (`_refresh`); on `None` it waits, and
    /// then calls [`Refreshable::frozen_after_waiting`]. It neither calls
    /// the provider nor waits.
    pub fn outside_mandatory(&self) -> Option<Credentials> {
        self.outside(MANDATORY)
    }

    /// The current credentials when they have at least `window` left,
    /// botocore's `not refresh_needed(window)`.
    fn outside(&self, window: Duration) -> Option<Credentials> {
        // `DeferredRefreshableCredentials.refresh_needed`: deferred
        // credentials always need their first refresh. The credentials are
        // copied out so that the lock, which a thread that must not block
        // takes, is released before the clock is read.
        let current = lock(&self.frozen).clone()?;
        let Some(expiry) = current.expiry() else {
            return Some(current);
        };
        // `refresh_needed`: enough time left means exactly the window or
        // more. A clock past the expiry leaves less than any window.
        let remaining = expiry.duration_since(self.clock.now()).ok()?;
        (remaining >= window).then_some(current)
    }

    /// botocore's `_protected_refresh`, which the
    /// caller holding the refresh lock runs. `fallback` is the current
    /// credentials when the refresh is advisory, and `None` when it is
    /// mandatory.
    fn protected_refresh(
        &self,
        fallback: Option<Credentials>,
    ) -> Result<Credentials, RefreshError> {
        let refreshed = match (self.refresh)() {
            Ok(refreshed) => refreshed,
            // botocore reads what the provider returned after the handler
            // that forgives an advisory failure (in `_set_from_data`), and
            // has not replaced the frozen credentials yet.
            Err(error) if error.is_metadata() => return Err(RefreshError::Metadata(error)),
            // The provider itself failed.
            Err(error) => return fallback.ok_or(RefreshError::Provider(error)),
        };
        if refreshed.expiry().is_none() {
            return Err(RefreshError::MissingExpiry {
                provider: self.method,
            });
        }
        *lock(&self.frozen) = Some(refreshed.clone());
        // `_protected_refresh`: the new credentials stay in place even when
        // they are refused, so the next caller refreshes again.
        if self.outside(Duration::ZERO).is_none() {
            return Err(RefreshError::StillExpired);
        }
        Ok(refreshed)
    }
}

/// Names the provider and the current access key, never a secret.
impl fmt::Debug for Refreshable {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Copied out, so the lock is not held while the formatter writes.
        let frozen = lock(&self.frozen).clone();
        f.debug_struct("Refreshable")
            .field("method", &self.method)
            .field("frozen", &frozen)
            .finish_non_exhaustive()
    }
}

/// A panic in a provider's refresh leaves the credentials as they were, so
/// a poisoned lock still guards a consistent value.
fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(PoisonError::into_inner)
}

#[cfg(test)]
mod tests;
