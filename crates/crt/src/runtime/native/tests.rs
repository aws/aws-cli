use super::*;

fn runtime_snapshot(runtime: &Runtime) -> c::RuntimeSnapshot {
    let mut snapshot = c::RuntimeSnapshot::default();
    // SAFETY: the shim copies a layout-checked value from a live runtime.
    unsafe { c::zaws_runtime_snapshot(runtime.pointer(), &mut snapshot) };
    snapshot
}

#[test]
fn file_and_memory_trust_stores_construct_tls_for_both_verification_modes()
-> Result<(), Box<dyn std::error::Error>> {
    let path =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("testdata/client-config-ca.pem");
    let pem = std::fs::read(&path)?;
    for in_memory in [false, true] {
        for verify_peer in [false, true] {
            let runtime = Runtime::new(RuntimeOptions {
                endpoint_url: "https://localhost".into(),
                event_loop_count: 1,
                no_sign_request: true,
                verify_peer,
                trust: if in_memory {
                    Trust::Pem(pem.clone())
                } else {
                    Trust::File {
                        path: path.clone(),
                        setting: "--ca-bundle",
                    }
                },
                ..RuntimeOptions::default()
            })?;
            let snapshot = runtime_snapshot(&runtime);
            assert!(snapshot.shared_tls);
            assert_eq!(snapshot.verify_peer, verify_peer);
        }
    }
    Ok(())
}

const TRUST_RECORD_CHILD: &str = "ZAWS_TRUST_RECORD_CHILD";
const TRUST_RECORD_TEST: &str =
    "runtime::native::tests::unloadable_trust_files_record_their_setting_before_the_outcome";
const INVALID_OUTCOME: &str = " - awscli.native.request - DEBUG - Request outcome: HTTP 0, CRT 34 \
    (AWS_ERROR_INVALID_ARGUMENT): An invalid argument was passed to a function.";
const OUTCOME: &str = " - awscli.native.request - DEBUG - Request outcome: HTTP 0, CRT ";

fn trust_records(path: &std::path::Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let output = std::process::Command::new(std::env::current_exe()?)
        .args(["--exact", TRUST_RECORD_TEST, "--nocapture"])
        .env(TRUST_RECORD_CHILD, path)
        .output()?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).into());
    }
    Ok(String::from_utf8_lossy(&output.stderr)
        .lines()
        .filter(|line| {
            line.contains(" - awscli.native.tls - ") || line.contains(" - awscli.native.request - ")
        })
        .filter_map(|line| line.get(23..))
        .map(str::to_owned)
        .collect())
}

#[test]
fn unloadable_trust_files_record_their_setting_before_the_outcome()
-> Result<(), Box<dyn std::error::Error>> {
    if let Some(path) = std::env::var_os(TRUST_RECORD_CHILD) {
        let result = Runtime::new_with_logger(
            RuntimeOptions {
                endpoint_url: "https://localhost".into(),
                event_loop_count: 1,
                no_sign_request: true,
                trust: Trust::File {
                    path: path.into(),
                    setting: "--ca-bundle",
                },
                ..RuntimeOptions::default()
            },
            crate::debug::Logger::new(true),
        );
        return if result.is_err() {
            Ok(())
        } else {
            Err("the runtime trusted an unloadable file".into())
        };
    }
    let directory =
        std::env::temp_dir().join(format!("aws-cli-trust-record-{}", std::process::id()));
    std::fs::create_dir_all(&directory)?;
    let tls = |path: &std::path::Path| {
        format!(
            " - awscli.native.tls - DEBUG - CA bundle setting=--ca-bundle path={}",
            path.display()
        )
    };
    let not_pem = directory.join("not-pem.txt");
    std::fs::write(&not_pem, "this is not a PEM certificate\n")?;
    assert_eq!(
        trust_records(&not_pem)?,
        [tls(&not_pem), INVALID_OUTCOME.to_owned()]
    );
    let missing = directory.join("missing.pem");
    let records = trust_records(&missing)?;
    assert!(
        matches!(records.as_slice(), [setting, outcome]
            if *setting == tls(&missing) && outcome.starts_with(OUTCOME)),
        "{records:?}"
    );
    let bad_body = directory.join("bad-body.pem");
    std::fs::write(
        &bad_body,
        "-----BEGIN CERTIFICATE-----\nnot base64\n-----END CERTIFICATE-----\n",
    )?;
    let records = trust_records(&bad_body)?;
    assert!(
        matches!(records.as_slice(), [outcome] if outcome.starts_with(OUTCOME)),
        "{records:?}"
    );
    std::fs::remove_dir_all(&directory)?;
    Ok(())
}

#[test]
fn retry_attempt_extremes_and_default_client_options_reach_the_crt()
-> Result<(), Box<dyn std::error::Error>> {
    for attempts in [None, Some(2), Some(3), Some(64)] {
        let runtime = Runtime::new(RuntimeOptions {
            endpoint_url: "https://localhost".into(),
            event_loop_count: 1,
            no_sign_request: true,
            max_attempts: attempts,
            ..RuntimeOptions::default()
        })?;
        let actual = runtime_snapshot(&runtime);
        assert_eq!(actual.max_retries, attempts.map_or(0, |value| value - 1));
        assert_eq!(actual.throughput_gbps, 10.0);
        assert_eq!(
            (
                actual.memory_limit,
                actual.max_connections,
                actual.connect_timeout_ms
            ),
            (0, 0, 0)
        );
        assert_eq!((actual.part_size, actual.multipart_threshold), (0, 0));
        assert!(!actual.keep_alive && !actual.file_io);
    }
    Ok(())
}

struct CallbackAddress(*const ShutdownSignal);
// SAFETY: the waiting owner retains the Arc until the callback acquires its reference.
unsafe impl Send for CallbackAddress {}
impl CallbackAddress {
    fn complete(self) {
        // SAFETY: the address comes from a retained Arc with one promised callback.
        unsafe {
            on_shutdown(self.0.cast_mut().cast());
        }
    }
}

#[test]
fn shutdown_callback_retains_signal_after_waiter_releases_owner() {
    for _ in 0..64 {
        let signal = Arc::new(ShutdownSignal::new());
        let weak = Arc::downgrade(&signal);
        let address = CallbackAddress(Arc::as_ptr(&signal));
        let thread = std::thread::spawn(move || address.complete());
        signal.wait();
        drop(signal);
        assert!(thread.join().is_ok());
        assert!(weak.upgrade().is_none());
    }
}

#[cfg(target_os = "linux")]
#[test]
fn real_client_retains_custom_source_pool() -> Result<(), Box<dyn std::error::Error>> {
    use std::sync::atomic::Ordering;
    let budget = 128 * 1024 * 1024;
    for _ in 0..2 {
        let runtime = Runtime::new(RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9/bucket".into(),
            event_loop_count: 1,
            numa_source_pool_config: Some(crate::source_pool::Config::new(vec![0], budget)?),
            ..RuntimeOptions::default()
        })?;
        let factory = runtime
            .lifecycle
            .ops()
            .pool
            .as_ref()
            .ok_or("missing factory")?;
        let diagnostics = factory.diagnostics();
        assert_eq!(diagnostics.budget_bytes.load(Ordering::Acquire), budget);
        assert_eq!(diagnostics.node_snapshot(), [(0, 0)]);
        assert_eq!(diagnostics.reservations.load(Ordering::Acquire), 0);
        drop(runtime);
        assert_eq!(diagnostics.allocations.load(Ordering::Acquire), 0);
    }
    Ok(())
}

#[cfg(target_os = "linux")]
struct PoolOwner(NonNull<ffi::AwsS3BufferPool>);
#[cfg(target_os = "linux")]
impl Drop for PoolOwner {
    fn drop(&mut self) {
        // SAFETY: this owner transfers its sole pool reference through its own vtable.
        unsafe {
            if let Some(release) = (*(*self.0.as_ptr()).vtable).release {
                release(self.0.as_ptr());
            }
        }
    }
}
#[cfg(target_os = "linux")]
struct FutureOwner(NonNull<ffi::AwsFutureS3BufferTicket>);
#[cfg(target_os = "linux")]
impl Drop for FutureOwner {
    fn drop(&mut self) {
        // SAFETY: this owner releases exactly one live CRT future reference.
        unsafe {
            ffi::aws_future_s3_buffer_ticket_release(self.0.as_ptr());
        }
    }
}

#[cfg(target_os = "linux")]
#[test]
fn pool_vtable_uses_crt_future_ownership() -> Result<(), Box<dyn std::error::Error>> {
    let _library = Library::acquire();
    let mut config = crate::source_pool::FactoryConfig::new(crate::source_pool::Config::new(
        vec![0],
        8 * 1024 * 1024,
    )?);
    // SAFETY: default allocator is process-lifetime; configuration is live for construction.
    let pointer = unsafe {
        crate::source_pool::factory(
            ffi::rust_crt_allocator(),
            ffi::AwsS3BufferPoolConfig {
                client: std::ptr::null_mut(),
                part_size: 8 * 1024 * 1024,
                max_part_size: 8 * 1024 * 1024,
                memory_limit: 8 * 1024 * 1024,
            },
            (&raw mut config).cast(),
        )
    };
    let pool = PoolOwner(NonNull::new(pointer).ok_or("pool construction failed")?);
    // SAFETY: this pool owns a live immutable vtable until its owner is released.
    let reserve = unsafe { (*(*pool.0.as_ptr()).vtable).reserve }.ok_or("missing reserve")?;
    // SAFETY: zero size completes an error without mapping or memory binding.
    let pointer = unsafe {
        reserve(
            pool.0.as_ptr(),
            ffi::AwsS3BufferPoolReserveMeta {
                size: 0,
                can_block: false,
                local_offset: 0,
                client: std::ptr::null_mut(),
                meta_request: std::ptr::null_mut(),
            },
        )
    };
    let future = FutureOwner(NonNull::new(pointer).ok_or("missing future")?);
    // SAFETY: the owner retains future through queries and acquiring its second reference.
    unsafe {
        assert!(ffi::aws_future_s3_buffer_ticket_is_done(future.0.as_ptr()));
        assert_eq!(
            ffi::aws_future_s3_buffer_ticket_get_error(future.0.as_ptr()),
            ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
        );
        let extra = ffi::aws_future_s3_buffer_ticket_acquire(future.0.as_ptr());
        let extra = FutureOwner(NonNull::new(extra).ok_or("future acquire failed")?);
        assert_eq!(future.0, extra.0);
        ffi::aws_future_s3_buffer_ticket_set_error(extra.0.as_ptr(), ffi::AWS_ERROR_S3_CANCELED);
        drop(extra);
        assert_eq!(
            ffi::aws_future_s3_buffer_ticket_get_error(future.0.as_ptr()),
            ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
        );
    }
    drop(pool);
    drop(future);
    Ok(())
}

#[cfg(not(target_os = "linux"))]
#[test]
fn factory_refuses_every_pool_off_linux() {
    let _library = Library::acquire();
    // SAFETY: this operation only changes the CRT thread-local error.
    unsafe {
        ffi::aws_raise_error(ffi::AWS_ERROR_S3_CANCELED);
    }
    // SAFETY: the default allocator is process-lifetime, and off Linux the
    // factory refuses before it reads the absent configuration.
    let pool = unsafe {
        crate::source_pool::factory(
            ffi::rust_crt_allocator(),
            ffi::AwsS3BufferPoolConfig {
                client: std::ptr::null_mut(),
                part_size: 8 * 1024 * 1024,
                max_part_size: 8 * 1024 * 1024,
                memory_limit: 64 * 1024 * 1024,
            },
            std::ptr::null_mut(),
        )
    };
    assert!(pool.is_null());
    assert_eq!(
        crate::s3::error_name(crate::crt_error::last_raised()),
        b"AWS_ERROR_INVALID_ARGUMENT"
    );
}

#[test]
fn runtime_client_options_reach_the_header_checked_client_builder()
-> Result<(), Box<dyn std::error::Error>> {
    use crate::runtime::{ChecksumMode, FileIoOptions};
    for anonymous in [false, true] {
        let runtime = Runtime::new(RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9/bucket".into(),
            event_loop_count: 1,
            no_sign_request: anonymous,
            verify_peer: false,
            keep_alive: true,
            connect_timeout_ms: 17_000,
            max_attempts: Some(7),
            max_active_connections_override: 3,
            throughput_target_gbps: 25.0,
            memory_limit_in_bytes: 256 * 1024 * 1024,
            part_size: 8 * 1024 * 1024,
            multipart_upload_threshold: Some(12 * 1024 * 1024),
            file_io: Some(FileIoOptions {
                should_stream: true,
                disk_throughput_gbps: 20.0,
                direct_io: true,
            }),
            request_checksum_calculation: ChecksumMode::WhenSupported,
            response_checksum_validation: ChecksumMode::WhenSupported,
            ..RuntimeOptions::default()
        })?;
        let mut snapshot = c::RuntimeSnapshot::default();
        // SAFETY: the shim copies a layout-checked value from a live runtime.
        unsafe {
            c::zaws_runtime_snapshot(runtime.pointer(), &mut snapshot);
        }
        assert_client_transfer_settings(&snapshot);
        assert_eq!(snapshot.max_connections, 3);
        assert_eq!(snapshot.connect_timeout_ms, 17_000);
        assert_eq!(snapshot.max_retries, 6);
        assert_eq!(snapshot.anonymous, anonymous);
        assert_eq!(
            (
                snapshot.shared_tls,
                snapshot.verify_peer,
                snapshot.keep_alive
            ),
            (true, false, true),
        );
        assert_eq!(
            (snapshot.file_io, snapshot.stream, snapshot.direct),
            (true, true, true),
        );
        assert_eq!(
            (snapshot.request_checksum, snapshot.response_checksum),
            (true, true),
        );
    }
    Ok(())
}

fn assert_client_transfer_settings(snapshot: &c::RuntimeSnapshot) {
    assert_eq!(snapshot.part_size, 8 * 1024 * 1024);
    assert_eq!(snapshot.max_part_size, 0);
    assert_eq!(snapshot.multipart_threshold, 12 * 1024 * 1024);
    assert_eq!(snapshot.memory_limit, 256 * 1024 * 1024);
    assert_eq!(snapshot.throughput_gbps, 25.0);
    assert_eq!(snapshot.disk_gbps, 20.0);
}

fn credentials_snapshot(runtime: &Runtime) -> c::CredentialsSnapshot {
    let mut snapshot = c::CredentialsSnapshot::default();
    // SAFETY: the shim copies a layout-checked value from a live runtime.
    unsafe { c::zaws_credentials_snapshot(runtime.pointer(), &mut snapshot) };
    snapshot
}

#[test]
fn a_signed_runtime_asks_its_delegate() -> Result<(), Box<dyn std::error::Error>> {
    for (no_sign_request, delegate) in [(false, true), (true, false)] {
        let runtime = Runtime::new(RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9/base".into(),
            event_loop_count: 1,
            no_sign_request,
            ..RuntimeOptions::default()
        })?;
        assert_eq!(credentials_snapshot(&runtime).delegate, delegate);
    }
    Ok(())
}

#[test]
fn construction_failures_name_the_proxy_only_once_it_is_configured() {
    let failure = |options: RuntimeOptions| {
        Runtime::new(RuntimeOptions {
            proxy_url: Some("http://user:secret@127.0.0.1:9".into()),
            event_loop_count: 1,
            no_sign_request: true,
            ..options
        })
        .err()
        .map(|failure| failure.proxy_url.as_bytes().to_vec())
    };
    let tls = failure(RuntimeOptions {
        endpoint_url: "https://localhost".into(),
        trust: Trust::File {
            path: "does-not-exist-ca-bundle.pem".into(),
            setting: "--ca-bundle",
        },
        ..RuntimeOptions::default()
    });
    assert_eq!(tls, Some(Vec::new()));
    let scheme = failure(RuntimeOptions {
        endpoint_url: "ftp://localhost".into(),
        ..RuntimeOptions::default()
    });
    assert_eq!(scheme, Some(Vec::new()));
    let client = failure(RuntimeOptions {
        endpoint_url: "http://localhost".into(),
        memory_limit_in_bytes: 1024 * 1024,
        ..RuntimeOptions::default()
    });
    assert_eq!(client.as_deref(), Some(&b"http://***:***@127.0.0.1:9"[..]));
}

#[test]
fn each_trust_store_reaches_the_shim_as_one_source() -> Result<(), Box<dyn std::error::Error>> {
    let pem = b"-----BEGIN CERTIFICATE-----\n".to_vec();
    let file = Trust::File {
        path: "ca.pem".into(),
        setting: "--ca-bundle",
    };
    for trust in [Trust::Platform, Trust::Pem(pem.clone()), file] {
        let options = RuntimeOptions {
            trust: trust.clone(),
            ..RuntimeOptions::default()
        };
        let ops = NativeOps::new(&options, None)?;
        let bundle = ca_bundle(&options)?;
        let shim = ops.shim_options(&options, bundle.as_ref());
        // SAFETY: both pointers borrow `bundle` and `options`, live here.
        let sources = unsafe {
            (
                (!shim.ca_bundle.is_null())
                    .then(|| std::ffi::CStr::from_ptr(shim.ca_bundle).to_bytes().to_vec()),
                (shim.ca_pem.len != 0)
                    .then(|| std::slice::from_raw_parts(shim.ca_pem.ptr, shim.ca_pem.len).to_vec()),
            )
        };
        let expected = match trust {
            Trust::Platform => (None, None),
            Trust::Pem(_) => (None, Some(pem.clone())),
            Trust::File { .. } => (Some(b"ca.pem".to_vec()), None),
        };
        assert_eq!(sources, expected);
    }
    Ok(())
}

#[derive(Debug, Default)]
struct CountingLibraryOps {
    library_init: usize,
    library_clean_up: usize,
    sdkutils_init: usize,
    sdkutils_clean_up: usize,
}
impl LibraryOps for CountingLibraryOps {
    fn library_init(&mut self) {
        self.library_init += 1;
    }
    fn library_clean_up(&mut self) {
        self.library_clean_up += 1;
    }
    fn sdkutils_init(&mut self) {
        self.sdkutils_init += 1;
    }
    fn sdkutils_clean_up(&mut self) {
        self.sdkutils_clean_up += 1;
    }
}

#[test]
fn s3_library_cleanup_waits_for_the_final_reference() {
    let mut ops = CountingLibraryOps::default();
    let mut state = LibraryState::new();
    state.acquire_full(&mut ops);
    state.acquire_full(&mut ops);
    assert_eq!((state.full, ops.library_init), (2, 1));
    state.release_full(&mut ops);
    assert_eq!((state.full, ops.library_clean_up), (1, 0));
    state.release_full(&mut ops);
    assert_eq!((state.full, ops.library_clean_up), (0, 1));
    assert_eq!((ops.sdkutils_init, ops.sdkutils_clean_up), (0, 0));
}

#[test]
fn sdkutils_holders_share_the_s3_library_state() {
    for full_first in [false, true] {
        let mut ops = CountingLibraryOps::default();
        let mut state = LibraryState::new();
        state.acquire_full(&mut ops);
        state.acquire_sdkutils(&mut ops);
        assert_eq!((ops.library_init, ops.sdkutils_init), (1, 0));
        if full_first {
            state.release_full(&mut ops);
        } else {
            state.release_sdkutils(&mut ops);
        }
        assert_eq!((ops.library_clean_up, ops.sdkutils_clean_up), (0, 0));
        if full_first {
            state.release_sdkutils(&mut ops);
        } else {
            state.release_full(&mut ops);
        }
        assert_eq!((ops.library_clean_up, ops.sdkutils_clean_up), (1, 0));
    }
    let mut ops = CountingLibraryOps::default();
    let mut state = LibraryState::new();
    state.acquire_sdkutils(&mut ops);
    state.acquire_sdkutils(&mut ops);
    state.acquire_full(&mut ops);
    assert_eq!((ops.sdkutils_init, ops.library_init), (1, 1));
    state.release_sdkutils(&mut ops);
    state.release_full(&mut ops);
    assert_eq!((ops.library_clean_up, ops.sdkutils_clean_up), (0, 0));
    state.release_sdkutils(&mut ops);
    assert_eq!((ops.library_clean_up, ops.sdkutils_clean_up), (1, 1));
}

#[test]
fn connection_errors_exclude_timeouts_and_tls_failures() {
    for (code, name, connection) in [
        (
            ffi::AWS_IO_SOCKET_CONNECTION_REFUSED,
            "AWS_IO_SOCKET_CONNECTION_REFUSED",
            true,
        ),
        (
            ffi::AWS_IO_SOCKET_NO_ROUTE_TO_HOST,
            "AWS_IO_SOCKET_NO_ROUTE_TO_HOST",
            true,
        ),
        (
            ffi::AWS_IO_SOCKET_NETWORK_DOWN,
            "AWS_IO_SOCKET_NETWORK_DOWN",
            true,
        ),
        (
            ffi::AWS_IO_SOCKET_CONNECT_ABORTED,
            "AWS_IO_SOCKET_CONNECT_ABORTED",
            true,
        ),
        (
            ffi::AWS_IO_DNS_QUERY_FAILED,
            "AWS_IO_DNS_QUERY_FAILED",
            true,
        ),
        (
            ffi::AWS_IO_DNS_INVALID_NAME,
            "AWS_IO_DNS_INVALID_NAME",
            true,
        ),
        (
            ffi::AWS_IO_DNS_NO_ADDRESS_FOR_HOST,
            "AWS_IO_DNS_NO_ADDRESS_FOR_HOST",
            true,
        ),
        (ffi::AWS_IO_SOCKET_TIMEOUT, "AWS_IO_SOCKET_TIMEOUT", false),
        (
            ffi::AWS_IO_TLS_ERROR_NEGOTIATION_FAILURE,
            "AWS_IO_TLS_ERROR_NEGOTIATION_FAILURE",
            false,
        ),
        (
            crate::s3::NO_CREDENTIALS_ERROR_CODE,
            "AWS_AUTH_SIGNING_NO_CREDENTIALS",
            false,
        ),
        (
            crate::s3::FILE_INVALID_PATH_ERROR_CODE,
            "AWS_ERROR_FILE_INVALID_PATH",
            false,
        ),
        (
            crate::s3::CONNECTION_REFUSED_ERROR_CODE,
            "AWS_IO_SOCKET_CONNECTION_REFUSED",
            true,
        ),
    ] {
        assert_eq!(crate::s3::error_name(code), name.as_bytes());
        assert_eq!(crate::s3::is_connection_error(code), connection, "{name}");
    }
}

#[test]
fn memory_limits_match_the_linked_crt_at_every_tier_boundary() {
    let _library = Library::acquire();
    for gbps in [
        0.000_1, 0.5, 4.99, 5.0, 9.99, 10.0, 24.99, 25.0, 74.99, 75.0, 99.99, 100.0, 199.99, 200.0,
        400.0,
    ] {
        // SAFETY: a pure lookup for a positive target; the library is held.
        let crt = unsafe { c::aws_s3_default_memory_limit_for_throughput(gbps) };
        assert_eq!(
            cli_core::client_config::memory_limit_for_throughput(gbps),
            u64::try_from(crt).unwrap_or(u64::MAX),
            "{gbps}"
        );
    }
}
