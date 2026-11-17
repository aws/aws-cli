//! How botocore's HTTP session puts one of the fetcher's URLs on the wire.
//!
//! botocore hands urllib3 the URL's path for a direct connection and for a
//! tunnel, and the whole URL for an `http` URL sent through a proxy
//! (httpsession.py `_get_request_target`), and `http.client` writes the
//! Host header from it (http/client.py `putrequest`). A transport sends
//! what [`Location`] holds and gets botocore's request for the URLs the
//! services use.
//!
//! Not ported: urllib3's rewriting of a path or a query (dot segments,
//! percent-encoding), which [`Location`] sends as written; credentials
//! before the host, which are dropped here and which urllib3 keeps in an
//! absolute target; a zone in an IPv6 address; and a host that is not
//! ASCII, which urllib3 encodes with IDNA.

/// Where a request for a URL connects, and what it sends.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Location {
    /// Whether the URL's scheme is `https`.
    pub tls: bool,
    /// The host in lower case, an IPv6 address without its brackets.
    pub host: String,
    /// The URL's port, else the scheme's own.
    pub port: u16,
    /// The Host header.
    pub host_header: String,
    /// The request target: a path, or the whole URL for a proxy.
    pub target: String,
}

impl Location {
    /// Reads `url`, which is sent through a proxy when `proxied`.
    ///
    /// `None` is urllib3's `LocationParseError`: a port that is not a
    /// number, or one past 65535. It is also a URL that is neither `http`
    /// nor `https` or that has no host, which urllib3 fails otherwise.
    pub fn parse(url: &str, proxied: bool) -> Option<Self> {
        let (scheme, rest) = url.split_once("://")?;
        let tls = if scheme.eq_ignore_ascii_case("https") {
            true
        } else if scheme.eq_ignore_ascii_case("http") {
            false
        } else {
            return None;
        };
        let (authority, tail) = rest.split_at(rest.find(['/', '?', '#']).unwrap_or(rest.len()));
        let authority = Authority::parse(authority)?;
        let default = if tls { 443 } else { 80 };
        // httpsession.py `_get_request_target`: the test is this one, on
        // the URL as written.
        let (host_header, target) = if proxied && url.starts_with("http:") {
            let netloc = authority.netloc(None);
            let target = format!("http://{netloc}{tail}");
            (netloc, target)
        } else {
            (authority.netloc(Some(default)), origin_form(tail))
        };
        Some(Self {
            tls,
            port: authority.port.unwrap_or(default),
            host: authority.host,
            host_header,
            target,
        })
    }
}

/// A URL's host and port as urllib3 normalizes them (util/url.py
/// `parse_url`).
struct Authority {
    host: String,
    bracketed: bool,
    port: Option<u16>,
}

impl Authority {
    fn parse(text: &str) -> Option<Self> {
        let text = text.rsplit_once('@').map_or(text, |(_, host)| host);
        let (host, bracketed, port) = match text.strip_prefix('[') {
            Some(rest) => {
                let (host, after) = rest.split_once(']')?;
                let port = match after {
                    "" => None,
                    _ => Some(after.strip_prefix(':')?),
                };
                (host, true, port)
            }
            None => match text.split_once(':') {
                Some((host, port)) => (host, false, Some(port)),
                None => (text, false, None),
            },
        };
        if host.is_empty() {
            return None;
        }
        Some(Self {
            host: host.to_ascii_lowercase(),
            bracketed,
            port: match port {
                Some(port) => Some(port.parse().ok()?),
                None => None,
            },
        })
    }
    /// The host and the port as they are written after `//` and in a Host
    /// header. `http.client` leaves out the port of a direct connection
    /// when it is the scheme's own, `default`; an absolute target and its
    /// Host header keep whatever port the URL names.
    fn netloc(&self, default: Option<u16>) -> String {
        let host = if self.bracketed {
            format!("[{}]", self.host)
        } else {
            self.host.clone()
        };
        match self.port {
            Some(port) if Some(port) != default => format!("{host}:{port}"),
            _ => host,
        }
    }
}

/// The target of a direct request: botocore's `_path_url`, the path, else
/// `/`, and the query.
fn origin_form(tail: &str) -> String {
    let rest = tail.split_once('#').map_or(tail, |(rest, _)| rest);
    let (path, query) = rest.split_once('?').unwrap_or((rest, ""));
    let path = if path.is_empty() { "/" } else { path };
    if query.is_empty() {
        path.to_owned()
    } else {
        format!("{path}?{query}")
    }
}

#[cfg(test)]
mod tests;
