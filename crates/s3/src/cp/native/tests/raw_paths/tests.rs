use super::*;
use cli_core::client_config::{ChecksumMode, ClientConfig, Command};
use std::io::{BufReader, Read};
use std::net::{TcpListener, TcpStream};
use std::os::unix::ffi::OsStrExt;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

type TestResult = Result<(), Box<dyn std::error::Error>>;
type Capture = (Vec<u8>, Vec<u8>, Vec<String>);

struct Directory(PathBuf);
impl Directory {
    fn new() -> io::Result<Self> {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "cp-raw-path-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed),
        ));
        std::fs::create_dir(&path)?;
        Ok(Self(path))
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn stores_non_utf8_names(directory: &Path) -> io::Result<bool> {
    let probe = directory.join(OsStr::from_bytes(b"probe-\xff"));
    match std::fs::create_dir(&probe) {
        Ok(()) => std::fs::remove_dir(&probe).map(|()| true),
        Err(error) if error.raw_os_error() == Some(libc::EILSEQ) => Ok(false),
        Err(error) => Err(error),
    }
}

#[test]
fn missing_upload_sources_preserve_raw_bytes_before_config_and_client_errors() -> TestResult {
    let directory = Directory::new()?;
    let source = directory
        .0
        .join(OsStr::from_bytes(b"missing-\xff\n\nfatal error: filename"));
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        region: Some(String::new()),
        ..Default::default()
    };
    let mut client = ClientConfig::new(Command::Cp);
    client.ignored.retry_mode_adaptive = true;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: &directory.0,
        payload: &[],
    };
    for recursive in [false, true] {
        let mut arguments = args("local", "s3://bucket/prefix/", recursive);
        arguments.paths[0] = source.clone().into_os_string();
        let (mut out, mut err) = (Vec::new(), Vec::new());
        let failure = run(&context, &arguments, &mut out, &mut err)
            .expect_err("preflight rejects the raw source");
        assert_eq!(failure.category, cli_core::cli_error::Category::General);
        assert_eq!(cli_core::cli_error::exit_status(failure.category), 255);
        assert_eq!(
            failure.message,
            [
                b"The user-provided path ".as_slice(),
                source.as_os_str().as_encoded_bytes(),
                b" does not exist.",
            ]
            .concat()
        );
        assert!(out.is_empty());
        assert!(err.is_empty());
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn recursive_file_source_preserves_blank_lines_and_event_prefixes() -> TestResult {
    let directory = Directory::new()?;
    if !stores_non_utf8_names(&directory.0)? {
        return Ok(());
    }
    let source = directory
        .0
        .join(OsStr::from_bytes(b"file-\xff\n\nfatal error: filename"));
    std::fs::write(&source, b"data")?;
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        endpoint_url: Some("http://127.0.0.1:9".into()),
        ..Default::default()
    };
    let payload = payload()?;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &ClientConfig::new(Command::Cp),
        directory: &directory.0,
        payload: &payload,
    };
    let mut arguments = args("local", "s3://bucket/prefix/", true);
    arguments.paths[0] = source.clone().into_os_string();
    arguments.quiet = false;
    arguments.progress = false;
    let (mut out, mut err) = (Vec::new(), Vec::new());
    assert_eq!(run(&context, &arguments, &mut out, &mut err)?, 2);
    assert!(out.is_empty());
    assert_eq!(
        err,
        [
            b"warning: Skipping file ".as_slice(),
            directory.0.as_os_str().as_encoded_bytes(),
            br"/file-\udcff",
            b"\n\nfatal error: filename/. File does not exist.\n",
        ]
        .concat()
    );
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn single_and_recursive_uploads_open_raw_paths_and_send_exact_key_bytes() -> TestResult {
    for recursive in [false, true] {
        let directory = Directory::new()?;
        if !stores_non_utf8_names(&directory.0)? {
            return Ok(());
        }
        let root = directory.0.join(OsStr::from_bytes(b"root-\xff"));
        std::fs::create_dir(&root)?;
        let path = root.join("file-é.txt");
        std::fs::write(&path, b"data")?;
        let mut arguments = args("local", "s3://bucket/prefix/", recursive);
        arguments.paths[0] = if recursive { root } else { path }.into_os_string();
        let (out, err, requests) = run_loopback(&directory.0, arguments, 1)?;
        assert!(err.is_empty(), "{err:?}");
        assert_eq!(requests, ["PUT /bucket/prefix/file-%C3%A9.txt HTTP/1.1"]);
        assert_eq!(
            out,
            [
                b"upload: root-\xff/".as_slice(),
                "file-é.txt to s3://bucket/prefix/file-é.txt\n".as_bytes(),
            ]
            .concat(),
        );
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn single_and_recursive_downloads_commit_into_raw_destination_roots() -> TestResult {
    for recursive in [false, true] {
        let directory = Directory::new()?;
        if !stores_non_utf8_names(&directory.0)? {
            return Ok(());
        }
        let root = directory.0.join(OsStr::from_bytes(b"root-\xff"));
        let destination = if recursive {
            root.clone()
        } else {
            root.join(OsStr::from_bytes(b"destination-\xfe"))
        };
        let mut arguments = args("s3://bucket/prefix/object", "local", recursive);
        if recursive {
            arguments.paths[0] = "s3://bucket/prefix/".into();
        }
        arguments.paths[1] = destination.into_os_string();
        let (out, err, requests) = run_loopback(&directory.0, arguments, 2)?;
        assert!(err.is_empty(), "{err:?}");
        let filename = if recursive {
            b"object".as_slice()
        } else {
            b"destination-\xfe"
        };
        assert_eq!(
            std::fs::read(root.join(OsStr::from_bytes(filename)))?,
            b"data"
        );
        assert_eq!(
            out,
            [
                b"download: s3://bucket/prefix/object to root-\xff/".as_slice(),
                filename,
                b"\n"
            ]
            .concat(),
        );
        assert_eq!(requests.len(), 2);
        assert_eq!(requests[1], "GET /bucket/prefix/object HTTP/1.1");
        assert_download_discovery(&requests[0], recursive);
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn an_empty_recursive_listing_into_a_regular_file_leaves_it_alone() -> TestResult {
    let directory = Directory::new()?;
    let destination = directory.0.join("file.txt");
    std::fs::write(&destination, b"original")?;
    let mut arguments = args("s3://bucket/empty/", "local", true);
    arguments.paths[1] = destination.clone().into_os_string();
    let (out, err, requests) = run_loopback(&directory.0, arguments, 1)?;
    assert!(out.is_empty(), "{out:?}");
    assert!(err.is_empty(), "{err:?}");
    assert_eq!(requests.len(), 1);
    assert_download_discovery(&requests[0], true);
    assert_eq!(std::fs::read(&destination)?, b"original");
    Ok(())
}

fn assert_download_discovery(request: &str, recursive: bool) {
    let prefix = if recursive {
        "GET /bucket?"
    } else {
        "HEAD /bucket/prefix/object "
    };
    assert!(request.starts_with(prefix));
}

fn run_loopback(
    cwd: &Path,
    mut arguments: Args,
    request_count: usize,
) -> Result<Capture, Box<dyn std::error::Error>> {
    let setup_started = Instant::now();
    let listener = TcpListener::bind("127.0.0.1:0")?;
    listener.set_nonblocking(true)?;
    let globals = Globals {
        endpoint_url: Some(format!("http://{}", listener.local_addr()?)),
        region: Some("us-east-1".into()),
        ..Default::default()
    };
    let server = std::thread::spawn(move || serve(&listener, request_count));
    let mut client = ClientConfig::new(Command::Cp);
    client.signing.value = false;
    client.request_checksum.value = ChecksumMode::WhenRequired;
    client.response_checksum.value = ChecksumMode::WhenRequired;
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let payload_started = Instant::now();
    let payload = payload()?;
    let payload_elapsed = payload_started.elapsed();
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: cwd,
        payload: &payload,
    };
    arguments.progress = false;
    arguments.quiet = false;
    let (mut out, mut err) = (Vec::new(), Vec::new());
    let setup_elapsed = setup_started.elapsed();
    let command_started = Instant::now();
    let result = run(&context, &arguments, &mut out, &mut err);
    let command_elapsed = command_started.elapsed();
    let server_result = server
        .join()
        .map_err(|_| io::Error::other("raw-path server panicked"))
        .and_then(|outcome| outcome);
    if server_result.is_err() || !matches!(result, Ok(0)) {
        let kind = server_result
            .as_ref()
            .err()
            .map_or(io::ErrorKind::Other, io::Error::kind);
        return Err(io::Error::new(
            kind,
            format!(
                "raw-path command failed: recursive={}, paths={:?}, \
                 setup_elapsed={setup_elapsed:?}, payload_elapsed={payload_elapsed:?}, \
                 command_elapsed={command_elapsed:?}, command_result={result:?}, \
                 server_result={server_result:?}, stdout={:?}, stderr={:?}",
                arguments.dir_op,
                arguments.paths,
                OsStr::from_bytes(&out),
                OsStr::from_bytes(&err),
            ),
        )
        .into());
    }
    let requests = server_result?;
    assert_eq!(result?, 0, "{err:?}");
    Ok((out, err, requests))
}

fn serve(listener: &TcpListener, count: usize) -> io::Result<Vec<String>> {
    let started = Instant::now();
    let deadline = started + Duration::from_secs(10);
    let mut requests = Vec::new();
    let mut headers_received_after = Vec::new();
    let mut stage = "accept";
    let outcome = (|| {
        while requests.len() < count {
            stage = "accept";
            let stream = match listener.accept() {
                Ok((stream, _)) => stream,
                Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                    if Instant::now() >= deadline {
                        return Err(io::ErrorKind::TimedOut.into());
                    }
                    std::thread::sleep(Duration::from_millis(1));
                    continue;
                }
                Err(error) => return Err(error),
            };
            // On macOS an accepted socket inherits the listener's
            // non-blocking mode, which Linux never passes on; the reads below
            // wait for the client.
            stream.set_nonblocking(false)?;
            let mut stream = BufReader::new(stream);
            stage = "read headers";
            let headers = read_headers(&mut stream)?;
            let first = headers.lines().next().unwrap_or_default();
            requests.push(first.to_owned());
            headers_received_after.push(started.elapsed());
            stage = "write response";
            if first.starts_with("PUT ") {
                stage = "read upload body and write response";
                receive_upload(&mut stream, &headers)?;
            } else if first.starts_with("HEAD ") {
                stream.get_mut().write_all(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\
                Last-Modified: Wed, 21 Oct 2015 07:28:00 GMT\r\nConnection: close\r\n\r\n",
                )?;
            } else if first.contains('?') {
                let body = "<ListBucketResult><IsTruncated>false</IsTruncated><Contents>\
                <Key>prefix/object</Key><Size>4</Size></Contents></ListBucketResult>";
                write!(
                    stream.get_mut(),
                    "HTTP/1.1 200 OK\r\nContent-Length: {}\r\n\
                Connection: close\r\n\r\n{body}",
                    body.len()
                )?;
            } else if headers.to_ascii_lowercase().contains("\r\nrange:") {
                stream.get_mut().write_all(
                    b"HTTP/1.1 206 Partial Content\r\nContent-Length: 4\r\n\
                Content-Range: bytes 0-3/4\r\nConnection: close\r\n\r\ndata",
                )?;
            } else {
                stream.get_mut().write_all(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\
                Connection: close\r\n\r\ndata",
                )?;
            }
        }
        Ok(())
    })();
    outcome.map_err(|error: io::Error| {
        io::Error::new(
            error.kind(),
            format!(
                "raw-path server failed: stage={stage}, served={}/{count}, \
                 elapsed={:?}, requests={requests:?}, \
                 headers_received_after={headers_received_after:?}, cause={error:?}",
                requests.len(),
                started.elapsed(),
            ),
        )
    })?;
    Ok(requests)
}

fn read_headers(stream: &mut BufReader<TcpStream>) -> io::Result<String> {
    stream
        .get_ref()
        .set_read_timeout(Some(Duration::from_secs(5)))?;
    let mut headers = Vec::new();
    while !headers.ends_with(b"\r\n\r\n") && headers.len() < 65536 {
        let mut byte = [0];
        stream.read_exact(&mut byte)?;
        headers.push(byte[0]);
    }
    String::from_utf8(headers).map_err(io::Error::other)
}

fn receive_upload(stream: &mut BufReader<TcpStream>, headers: &str) -> io::Result<()> {
    let length = headers
        .lines()
        .find_map(|line| {
            let (name, value) = line.split_once(':')?;
            name.eq_ignore_ascii_case("content-length")
                .then(|| value.trim().parse::<usize>().ok())?
        })
        .ok_or_else(|| io::Error::other("upload length missing"))?;
    assert_eq!(length, 4);
    let mut data = [0; 4];
    stream.read_exact(&mut data)?;
    assert_eq!(&data, b"data");
    stream.get_mut().write_all(
        b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nETag: \"tag\"\r\n\
        Connection: close\r\n\r\n",
    )
}
