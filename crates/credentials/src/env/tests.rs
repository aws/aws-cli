use super::*;
use crate::tests::{Staged, TestResult, Time, env};
use crate::{RefreshError, Refreshable};

const KEYS: [(&str, &str); 2] = [
    ("AWS_ACCESS_KEY_ID", "AKIDENV"),
    ("AWS_SECRET_ACCESS_KEY", "env-secret"),
];
const EXPIRES_AT_EIGHT: (&str, &str) = ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21T08:00:00Z");

/// The provider's credentials, which must be refreshable, on `time`.
fn refreshable(
    environment: &(impl EnvMap + Clone + Send + Sync + 'static),
    time: &Time,
) -> Result<Refreshable, Box<dyn std::error::Error>> {
    match EnvProvider::new(environment).load()? {
        Some(Loaded::Refreshable(found)) => Ok(found.with_clock(time.clock())),
        other => Err(format!("expected refreshable credentials, found {other:?}").into()),
    }
}

#[test]
fn keys_without_an_expiry_are_static() -> TestResult {
    let found = EnvProvider::new(&env(&KEYS)).load()?;
    assert!(matches!(found, Some(Loaded::Static(_))), "{found:?}");
    Ok(())
}

#[test]
fn an_expiry_makes_the_keys_refreshable_from_the_same_variables() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let staged = Staged::new(&[
        &[KEYS[0], KEYS[1], EXPIRES_AT_EIGHT],
        &[
            ("AWS_ACCESS_KEY_ID", "AKIDLATER"),
            ("AWS_SECRET_ACCESS_KEY", "later-secret"),
            ("AWS_SESSION_TOKEN", "later-token"),
            ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21T09:00:00Z"),
        ],
    ]);
    let found = refreshable(&staged, &time)?;
    assert_eq!(found.method(), "env");
    assert_eq!(found.frozen()?.access_key_id(), "AKIDENV");
    staged.step();
    // Still outside the advisory window: the new variables are not read.
    assert_eq!(found.frozen()?.access_key_id(), "AKIDENV");
    time.advance(55 * 60);
    let refreshed = found.frozen()?;
    assert_eq!(refreshed.access_key_id(), "AKIDLATER");
    assert_eq!(refreshed.session_token(), Some("later-token"));
    Ok(())
}

/// The first load takes keys without an expiry; a refresh does not
/// (`EnvProvider`'s `fetch_credentials`).
#[test]
fn a_refresh_requires_the_expiry_the_first_load_does_not() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let staged = Staged::new(&[&[KEYS[0], KEYS[1], EXPIRES_AT_EIGHT], &KEYS]);
    let found = refreshable(&staged, &time)?;
    staged.step();
    // An advisory refresh forgives the provider's error.
    time.advance(46 * 60);
    assert_eq!(found.frozen()?.access_key_id(), "AKIDENV");
    // A mandatory refresh reports it.
    time.advance(5 * 60);
    assert_eq!(
        found.frozen().map_err(|error| error.to_string()),
        Err("Partial credentials found in env, missing: AWS_CREDENTIAL_EXPIRATION".into())
    );
    Ok(())
}

/// A snapshot holds what the process started with, so its refresh finds
/// the expiry it already had.
#[test]
fn a_snapshots_refresh_fails_once_its_expiry_has_passed() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let found = refreshable(&env(&[KEYS[0], KEYS[1], EXPIRES_AT_EIGHT]), &time)?;
    // Inside the mandatory window but not expired: the same keys again.
    time.advance(59 * 60);
    assert_eq!(found.frozen()?.access_key_id(), "AKIDENV");
    time.advance(60 + 1);
    assert_eq!(found.frozen(), Err(RefreshError::StillExpired));
    Ok(())
}

#[test]
fn an_expiry_without_a_zone_is_an_error() {
    let unzoned = env(&[
        KEYS[0],
        KEYS[1],
        ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21T08:00:00"),
    ]);
    assert_eq!(
        EnvProvider::new(&unzoned).load().map(|_| ()),
        Err(LoadError::Expiry {
            provider: "env",
            value: "2037-10-21T08:00:00".into()
        })
    );
}
