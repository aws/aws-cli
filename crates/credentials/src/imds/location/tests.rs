use super::*;

/// The fields of a location, in the struct's order.
type Fields<'a> = (bool, &'a str, u16, &'a str, &'a str);

fn fields(url: &str, proxied: bool) -> Option<(bool, String, u16, String, String)> {
    let found = Location::parse(url, proxied)?;
    Some((
        found.tls,
        found.host,
        found.port,
        found.host_header,
        found.target,
    ))
}

fn owned(fields: Fields<'_>) -> (bool, String, u16, String, String) {
    let (tls, host, port, host_header, target) = fields;
    (tls, host.into(), port, host_header.into(), target.into())
}

/// Each expectation is the path botocore's `_path_url` leaves, and the
/// Host header `http.client` writes for a connection to the host urllib3
/// reads.
#[test]
fn a_direct_request_sends_the_path_and_names_the_host() {
    let rows: [(&str, Fields<'_>); 9] = [
        (
            "http://169.254.169.254/latest/api/token",
            (
                false,
                "169.254.169.254",
                80,
                "169.254.169.254",
                "/latest/api/token",
            ),
        ),
        (
            "http://[FD00:ec2::254]/latest/api/token",
            (
                false,
                "fd00:ec2::254",
                80,
                "[fd00:ec2::254]",
                "/latest/api/token",
            ),
        ),
        (
            "http://[fd00:ec2::254]:8080/p/x",
            (false, "fd00:ec2::254", 8080, "[fd00:ec2::254]:8080", "/p/x"),
        ),
        (
            "http://H.Example:8080/p/latest/x",
            (false, "h.example", 8080, "h.example:8080", "/p/latest/x"),
        ),
        // The scheme's own port is left out of the header, zeros or not.
        ("http://h:080/x", (false, "h", 80, "h", "/x")),
        ("https://h:443/x", (true, "h", 443, "h", "/x")),
        ("https://h/x", (true, "h", 443, "h", "/x")),
        ("http://h:443/x", (false, "h", 443, "h:443", "/x")),
        ("http://h", (false, "h", 80, "h", "/")),
    ];
    for (url, expected) in rows {
        assert_eq!(fields(url, false), Some(owned(expected)), "{url}");
    }
}

/// Each expectation is the URL urllib3's `parse_url` writes back, and the
/// Host header `http.client` takes from it.
#[test]
fn a_proxied_http_request_sends_the_url_and_names_its_netloc() {
    let rows: [(&str, Fields<'_>); 5] = [
        (
            "http://169.254.169.254/latest/api/token",
            (
                false,
                "169.254.169.254",
                80,
                "169.254.169.254",
                "http://169.254.169.254/latest/api/token",
            ),
        ),
        (
            "http://[FD00:ec2::254]/latest/api/token",
            (
                false,
                "fd00:ec2::254",
                80,
                "[fd00:ec2::254]",
                "http://[fd00:ec2::254]/latest/api/token",
            ),
        ),
        (
            "http://H.Example:80/p/x",
            (
                false,
                "h.example",
                80,
                "h.example:80",
                "http://h.example:80/p/x",
            ),
        ),
        ("http://h:080/x", (false, "h", 80, "h:80", "http://h:80/x")),
        ("http://h", (false, "h", 80, "h", "http://h")),
    ];
    for (url, expected) in rows {
        assert_eq!(fields(url, true), Some(owned(expected)), "{url}");
    }
    // A proxy for `https` is a tunnel, which the path goes through.
    assert_eq!(
        fields("https://h:8443/x", true),
        Some(owned((true, "h", 8443, "h:8443", "/x")))
    );
}

/// Each row is a URL, the target of a direct request for it and the
/// target of a proxied one: the path and the query as written, `/` for no
/// path, and the fragment only in a proxy's.
#[test]
fn a_target_is_the_path_and_the_query_as_written() {
    for (url, direct, proxied) in [
        (
            "http://h/a/../b;p?x y#f",
            "/a/../b;p?x y",
            "http://h/a/../b;p?x y#f",
        ),
        ("http://h?q", "/?q", "http://h?q"),
        ("http://h/a?", "/a", "http://h/a?"),
        ("http://h#f", "/", "http://h#f"),
    ] {
        let target = |proxied| Location::parse(url, proxied).map(|found| found.target);
        assert_eq!(target(false).as_deref(), Some(direct), "{url:?}");
        assert_eq!(target(true).as_deref(), Some(proxied), "{url:?}");
    }
}

/// urllib3 raises `LocationParseError` for the ports; the rest it fails
/// in other ways, and none of them is a URL a request can be sent to.
#[test]
fn a_url_that_cannot_be_read_has_no_location() {
    for url in [
        "http://h:abc/x",
        "http://h:99999/x",
        "http://h:65536/x",
        "http://h:/x",
        "http://h:1:2/x",
        "http://[::1/x",
        "http://[::1]x/",
        "http:///x",
        "ftp://h/x",
        "h/x",
        "//h:abc/x",
        "//h:65536/x",
        "///x",
    ] {
        for proxied in [false, true] {
            assert_eq!(Location::parse(url, proxied), None, "{url}");
        }
    }
    let found = Location::parse("http://h:65535/x", false);
    assert_eq!(found.map(|found| found.port), Some(65535));
    let found = Location::parse("http://h:0/x", true);
    assert_eq!(
        found.map(|found| (found.port, found.host_header)),
        Some((0, "h:0".into()))
    );
}
