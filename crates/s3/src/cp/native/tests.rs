#![allow(
    clippy::expect_used,
    clippy::panic,
    clippy::too_many_lines,
    reason = "copy fixtures fail at the violated setup and keep each request matrix in one test"
)]
use super::*;
use cli_core::command::Globals;
use std::collections::BTreeMap;
use std::io;

fn args(source: &str, destination: &str, recursive: bool) -> Args {
    Args {
        paths: [source.into(), destination.into()],
        dir_op: recursive,
        dryrun: false,
        quiet: true,
        no_overwrite: false,
        page_size: None,
        only_show_errors: false,
        progress: true,
        progress_frequency: Some(0),
        progress_multiline: false,
        ignore_glacier_warnings: false,
        force_glacier_transfer: false,
        filters: Vec::new(),
        follow_symlinks: true,
        content_type: None,
        cache_control: None,
        content_disposition: None,
        content_encoding: None,
        content_language: None,
        expires: None,
        website_redirect: None,
        metadata: Default::default(),
        acl: None,
        storage_class: None,
        sse: None,
        sse_kms_key_id: None,
        sse_c: None,
        sse_c_key: None,
        request_payer: None,
        checksum_mode: None,
        checksum_algorithm: None,
        guess_mime_type: true,
        grants: Vec::new(),
        case_conflict: crate::sync::OnCaseConflict::Ignore,
    }
}
fn payload() -> io::Result<Vec<u8>> {
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX")
        .ok_or_else(|| io::Error::other("native payload prefix missing"))?;
    std::fs::read(PathBuf::from(prefix).join("awscli-v2.blob"))
}
#[cfg(not(windows))]
#[test]
fn local_operands_normalize_lexically_and_keep_double_slash_roots() {
    // The guess reads only the final component, so a malformed `//` netloc,
    // which upstream's `guess_type` raises for, still names a type.
    let database = crate::mime::Database::default();
    let text: Option<&[u8]> = Some(b"text/plain");
    for (source, normalized, guessed) in [
        ("//[foo/report.txt", "//[foo/report.txt", text),
        ("//a/../[foo/report.txt", "//[foo/report.txt", text),
        ("///[foo/report.txt", "/[foo/report.txt", text),
        ("/work/link/../file", "/work/file", None),
        ("dir/", "/cwd/dir/", None),
        ("./a//b/../c.txt", "/cwd/a/c.txt", text),
    ] {
        let arguments = args(source, "s3://bucket/a/../key", false);
        let plan = cp_args::make_copy_plan(&arguments);
        let local = normalize_local_operand(Path::new("/cwd"), &plan);
        assert_eq!(local, OsStr::new(normalized));
        assert_eq!(plan.destination, "s3://bucket/a/../key");
        assert_eq!(database.guess(Path::new(&local)), Ok(guessed), "{source}");
    }
    let arguments = args("s3://bucket/key", "out/../dir/", false);
    let plan = cp_args::make_copy_plan(&arguments);
    assert_eq!(
        normalize_local_operand(Path::new("/cwd"), &plan),
        OsStr::new("/cwd/dir/")
    );
}
#[cfg(not(windows))]
#[test]
fn a_recursive_download_prepares_its_raw_destination_before_normalizing() -> io::Result<()> {
    let root = std::env::temp_dir().join(format!("cp-raw-destination-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    std::fs::write(root.join("blocker"), b"original")?;
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &cli_core::client_config::ClientConfig::default(),
        directory: &root,
        payload: &[],
    };
    // `blocker/../dir` normalizes to `dir`, but its raw spelling cannot be
    // created, as upstream's `makedirs` of the raw destination fails.
    let destination = root.join("blocker/../dir");
    let arguments = args("s3://bucket/prefix", &destination.to_string_lossy(), true);
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    let failure = run(&context, &arguments, &mut stdout, &mut stderr).expect_err("raw failure");
    assert_eq!(failure.message, b"Not a directory");
    assert!(!root.join("dir").exists());
    assert!(stdout.is_empty() && stderr.is_empty());
    std::fs::remove_dir_all(root)
}
#[test]
fn every_direction_rejects_empty_region_before_runtime_or_payload_access() {
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        region: Some(String::new()),
        ..Default::default()
    };
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &cli_core::client_config::ClientConfig::default(),
        directory: Path::new("/"),
        payload: &[],
    };
    let root = std::env::temp_dir().join(format!("cp-empty-region-{}", std::process::id()));
    let local = root.join("local");
    let local = local.to_string_lossy();
    for recursive in [false, true] {
        for (source, destination) in [(".", "s3://bucket/key"), ("s3://bucket/key", &*local)] {
            let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
            assert_eq!(
                run(
                    &context,
                    &args(source, destination, recursive),
                    &mut stdout,
                    &mut stderr
                )
                .expect("empty region"),
                1
            );
            assert!(stdout.is_empty());
            assert_eq!(stderr, b"error: --region must not be empty\n");
        }
    }
    let _ = std::fs::remove_dir_all(root);
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn malformed_endpoint_is_reported_before_any_transfer() -> io::Result<()> {
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        endpoint_url: Some("not-a-url".into()),
        ..Default::default()
    };
    let payload = payload()?;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &cli_core::client_config::ClientConfig::default(),
        directory: Path::new("/unusable/working-directory"),
        payload: &payload,
    };
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    assert_eq!(
        run(
            &context,
            &args(".", "s3://bucket/key", false),
            &mut stdout,
            &mut stderr
        )
        .expect("endpoint diagnostic"),
        1
    );
    assert!(stdout.is_empty());
    assert_eq!(stderr, b"error: failed to resolve the S3 endpoint\n");
    Ok(())
}

#[test]
fn downloads_refuse_keys_botocore_cannot_encode() {
    let refusal = "'utf-8' codec can't encode character '\\udcff' in position 4: \
                   surrogates not allowed";
    let single = |key| uri::S3Uri { bucket: "b", key };
    let prefix = |prefix| uri::S3PrefixUri {
        bucket: "b",
        prefix,
    };
    for (operation, syncs) in [
        (Operation::SingleDownload(single(b"key-\xff")), false),
        (Operation::RecursiveDownload(prefix(b"key-\xff")), false),
        (Operation::RecursiveDownload(prefix(b"key-\xff")), true),
        (Operation::RecursiveUpload(prefix(b"key-\xff")), true),
    ] {
        assert_eq!(
            generator_key_refusal(operation, syncs).as_deref(),
            Some(refusal),
            "{operation:?} {syncs}"
        );
    }
    for (operation, syncs) in [
        (
            Operation::SingleDownload(single("k\u{e9}y".as_bytes())),
            false,
        ),
        (Operation::RecursiveDownload(prefix(b"")), false),
        (Operation::SingleUpload(single(b"key-\xff")), false),
        (Operation::RecursiveUpload(prefix(b"key-\xff")), false),
        (
            Operation::RecursiveUpload(prefix("k\u{e9}y/".as_bytes())),
            true,
        ),
    ] {
        assert_eq!(
            generator_key_refusal(operation, syncs),
            None,
            "{operation:?} {syncs}"
        );
    }
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_download_of_a_key_that_is_not_utf8_is_the_fatal_error() -> io::Result<()> {
    use std::os::unix::ffi::OsStrExt;
    let root = std::env::temp_dir().join(format!("cp-key-refusal-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        region: Some("us-east-1".into()),
        ..Default::default()
    };
    let payload = payload()?;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &cli_core::client_config::ClientConfig::default(),
        directory: &root,
        payload: &payload,
    };
    let destination = root.join("out");
    for recursive in [false, true] {
        let mut input = args("s3://bucket/key", &destination.to_string_lossy(), recursive);
        input.quiet = false;
        input.paths[0] = OsStr::from_bytes(b"s3://bucket/key-\xff").into();
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let status = run(&context, &input, &mut stdout, &mut stderr).expect("fatal error");
        assert_eq!(status, 1);
        assert!(stdout.is_empty(), "{stdout:?}");
        assert_eq!(
            String::from_utf8_lossy(&stderr),
            "fatal error: 'utf-8' codec can't encode character '\\udcff' in position 4: \
             surrogates not allowed\n"
        );
        // The recursive download prepared its missing destination, as
        // upstream does before it lists anything.
        assert_eq!(destination.exists(), recursive);
    }
    std::fs::remove_dir(&destination)?;
    std::fs::remove_dir(&root)
}

#[test]
fn printer_broken_pipe_becomes_python_command_failure() {
    let failure = io_failure(io::ErrorKind::BrokenPipe.into());
    assert_eq!(
        failure.message,
        cli_core::cli_error::BROKEN_PIPE_MESSAGE.as_bytes()
    );
    assert_eq!(cli_core::cli_error::exit_status(failure.category), 255);
}

// Upstream does not flag a bare `..` basename on any host: it joins it to
// the directory, and the transfer fails on that path after the GET. The
// path is the directory's parent, where nothing may be created. A `\` is a
// separator only on Windows, where the key has no `/` basename boundary to
// strip the parent reference; on POSIX it names a file inside the directory.
#[test]
fn download_destination_flags_a_basename_only_where_upstream_normalizes_it_above() -> io::Result<()>
{
    let root = std::env::temp_dir().join(format!("s3-destination-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let (destination, outcome) = download_destination(root.as_os_str(), b"nested/prefix/..");
    assert_eq!(destination, root.join(".."));
    assert_eq!(outcome, EntryLocal::RootParent);
    let (destination, outcome) =
        download_destination(root.as_os_str(), br"nested/prefix/..\escaped.txt");
    if cfg!(windows) {
        assert_eq!(destination, root);
        assert_eq!(outcome, EntryLocal::ParentEscape(r"..\escaped.txt".into()));
    } else {
        assert_eq!(destination, root.join(r"..\escaped.txt"));
        assert_eq!(outcome, EntryLocal::Resolved);
    }
    let file = root.join("file");
    let (destination, outcome) = download_destination(file.as_os_str(), b"prefix/..");
    assert_eq!(destination, file);
    assert_eq!(outcome, EntryLocal::Resolved);
    std::fs::remove_dir(root)
}
#[test]
fn recursive_boundaries_preserve_settings_normalization_and_sizing() {
    let env = BTreeMap::from([("ZS3_TRANSFER_STATS".into(), "1".into())]);
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        profile: Some("named".into()),
        ..Default::default()
    };
    let mut client =
        cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Cp);
    client.target_gbps.value = 25.0;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: Path::new("/"),
        payload: &[],
    };
    let settings = config::Settings {
        in_flight_max: Some(512),
        io_workers: Some(3),
        ..Default::default()
    };
    for download in [false, true] {
        let mut arguments = if download {
            args("s3://bucket/prefix", "destination", true)
        } else {
            args("source", "s3://bucket/prefix", true)
        };
        arguments.page_size = Some(17);
        arguments.no_overwrite = true;
        let plan = cp_args::make_copy_plan(&arguments);
        let options = RuntimeOptions {
            region: "us-test-1".into(),
            signing_region: Some("us-sign-1".into()),
            endpoint_url: "http://localhost:1/bucket".into(),
            connect_timeout_ms: 4321,
            throughput_target_gbps: 25.0,
            ..Default::default()
        };
        let request = recursive_request(
            &context,
            &plan,
            uri::S3PrefixUri {
                bucket: "bucket",
                prefix: b"prefix",
            },
            &settings,
            options.clone(),
        );
        assert_recursive_paths(&request, download);
        assert_runtime_options(&request.runtime, &options);
        assert_eq!(
            (request.quiet, request.no_overwrite, request.collect_stats),
            (true, true, true)
        );
        assert_eq!(request.max_in_flight, 512);
        assert_eq!(
            request.download,
            download.then(|| settings.resolve_download())
        );
        assert_recursive_sizing(&request, download);
    }
}
fn assert_runtime_options(actual: &RuntimeOptions, expected: &RuntimeOptions) {
    assert_eq!(actual.region, expected.region);
    assert_eq!(actual.signing_region, expected.signing_region);
    assert_eq!(actual.endpoint_url, expected.endpoint_url);
    assert_eq!(actual.connect_timeout_ms, expected.connect_timeout_ms);
}
fn assert_recursive_paths(request: &recursive::TransferRequest, download: bool) {
    let (direction, root) = if download {
        (Direction::Download, "destination/")
    } else {
        (Direction::Upload, "source/")
    };
    assert_eq!(request.direction, direction);
    assert_eq!(request.local_root, Path::new(root));
    assert_eq!(request.bucket, "bucket");
    assert_eq!(request.prefix, b"prefix/");
}
fn assert_recursive_sizing(request: &recursive::TransferRequest, download: bool) {
    let (memory, throughput) = if download {
        (4 << 30, 0.4 * (512.0 + 32.0))
    } else {
        (0, 25.0)
    };
    assert_eq!(request.page_size, 17);
    assert_eq!(request.sizing.memory_limit_in_bytes, memory);
    assert_eq!(request.sizing.source_pool_bytes, 4 << 30);
    assert_eq!(request.sizing.single_request_bytes_max, 4 << 30);
    assert_eq!(request.sizing.throughput_target_gbps, throughput);
    assert_eq!(request.runtime.throughput_target_gbps, 25.0);
}
#[test]
fn unusable_recursive_roots_fail_before_creating_crt_runtime() -> io::Result<()> {
    let root = std::env::temp_dir().join(format!("cp-root-validation-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let blocker = root.join("blocker");
    std::fs::write(&blocker, b"original")?;
    let local = blocker.join("child");
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals {
        endpoint_url: Some("http://localhost:1".into()),
        ..Default::default()
    };
    let payload = payload()?;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &cli_core::client_config::ClientConfig::default(),
        directory: &root,
        payload: &payload,
    };
    for download in [false, true] {
        let local_text = local.to_string_lossy();
        let arguments = if download {
            args("s3://bucket/prefix", &local_text, true)
        } else {
            args(&local_text, "s3://bucket/prefix", true)
        };
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let result = run(&context, &arguments, &mut stdout, &mut stderr);
        if download {
            assert_eq!(
                result.expect_err("invalid download root").message,
                b"Not a directory"
            );
        } else {
            let failure = result.expect_err("upload source preflight");
            assert_eq!(failure.category, cli_core::cli_error::Category::General);
            assert_eq!(
                failure.message,
                format!("The user-provided path {local_text} does not exist.").as_bytes(),
            );
        }
        assert!(stderr.is_empty());
        assert!(stdout.is_empty());
    }
    assert_eq!(std::fs::read(blocker)?, b"original");
    std::fs::remove_dir_all(root)
}

// AWS CLI v2 treats an existing directory or a trailing separator as a
// directory destination that takes the key's basename; like its
// `os.path.isdir`, a destination that cannot be examined is no directory,
// and the transfer fails on that path once it prepares its output.
fn resolve(destination: &Path, key: &str) -> PathBuf {
    download_destination(destination.as_os_str(), key.as_bytes()).0
}
#[test]
fn download_destinations_take_the_basename_only_for_directories() -> io::Result<()> {
    let root = std::env::temp_dir().join(format!("cp-resolve-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    assert_eq!(resolve(&root, "prefix/name"), root.join("name"));
    let missing = root.join("missing/");
    assert_eq!(resolve(&missing, "prefix/name"), missing.join("name"));
    // A `\` is a separator only on Windows; on POSIX it ends a file's name.
    let backslash = root.join("missing\\");
    let expected = if cfg!(windows) {
        backslash.join("name")
    } else {
        backslash.clone()
    };
    assert_eq!(resolve(&backslash, "prefix/name"), expected);
    let destination = root.join("destination");
    assert_eq!(resolve(&destination, "key"), destination);
    std::fs::write(&destination, b"existing")?;
    assert_eq!(resolve(&destination, "key"), destination);
    // A component over NAME_MAX fails stat even when the test user is root.
    let unexaminable = PathBuf::from(format!("/{}/child", "x".repeat(256)));
    assert_eq!(resolve(&unexaminable, "a b"), unexaminable);
    std::fs::remove_dir_all(root)
}

// Upstream's path ends with the separator whether or not the operand spells
// one, so the temp file and the result line stay inside the directory.
#[test]
fn single_download_keeps_the_directory_separator_for_a_folder_marker_s_empty_basename()
-> io::Result<()> {
    let root = std::env::temp_dir().join(format!("cp-folder-marker-{}", std::process::id()));
    let directory = root.join("my-dir");
    std::fs::create_dir_all(&directory)?;
    let mut expected = directory.clone().into_os_string();
    expected.push(std::path::MAIN_SEPARATOR_STR);
    for destination in [directory.as_os_str(), expected.as_os_str()] {
        let resolved = resolve(Path::new(destination), "nested/folder/");
        assert_eq!(resolved.as_os_str(), expected.as_os_str());
    }
    std::fs::remove_dir_all(root)
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn recursive_connections_keep_the_floor_unless_the_cap_is_explicit() {
    use cli_core::client_config::{ClientConfig, Command, Resolved, Source};
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    let arguments = args("s3://bucket/prefix", "destination", true);
    let plan = cp_args::make_copy_plan(&arguments);
    let mut client = ClientConfig::new(Command::Cp);
    for (cap, client_cap, expected) in [
        (Resolved::new(10, Source::Persona), 10, 0),
        (
            Resolved::new(3, Source::S3("max_concurrent_requests")),
            3,
            3,
        ),
    ] {
        client.max_connections = Some(cap);
        let context = CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            client: &client,
            directory: Path::new("/"),
            payload: &[],
        };
        let request = recursive_request(
            &context,
            &plan,
            uri::S3PrefixUri {
                bucket: "bucket",
                prefix: b"prefix",
            },
            &config::Settings::default(),
            command::client_options(&client, false),
        );
        assert_eq!(request.runtime.max_active_connections_override, client_cap);
        assert_eq!(request.sizing.max_connections, expected);
    }
}

fn sized_recursive_request(
    env: &BTreeMap<String, String>,
    client: &cli_core::client_config::ClientConfig,
    settings: &config::Settings,
) -> recursive::TransferRequest {
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    let arguments = args("s3://bucket/prefix", "destination", true);
    let plan = cp_args::make_copy_plan(&arguments);
    let context = CommandContext {
        env,
        shared_files: &files,
        globals: &globals,
        client,
        directory: Path::new("/"),
        payload: &[],
    };
    recursive_request(
        &context,
        &plan,
        uri::S3PrefixUri {
            bucket: "bucket",
            prefix: b"prefix",
        },
        settings,
        command::client_options(client, false),
    )
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn a_recursive_download_defers_to_the_memory_limit_variables_the_record_read() {
    use cli_core::client_config::{ClientConfig, Command, MemoryLimit};
    let env = BTreeMap::from([("AWS_CRT_S3_MEMORY_LIMIT_IN_GIB".into(), "1".into())]);
    let settings = config::Settings {
        in_flight_max: Some(11),
        ..Default::default()
    };
    for pool in [6 << 30, 256 << 20] {
        let mut client = ClientConfig::new(Command::Cp);
        client.target_gbps.value = 12.5;
        client.memory_limit.value = MemoryLimit::Override(pool);
        let request = sized_recursive_request(&env, &client, &settings);
        assert!((request.sizing.throughput_target_gbps - 17.2).abs() <= 0.0001);
        assert_eq!(request.sizing.memory_limit_in_bytes, 0);
        assert_eq!(request.sizing.source_pool_bytes, pool);
        assert_eq!(request.sizing.single_request_bytes_max, pool);
        assert_eq!(request.engine_window(), 11);
    }
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn the_records_target_and_client_settings_reach_recursive_transfer_requests() {
    use cli_core::client_config::{ClientConfig, Command, Resolved, Source};
    let mut client = ClientConfig::new(Command::Cp);
    client.target_gbps = Resolved::new(12.5, Source::S3("target_bandwidth"));
    client.part_size = Resolved::new(5 << 20, Source::S3("multipart_chunksize"));
    client.max_connections = Some(Resolved::new(3, Source::S3("max_concurrent_requests")));
    let request = sized_recursive_request(&BTreeMap::new(), &client, &config::Settings::default());
    assert_eq!(request.sizing.throughput_target_gbps, 12.5);
    assert_eq!(request.sizing.memory_limit_in_bytes, 2 << 30);
    assert_eq!(request.sizing.source_pool_bytes, 2 << 30);
    assert_eq!(request.sizing.max_connections, 3);
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn a_recursive_downloads_scheduler_bounds_single_request_bodies_by_the_tier() {
    use cli_core::client_config::{ClientConfig, Command, Resolved, Source};
    let mut client = ClientConfig::new(Command::Cp);
    client.target_gbps.value = 200.0;
    client.multipart_threshold = Some(Resolved::new(32 << 20, Source::S3("multipart_threshold")));
    let request = sized_recursive_request(&BTreeMap::new(), &client, &config::Settings::default());
    let mapped = cfg!(any(target_os = "linux", target_os = "macos"));
    assert_eq!(
        request.sizing.source_pool_bytes,
        if mapped { 4 << 30 } else { 24 << 30 }
    );
    assert_eq!(request.sizing.single_request_bytes_max, 24 << 30);
    assert_eq!(request.runtime.single_request_threshold, Some(32 << 20));
    assert_eq!(
        request.engine_window(),
        crate::constants::IN_FLIGHT_MAX_DEFAULT
    );
}

#[cfg(unix)]
fn file_trust(path: Option<PathBuf>) -> crt::runtime::Trust {
    path.map_or(crt::runtime::Trust::Platform, |path| {
        crt::runtime::Trust::File { path, setting: "" }
    })
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn single_upload_builds_its_client_before_it_warns_or_inspects_its_source() -> io::Result<()> {
    let root = std::env::temp_dir().join(format!("cp-single-upload-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let regular = root.join("local.txt");
    std::fs::write(&regular, b"local")?;
    let special = PathBuf::from("/dev/null");
    for (source, refuse, invalid_ca) in [
        (&special, false, true),
        (&regular, false, true),
        (&special, false, false),
        (&special, true, true),
    ] {
        let request = recursive::TransferRequest {
            direction: Direction::Upload,
            bucket: "bucket".into(),
            prefix: Vec::new(),
            local_root: PathBuf::new(),
            runtime: RuntimeOptions {
                region: "us-east-1".into(),
                endpoint_url: "https://127.0.0.1:9/bucket".into(),
                no_sign_request: true,
                trust: file_trust(invalid_ca.then(|| root.join("missing-ca.pem"))),
                ..Default::default()
            },
            quiet: true,
            dryrun: false,
            no_overwrite: false,
            glacier: transfer::GlacierPolicy::Warn,
            content_types: None,
            refusal: refuse.then(|| "endpoint rule refused".into()),
            page_size: 0,
            max_in_flight: 4,
            collect_stats: false,
            prefetch: false,
            sizing: Default::default(),
            download: None,
            object: Some(recursive::SingleObject {
                key: b"key".to_vec(),
                local_path: source.clone(),
                local: EntryLocal::Resolved,
                remote: None,
            }),
            filter: Default::default(),
            headers: Default::default(),
            checksums: Default::default(),
            delete: Default::default(),
            sources: Default::default(),
            sync: None,
            listing_user_agent: None,
            links: Default::default(),
        };
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let result = crt_backend::run(
            request,
            &crt_backend::NativeEnv {
                cwd: &root,
                debug: false,
                resolver: None,
            },
            source.as_os_str(),
            None,
            "warning: ignored setting\n",
            &mut stdout,
            &mut stderr,
        );
        assert!(stdout.is_empty());
        if invalid_ca && !refuse {
            let failure = result.expect_err("client failure");
            assert_eq!(failure.category, cli_core::cli_error::Category::General);
            assert!(stderr.is_empty());
        } else {
            assert_eq!(result.expect("skipped source"), 2);
            assert_eq!(stderr, b"warning: ignored setting\n");
        }
    }
    std::fs::remove_dir_all(root)
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test checks every field the upload request carries"
)]
fn single_upload_requests_carry_the_key_destination_and_settings() {
    let env = BTreeMap::from([("ZS3_TRANSFER_STATS".into(), "1".into())]);
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    let client = cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Cp);
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: Path::new("/work"),
        payload: &[],
    };
    let root = if cfg!(windows) { "C:\\" } else { "/" };
    let cases: [(&str, &str, &[u8], Option<&str>); 4] = [
        (
            "local.txt",
            "s3://bucket/a b%?#.txt",
            b"a b%?#.txt",
            Some("s3://bucket/a b%?#.txt"),
        ),
        ("local.txt", "s3://bucket/", b"local.txt", None),
        ("local.txt", "s3://bucket/dir/", b"dir/local.txt", None),
        (root, "s3://bucket", b"", Some("s3://bucket")),
    ];
    for (source, destination, key, remote) in cases {
        let options = RuntimeOptions {
            region: "us-test-7".into(),
            endpoint_url: "http://localhost:4566/base/bucket".into(),
            keep_alive: true,
            throughput_target_gbps: 12.5,
            ..Default::default()
        };
        let request = upload_request(&context, &options, source, destination);
        assert_eq!(request.direction, Direction::Upload);
        assert_eq!(request.bucket, "bucket");
        assert_eq!(
            request.object,
            Some(recursive::SingleObject {
                key: key.to_vec(),
                local_path: source.into(),
                local: EntryLocal::Resolved,
                remote: remote.map(Into::into),
            })
        );
        assert_runtime_options(&request.runtime, &options);
        assert_eq!(request.runtime.throughput_target_gbps, 12.5);
        assert_eq!((request.quiet, request.collect_stats), (true, true));
        assert_eq!(request.refusal, None);
        assert!(request.content_types.is_some());
        assert_eq!(
            request.max_in_flight,
            crate::constants::IN_FLIGHT_MAX_DEFAULT
        );
        assert_eq!((request.engine_window(), request.finish_workers()), (1, 1));
    }
}

#[test]
fn only_an_upload_that_guesses_loads_the_type_database() {
    let upload = args("local.txt", "s3://bucket/key", false);
    let typed = Args {
        content_type: Some("text/x-explicit".into()),
        ..upload.clone()
    };
    let unguessed = Args {
        guess_mime_type: false,
        ..upload.clone()
    };
    let download = args("s3://bucket/key", "local.txt", false);
    for (args, loads) in [
        (&upload, true),
        (&typed, false),
        (&unguessed, false),
        (&download, false),
    ] {
        let plan = cp_args::make_copy_plan(args);
        assert_eq!(content_types(&plan).is_some(), loads, "{args:?}");
    }
}

#[test]
fn a_directory_single_upload_keeps_its_trailing_separator() -> io::Result<()> {
    let env = BTreeMap::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    let client = cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Cp);
    let directory =
        std::env::temp_dir().join(format!("cp-directory-source-{}", std::process::id()));
    std::fs::create_dir_all(&directory)?;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: &directory,
        payload: &[],
    };
    let mut separated = directory.clone().into_os_string();
    separated.push(std::path::MAIN_SEPARATOR_STR);
    let source = directory.to_str().expect("a UTF-8 temp directory");
    for (destination, key, remote) in [
        ("s3://bucket/", b"".as_slice(), Some("s3://bucket/")),
        (
            "s3://bucket/prefix/",
            b"prefix/",
            Some("s3://bucket/prefix/"),
        ),
        ("s3://bucket/key", b"key", Some("s3://bucket/key")),
    ] {
        let request = upload_request(&context, &RuntimeOptions::default(), source, destination);
        let object = request.object.expect("one object");
        assert_eq!(object.key, key, "{destination}");
        assert_eq!(object.local_path.as_os_str(), separated.as_os_str());
        assert_eq!(object.remote, remote.map(Into::into));
    }
    std::fs::remove_dir(&directory)
}
fn upload_request(
    context: &CommandContext<'_, BTreeMap<String, String>>,
    options: &RuntimeOptions,
    source: &str,
    destination: &str,
) -> recursive::TransferRequest {
    let arguments = args(source, destination, false);
    let plan = cp_args::make_copy_plan(&arguments);
    let uri = match plan.operation {
        Operation::SingleUpload(uri) => Some(uri),
        _ => None,
    }
    .expect("a single upload");
    let prepared = command::PreparedRuntime {
        options: options.clone(),
        refusal: None,
        resolver: None,
    };
    single_upload_request(context, &plan, uri, &config::Settings::default(), prepared)
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn recursive_client_failures_reach_the_general_handler_without_the_warning() -> io::Result<()> {
    let root = std::env::temp_dir().join(format!("cp-recursive-client-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    for direction in [Direction::Upload, Direction::Download] {
        for quiet in [false, true] {
            let request = recursive::TransferRequest {
                direction,
                bucket: "bucket".into(),
                prefix: Vec::new(),
                local_root: root.clone(),
                runtime: RuntimeOptions {
                    region: "us-east-1".into(),
                    endpoint_url: "https://127.0.0.1:9/bucket".into(),
                    no_sign_request: true,
                    trust: file_trust(Some(root.join("missing-ca.pem"))),
                    ..Default::default()
                },
                quiet,
                dryrun: false,
                no_overwrite: false,
                glacier: transfer::GlacierPolicy::Warn,
                content_types: None,
                refusal: None,
                page_size: 0,
                max_in_flight: 4,
                collect_stats: true,
                prefetch: false,
                sizing: Default::default(),
                download: (direction == Direction::Download)
                    .then(|| config::Settings::default().resolve_download()),
                object: None,
                filter: Default::default(),
                headers: Default::default(),
                checksums: Default::default(),
                delete: Default::default(),
                sources: Default::default(),
                sync: None,
                listing_user_agent: None,
                links: Default::default(),
            };
            let printer = (!quiet).then(crate::results::PrinterConfig::default);
            let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
            let failure = crt_backend::run(
                request,
                &crt_backend::NativeEnv {
                    cwd: &root,
                    debug: false,
                    resolver: None,
                },
                OsStr::new("source"),
                printer,
                "warning: ignored setting\n",
                &mut stdout,
                &mut stderr,
            )
            .expect_err("client failure");
            assert_eq!(failure.category, cli_core::cli_error::Category::General);
            assert!(!failure.message.is_empty());
            assert!(stdout.is_empty());
            assert!(stderr.is_empty(), "{}", String::from_utf8_lossy(&stderr));
        }
    }
    std::fs::remove_dir_all(root)
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn single_download_setup_failures_reach_the_general_handler_before_the_warning() -> io::Result<()> {
    use crate::download::{NumaMode, Requirement};
    let root = std::env::temp_dir().join(format!("cp-single-setup-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let missing_ca = root.join("missing-ca.pem");
    for unplaceable in [false, true] {
        let mut tuning = config::Settings::default().resolve_download();
        if unplaceable {
            tuning.writer.numa.mode = NumaMode::SameNode;
            tuning.writer.numa.nodes = vec![0, 1];
            tuning.writer.numa.requirement = Requirement::Required;
        }
        let request = recursive::TransferRequest {
            direction: Direction::Download,
            bucket: "bucket".into(),
            prefix: Vec::new(),
            local_root: PathBuf::new(),
            runtime: RuntimeOptions {
                region: "us-east-1".into(),
                endpoint_url: "https://127.0.0.1:9/bucket".into(),
                no_sign_request: true,
                trust: file_trust((!unplaceable).then(|| missing_ca.clone())),
                ..Default::default()
            },
            quiet: true,
            dryrun: false,
            no_overwrite: false,
            glacier: transfer::GlacierPolicy::Warn,
            content_types: None,
            refusal: None,
            page_size: 0,
            max_in_flight: 4,
            collect_stats: false,
            prefetch: false,
            sizing: Default::default(),
            download: Some(tuning),
            object: Some(recursive::SingleObject {
                key: b"key".to_vec(),
                local_path: root.join("object"),
                local: EntryLocal::Resolved,
                remote: Some("s3://bucket/key".into()),
            }),
            filter: Default::default(),
            headers: Default::default(),
            checksums: Default::default(),
            delete: Default::default(),
            sources: Default::default(),
            sync: None,
            listing_user_agent: None,
            links: Default::default(),
        };
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let failure = crt_backend::run(
            request,
            &crt_backend::NativeEnv {
                cwd: &root,
                debug: false,
                resolver: None,
            },
            OsStr::new("s3://bucket/key"),
            None,
            "warning: ignored setting\n",
            &mut stdout,
            &mut stderr,
        )
        .expect_err("setup fails the command");
        assert_eq!(failure.category, cli_core::cli_error::Category::General);
        if unplaceable {
            assert!(failure.message.starts_with(b"Numa"), "{failure:?}");
        } else {
            assert!(!failure.message.starts_with(b"Numa"), "{failure:?}");
        }
        assert!(stdout.is_empty());
        assert!(stderr.is_empty());
        assert!(!root.join("object").exists());
    }
    std::fs::remove_dir_all(root)
}

#[cfg(unix)]
#[test]
fn single_download_requests_carry_the_settings_and_the_resolved_destination() -> io::Result<()> {
    use crate::download::WriterMode;
    let env = BTreeMap::from([("ZS3_TRANSFER_STATS".into(), "1".into())]);
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    let mut client =
        cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Cp);
    client.direct_io = Some(cli_core::client_config::Resolved::new(
        true,
        cli_core::client_config::Source::S3("direct_io"),
    ));
    let root = std::env::temp_dir().join(format!("cp-single-request-{}", std::process::id()));
    std::fs::create_dir_all(root.join("dir"))?;
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: &root,
        payload: &[],
    };
    let directory = root.join("dir");
    let into_directory = directory.join("a b%?#.txt");
    let cases = [
        (
            "s3://bucket/nested/a b%?#.txt",
            directory.clone(),
            b"nested/a b%?#.txt".as_slice(),
            into_directory.clone(),
            EntryLocal::Resolved,
        ),
        (
            "s3://bucket/object",
            into_directory.clone(),
            b"object",
            into_directory,
            EntryLocal::Resolved,
        ),
        // A bare `..` basename does not rule the transfer out: it fails on
        // the directory's parent after the GET.
        (
            "s3://bucket/nested/..",
            directory.clone(),
            b"nested/..",
            directory.join(".."),
            EntryLocal::RootParent,
        ),
    ];
    for (source, destination, key, local_path, local) in cases {
        let destination = destination.into_os_string();
        let arguments = Args {
            paths: [source.into(), destination.clone()],
            ..args(source, "", false)
        };
        let plan = cp_args::make_copy_plan(&arguments);
        let Operation::SingleDownload(uri) = plan.operation else {
            panic!("a single download");
        };
        let options = RuntimeOptions {
            region: "us-test-7".into(),
            endpoint_url: "http://localhost:4566/base/bucket".into(),
            keep_alive: true,
            throughput_target_gbps: 12.5,
            ..Default::default()
        };
        let prepared = command::PreparedRuntime {
            options: options.clone(),
            refusal: None,
            resolver: None,
        };
        let settings = config::Settings::default();
        let request = single_download_request(&context, &plan, uri, &settings, prepared);
        assert_eq!(request.direction, Direction::Download);
        assert_eq!(request.bucket, "bucket");
        assert_eq!(
            request.object,
            Some(recursive::SingleObject {
                key: key.to_vec(),
                local_path,
                local,
                remote: Some(source.into()),
            })
        );
        assert_runtime_options(&request.runtime, &options);
        assert_eq!((request.quiet, request.collect_stats), (true, true));
        assert_eq!(
            request.max_in_flight,
            crate::constants::IN_FLIGHT_MAX_DEFAULT
        );
        assert_eq!((request.engine_window(), request.finish_workers()), (1, 1));
        let tuning = request.download.expect("download tuning");
        assert_eq!(tuning.writer.mode, WriterMode::Direct);
        assert!(!tuning.custom_writer_required);
    }
    std::fs::remove_dir_all(root)
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn ignored_settings_warn_once_before_request_rules_even_in_quiet_mode() -> io::Result<()> {
    let bytes = payload()?;
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let mut client =
        cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Cp);
    client.use_accelerate_endpoint.value = true;
    client.ignored.retry_mode_adaptive = true;
    client.ignored.max_attempts = Some(1);
    let warning = concat!(
        "warning: The following configuration values are not supported by the ",
        "'crt' s3 transfer client and will be ignored: retry_mode = adaptive, ",
        "max_attempts = 1 (must be between 2 and 64).\n"
    );
    let root = std::env::temp_dir().join(format!("cp-warning-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let path = root.join("source");
    std::fs::write(&path, b"source")?;
    let source = path.to_string_lossy();
    let globals = Globals {
        region: Some("us-east-1".into()),
        ..Default::default()
    };
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: &root,
        payload: &bytes,
    };
    for (source, destination, status) in [
        (source.as_ref(), "s3://bucket.with.dots/key", 1),
        ("/dev/null", "s3://bucket.with.dots/key", 2),
        ("s3://bucket.with.dots/key", "destination", 1),
    ] {
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        assert_eq!(
            run(
                &context,
                &args(source, destination, false),
                &mut stdout,
                &mut stderr
            )
            .expect("rule result"),
            status
        );
        assert!(stdout.is_empty());
        assert_eq!(stderr, warning.as_bytes());
    }
    let missing = root.join("missing");
    for recursive in [false, true] {
        let mut arguments = args("source", "s3://bucket.with.dots/key", recursive);
        arguments.paths[0] = missing.clone().into_os_string();
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let failure = run(&context, &arguments, &mut stdout, &mut stderr)
            .expect_err("source absence precedes ignored settings");
        assert_eq!(failure.category, cli_core::cli_error::Category::General);
        assert_eq!(
            failure.message,
            [
                b"The user-provided path ".as_slice(),
                missing.as_os_str().as_encoded_bytes(),
                b" does not exist.",
            ]
            .concat()
        );
        assert!(stdout.is_empty());
        assert!(stderr.is_empty());
    }
    std::fs::remove_dir_all(root)
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn an_endpoint_rule_error_fails_the_single_download_after_the_warning() -> io::Result<()> {
    let bytes = payload()?;
    let env = BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let mut client =
        cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Cp);
    client.use_accelerate_endpoint.value = true;
    client.ignored.retry_mode_adaptive = true;
    client.ignored.max_attempts = Some(1);
    let warning = concat!(
        "warning: The following configuration values are not supported by the ",
        "'crt' s3 transfer client and will be ignored: retry_mode = adaptive, ",
        "max_attempts = 1 (must be between 2 and 64).\n"
    );
    let root = std::env::temp_dir().join(format!("cp-rule-error-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    let globals = Globals {
        region: Some("us-east-1".into()),
        ..Default::default()
    };
    let context = CommandContext {
        env: &env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: &root,
        payload: &bytes,
    };
    for quiet in [false, true] {
        let mut arguments = args("s3://bucket.with.dots/object", "local.txt", false);
        arguments.quiet = quiet;
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let status = run(&context, &arguments, &mut stdout, &mut stderr).expect("rule result");
        assert_eq!(status, 1);
        assert!(stdout.is_empty());
        let fatal = "fatal error: Path-style addressing cannot be used with S3 Accelerate\n";
        let expected = if quiet {
            warning.to_owned()
        } else {
            [warning, fatal].concat()
        };
        assert_eq!(String::from_utf8_lossy(&stderr), expected);
        assert!(!root.join("local.txt").exists());
    }
    std::fs::remove_dir_all(root)
}

#[test]
fn the_transfer_runs_on_the_callers_thread_beside_the_processors_own() {
    let caller = std::thread::current().id();
    let drained_on = std::sync::Arc::new(std::sync::Mutex::new(None));
    let recorded = std::sync::Arc::clone(&drained_on);
    let mut transferred_on = None;
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    let processor = crate::results::Processor::with_diagnostics(None);
    let status = crt_backend::run_reported(
        processor,
        (&mut stdout, &mut stderr),
        |scope, drain| {
            crate::results::spawn_drain(
                scope,
                Box::new(move || {
                    *recorded.lock().expect("drain thread record") =
                        Some(std::thread::current().id());
                    drain()
                }),
            )
        },
        |publisher| {
            transferred_on = Some(std::thread::current().id());
            publisher.publish(crate::results::Event::Diagnostic(b"diagnostic".to_vec()));
            Ok(0)
        },
    );
    assert_eq!(status.expect("transfer status"), 0);
    assert_eq!(transferred_on, Some(caller));
    let drained_on = drained_on.lock().expect("drain thread record").take();
    assert!(drained_on.is_some_and(|id| id != caller), "{drained_on:?}");
    assert!(stdout.is_empty());
    assert_eq!(stderr, b"diagnostic\n");
}

#[cfg(unix)]
#[test]
fn a_refused_processor_thread_fails_the_command_before_the_transfer() {
    for printer in [None, Some(crate::results::PrinterConfig::default())] {
        let mut transferred = false;
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let failure = crt_backend::run_reported(
            crate::results::Processor::with_diagnostics(printer),
            (&mut stdout, &mut stderr),
            |_, _| Err(io::Error::from_raw_os_error(libc::EAGAIN)),
            |_| {
                transferred = true;
                Ok(0)
            },
        )
        .expect_err("spawn failure");
        assert_eq!(failure.category, cli_core::cli_error::Category::General);
        assert_eq!(failure.message, b"Insufficient system resources");
        assert!(!transferred);
        assert!(stdout.is_empty() && stderr.is_empty());
    }
}

#[cfg(unix)]
mod raw_paths;
