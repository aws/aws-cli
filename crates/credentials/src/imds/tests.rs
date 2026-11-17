use super::*;
use crate::tests::{TestResult, Time, env, files, no_container};
use crate::{Profile, RefreshError, default_resolver, expiry};
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};

/// What the stand-in service returns the `turn`th time it is asked: a key,
/// secret and token of that turn, which expire `turn` hours after eight.
fn role(turn: usize) -> Result<RoleCredentials, LoadError> {
    Ok(RoleCredentials {
        access_key: format!("AKIDROLE{turn}"),
        secret_key: format!("role-secret-{turn}"),
        token: format!("role-token-{turn}"),
        expiry: expiry::parse("test", &format!("2037-10-21T{:02}:00:00Z", 8 + turn))?,
    })
}

/// A stand-in service that gives `answers` in order and then nothing, and
/// how often it was asked.
fn service(answers: Vec<Option<RoleCredentials>>) -> (RoleFetcher, Arc<AtomicUsize>) {
    let asked = Arc::new(AtomicUsize::new(0));
    let count = Arc::clone(&asked);
    let answers = Mutex::new(answers.into_iter());
    let fetcher = RoleFetcher::new(move || {
        count.fetch_add(1, Ordering::SeqCst);
        let mut answers = answers
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        Ok(answers.next().flatten())
    });
    (fetcher, asked)
}

const KEYS: [(&str, &str); 2] = [
    ("AWS_ACCESS_KEY_ID", "AKIDENV"),
    ("AWS_SECRET_ACCESS_KEY", "env-secret"),
];
const SHARED: &str = "[default]\naws_access_key_id = AKIDSHARED\n\
    aws_secret_access_key = shared-secret\n";

#[test]
fn the_chain_asks_the_service_last_and_only_when_every_other_provider_passed() -> TestResult {
    let ambient = Profile::Ambient("default");
    for (variables, credentials, method, asks) in [
        (&KEYS[..], SHARED, "env", 0),
        (&[], SHARED, "shared-credentials-file", 0),
        (&[], "", "iam-role", 1),
    ] {
        let (fetcher, asked) = service(vec![Some(role(0)?)]);
        let (variables, parsed) = (env(variables), files("", credentials));
        let resolver = default_resolver(&variables, &parsed, ambient, no_container(), fetcher);
        assert_eq!(resolver.methods().last(), Some("iam-role"));
        let found = resolver.load_credentials()?.ok_or("no credentials")?;
        assert_eq!(
            (found.method(), asked.load(Ordering::SeqCst)),
            (method, asks)
        );
    }
    Ok(())
}

#[test]
fn the_roles_credentials_are_refreshable_and_carry_the_services_expiry() -> TestResult {
    let (fetcher, _) = service(vec![Some(role(0)?)]);
    let found = InstanceMetadataProvider::new(&env(&[]), fetcher).load()?;
    let Some(Loaded::Refreshable(found)) = found else {
        return Err(format!("expected refreshable credentials, found {found:?}").into());
    };
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let found = found.with_clock(time.clock()).frozen()?;
    assert_eq!(found.method(), "iam-role");
    assert_eq!(found.access_key_id(), "AKIDROLE0");
    assert_eq!(found.secret_access_key(), "role-secret-0");
    assert_eq!(found.session_token(), Some("role-token-0"));
    assert_eq!(found.expiry(), Some(role(0)?.expiry));
    Ok(())
}

/// botocore's `load` returns `None` for the fetcher's empty answer, and
/// its chain then raises `NoCredentialsError`.
#[test]
fn a_service_without_credentials_passes_and_the_chain_finds_nothing() -> TestResult {
    let (fetcher, asked) = service(vec![None]);
    let (variables, parsed) = (env(&[]), files("", ""));
    let resolver = default_resolver(
        &variables,
        &parsed,
        Profile::Explicit("dev"),
        no_container(),
        fetcher,
    );
    assert!(resolver.load_credentials()?.is_none());
    assert_eq!(asked.load(Ordering::SeqCst), 1);
    Ok(())
}

/// Only `true` disables the service, in any case (`IMDSFetcher.__init__`).
/// The CRT's own chain skips its provider for every value but `false`.
#[test]
fn the_disabled_switch_skips_the_service_without_asking_it() -> TestResult {
    for (value, asks) in [
        ("true", 0),
        ("TRUE", 0),
        ("True", 0),
        ("false", 1),
        ("1", 1),
        ("", 1),
    ] {
        let (fetcher, asked) = service(vec![Some(role(0)?)]);
        let variables = env(&[("AWS_EC2_METADATA_DISABLED", value)]);
        let found = InstanceMetadataProvider::new(&variables, fetcher).load()?;
        assert_eq!(
            (found.is_some(), asked.load(Ordering::SeqCst)),
            (asks == 1, asks),
            "{value:?}"
        );
    }
    Ok(())
}

/// The provider's credentials on `time`, over a service that gives
/// `answers` in order.
fn loaded(
    answers: Vec<Option<RoleCredentials>>,
    time: &Time,
) -> Result<(Loaded, Arc<AtomicUsize>), Box<dyn std::error::Error>> {
    let (fetcher, asked) = service(answers);
    let found = InstanceMetadataProvider::new(&env(&[]), fetcher)
        .load()?
        .ok_or("the service gave no credentials")?;
    Ok((found.with_clock(time.clock()), asked))
}

/// The clock starts with an hour left. Sixteen minutes left is outside
/// both windows, fourteen is the advisory window, and five on the second
/// set is the mandatory one.
#[test]
fn a_refresh_asks_the_service_again_inside_the_windows_only() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let (found, asked) = loaded(vec![Some(role(0)?), Some(role(1)?), Some(role(2)?)], &time)?;
    let mut signed = Vec::new();
    for minutes in [0, 44, 2, 69] {
        time.advance(minutes * 60);
        let current = found.frozen()?;
        signed.push((
            current.access_key_id().to_owned(),
            current.session_token().map(str::to_owned),
            asked.load(Ordering::SeqCst),
        ));
    }
    let turn = |turn: usize, asked: usize| {
        let token = Some(format!("role-token-{turn}"));
        (format!("AKIDROLE{turn}"), token, asked)
    };
    assert_eq!(signed, [turn(0, 1), turn(0, 1), turn(1, 2), turn(2, 3)]);
    Ok(())
}

/// botocore's fetcher returns its empty answer for a service that fails,
/// and `_set_from_data` raises for it after the refresh callable has
/// returned, so the advisory window does not forgive it as it would a
/// provider that raised.
#[test]
fn a_refresh_the_service_does_not_answer_fails_in_the_advisory_window_too() -> TestResult {
    let time = Time::at("2037-10-21T07:46:00Z")?;
    let (found, asked) = loaded(vec![Some(role(0)?)], &time)?;
    let error = found.frozen().err().ok_or("the refresh succeeded")?;
    assert_eq!(
        error,
        RefreshError::Metadata(LoadError::EmptyRefresh {
            provider: "iam-role"
        })
    );
    assert_eq!(
        error.to_string(),
        "Error when retrieving credentials from iam-role: Credential refresh failed, \
         response did not contain: access_key, secret_key, token, expiry_time"
    );
    assert_eq!(asked.load(Ordering::SeqCst), 2);
    // The credentials it had stay in place for a caller that need not
    // refresh.
    assert_eq!(
        found
            .outside_mandatory()
            .map(|current| current.access_key_id().to_owned()),
        Some("AKIDROLE0".into())
    );
    Ok(())
}

#[test]
fn debug_output_never_shows_the_secret_or_the_token() -> TestResult {
    let debug = format!("{:?}", role(0)?);
    assert!(debug.contains("AKIDROLE0"), "{debug}");
    assert!(!debug.contains("role-secret-0") && !debug.contains("role-token-0"));
    Ok(())
}

/// What the fetcher raises stops the chain where it loads, and inside a
/// refresh it is the provider's own failure, which the advisory window
/// forgives and the mandatory one raises
/// (`RefreshableCredentials._protected_refresh`).
#[test]
fn what_the_fetcher_raises_stops_the_chain_and_fails_a_mandatory_refresh() -> TestResult {
    let raised = || LoadError::MetadataRetrieval {
        error_msg: "no token".into(),
    };
    let failing = RoleFetcher::new(move || Err(raised()));
    let (variables, parsed) = (env(&[]), files("", ""));
    let resolver = default_resolver(
        &variables,
        &parsed,
        Profile::Ambient("default"),
        no_container(),
        failing,
    );
    assert_eq!(resolver.load_credentials().err(), Some(raised()));

    let asked = Arc::new(AtomicUsize::new(0));
    let count = Arc::clone(&asked);
    let first = role(0)?;
    let fetcher = RoleFetcher::new(move || match count.fetch_add(1, Ordering::SeqCst) {
        0 => Ok(Some(first.clone())),
        _ => Err(raised()),
    });
    // Fourteen minutes are left: the advisory window.
    let time = Time::at("2037-10-21T07:46:00Z")?;
    let found = InstanceMetadataProvider::new(&variables, fetcher)
        .load()?
        .ok_or("the service gave no credentials")?
        .with_clock(time.clock());
    assert_eq!(found.frozen()?.access_key_id(), "AKIDROLE0");
    assert_eq!(asked.load(Ordering::SeqCst), 2);
    // Five minutes are left: the mandatory window.
    time.advance(9 * 60);
    assert_eq!(found.frozen().err(), Some(RefreshError::Provider(raised())));
    Ok(())
}

/// A walk that asks the service is the walk `CredentialSource::select`
/// names no earlier provider for: `cli_core` decides the service's proxy
/// from that answer, before the chain is walked.
#[test]
#[cfg_attr(miri, ignore = "tries to start a process, which Miri cannot do")]
fn the_service_is_asked_exactly_when_no_earlier_provider_is_selected() {
    use cli_core::command::CredentialSource;
    let key = "aws_access_key_id = AKIDFILE\n";
    let secret = "aws_secret_access_key = file-secret\n";
    let process = "credential_process = /nonexistent/credential-helper\n";
    let sections = ["", key, secret, process];
    let variables: [&[(&str, &str)]; 4] = [
        &[],
        &[("AWS_ACCESS_KEY_ID", "AKIDENV")],
        &[("AWS_ACCESS_KEY_ID", "")],
        &[("AWS_SECRET_ACCESS_KEY", "env-secret")],
    ];
    for (config, credentials) in sections.iter().flat_map(|c| sections.map(|s| (*c, s))) {
        let parsed = files(
            &format!("[default]\n{config}[profile work]\n{config}"),
            &format!("[default]\n{credentials}[work]\n{credentials}"),
        );
        for (pairs, cli_profile) in variables
            .iter()
            .flat_map(|v| [(*v, None), (*v, Some("work"))])
        {
            let environment = env(pairs);
            let profile = match cli_profile {
                Some(name) => Profile::Explicit(name),
                None => Profile::Ambient("default"),
            };
            let (fetcher, asked) = service(vec![]);
            // A provider that fails stops the walk short of the service too.
            let _ = default_resolver(&environment, &parsed, profile, no_container(), fetcher)
                .load_credentials();
            let predicted = CredentialSource::select(&environment, &parsed, cli_profile);
            assert_eq!(
                asked.load(Ordering::SeqCst) == 1,
                predicted == CredentialSource::DefaultChain,
                "{pairs:?} {cli_profile:?} config {config:?} credentials {credentials:?}"
            );
        }
    }
}
