//! The container provider, answered by the CRT from a stand-in endpoint on
//! loopback, onto the wire and through a refresh.
use super::super::{MINUTE, TestResult, access_key, clock, list, parse, serve};
use crate::credentials::Chain;
use ::credentials::Profile;
use cli_core::SnapshotEnv;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::atomic::Ordering;
use std::time::Duration;

/// The credentials the endpoint gives on the `turn`th fetch, which expire
/// `turn` hours after eight.
fn document(turn: usize) -> String {
    format!(
        r#"{{"AccessKeyId": "AKIDCONTAINER{turn}", "SecretAccessKey": "container-secret-{turn}",
            "Token": "container-token-{turn}", "Expiration": "2037-10-21T{:02}:00:00Z"}}"#,
        8 + turn
    )
}

/// Answers one connection per document, in order, and returns each
/// request's head.
fn answer(listener: &TcpListener, documents: Vec<String>) -> std::io::Result<Vec<String>> {
    let mut heads = Vec::new();
    for body in documents {
        let (mut stream, _) = listener.accept()?;
        stream.set_read_timeout(Some(Duration::from_secs(10)))?;
        let mut head = Vec::new();
        let mut chunk = [0; 1024];
        while !head.windows(4).any(|window| window == b"\r\n\r\n") {
            let count = stream.read(&mut chunk)?;
            if count == 0 {
                break;
            }
            head.extend_from_slice(&chunk[..count]);
        }
        write!(
            stream,
            "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
            body.len()
        )?;
        heads.push(String::from_utf8_lossy(&head).into_owned());
    }
    Ok(heads)
}

/// A local agent's full URI with a token: the chain stops at the container
/// provider, which asks once the runtime exists and again for a refresh,
/// with botocore's path and headers (`ContainerMetadataFetcher`).
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn the_containers_credentials_sign_and_refresh_through_the_delegate() -> TestResult {
    let endpoint = TcpListener::bind("127.0.0.1:0")?;
    let address = endpoint.local_addr()?;
    let agent = std::thread::spawn(move || answer(&endpoint, vec![document(0), document(1)]));
    let url = format!("http://{address}/creds?task=1");
    let env = SnapshotEnv::from_pairs([
        ("AWS_CONTAINER_CREDENTIALS_FULL_URI", url.as_str()),
        ("AWS_CONTAINER_AUTHORIZATION_TOKEN", "Basic agent-token"),
        // botocore's `ContainerMetadataFetcher` never takes a proxy.
        ("HTTP_PROXY", "http://127.0.0.1:9"),
    ]);
    let s3 = TcpListener::bind("127.0.0.1:0")?;
    let s3_address = s3.local_addr()?;
    let server = std::thread::spawn(move || serve(s3, 2));
    let (clock, seconds) = clock();
    let chain = Chain::walk_with_clock(
        &env,
        &parse(b"", b""),
        Profile::Ambient("default"),
        Some(clock),
    )?;
    let runtime = crt::Runtime::new(crt::RuntimeOptions {
        endpoint_url: format!("http://{s3_address}/bucket"),
        credentials: chain.source(),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    })?;
    assert_eq!(chain.method(), Some("container-role"));
    assert_eq!(list(&runtime), 0);
    // Fourteen minutes left: the advisory window refreshes.
    seconds.fetch_add(46 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&runtime), 0);
    let debug = format!("{chain:?}");
    for secret in ["agent-token", "container-secret", "container-token"] {
        assert!(!debug.contains(secret), "{debug}");
    }
    drop(runtime);
    let listings = server.join().map_err(|_| "the S3 endpoint panicked")??;
    let keys: Vec<_> = listings.iter().map(|listing| access_key(listing)).collect();
    assert_eq!(keys, ["AKIDCONTAINER0", "AKIDCONTAINER1"].map(Some));
    let heads = agent.join().map_err(|_| "the agent panicked")??;
    assert_eq!(heads.len(), 2);
    heads.iter().for_each(|head| assert_asked(head));
    Ok(())
}

/// A request for the URI's path, with botocore's headers.
fn assert_asked(head: &str) {
    let lines: Vec<_> = head.lines().collect();
    assert_eq!(lines.first(), Some(&"GET /creds?task=1 HTTP/1.1"), "{head}");
    for header in [
        "Accept: application/json",
        "Authorization: Basic agent-token",
    ] {
        assert!(lines.contains(&header), "{head}");
    }
}
