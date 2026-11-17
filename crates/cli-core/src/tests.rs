#![expect(
    clippy::unwrap_used,
    reason = "test assertions require expected successful results"
)]
mod endpoint;
mod output;
mod proxy;
mod region;
mod shared;
use super::*;
use awscli_config::{Contents, Inputs, ParsedFiles};
fn parsed(config: &str, credentials: Option<&str>) -> ParsedFiles {
    ParsedFiles::parse(Inputs {
        config: Some(Contents {
            bytes: config.as_bytes(),
            source: "config",
        }),
        credentials: credentials.map(|text| Contents {
            bytes: text.as_bytes(),
            source: "credentials",
        }),
        aliases: None,
    })
}
fn env(pairs: &[(&str, &str)]) -> SnapshotEnv {
    SnapshotEnv::from_pairs(pairs.iter().copied())
}
