//! The seam where the CLI's own credentials reach the CRT's signer.
//!
//! A signed runtime builds aws-c-auth's delegate provider for the
//! [`Delegate`] its options name, and no other provider: the CLI finds its
//! credentials with its own chain. The S3 client's signing configuration
//! holds that provider, and aws-c-auth asks it for credentials each time it
//! signs a request.
use std::fmt;
use std::sync::Arc;
use std::time::SystemTime;

/// Credentials borrowed to answer one [`Query`]; the CRT copies them.
///
/// The expiry rides along on the CRT's copy and nothing there acts on it:
/// the signer does not compare it with the clock, and the CRT caches
/// nothing between queries. The delegate decides when its credentials are
/// stale, and answers each query with ones that are not.
#[derive(Clone, Copy)]
pub struct View<'a> {
    pub access_key_id: &'a str,
    pub secret_access_key: &'a str,
    pub session_token: Option<&'a str>,
    pub account_id: Option<&'a str>,
    /// When the credentials stop being valid, to the whole second; `None`
    /// for ones that never do.
    pub expiration: Option<SystemTime>,
}

/// Names the access key, never the secret or the token.
impl fmt::Debug for View<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("View")
            .field("access_key_id", &self.access_key_id)
            .field("account_id", &self.account_id)
            .field("expiration", &self.expiration)
            .finish_non_exhaustive()
    }
}

type Answer = Box<dyn for<'a> FnOnce(Option<View<'a>>) + Send>;

/// One request from the CRT's signer for credentials.
///
/// A query is answered exactly once, from any thread, during
/// [`Delegate::credentials`] or after it returns. Dropping it unanswered
/// reports a failure, so a signer never waits on a query that was lost.
pub struct Query {
    answer: Option<Answer>,
}

impl Query {
    /// A query that `answer` receives the result of: the credentials, or
    /// `None` for a failure.
    pub fn new(answer: impl for<'a> FnOnce(Option<View<'a>>) + Send + 'static) -> Self {
        Self {
            answer: Some(Box::new(answer)),
        }
    }
    /// Signs the request with `credentials`.
    pub fn complete(mut self, credentials: View<'_>) {
        if let Some(answer) = self.answer.take() {
            answer(Some(credentials));
        }
    }
    /// Fails the request with the CRT's `AWS_AUTH_SIGNING_NO_CREDENTIALS`.
    ///
    /// The signer reports that one code for every failure, so a delegate
    /// keeps the reason itself for the command to print
    /// ([`Delegate::failure`]).
    pub fn fail(self) {
        drop(self);
    }
}

impl Drop for Query {
    fn drop(&mut self) {
        if let Some(answer) = self.answer.take() {
            answer(None);
        }
    }
}

impl fmt::Debug for Query {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Query")
            .field("answered", &self.answer.is_none())
            .finish()
    }
}

/// The CLI's source of signing credentials.
pub trait Delegate: Send + Sync + fmt::Debug {
    /// Answers one signing request.
    ///
    /// The CRT calls this for every HTTP request it signs, on one of its
    /// own threads, so this must not block. Answer from memory, or move
    /// `query` to another thread and answer it there: a delegate whose
    /// credentials are being refreshed keeps the query until they are, and
    /// the request it belongs to waits while the CRT's threads go on.
    fn credentials(&self, query: Query);
    /// Hands the delegate each runtime that signs with it, before that
    /// runtime is returned to the caller that builds it, so before it sends
    /// anything.
    ///
    /// It runs on the thread that builds the runtime, which may wait here:
    /// a delegate whose credentials come from a service the runtime
    /// reaches, through [`crate::Runtime::http_client`], asks it now.
    ///
    /// # Errors
    /// The delegate cannot serve the runtime, which is then not built: its
    /// construction fails with the code a failed query gives,
    /// `AWS_AUTH_SIGNING_NO_CREDENTIALS`, and the reason stays with the
    /// delegate ([`Delegate::failure`]).
    fn attach(&self, runtime: &crate::Runtime) -> Result<(), Unavailable> {
        let _ = runtime;
        Ok(())
    }
    /// Why the delegate refused its runtime, or else why the latest query
    /// it failed could not be answered, in the words the command prints,
    /// when the delegate has more to say than that it found no
    /// credentials. The signer reports every failed query as one code, so
    /// the reason stays with the delegate.
    fn failure(&self) -> Option<String> {
        None
    }
}

/// A delegate that cannot serve the runtime it was handed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Unavailable;

/// Where a signed runtime's credentials come from.
#[derive(Clone, Debug, Default)]
pub enum Source {
    /// Nowhere: every request the runtime signs fails as one whose
    /// delegate failed its query. An unsigned runtime asks for none.
    #[default]
    Missing,
    /// The CLI's own providers.
    Delegate(Arc<dyn Delegate>),
}

impl Source {
    /// The delegate's [`Delegate::failure`].
    pub fn failure(&self) -> Option<String> {
        match self {
            Self::Missing => None,
            Self::Delegate(delegate) => delegate.failure(),
        }
    }
    /// The delegate the runtime's provider asks.
    pub(crate) fn delegate(&self) -> Arc<dyn Delegate> {
        match self {
            Self::Missing => Arc::new(Missing),
            Self::Delegate(delegate) => Arc::clone(delegate),
        }
    }
}

/// Fails every query.
#[derive(Debug)]
struct Missing;

impl Delegate for Missing {
    fn credentials(&self, query: Query) {
        query.fail();
    }
}

/// Two delegates are equal when they are the same object.
impl PartialEq for Source {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Missing, Self::Missing) => true,
            (Self::Delegate(left), Self::Delegate(right)) => Arc::ptr_eq(left, right),
            _ => false,
        }
    }
}

pub(crate) mod native;
#[cfg(test)]
mod tests;
