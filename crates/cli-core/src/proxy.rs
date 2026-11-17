//! Proxy environment precedence and bounded credential-masked diagnostics.
//! Resolution follows CPython's `getproxies_environment` and
//! `proxy_bypass_environment`: on POSIX an empty lowercase override disables
//! the corresponding uppercase setting, and a matching bypass list connects a
//! client directly. The router and transport share this policy.
#![forbid(unsafe_code)]
use crate::EnvMap;
const BYTES_MAX: usize = 4096;
/// The ASCII characters Python's `str.strip()` removes: `str.isspace()` holds
/// for C's six whitespace characters and the separators 0x1c-0x1f.
/// Non-ASCII bypass lists require Python, so no other character can be stripped.
const WHITESPACE: [char; 10] = [
    ' ', '\t', '\n', '\x0b', '\x0c', '\r', '\x1c', '\x1d', '\x1e', '\x1f',
];
/// The two spellings of one proxy environment setting.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Pair<'a> {
    /// Uppercase fallback, borrowed from the environment.
    pub upper: Option<&'a str>,
    /// Lowercase override; an empty value explicitly disables the proxy.
    pub lower: Option<&'a str>,
}
impl<'a> Pair<'a> {
    /// Python's effective URL, with absence and explicit disabling both direct.
    pub fn resolve(self) -> Option<&'a str> {
        self.lower.or(self.upper).filter(|value| !value.is_empty())
    }
    /// aws-c-http's environment reader skips empty lowercase values, so
    /// these pairs have been Python's since a credential provider used that
    /// reader. No native request reads the environment through it now.
    pub fn requires_python(self) -> bool {
        self.lower == Some("") && self.upper.is_some_and(|value| !value.is_empty())
    }
}
/// Borrowed proxy settings for both destination schemes and the bypass list.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Environment<'a> {
    /// Settings for cleartext destinations.
    pub http: Pair<'a>,
    /// Settings for TLS destinations, including HTTPS credential providers.
    pub https: Pair<'a>,
    /// The comma-separated bypass list from `NO_PROXY` and `no_proxy`, which
    /// Python resolves with the same lowercase precedence as the schemes.
    pub no_proxy: Pair<'a>,
    /// Whether `REQUEST_METHOD` is present, even empty or not Unicode. Python
    /// then treats the process as a CGI script and ignores uppercase
    /// `HTTP_PROXY`, which a client's `Proxy:` header could set
    /// (CVE-2016-1000110).
    pub request_method: bool,
    /// Whether one of the three variables is spelled in mixed case, such as
    /// `No_Proxy`. Python's result then depends on `os.environ` order, which
    /// this reader does not model.
    pub mixed_case: bool,
    /// The spellings of each setting present with a value that is not
    /// Unicode. Python keeps such a value, surrogate-escaped, while a `Pair`
    /// cannot hold it and reads it as absent.
    pub not_unicode: NotUnicode,
}
/// The spellings of the three settings the reader found with a value that is
/// not Unicode.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct NotUnicode {
    pub http: Spellings,
    pub https: Spellings,
    pub no_proxy: Spellings,
}
/// Whether each spelling of one setting holds a value that is not Unicode.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Spellings {
    pub upper: bool,
    pub lower: bool,
}
impl Spellings {
    fn resolved(self, pair: Pair<'_>) -> bool {
        self.lower || (pair.lower.is_none() && self.upper)
    }
    fn empty_lower_requires_python(self, pair: Pair<'_>) -> bool {
        pair.requires_python() || (pair.lower == Some("") && self.upper)
    }
}
const NAMES: [&str; 3] = ["http_proxy", "https_proxy", "no_proxy"];
/// Every spelling [`Environment::from_map`] reads as a setting, uppercase
/// before lowercase, in the decision table's order; cli-router's tests check
/// that its honored proxy rows name exactly these. `REQUEST_METHOD` is read
/// too, but only as a marker that changes how `HTTP_PROXY` applies, so it is
/// not a setting of its own.
pub const VARIABLES: [&str; 6] = [
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "NO_PROXY",
    "no_proxy",
];
const _: () = {
    assert!(VARIABLES.len() == 2 * NAMES.len());
    let mut index = 0;
    while index < NAMES.len() {
        let mut spellings = 0;
        let mut variable = 0;
        while variable < VARIABLES.len() {
            if VARIABLES[variable].eq_ignore_ascii_case(NAMES[index]) {
                spellings += 1;
            }
            variable += 1;
        }
        assert!(spellings == 2);
        index += 1;
    }
};
/// Whether environment names have case. Windows looks names up without case,
/// and CPython's `os.environ` uppercases every name there, so each proxy
/// setting has only its uppercase spelling and no lowercase override.
pub const NAMES_HAVE_CASE: bool = !cfg!(windows);
impl<'a> Environment<'a> {
    /// Reads the proxy variables and the CGI marker under the host's name rules.
    pub fn from_map(env: &'a impl EnvMap) -> Self {
        Self::from_map_with(env, NAMES_HAVE_CASE)
    }
    /// Reads the proxy variables, without collapsing empty values, and the
    /// `REQUEST_METHOD` marker by presence alone. Where names have no case,
    /// `getproxies_environment`'s lowercase pass never matches, so every
    /// spelling is the uppercase setting and none is mixed case; the map's
    /// own lookups must then ignore case.
    pub fn from_map_with(env: &'a impl EnvMap, names_have_case: bool) -> Self {
        let pair = |upper, lower| {
            let (upper, upper_not_unicode) = read(env, upper);
            let (lower, lower_not_unicode) = if names_have_case {
                read(env, lower)
            } else {
                (None, false)
            };
            let spellings = Spellings {
                upper: upper_not_unicode,
                lower: lower_not_unicode,
            };
            (Pair { upper, lower }, spellings)
        };
        let (https, https_not_unicode) = pair(VARIABLES[0], VARIABLES[1]);
        let (http, http_not_unicode) = pair(VARIABLES[2], VARIABLES[3]);
        let (no_proxy, no_proxy_not_unicode) = pair(VARIABLES[4], VARIABLES[5]);
        Self {
            http,
            https,
            no_proxy,
            request_method: env.var_os("REQUEST_METHOD").is_some(),
            mixed_case: names_have_case && from_map_mixed_case(env),
            not_unicode: NotUnicode {
                http: http_not_unicode,
                https: https_not_unicode,
                no_proxy: no_proxy_not_unicode,
            },
        }
    }
    /// Whether a bypass list is in force, which makes the client endpoint's
    /// netloc an input of proxy resolution.
    pub fn has_bypass_list(self) -> bool {
        self.no_proxy.resolve().is_some()
    }
    /// Resolve the proxy for the destination URL, independently of proxy TLS.
    pub fn resolve(self, endpoint: &str) -> Option<&'a str> {
        if endpoint
            .get(..6)
            .is_some_and(|prefix| prefix.eq_ignore_ascii_case("https:"))
        {
            return self.https.resolve();
        }
        let http = if self.request_method {
            Pair {
                upper: None,
                lower: self.http.lower,
            }
        } else {
            self.http
        };
        http.resolve()
    }
    /// Check both schemes: credentials can use HTTPS even for an HTTP S3 URL.
    /// Environments this reader cannot resolve exactly also require Python.
    pub fn requires_python(self) -> bool {
        if self.mixed_case || self.schemes_require_python() {
            return true;
        }
        // An empty `no_proxy` deletes Python's list, while aws-c-http's
        // reader skips it and bypasses `NO_PROXY`'s hosts.
        if self
            .not_unicode
            .no_proxy
            .empty_lower_requires_python(self.no_proxy)
        {
            return true;
        }
        // Python drops uppercase HTTP_PROXY here, and aws-c-http's reader
        // would honor it.
        let http = self.not_unicode.http;
        if self.request_method
            && self.http.lower.is_none()
            && !http.lower
            && (http.upper || self.http.upper.is_some_and(|upper| !upper.is_empty()))
        {
            return true;
        }
        // Python strips and lowercases entries with Unicode rules: NO-BREAK
        // SPACE strips and KELVIN SIGN lowers to `k`. Matching here is ASCII,
        // and a list that is not Unicode is not ASCII either.
        self.not_unicode.no_proxy.resolved(self.no_proxy)
            || self.no_proxy.resolve().is_some_and(|list| !list.is_ascii())
    }
    fn schemes_require_python(self) -> bool {
        [
            (self.http, self.not_unicode.http),
            (self.https, self.not_unicode.https),
        ]
        .into_iter()
        .any(|(pair, not_unicode)| {
            not_unicode.empty_lower_requires_python(pair) || not_unicode.resolved(pair)
        })
    }
    /// `requires_python` for a client whose endpoint netloc meets the bypass
    /// list. Python lowercases that host with Unicode rules too, so a
    /// non-ASCII netloc also requires Python.
    pub fn requires_python_for(self, netloc: &str) -> bool {
        self.requires_python() || (self.has_bypass_list() && !netloc.is_ascii())
    }
    /// Resolve like botocore's `get_environ_proxies`, which tests the bypass
    /// list once against the client endpoint's netloc. A match sends every
    /// request of the client directly, whatever its scheme or host.
    pub fn resolve_for(self, endpoint: &str, client_netloc: &str) -> Option<&'a str> {
        if self.bypass(client_netloc) {
            None
        } else {
            self.resolve(endpoint)
        }
    }
    /// Match urllib's `proxy_bypass_environment` for a netloc as `urlparse`
    /// returns it, with any userinfo, port, and IPv6 brackets. Entries are
    /// plain strings compared without case: no CIDR or IP parsing.
    pub fn bypass(self, netloc: &str) -> bool {
        let Some(list) = self.no_proxy.resolve() else {
            return false;
        };
        // Only the whole, unstripped value bypasses every host.
        if list == "*" {
            return true;
        }
        let host = Host {
            netloc,
            hostonly: bypass_host_only(netloc),
        };
        list.split(',').any(|entry| bypass_entry(entry, host))
    }
}
fn read<'a>(env: &'a impl EnvMap, name: &str) -> (Option<&'a str>, bool) {
    match env.var_os(name).map(|value| value.to_str()) {
        None => (None, false),
        Some(value) => (value, value.is_none()),
    }
}
fn from_map_mixed_case(env: &impl EnvMap) -> bool {
    env.names().iter().any(|name| {
        NAMES.iter().any(|lower| name.eq_ignore_ascii_case(lower)) && is_mixed_case(name)
    })
}
fn is_mixed_case(name: &str) -> bool {
    name.bytes().any(|c| c.is_ascii_uppercase()) && name.bytes().any(|c| c.is_ascii_lowercase())
}
// `_splitport` fullmatches `(.*):([0-9]*)`. The greedy group ends at the
// last colon, which only ASCII digits may follow. An empty port still drops
// the colon, so `h:` yields `h`.
fn bypass_host_only(host: &str) -> &str {
    host.rsplit_once(':')
        .filter(|(_, port)| port.bytes().all(|c| c.is_ascii_digit()))
        .map_or(host, |(hostonly, _)| hostonly)
}
#[derive(Clone, Copy)]
struct Host<'a> {
    netloc: &'a str,
    hostonly: &'a str,
}
fn bypass_entry(entry: &str, host: Host<'_>) -> bool {
    let stripped = entry.trim_matches(WHITESPACE);
    if stripped.is_empty() {
        return false;
    }
    // Removing leading dots can leave an empty name, which then matches an
    // empty host or, through the suffix rule, any host ending in a dot.
    let name = stripped.trim_start_matches('.');
    host.hostonly.eq_ignore_ascii_case(name)
        || host.netloc.eq_ignore_ascii_case(name)
        || bypass_suffix(host.hostonly, name)
        || bypass_suffix(host.netloc, name)
}
// Python appends `.` to the name before `endswith`, so a suffix match must
// start at a label boundary.
fn bypass_suffix(host: &str, name: &str) -> bool {
    let Some(start) = host.len().checked_sub(name.len()) else {
        return false;
    };
    let host = host.as_bytes();
    start > 0 && host[start - 1] == b'.' && host[start..].eq_ignore_ascii_case(name.as_bytes())
}

/// `urlparse(url).netloc`: the authority after a scheme's `//`, up to the
/// first `/`, `?`, or `#`, userinfo and port included; empty when the URL has
/// no authority. The S3 endpoint code passes only URLs botocore accepted as
/// endpoints (`is_valid_endpoint_url`), so urlsplit's stripping of control
/// characters and its validation of brackets never apply.
pub fn netloc(url: &str) -> &str {
    let Some((_, rest)) = url.split_once(':') else {
        return "";
    };
    let Some(authority) = rest.strip_prefix("//") else {
        return "";
    };
    authority
        .find(['/', '?', '#'])
        .map_or(authority, |end| &authority[..end])
}

/// Where a request leaves for, as botocore's `URLLib3Session` decides
/// when it is built with `get_environ_proxies(url)`, the way its instance
/// metadata fetcher's is.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Forward {
    /// The destination itself: no proxy is set for it, or the bypass list
    /// names it.
    Direct,
    /// A proxy reached in cleartext: it takes a cleartext request with an
    /// absolute target, and would tunnel one for an `https` URL.
    Proxy(ForwardProxy),
    /// A proxy botocore uses and the native transport does not: one that is
    /// spoken to over TLS or that takes credentials, and any URL
    /// [`ForwardProxy::parse`] does not read. It keeps nothing of the
    /// proxy's URL, which may hold a password.
    Unsupported,
}
/// A forwarding proxy reached in cleartext, without credentials.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ForwardProxy {
    pub host: String,
    pub port: u16,
    /// The proxy's URL as botocore's ProxyConnectionError names it: with
    /// the scheme `_fix_proxy_url` gives one that has none. It holds no
    /// credentials to mask.
    pub url: String,
}
impl ForwardProxy {
    /// Reads `proxy`, the environment's value, when it is `host` or
    /// `host:port`, of a name's or an IPv4 address's characters, after an
    /// optional `http://` or `//` and before an optional `/`. urllib3 gives
    /// a proxy without a port its scheme's, 80.
    pub fn parse(proxy: &str) -> Option<Self> {
        let url = if proxy.starts_with("http:") || proxy.starts_with("https:") {
            proxy.to_owned()
        } else if proxy.starts_with("//") {
            format!("http:{proxy}")
        } else {
            format!("http://{proxy}")
        };
        let authority = url.strip_prefix("http://")?;
        let authority = authority.strip_suffix('/').unwrap_or(authority);
        let (host, port) = match authority.split_once(':') {
            Some((host, port)) => {
                let digits = !port.is_empty() && port.bytes().all(|c| c.is_ascii_digit());
                (host, port.parse().ok().filter(|port| digits && *port != 0)?)
            }
            None => (authority, 80),
        };
        let named = !host.is_empty()
            && host
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'.' | b'-'));
        let host = named.then(|| host.to_owned())?;
        Some(Self { host, port, url })
    }
}
impl Environment<'_> {
    /// Where a request to `url` leaves for. botocore tests the bypass list
    /// against `urlparse(url).netloc` once, then takes the proxy of the
    /// URL's scheme.
    pub fn forward(self, url: &str) -> Forward {
        match self.resolve_for(url, netloc(url)) {
            None => Forward::Direct,
            Some(proxy) => ForwardProxy::parse(proxy).map_or(Forward::Unsupported, Forward::Proxy),
        }
    }
}
/// Owned sanitized diagnostic text. Oversized inputs are hidden completely.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct DisplayUrl(String);
impl DisplayUrl {
    pub fn new(url: &str) -> Self {
        let prefix = if url.starts_with("http:") || url.starts_with("https:") {
            ""
        } else if url.starts_with("//") {
            "http:"
        } else {
            "http://"
        };
        if prefix.len() + url.len() > BYTES_MAX {
            return Self("***".to_owned());
        }
        let fixed = format!("{prefix}{url}");
        let start = fixed.find("//").map_or(fixed.len(), |index| index + 2);
        let end = fixed[start..]
            .find(['/', '?', '#'])
            .map_or(fixed.len(), |index| start + index);
        let netloc = &fixed[start..end];
        let userinfo = netloc.rfind('@').map_or("", |index| &netloc[..index]);
        let (username, password) = userinfo.split_once(':').unwrap_or((userinfo, ""));
        let mut result = fixed.clone();
        for secret in [username, password] {
            if secret.is_empty() {
                continue;
            }
            if let Some(index) = result.find(secret) {
                if result.len() - secret.len() + 3 > BYTES_MAX {
                    return Self("***".to_owned());
                }
                result.replace_range(index..index + secret.len(), "***");
            }
        }
        Self(result)
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
impl std::fmt::Display for DisplayUrl {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.write_str(&self.0)
    }
}
