use super::*;
use awscli_config::{Contents, Inputs};
use cli_core::SnapshotEnv;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::time::{Duration, UNIX_EPOCH};

pub(crate) type TestResult = Result<(), Box<dyn std::error::Error>>;

/// A clock that a test moves, in whole seconds since the epoch.
#[derive(Clone, Debug)]
pub(crate) struct Time(Arc<AtomicU64>);

impl Time {
    pub(crate) fn new(seconds: u64) -> Self {
        Self(Arc::new(AtomicU64::new(seconds)))
    }
    /// A clock that starts at the instant an ISO 8601 `text` names.
    pub(crate) fn at(text: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let since_epoch = expiry::parse("test", text)?.duration_since(UNIX_EPOCH)?;
        Ok(Self::new(since_epoch.as_secs()))
    }
    pub(crate) fn advance(&self, seconds: u64) {
        self.0.fetch_add(seconds, Ordering::SeqCst);
    }
    pub(crate) fn clock(&self) -> Clock {
        let seconds = Arc::clone(&self.0);
        Clock::new(move || UNIX_EPOCH + Duration::from_secs(seconds.load(Ordering::SeqCst)))
    }
}

/// An environment that a test replaces whole, stage by stage, as a process
/// that changed its own variables would.
#[derive(Clone, Debug)]
pub(crate) struct Staged {
    stages: Arc<Vec<SnapshotEnv>>,
    stage: Arc<AtomicUsize>,
}

impl Staged {
    pub(crate) fn new(stages: &[&[(&str, &str)]]) -> Self {
        Self {
            stages: Arc::new(stages.iter().map(|pairs| env(pairs)).collect()),
            stage: Arc::default(),
        }
    }
    /// Moves on to the next stage's variables.
    pub(crate) fn step(&self) {
        self.stage.fetch_add(1, Ordering::SeqCst);
    }
}

impl EnvMap for Staged {
    fn var(&self, name: &str) -> Option<&str> {
        self.stages
            .get(self.stage.load(Ordering::SeqCst))?
            .var(name)
    }
}

pub(crate) fn env(pairs: &[(&str, &str)]) -> SnapshotEnv {
    SnapshotEnv::from_pairs(pairs.iter().copied())
}

pub(crate) fn files(config: &str, credentials: &str) -> ParsedFiles {
    ParsedFiles::parse(Inputs {
        config: Some(Contents {
            bytes: config.as_bytes(),
            source: "/home/.aws/config",
        }),
        credentials: Some(Contents {
            bytes: credentials.as_bytes(),
            source: "/home/.aws/credentials",
        }),
        aliases: None,
    })
}

/// An instance metadata service that has no credentials.
fn no_role() -> RoleFetcher {
    RoleFetcher::new(|| Ok(None))
}

/// A stand-in for the container's endpoint, which no test of the chain
/// alone sets.
pub(crate) fn no_container<'a>() -> ContainerFetch<'a> {
    ContainerFetch::new(|_| Ok(None))
}

/// What the default chain finds, as the credentials a request would be
/// signed with.
fn resolve(
    env: &SnapshotEnv,
    files: &ParsedFiles,
    profile: Profile<'_>,
) -> Result<Option<Credentials>, LoadError> {
    let loaded =
        default_resolver(env, files, profile, no_container(), no_role()).load_credentials()?;
    Ok(loaded.and_then(|loaded| loaded.outside_advisory()))
}

/// The error of a test whose chain must find credentials and finds none.
const MISSING: &str = "the chain found no credentials";

const BOTH_FILES: (&str, &str) = (
    "[default]\naws_access_key_id = AKIDCONFIG\naws_secret_access_key = config-secret\n\
     [profile dev]\naws_access_key_id = AKIDDEV\naws_secret_access_key = dev-secret\n",
    "[default]\naws_access_key_id = AKIDSHARED\naws_secret_access_key = shared-secret\n\
     aws_session_token = shared-token\n",
);

#[test]
fn the_chain_asks_the_environment_then_the_credentials_file_then_the_config_file() -> TestResult {
    let parsed = files(BOTH_FILES.0, BOTH_FILES.1);
    let full = env(&[
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ]);
    let ambient = Profile::Ambient("default");
    assert_eq!(
        default_resolver(&full, &parsed, ambient, no_container(), no_role())
            .methods()
            .collect::<Vec<_>>(),
        [
            "env",
            "shared-credentials-file",
            "custom-process",
            "config-file",
            "container-role",
            "iam-role"
        ]
    );
    let found = resolve(&full, &parsed, ambient)?.ok_or(MISSING)?;
    assert_eq!((found.method(), found.access_key_id()), ("env", "AKIDENV"));
    let found = resolve(&env(&[]), &parsed, ambient)?.ok_or(MISSING)?;
    assert_eq!(found.method(), "shared-credentials-file");
    assert_eq!(found.access_key_id(), "AKIDSHARED");
    assert_eq!(found.session_token(), Some("shared-token"));
    let found = resolve(&env(&[]), &files(BOTH_FILES.0, ""), ambient)?.ok_or(MISSING)?;
    assert_eq!(
        (found.method(), found.access_key_id()),
        ("config-file", "AKIDCONFIG")
    );
    assert_eq!(resolve(&env(&[]), &files("", ""), ambient)?, None);
    Ok(())
}

#[test]
fn an_explicit_profile_drops_the_environment_provider() -> TestResult {
    let parsed = files(BOTH_FILES.0, BOTH_FILES.1);
    let full = env(&[
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ]);
    let found = resolve(&full, &parsed, Profile::Explicit("dev"))?.ok_or(MISSING)?;
    assert_eq!(
        (found.method(), found.access_key_id()),
        ("config-file", "AKIDDEV")
    );
    // A profile the environment selects leaves the environment's keys first.
    let found = resolve(&full, &parsed, Profile::Ambient("dev"))?.ok_or(MISSING)?;
    assert_eq!(found.method(), "env");
    Ok(())
}

/// The CRT's chain goes on to the profile when the environment has half a
/// key pair; botocore stops.
#[test]
fn a_partial_key_pair_stops_the_chain() {
    let parsed = files(BOTH_FILES.0, BOTH_FILES.1);
    let partial = env(&[("AWS_ACCESS_KEY_ID", "AKIDENV")]);
    let error = resolve(&partial, &parsed, Profile::Ambient("default"));
    assert_eq!(
        error.as_ref().map_err(ToString::to_string),
        Err("Partial credentials found in env, missing: AWS_SECRET_ACCESS_KEY".to_owned())
    );
}

/// The CRT merges the two files before it reads a profile, so this pair
/// works there; botocore's providers each read one file.
#[test]
fn a_key_pair_split_across_the_two_files_is_partial() {
    let parsed = files(
        "[default]\naws_secret_access_key = config-secret\n",
        "[default]\naws_access_key_id = AKIDSHARED\n",
    );
    assert_eq!(
        resolve(&env(&[]), &parsed, Profile::Ambient("default")),
        Err(LoadError::PartialCredentials {
            provider: "shared-credentials-file",
            cred_var: "aws_secret_access_key",
        })
    );
}

#[test]
fn the_legacy_token_names_win_over_the_standard_ones() -> TestResult {
    let tokens = env(&[
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
        ("AWS_SESSION_TOKEN", "standard"),
        ("AWS_SECURITY_TOKEN", "legacy"),
        ("AWS_ACCOUNT_ID", "123456789012"),
    ]);
    let found = resolve(&tokens, &files("", ""), Profile::Ambient("default"))?.ok_or(MISSING)?;
    assert_eq!(found.session_token(), Some("legacy"));
    assert_eq!(found.account_id(), Some("123456789012"));
    let parsed = files(
        "",
        "[default]\naws_access_key_id = AKID\naws_secret_access_key = secret\n\
         aws_session_token = standard\naws_security_token = legacy\n",
    );
    let found = resolve(&env(&[]), &parsed, Profile::Ambient("default"))?.ok_or(MISSING)?;
    assert_eq!(found.session_token(), Some("legacy"));
    Ok(())
}

/// botocore signs with a token only when Python counts it as true, so an
/// empty one is no token. The environment skips an empty variable for the
/// next name (`EnvProvider`); a profile stops at the first name it has
/// (`SharedCredentialProvider._get_session_token`).
#[test]
fn an_empty_token_is_no_token() -> TestResult {
    let keys = [
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ];
    let none = files("", "");
    for (legacy, standard, token) in [("", "", None), ("", "standard", Some("standard"))] {
        let tokens = env(&[
            keys[0],
            keys[1],
            ("AWS_SECURITY_TOKEN", legacy),
            ("AWS_SESSION_TOKEN", standard),
        ]);
        let found = resolve(&tokens, &none, Profile::Ambient("default"))?.ok_or(MISSING)?;
        assert_eq!(found.session_token(), token);
    }
    let profile = "[default]\naws_access_key_id = AKID\naws_secret_access_key = secret\n";
    for tokens in [
        "aws_session_token =\n",
        "aws_security_token =\naws_session_token = standard\n",
    ] {
        for parsed in [
            files("", &format!("{profile}{tokens}")),
            files(&format!("{profile}{tokens}"), ""),
        ] {
            let found = resolve(&env(&[]), &parsed, Profile::Ambient("default"))?.ok_or(MISSING)?;
            assert_eq!(found.session_token(), None, "{tokens}");
        }
    }
    let empty = Credentials::new("test", "AKID", "secret").with_session_token(Some(String::new()));
    assert_eq!(empty, Credentials::new("test", "AKID", "secret"));
    Ok(())
}

#[test]
fn a_file_that_does_not_parse_is_an_error() {
    let parsed = files("not a section\n", "");
    assert_eq!(
        resolve(&env(&[]), &parsed, Profile::Ambient("default")),
        Err(LoadError::ConfigParse {
            path: "/home/.aws/config".into()
        })
    );
}

#[test]
fn debug_output_never_shows_the_secret_or_the_token() {
    let credentials = Credentials::new("env", "AKIDENV", "env-secret")
        .with_session_token(Some("env-token".into()));
    let debug = format!("{credentials:?}");
    assert!(debug.contains("AKIDENV"));
    assert!(!debug.contains("env-secret") && !debug.contains("env-token"));
}

/// A provider that counts how often the chain asks it.
#[derive(Debug)]
struct Counted<P> {
    provider: P,
    loads: Arc<AtomicUsize>,
}

impl<P: Provider> Provider for Counted<P> {
    fn method(&self) -> &'static str {
        self.provider.method()
    }
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        self.loads.fetch_add(1, Ordering::SeqCst);
        self.provider.load()
    }
}

/// The default chain's four providers, each counted, with a credential
/// process that `runner` stands in for.
fn counted_chain<'a>(
    env: &'a Staged,
    files: &'a ParsedFiles,
    runner: Runner,
) -> (Resolver<'a>, [Arc<AtomicUsize>; 4]) {
    let loads: [Arc<AtomicUsize>; 4] = Default::default();
    let [first, second, third, fourth] = loads.clone();
    let resolver = Resolver::new(vec![
        Box::new(Counted {
            provider: EnvProvider::new(env),
            loads: first,
        }),
        Box::new(Counted {
            provider: SharedCredentialsProvider::new(files, "default"),
            loads: second,
        }),
        Box::new(Counted {
            provider: ProcessProvider::new_with_runner(files, "default", runner),
            loads: third,
        }),
        Box::new(Counted {
            provider: ConfigProvider::new(files, "default"),
            loads: fourth,
        }),
    ]);
    (resolver, loads)
}

/// The chain is walked once. When the credentials it found come due, only
/// the provider that found them is asked again, even though by then a
/// provider earlier in the chain has credentials of its own.
#[test]
fn a_refresh_asks_only_the_provider_that_resolved() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let runs = Arc::new(AtomicUsize::new(0));
    let runner = {
        let runs = Arc::clone(&runs);
        Runner::new(move |_| {
            let run = runs.fetch_add(1, Ordering::SeqCst);
            let stdout = format!(
                r#"{{"Version": 1, "AccessKeyId": "AKIDRUN{run}", "SecretAccessKey": "s",
                    "Expiration": "2037-10-21T{:02}:00:00Z"}}"#,
                8 + run
            );
            Ok(ProcessOutput {
                success: true,
                stdout: stdout.into_bytes(),
                stderr: Vec::new(),
            })
        })
    };
    // The config file's own keys come after the process in the chain.
    let parsed = files(
        "[default]\ncredential_process = fetch-credentials\n\
         aws_access_key_id = AKIDCONFIG\naws_secret_access_key = config-secret\n",
        "",
    );
    let staged = Staged::new(&[
        &[],
        &[
            ("AWS_ACCESS_KEY_ID", "AKIDENV"),
            ("AWS_SECRET_ACCESS_KEY", "env-secret"),
        ],
    ]);
    let (resolver, loads) = counted_chain(&staged, &parsed, runner);
    let counts = || loads.each_ref().map(|count| count.load(Ordering::SeqCst));
    let loaded = resolver.load_credentials()?.ok_or(MISSING)?;
    let loaded = loaded.with_clock(time.clock());
    drop(resolver);
    assert_eq!(counts(), [1, 1, 1, 0]);
    assert_eq!(loaded.method(), "custom-process");
    assert_eq!(loaded.frozen()?.access_key_id(), "AKIDRUN0");
    assert_eq!(runs.load(Ordering::SeqCst), 1);

    // Five minutes before the expiry, with keys now in the environment.
    staged.step();
    time.advance(55 * 60);
    let refreshed = loaded.frozen()?;
    assert_eq!(refreshed.access_key_id(), "AKIDRUN1");
    assert_eq!(refreshed.method(), "custom-process");
    assert_eq!(runs.load(Ordering::SeqCst), 2);
    assert_eq!(counts(), [1, 1, 1, 0]);
    Ok(())
}

/// The chain keeps a copy of the variables its providers read, and of no
/// others.
#[test]
fn the_environment_copy_holds_the_chains_variables_alone() {
    let copy = environment(&env(&[
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECURITY_TOKEN", ""),
        (
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "http://127.0.0.1:1/creds",
        ),
        ("AWS_EC2_METADATA_DISABLED", "true"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://127.0.0.1:1"),
        ("AWS_METADATA_SERVICE_TIMEOUT", "2"),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "3"),
        ("AWS_PROFILE", "work"),
        ("HOME", "/home/someone"),
    ]));
    assert_eq!(
        copy.names(),
        [
            "AWS_ACCESS_KEY_ID",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "AWS_EC2_METADATA_DISABLED",
            "AWS_EC2_METADATA_SERVICE_ENDPOINT",
            "AWS_METADATA_SERVICE_NUM_ATTEMPTS",
            "AWS_METADATA_SERVICE_TIMEOUT",
            "AWS_SECURITY_TOKEN",
        ]
    );
    assert_eq!(copy.var("AWS_ACCESS_KEY_ID"), Some("AKIDENV"));
    assert_eq!(variables().count(), 17);
}

#[test]
fn only_a_zoned_iso_8601_expiry_is_read() {
    // The forms themselves are the expiry module's to test.
    for (expiry, read) in [
        ("2037-10-21T07:28:00Z", true),
        ("2037-10-21T07:28:00.25-0530", true),
        ("2037-10-21T07:28:00", false),
        ("2037-10-21 07:28:00Z", true),
        ("2037-10-21T07:28:00 UTC", false),
        ("Oct 21 2037", false),
        ("", false),
    ] {
        assert_eq!(reads_expiry(expiry), read, "{expiry:?}");
    }
}
