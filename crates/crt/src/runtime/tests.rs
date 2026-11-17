use super::*;
use crate::signal::lock;
use std::sync::{Arc, Mutex};
#[test]
fn platform_information_keeps_only_positive_finite_estimates_and_the_recommended_flag() {
    for (estimate, optimized, expected) in [
        (0.0, false, None),
        (25.0, false, Some(25.0)),
        (400.0, true, Some(400.0)),
        (-1.0, true, None),
        (f64::NAN, false, None),
        (f64::INFINITY, true, None),
    ] {
        let actual = platform_from_info(estimate, optimized);
        assert_eq!(actual.recommended_gbps, expected);
        assert_eq!(actual.optimized, optimized);
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Event {
    LibraryInit,
    Start(Stage),
    Release(Stage),
    LibraryCleanup,
}
#[derive(Debug)]
struct FakeRuntimeLifecycle {
    events: Arc<Mutex<Vec<Event>>>,
    fail_at: Option<Stage>,
    options: Arc<Mutex<Vec<RuntimeOptions>>>,
}
impl RuntimeLifecycleOps for FakeRuntimeLifecycle {
    type Error = Stage;
    fn acquire_library(&mut self) {
        lock(&self.events).push(Event::LibraryInit);
    }
    fn release_library(&mut self) {
        lock(&self.events).push(Event::LibraryCleanup);
    }
    fn start(&mut self, stage: Stage, options: &RuntimeOptions) -> Result<(), Stage> {
        lock(&self.events).push(Event::Start(stage));
        lock(&self.options).push(options.clone());
        if self.fail_at == Some(stage) {
            Err(stage)
        } else {
            Ok(())
        }
    }
    fn release(&mut self, stage: Stage) {
        lock(&self.events).push(Event::Release(stage));
    }
}
#[test]
fn lifecycle_failures_release_every_completed_stage_in_reverse() {
    for (index, stage) in STAGES.into_iter().enumerate() {
        let events = Arc::new(Mutex::new(Vec::new()));
        let ops = FakeRuntimeLifecycle {
            events: events.clone(),
            fail_at: Some(stage),
            options: Arc::new(Mutex::new(Vec::new())),
        };
        assert!(Lifecycle::new(ops, &RuntimeOptions::default()).is_err());
        let mut expected = vec![Event::LibraryInit];
        expected.extend(STAGES[..=index].iter().map(|s| Event::Start(*s)));
        expected.extend(STAGES[..index].iter().rev().map(|s| Event::Release(*s)));
        expected.push(Event::LibraryCleanup);
        assert_eq!(*lock(&events), expected);
    }
}
#[test]
fn lifecycle_success_forwards_options_and_releases_once() -> Result<(), String> {
    let events = Arc::new(Mutex::new(Vec::new()));
    let recorded = Arc::new(Mutex::new(Vec::new()));
    let ops = FakeRuntimeLifecycle {
        events: events.clone(),
        fail_at: None,
        options: recorded.clone(),
    };
    let options = RuntimeOptions {
        region: "long-test-region".into(),
        signing_region: Some("resolved-signing-region".into()),
        endpoint_url: "http://localhost:4566/base".into(),
        event_loop_count: 4,
        throughput_target_gbps: 22.5,
        memory_limit_in_bytes: 8192,
        max_active_connections_override: 9,
        ..RuntimeOptions::default()
    };
    let mut lifecycle = Lifecycle::new(ops, &options).map_err(|e| format!("{e:?}"))?;
    assert!(lock(&recorded).iter().all(|value| value == &options));
    lifecycle.close();
    let count = lock(&events).len();
    lifecycle.close();
    assert_eq!(lock(&events).len(), count);
    assert_eq!(lock(&events).last(), Some(&Event::LibraryCleanup));
    Ok(())
}
#[test]
fn fips_signing_region_normalization() {
    for (input, expected) in [
        ("fips-us-east-1", "us-east-1"),
        ("us-east-1-fips", "us-east-1"),
        ("fips-us-gov-west-1", "us-gov-west-1"),
        ("eu-west-1", "eu-west-1"),
    ] {
        let mut options = RuntimeOptions {
            region: input.into(),
            ..RuntimeOptions::default()
        };
        assert_eq!(effective_signing_region(&options), expected);
        options.signing_region = Some("resolved-signing-region".into());
        assert_eq!(
            effective_signing_region(&options),
            "resolved-signing-region"
        );
    }
}
#[test]
fn runtime_invalid_ca_preserves_error_before_cleanup() {
    let result = Runtime::new(RuntimeOptions {
        endpoint_url: "https://localhost".into(),
        event_loop_count: 1,
        trust: Trust::File {
            path: "test/does-not-exist-ca-bundle.pem".into(),
            setting: "",
        },
        ..RuntimeOptions::default()
    });
    assert!(result.is_err());
    if let Err(failure) = result {
        assert_ne!(failure.error_code, 0);
        assert!(!failure.crt_name.is_empty());
        assert_ne!(failure.crt_message.as_bytes(), b"Unknown Error Code");
    }
}
#[test]
fn runtime_two_live_references_and_endpoint_tls_schemes() -> Result<(), Box<dyn std::error::Error>>
{
    for scheme in ["http", "https"] {
        let first = Runtime::new(RuntimeOptions {
            endpoint_url: format!("{scheme}://127.0.0.1:9/base"),
            event_loop_count: 1,
            ..RuntimeOptions::default()
        })?;
        let second = Runtime::new(RuntimeOptions {
            endpoint_url: format!("{scheme}://127.0.0.1:9/base"),
            event_loop_count: 1,
            ..RuntimeOptions::default()
        })?;
        drop(first);
        assert_eq!(second.options().region, "us-east-1");
        // SAFETY: the second runtime retains the library reference and error
        // tables; this lookup deliberately bypasses the guard-creating helper.
        let registered = unsafe {
            std::ffi::CStr::from_ptr(crt_sys::rust_crt_error_name(crt_sys::AWS_ERROR_S3_CANCELED))
        };
        assert_eq!(registered.to_bytes(), b"AWS_ERROR_S3_CANCELED");
        drop(second);
    }
    Ok(())
}
#[test]
fn default_trust_always_builds_a_shared_tls_context() -> Result<(), Box<dyn std::error::Error>> {
    for verify_peer in [true, false] {
        let runtime = Runtime::new(RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9".into(),
            event_loop_count: 1,
            verify_peer,
            ..RuntimeOptions::default()
        })?;
        // SAFETY: the accessor reads the live C-owned runtime synchronously.
        assert!(unsafe { crt_sys::native::zaws_runtime_has_custom_tls(runtime.pointer()) });
    }
    Ok(())
}
