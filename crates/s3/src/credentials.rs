//! The CLI's own credential chain as a native S3 client's signing credentials.
//!
//! `command::copy_runtime_options` walks the chain once for a command that
//! signs, with [`Chain::walk`], and gives the runtime [`Chain::source`] as
//! its `RuntimeOptions::credentials`.
//!
//! # Refreshing without blocking the CRT
//!
//! botocore refreshes inside `get_frozen_credentials`, on the thread that
//! is about to sign, and that thread waits. The CRT asks for credentials on
//! an event-loop thread that must not wait, so a query that needs a refresh
//! or must wait for one is parked, and one refresh thread, started on
//! demand, runs botocore's blocking path for the parked queries.
//!
//! The refresh thread stands for botocore's refresh lock, held from the
//! query the thread is started for until no query is left waiting. Each
//! query then takes the branch botocore's caller takes
//! (`RefreshableCredentials._refresh`):
//!
//! * Credentials outside the advisory window are answered at once, on the
//!   CRT's thread.
//! * A query that finds no refresh thread took the lock. It starts the
//!   thread and refreshes through the provider that resolved.
//! * A query that finds the thread running lost the lock to it. With the
//!   mandatory window still ahead it is answered at once with the current
//!   credentials. Inside that window it waits, behind whichever queries
//!   the thread still has, and is then signed with what their refreshes
//!   left; it refreshes again itself only if that is still inside the
//!   mandatory window, and never tries an advisory refresh.
//!
//! The request a parked query belongs to waits, as botocore's caller does;
//! the CRT's threads do not. So a request is never signed with credentials
//! botocore would have replaced first, one refresh serves every request
//! that waited for it, and a refresh botocore raises fails the request it
//! would have failed. The signer reports every failure as one code, so the
//! reason stays here, in [`Resolved::refresh_error`], for the command to
//! print.
//!
//! A CRT thread takes two locks on the way: the one around the current
//! credentials, to copy them, and the one around the parked queries, to
//! see whether the refresh thread runs and to add a query. Neither is ever
//! held across a provider's refresh, a read of the clock or a query's
//! answer.
//!
//! # Container and instance metadata
//!
//! The chain's last two providers ask the container's endpoint and the
//! instance metadata service with botocore's own fetchers
//! ([`::credentials::ContainerFetcher`], [`::credentials::Fetcher`]), whose
//! requests go out through the HTTP client of the runtime that will sign
//! ([`crt::http::Client`]). So a walk that reaches either provider with
//! something to ask stops there, and the service is asked once the runtime
//! exists: the runtime hands itself to its delegate ([`Delegate::attach`])
//! before it is returned to the command, so before any request. The
//! container provider then answers or fails, and no provider follows the
//! instance's, so the result is the single walk botocore makes as it
//! creates the client, and an error the fetcher raises fails the client's
//! creation as it does botocore's.
//!
//! The fetch waits for each answer. The first runs on the thread that
//! builds the runtime, and a refresh runs it on the refresh thread; the
//! CRT's threads, which deliver the answers, never wait for one. Each wait
//! ends at the service's configured timeout: see [`crt::http`].
use ::credentials::{
    Clock, ContainerEndpoint, ContainerFetch, ContainerFetcher, Credentials, Fetcher,
    InstanceMetadataSettings, LoadError, Loaded, Location, Profile, RefreshError, Resolver,
    RoleFetcher, Transport, TransportError, default_resolver,
};
use awscli_config::ParsedFiles;
use cli_core::EnvMap;
use cli_core::proxy::{Forward, ForwardProxy};
use crt::credentials::{Delegate, Query, Source, Unavailable, View};
use crt::http::{Client, Error as HttpError};
use std::cell::RefCell;
use std::collections::VecDeque;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, MutexGuard, OnceLock, PoisonError};
use std::time::Duration;

/// The credentials a chain found, as botocore's session holds the result of
/// `get_credentials()` for a client: found once, then asked for by every
/// request. The chain itself is never asked again; credentials that expire
/// refresh through the provider that found them.
///
/// A chain that found none is not an error here. As in botocore, each
/// request then fails to sign, which the CLI reports as "Unable to locate
/// credentials".
///
/// Clones share the credentials, so a command keeps one to read
/// [`Resolved::refresh_error`] after it hands the runtime another.
#[derive(Clone, Debug)]
pub struct Resolved(Option<Arc<Live>>);

impl Resolved {
    /// Asks `resolver` once, before the client exists.
    ///
    /// # Errors
    /// A provider that is configured wrongly, which botocore raises as it
    /// creates the client, before any request.
    pub fn load(resolver: &Resolver<'_>) -> Result<Self, LoadError> {
        resolver.load_credentials().map(Self::new)
    }
    /// What a chain found: `None` for a chain that found nothing.
    pub fn new(loaded: Option<Loaded>) -> Self {
        Self(loaded.map(|loaded| {
            Arc::new(Live {
                loaded,
                waiting: Mutex::default(),
                refresh_error: Mutex::default(),
            })
        }))
    }
    /// The provider that found the credentials, botocore's `method`.
    pub fn method(&self) -> Option<&'static str> {
        self.0.as_ref().map(|live| live.loaded.method())
    }
    /// The runtime option that signs with these credentials.
    pub fn source(&self) -> Source {
        Source::Delegate(Arc::new(self.clone()))
    }
    /// Why the latest request that waited for a refresh failed to sign:
    /// the error botocore would have raised to that request.
    pub fn refresh_error(&self) -> Option<RefreshError> {
        lock(&self.0.as_ref()?.refresh_error).clone()
    }
}

impl Delegate for Resolved {
    /// Answers from memory, or parks the query for the refresh thread, so
    /// it never blocks the CRT's thread.
    fn credentials(&self, query: Query) {
        let Some(live) = &self.0 else {
            return query.fail();
        };
        // `_refresh`: no refresh is due.
        if let Some(credentials) = live.loaded.outside_advisory() {
            return answer(query, &credentials);
        }
        // Read here, before the lock on the parked queries is taken.
        let usable = live.loaded.outside_mandatory();
        live.park(query, usable);
    }
}

/// A command's signing credentials: its chain, walked once.
///
/// Clones share the walk. A command reads why a request failed to sign
/// from the runtime's own option ([`Source::failure`]).
#[derive(Clone, Debug)]
pub struct Chain(Arc<Walked>);

#[derive(Debug)]
struct Walked {
    /// The service to ask, for a walk that reached the container provider
    /// with an endpoint, or the instance provider with nothing found.
    metadata: Option<Metadata>,
    /// What the credentials are compared with, when not the system's clock.
    clock: Option<Clock>,
    /// What the chain found, or the error that stopped it, once every
    /// provider the walk reached has answered.
    found: OnceLock<Result<Resolved, LoadError>>,
}

/// The container's endpoint or the instance metadata service, as the chain
/// asks it.
#[derive(Debug)]
struct Metadata {
    /// The runtimes the requests go out through.
    service: Arc<Service>,
    /// botocore's fetcher, sending through `service`.
    fetcher: Remote,
}

#[derive(Debug)]
enum Remote {
    Container(ContainerFetcher, ContainerEndpoint),
    Instance(RoleFetcher),
}

impl Metadata {
    /// The container's endpoint, asked directly: botocore's container
    /// fetcher has a session of its own, without proxies
    /// (`ContainerMetadataFetcher`).
    fn container(endpoint: ContainerEndpoint) -> Self {
        let service = Arc::new(Service {
            forward: Forward::Direct,
            clients: Mutex::default(),
        });
        let transport = Arc::clone(&service) as Arc<dyn Transport>;
        Self {
            service,
            fetcher: Remote::Container(ContainerFetcher::new(transport), endpoint),
        }
    }
}

impl Remote {
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        match self {
            Self::Container(fetcher, endpoint) => fetcher.load(endpoint.clone()).map(Some),
            Self::Instance(fetcher) => fetcher.load(),
        }
    }
}

impl Chain {
    /// Walks botocore's chain for `profile`, as botocore does when it
    /// creates the client (`Session.create_client`), up to the container or
    /// instance metadata provider, which waits for the runtime.
    ///
    /// # Errors
    /// A provider that is configured wrongly or that failed, which
    /// botocore raises before any request, and settings of the instance
    /// metadata service that botocore refuses as it builds its chain.
    pub fn walk(
        env: &impl EnvMap,
        files: &ParsedFiles,
        profile: Profile<'_>,
    ) -> Result<Self, LoadError> {
        Self::walk_with_clock(env, files, profile, None)
    }
    /// [`Chain::walk`], comparing what is found with `clock`.
    pub(crate) fn walk_with_clock(
        env: &impl EnvMap,
        files: &ParsedFiles,
        profile: Profile<'_>,
        clock: Option<Clock>,
    ) -> Result<Self, LoadError> {
        let proxies = cli_core::proxy::Environment::from_map(env);
        let (Profile::Explicit(name) | Profile::Ambient(name)) = profile;
        // botocore builds its fetcher, and refuses its settings, before any
        // provider is asked (`create_credential_resolver`). The settings refuse
        // variables that are not Unicode too, which the copy leaves out.
        let settings = InstanceMetadataSettings::resolve(env, files, name)?;
        let env = ::credentials::environment(env);
        // Stands for the service until a runtime can ask it, and notes
        // that the walk came this far.
        let reached = Arc::new(AtomicBool::new(false));
        let noted = Arc::clone(&reached);
        let probe = RoleFetcher::new(move || {
            noted.store(true, Ordering::Relaxed);
            Ok(None)
        });
        // Stands for the container's endpoint the same way, and keeps the
        // endpoint the provider found. Only the instance's probe follows,
        // which finds nothing.
        let endpoint = RefCell::new(None);
        let container = ContainerFetch::new(|found| {
            endpoint.replace(Some(found));
            Ok(None)
        });
        let found = default_resolver(&env, files, profile, container, probe).load_credentials()?;
        let metadata = if let Some(endpoint) = endpoint.into_inner() {
            Some(Metadata::container(endpoint))
        } else {
            (found.is_none() && reached.load(Ordering::Relaxed)).then(|| {
                // botocore's fetcher takes the environment's proxies for its
                // own URL (`IMDSFetcher.__init__`).
                let forward = proxies.forward(&settings.base_url);
                let service = Arc::new(Service {
                    forward,
                    clients: Mutex::default(),
                });
                let transport = Arc::clone(&service) as Arc<dyn Transport>;
                let fetcher = Fetcher::new(settings, Some(user_agent()), transport);
                Metadata {
                    service,
                    fetcher: Remote::Instance(fetcher.into()),
                }
            })
        };
        let walked = Walked {
            found: match metadata {
                Some(_) => OnceLock::new(),
                None => OnceLock::from(Ok(resolved(found, clock.as_ref()))),
            },
            metadata,
            clock,
        };
        Ok(Self(Arc::new(walked)))
    }
    /// The runtime option that signs with what the chain found.
    pub fn source(&self) -> Source {
        Source::Delegate(Arc::new(self.clone()))
    }
    /// What the chain found: `None` for one that failed, and for one whose
    /// service has not been asked yet.
    fn found(&self) -> Option<&Resolved> {
        self.0.found.get()?.as_ref().ok()
    }
    /// The provider that found the credentials, botocore's `method`:
    /// `None` for a chain that found none, and for one whose service has
    /// not been asked yet.
    pub fn method(&self) -> Option<&'static str> {
        self.found()?.method()
    }
    /// Why the latest request that waited for a refresh failed to sign;
    /// see [`Resolved::refresh_error`].
    pub fn refresh_error(&self) -> Option<RefreshError> {
        self.found()?.refresh_error()
    }
    /// The error the container or instance metadata provider raised when a
    /// runtime asked it, which botocore raises as it creates the client.
    pub fn load_error(&self) -> Option<&LoadError> {
        self.0.found.get()?.as_ref().err()
    }
}

/// What botocore raises for the instance metadata settings as the CLI's
/// session starts ([`InstanceMetadataSettings::refusal`]), as the CLI
/// prints it: `str()` of the exception.
pub fn settings_refusal(env: &impl EnvMap, files: &ParsedFiles, profile: &str) -> Option<String> {
    InstanceMetadataSettings::refusal(env, files, profile).map(|error| error.to_string())
}

/// botocore's `session.user_agent(truncate=True)`, which its fetcher sends
/// (`create_credential_resolver`).
fn user_agent() -> String {
    format!("aws-cli/{}", cli_core::AWS_CLI_VERSION)
}

fn resolved(found: Option<Loaded>, clock: Option<&Clock>) -> Resolved {
    Resolved::new(found.map(|found| match clock {
        Some(clock) => found.with_clock(clock.clone()),
        None => found,
    }))
}

impl Delegate for Chain {
    /// A request signed before the service was asked, or by a chain that
    /// failed, fails as one whose chain found nothing does.
    fn credentials(&self, query: Query) {
        match self.found() {
            Some(resolved) => resolved.credentials(query),
            None => query.fail(),
        }
    }
    /// botocore's error for the chain that failed as the client was
    /// created, else for the refresh the latest failed request waited for.
    fn failure(&self) -> Option<String> {
        match self.load_error() {
            Some(error) => Some(error.to_string()),
            None => self.refresh_error().map(|error| error.to_string()),
        }
    }
    /// Asks the service, for a walk that reached its provider, on the first
    /// runtime that signs with this chain. A runtime built later,
    /// such as a redirect's regional client, signs with what that one
    /// found, and a refresh asks through the newest runtime still there.
    fn attach(&self, runtime: &crt::Runtime) -> Result<(), Unavailable> {
        let Some(metadata) = &self.0.metadata else {
            return Ok(());
        };
        lock(&metadata.service.clients).push(runtime.http_client());
        let found = self.0.found.get_or_init(|| {
            if let (Forward::Unsupported, Some(logger)) =
                (&metadata.service.forward, runtime.logger())
            {
                logger.record("awscli.native.credentials", PROXY_UNSUPPORTED);
            }
            let loaded = metadata.fetcher.load()?;
            Ok(resolved(loaded, self.0.clock.as_ref()))
        });
        found.as_ref().map(drop).map_err(|_| Unavailable)
    }
}

/// botocore's HTTP session for the instance metadata service
/// (`IMDSFetcher`) or the container's (`ContainerMetadataFetcher`), over the
/// HTTP clients of the runtimes that sign with the chain.
///
/// An `https` endpoint is verified with the trust of the runtime that
/// sends, the CA bundle the command's S3 client has. botocore's session
/// for either service has its own bundle whatever the CLI's settings name;
/// that difference is deliberate.
///
/// So is the proxy: a proxy in front of the service is not an AWS product.
/// One botocore would use and this transport does not is sent nothing, and
/// the fetch ends at once as it does for a service that cannot be reached.
#[derive(Debug)]
struct Service {
    /// Where a request leaves for: the service, the environment's proxy
    /// for the service's URL, or nowhere.
    forward: Forward,
    /// The client of each runtime that signs with this chain, the newest
    /// last.
    clients: Mutex<Vec<Client>>,
}

impl Transport for Service {
    /// Sends through the newest runtime that is still there. `timeout` is
    /// botocore's one number for the connect and for each read
    /// (`IMDSFetcher.__init__`).
    ///
    /// The requests carry what `http.client` adds to botocore's own: the
    /// Host header and `Accept-Encoding: identity` first, and a zero
    /// `Content-Length` last on a PUT, which has no body.
    fn send(
        &self,
        request: &::credentials::Request,
        timeout: Duration,
    ) -> Result<::credentials::Response, TransportError> {
        let proxy = match &self.forward {
            Forward::Direct => None,
            Forward::Proxy(proxy) => Some(proxy),
            Forward::Unsupported => return Err(TransportError::NoRoute),
        };
        let location =
            Location::parse(&request.url, proxy.is_some()).ok_or(TransportError::InvalidUrl)?;
        if location.tls && proxy.is_some() {
            return Err(tunnel_unsupported());
        }
        let (host, port) = match proxy {
            Some(proxy) => (proxy.host.as_str(), proxy.port),
            None => (location.host.as_str(), location.port),
        };
        // This crate's tests build clients for commands whose environment
        // names no service, and none of them may reach the instance's own
        // address: there the service is one that cannot be reached.
        #[cfg(test)]
        if host != "127.0.0.1" {
            return Err(TransportError::Connect);
        }
        let mut headers = vec![
            ("Host", location.host_header.as_str()),
            ("Accept-Encoding", "identity"),
        ];
        headers.extend(
            request
                .headers
                .iter()
                .map(|(name, value)| (*name, value.as_str())),
        );
        if request.method == "PUT" {
            headers.push(("Content-Length", "0"));
        }
        let sent = crt::http::Request {
            host,
            port,
            tls: location.tls,
            method: request.method,
            target: &location.target,
            headers: &headers,
            signing: None,
            connect_timeout: timeout,
            read_timeout: timeout,
        };
        // Copied out, so nothing is sent under the lock.
        let clients = lock(&self.clients).clone();
        let mut answer = Err(HttpError::Closed);
        for client in clients.iter().rev() {
            answer = client.send(&sent);
            if answer != Err(HttpError::Closed) {
                break;
            }
        }
        match answer {
            Ok(response) => Ok(::credentials::Response {
                status: response.status,
                body: response.body,
            }),
            Err(error) => Err(transport_error(error, proxy)),
        }
    }
}

/// The `--debug` record of a fetch that sends nothing, for a proxy botocore
/// would use and this transport does not ([`Forward::Unsupported`]). It
/// names no part of the proxy's URL, which may hold a password.
const PROXY_UNSUPPORTED: &str = "The proxy for the instance metadata service is not supported \
    (only an http:// proxy given as host:port, without a username or password, is), so the \
    service is not asked for credentials";

/// Why no request for an `https` endpoint goes to a proxy: that is a
/// tunnel, which aws-c-http cannot bound. The endpoint is one the user
/// named, so the fetch fails and says why, with the HTTPClientError that
/// botocore's fetcher does not try again.
fn tunnel_unsupported() -> TransportError {
    TransportError::Client {
        reason: "cannot ask the instance metadata service for credentials: an https endpoint is \
            not supported through a proxy"
            .to_owned(),
    }
}

/// The error botocore's session raises for a request that failed as
/// `error` says (`URLLib3Session.send`).
fn transport_error(error: HttpError, proxy: Option<&ForwardProxy>) -> TransportError {
    match error {
        HttpError::ReadTimeout => TransportError::ReadTimeout,
        // A connection that closed or broke before the response was whole
        // is urllib3's ProtocolError.
        HttpError::Response(_) => TransportError::ConnectionClosed,
        // http.client sends what aws-c-http refuses to, so this has no
        // error of botocore's; it names the CRT's.
        HttpError::Connect(code) if crt::http::is_refusal(code) => TransportError::Client {
            reason: String::from_utf8_lossy(&crt::s3::error_message(code)).into_owned(),
        },
        // urllib3 raises every failure to reach a proxy, a timeout among
        // them, as its ProxyError.
        HttpError::Connect(_) if proxy.is_some() => TransportError::Proxy {
            url: proxy.map(|proxy| proxy.url.clone()).unwrap_or_default(),
        },
        HttpError::Connect(
            crt::http::SOCKET_TIMEOUT_ERROR_CODE | crt::http::TLS_TIMEOUT_ERROR_CODE,
        ) => TransportError::ConnectTimeout,
        // Every other failure to connect, a certificate the runtime's
        // trust does not verify among them, and a chain whose runtimes are
        // all gone, is a service that cannot be reached.
        _ => TransportError::Connect,
    }
}

fn answer(query: Query, credentials: &Credentials) {
    query.complete(View {
        access_key_id: credentials.access_key_id(),
        secret_access_key: credentials.secret_access_key(),
        session_token: credentials.session_token(),
        account_id: credentials.account_id(),
        expiration: credentials.expiry(),
    });
}

/// Credentials a chain found, and the requests waiting on their refresh.
#[derive(Debug)]
struct Live {
    loaded: Loaded,
    waiting: Mutex<Waiting>,
    refresh_error: Mutex<Option<RefreshError>>,
}

/// Queries that need a refresh or must wait for one.
#[derive(Debug, Default)]
struct Waiting {
    /// The query the refresh thread was started for, until the thread
    /// takes it, and behind it the queries that wait.
    queries: VecDeque<Query>,
    /// Whether a refresh thread is taking queries, which stands for
    /// botocore's refresh lock being held. It is cleared under the lock
    /// that found the queue empty, so a query is never left behind.
    served: bool,
}

impl Live {
    /// botocore's attempt on the refresh lock, for a query whose
    /// credentials are inside the advisory window. `usable` is the current
    /// credentials while the mandatory window is still ahead.
    fn park(self: &Arc<Self>, query: Query, usable: Option<Credentials>) {
        let mut waiting = lock(&self.waiting);
        if waiting.served {
            // `_refresh`: a refresh is under way, whichever query's it is. Only
            // the mandatory window waits for it.
            let Some(credentials) = usable else {
                waiting.queries.push_back(query);
                return;
            };
            drop(waiting);
            return answer(query, &credentials);
        }
        // `_refresh`: no refresh is under way, so this query refreshes.
        waiting.served = true;
        waiting.queries.push_back(query);
        drop(waiting);
        let live = Arc::clone(self);
        let spawned = std::thread::Builder::new()
            .name("credential-refresh".into())
            .spawn(move || live.serve());
        if spawned.is_err() {
            // Nothing can refresh, so the waiting requests fail to sign.
            self.abandon();
        }
    }

    /// The refresh thread: botocore's blocking path for the parked queries.
    fn serve(&self) {
        let _abandon_on_panic = Serving(self);
        // `_refresh`: the query the thread was started for found no refresh
        // under way, so it refreshes.
        let Some(refresher) = self.next() else {
            return;
        };
        self.settle(refresher, self.loaded.frozen());
        // `_refresh`: every query parked since found a refresh under way, this
        // one or a waiter's own, and waited for it. Each rechecks the mandatory
        // window alone.
        while let Some(waiter) = self.next() {
            self.settle(waiter, self.loaded.frozen_after_waiting());
        }
    }

    fn settle(&self, query: Query, frozen: Result<Credentials, RefreshError>) {
        match frozen {
            Ok(credentials) => answer(query, &credentials),
            Err(error) => {
                *lock(&self.refresh_error) = Some(error);
                query.fail();
            }
        }
    }

    /// The next parked query, or `None` as the thread stops.
    fn next(&self) -> Option<Query> {
        let mut waiting = lock(&self.waiting);
        let query = waiting.queries.pop_front();
        waiting.served = query.is_some();
        query
    }

    /// Fails every parked query and lets a later one start a new thread.
    fn abandon(&self) {
        let abandoned = {
            let mut waiting = lock(&self.waiting);
            waiting.served = false;
            std::mem::take(&mut waiting.queries)
        };
        // Dropped outside the lock: a failed query runs the signer's
        // callback, which may ask for credentials again.
        drop(abandoned);
    }
}

/// Fails the parked queries if a provider's refresh panics, so no signer
/// waits on a thread that is gone.
struct Serving<'a>(&'a Live);

impl Drop for Serving<'_> {
    fn drop(&mut self) {
        if std::thread::panicking() {
            self.0.abandon();
        }
    }
}

/// A provider's panic happens outside these locks, so a poisoned one still
/// guards a consistent value.
fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(PoisonError::into_inner)
}

#[cfg(test)]
mod tests;
