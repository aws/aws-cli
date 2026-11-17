use super::*;
use pyload::format::{flags, testing};

#[test]
fn missing_or_invalid_payload_has_no_bundle_and_present_bundle_is_borrowed()
-> Result<(), Box<dyn std::error::Error>> {
    let without = testing::blob(
        &[
            testing::entry(b"awscli/data/cli.json", b"{}", flags::RESOURCE),
            testing::entry(b"botocore/data/endpoints.json", b"{}", flags::RESOURCE),
        ],
        false,
        2,
    );
    assert!(pyload::View::new(&without).is_ok());
    assert_eq!(find(&without), None);
    assert_eq!(find(b""), None);
    let pem = b"-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n";
    let with = testing::blob(
        &[
            testing::entry(b"awscli/data/cli.json", b"{}", flags::RESOURCE),
            testing::entry(ENTRY_NAME, pem, flags::RESOURCE),
        ],
        false,
        2,
    );
    let found = find(&with).ok_or("fixture bundle was not found")?;
    assert_eq!(found, pem);
    assert!(found.as_ptr() >= with.as_ptr());
    assert!((found.as_ptr() as usize) < with.as_ptr() as usize + with.len());
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn payload_cli_bundle_is_raw_complete_and_borrowed() -> Result<(), Box<dyn std::error::Error>> {
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX")
        .ok_or("AWS_NATIVE_FALLBACK_PREFIX must name the declared payload")?;
    let payload = std::fs::read(std::path::PathBuf::from(prefix).join("awscli-v2.blob"))?;
    let view = pyload::View::new(&payload)?;
    let packs_cli = view.find(b"awscli/data/cli.json")?.is_some();
    let Some(pem) = find(&payload) else {
        assert!(!packs_cli);
        return Ok(());
    };
    assert!(packs_cli);
    let marker = b"-----BEGIN CERTIFICATE-----";
    assert!(
        pem.windows(marker.len())
            .filter(|part| *part == marker)
            .count()
            > 100
    );
    assert!(pem.ends_with(b"\n"));
    assert!(pem.trim_ascii_end().ends_with(b"-----END CERTIFICATE-----"));
    assert_eq!(Some(pem.as_ptr()), find(&payload).map(<[u8]>::as_ptr));
    let runtime = crt::Runtime::new(crt::RuntimeOptions {
        endpoint_url: "https://localhost".into(),
        no_sign_request: true,
        event_loop_count: 1,
        trust: crt::runtime::Trust::Pem(pem.to_vec()),
        ..Default::default()
    })?;
    drop(runtime);
    Ok(())
}

#[cfg(debug_assertions)]
#[test]
#[should_panic(expected = "the packer stores the CA bundle uncompressed")]
fn compressed_bundle_breaks_the_packer_invariant() {
    let pem = b"compressed bytes";
    let compressed = testing::TestEntry {
        raw_len: 4 * pem.len() as u32,
        flags: (flags::RESOURCE | flags::COMPRESSED) as u16,
        ..testing::entry(ENTRY_NAME, pem, flags::RESOURCE)
    };
    let payload = testing::blob(&[compressed], false, 2);
    let _ = find(&payload);
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn only_an_embedded_trust_takes_the_payload_bundle() {
    use cli_core::client_config::{ClientConfig, Command, Resolved, Source, Trust};
    let pem = b"-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n";
    let with = testing::blob(
        &[testing::entry(ENTRY_NAME, pem, flags::RESOURCE)],
        false,
        2,
    );
    let without = testing::blob(&[testing::entry(b"a", b"{}", flags::RESOURCE)], false, 2);
    assert!(super::super::embeds_trust_bundle(&with));
    assert!(!super::super::embeds_trust_bundle(&without));
    let file = crt::runtime::Trust::File {
        path: "ca.pem".into(),
        setting: "AWS_CA_BUNDLE",
    };
    let env = std::collections::BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = cli_core::command::Globals::default();
    for (trust, source, payload, expected) in [
        (
            Trust::Platform,
            Source::Default,
            &with,
            crt::runtime::Trust::Platform,
        ),
        (
            Trust::Embedded,
            Source::Default,
            &with,
            crt::runtime::Trust::Pem(pem.to_vec()),
        ),
        (
            Trust::Embedded,
            Source::Default,
            &without,
            crt::runtime::Trust::Platform,
        ),
        (
            Trust::File("ca.pem".into()),
            Source::Env("AWS_CA_BUNDLE"),
            &with,
            file,
        ),
    ] {
        let client = ClientConfig {
            trust: Resolved::new(trust, source),
            ..ClientConfig::new(Command::Ls)
        };
        let context = cli_core::command::CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            client: &client,
            directory: std::path::Path::new("/"),
            payload,
        };
        let mut options = super::super::client_options(&client, false);
        super::super::embedded_ca(&context, &mut options);
        assert_eq!(options.trust, expected, "{:?}", client.trust);
    }
}
