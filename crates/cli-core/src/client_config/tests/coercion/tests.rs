use super::*;

#[test]
fn transfer_pipeline_converts_all_supplied_keys_and_routes_invalid_stages_to_python()
-> Result<(), PythonReason> {
    let config = resolved(
        concat!(
            "[default]\ns3 =\n  preferred_transfer_client = crt\n",
            "  multipart_threshold = 64MB\n  multipart_chunksize = 16MiB\n",
            "  max_concurrent_requests = 20\n  max_queue_size = 1_000\n",
            "  max_bandwidth = 50MB/s\n  target_bandwidth = 100Gb/s\n",
            "  io_chunksize = 1MB\n  should_stream = no\n",
            "  disk_throughput = 1GB/s\n  direct_io = no\n"
        ),
        &[],
        Command::Cp,
    )?;
    assert_transfer_pipeline_values(&config);
    assert_transfer_pipeline_io(&config);
    for entries in [
        "io_chunksize = 8M\n  target_bandwidth = fast",
        "multipart_chunksize = 0\n  max_bandwidth = fast",
        "preferred_transfer_client = bogus\n  max_queue_size = 0",
        "max_concurrent_requests = ten",
        "target_bandwidth = 1b/s",
        "preferred_transfer_client = Crt",
        "direct_io = maybe\n  max_queue_size = -5",
    ] {
        assert_eq!(
            resolved(&format!("[default]\ns3 =\n  {entries}\n"), &[], Command::Cp),
            Err(PythonReason::TransferSetting)
        );
    }
    let crt = resolved(
        "[default]\ns3 =\n  preferred_transfer_client = crt\n",
        &[],
        Command::Cp,
    )?;
    assert_unset_transfer_pipeline(&crt);
    Ok(())
}
#[test]
fn integer_literals_follow_python_and_reject_unmodeled_unicode() {
    for (text, value) in [
        ("0", 0),
        (" 42 ", 42),
        ("+7", 7),
        ("-7", -7),
        ("1_000", 1000),
        ("\t10\n", 10),
        ("007", 7),
        ("9223372036854775807", i64::MAX),
    ] {
        assert_eq!(coerce::integer(text), Some(value));
    }
    for invalid in [
        "",
        " ",
        "1.5",
        "1e3",
        "_1",
        "1_",
        "1__0",
        "0x10",
        "+",
        "ten",
        "9223372036854775808",
        "١",
        "5\u{1c}",
        "\u{3000}5",
    ] {
        assert_eq!(coerce::integer(invalid), None, "{invalid:?}");
    }
    let fits = format!("{}7", " ".repeat(awscli_argparse::ARG_LEN_MAX - 1));
    assert_eq!(coerce::integer(&fits), Some(7));
    for len in [
        awscli_argparse::ARG_LEN_MAX + 1,
        awscli_argparse::unpack::PARAMFILE_BYTES_MAX + 2,
    ] {
        assert_eq!(coerce::integer(&"0".repeat(len)), None, "{len}");
        assert_eq!(coerce::size(&format!("{}MB", "0".repeat(len))), None);
        assert_eq!(coerce::rate(&format!("{}MB/s", "0".repeat(len))), None);
    }
}
#[test]
fn integers_over_cpythons_digit_limit_are_left_to_python() {
    let at_limit = format!("{}5", "0".repeat(4299));
    assert_eq!(coerce::integer(&at_limit), Some(5));
    let decorated = format!(" -{}5\t", "0_".repeat(4299));
    assert_eq!(coerce::integer(&decorated), Some(-5));
    assert_eq!(coerce::size(&format!("{at_limit}KB")), Some(5 << 10));
    assert_eq!(coerce::rate(&format!("{at_limit}B/s")), Some(5));
    let over = format!("0{at_limit}");
    for text in [over.clone(), format!("+{over}"), format!("0_{at_limit}")] {
        assert_eq!(coerce::integer(&text), None, "{}", text.len());
    }
    assert_eq!(coerce::size(&format!("{over}MiB")), None);
    assert_eq!(coerce::rate(&format!("{over}B/s")), None);
    assert_eq!(coerce::rate(&format!("{over}Mb/s")), None);
}
#[test]
fn sizes_and_rates_use_binary_suffixes_and_case_sensitive_rate_units() {
    for (text, expected) in [
        ("8MB", 8 << 20),
        ("8mib", 8 << 20),
        ("3KiB", 3 << 10),
        ("1TB", 1_i64 << 40),
        (" 2 mb", 2 << 20),
        ("+1_024", 1024),
    ] {
        assert_eq!(coerce::size(text), Some(expected), "{text}");
    }
    for (text, expected) in [
        ("8Mb/s", 1 << 20),
        ("8MB/s", 8 << 20),
        ("16b/s", 2),
        ("7b/s", 0),
        ("125MB/s", 125 << 20),
        ("100", 100),
    ] {
        assert_eq!(coerce::rate(text), Some(expected), "{text}");
    }
    for text in ["8M", "8.5MB", "1PB", "8MB ", "2e3"] {
        assert_eq!(coerce::size(text), None);
    }
    for text in ["8mb/S", "1.5MB/s", "10/s", "fast", "8M/s"] {
        assert_eq!(coerce::rate(text), None);
    }
}
#[test]
fn booleans_are_exact_case_insensitive_true_and_positive_checks_reject_zero() {
    for text in ["true", "TRUE", "True"] {
        assert!(coerce::boolean(text));
    }
    for text in ["1", "yes", "false", " true ", "", "tRuE\n"] {
        assert!(!coerce::boolean(text));
    }
    assert_eq!(coerce::positive(Some(1)), Ok(1));
    for value in [None, Some(0), Some(-1)] {
        assert_eq!(coerce::positive(value), Err(PythonReason::TransferSetting));
    }
}
#[test]
fn sizes_accept_binary_suffixes_in_any_case() {
    for (text, expected) in [
        ("1024", 1024),
        (" 1024 ", 1024),
        ("8MB", 8 << 20),
        ("8mb", 8 << 20),
        ("8Mb", 8 << 20),
        ("1KB", 1 << 10),
        ("2GB", 2 << 30),
        ("1TB", 1_i64 << 40),
        ("8MiB", 8 << 20),
        ("8mib", 8 << 20),
        ("3KiB", 3 << 10),
        ("1GiB", 1 << 30),
        ("1TiB", 1_i64 << 40),
        (" 8 MB", 8 << 20),
        ("8 MiB", 8 << 20),
        ("-8MB", -(8 << 20)),
        ("1_0KB", 10 << 10),
        ("0", 0),
    ] {
        assert_eq!(coerce::size(text), Some(expected), "{text:?}");
    }
}
#[test]
fn sizes_reject_what_upstream_rejects_or_only_python_models() {
    for text in [
        "",
        "b",
        "ib",
        "8M",
        "8B",
        "8K",
        "8PB",
        "8 mb ",
        "abc",
        "MB",
        "kib",
        "8.5MB",
        "x8MB",
        "8_MB",
        "9000000TB",
        "8\u{212A}B",
    ] {
        assert_eq!(coerce::size(text), None, "{text:?}");
    }
}
#[test]
fn rates_follow_the_case_sensitive_byte_and_bit_suffixes() {
    for (text, expected) in [
        ("10485760", 10_485_760),
        (" 5 ", 5),
        ("1024B/s", 1024),
        ("10MB/s", 10 << 20),
        ("800KB/s", 800 << 10),
        ("10MiB/s", 10 << 20),
        ("10mB/s", 10 << 20),
        ("1GB/s", 1 << 30),
        ("10 MB/s", 10 << 20),
        ("10Mb/s", (10 << 20) / 8),
        ("10mb/s", (10 << 20) / 8),
        ("800Kb/s", (800 << 10) / 8),
        ("100Gb/s", (100_i64 << 30) / 8),
        ("8b/s", 1),
        ("15b/s", 1),
        ("1b/s", 0),
        ("-9b/s", -1),
        ("0", 0),
    ] {
        assert_eq!(coerce::rate(text), Some(expected), "{text:?}");
    }
}
#[test]
fn rates_reject_what_upstream_rejects_or_only_python_models() {
    for text in [
        "",
        "5/s",
        "10MB/S",
        "10MB",
        "fast",
        "10 Mbps",
        "5kb",
        "B/s",
        "10PB/s",
        "1.5MB/s",
        "MB/s",
        "99999999999TB/s",
    ] {
        assert_eq!(coerce::rate(text), None, "{text:?}");
    }
}
#[test]
fn ensure_boolean_accepts_only_true_in_any_case_and_positive_checks_i64_extremes() {
    for text in ["true", "True", "TRUE", "tRuE"] {
        assert!(coerce::boolean(text), "{text:?}");
    }
    for text in ["", "false", "1", "yes", "on", " true", "truee"] {
        assert!(!coerce::boolean(text), "{text:?}");
    }
    assert_eq!(
        coerce::positive(Some(i64::MAX)),
        Ok(i64::MAX.unsigned_abs())
    );
    assert_eq!(
        coerce::positive(Some(i64::MIN)),
        Err(PythonReason::TransferSetting)
    );
}
#[test]
fn transfer_client_choice_is_exact_after_the_default_alias() {
    use coerce::TransferClient;
    assert_eq!(coerce::transfer_client_alias("default"), "classic");
    assert_eq!(coerce::transfer_client_alias("Default"), "Default");
    for (text, client) in [
        ("auto", TransferClient::Auto),
        ("classic", TransferClient::Classic),
        ("crt", TransferClient::Crt),
    ] {
        assert_eq!(coerce::transfer_client(text), Some(client));
    }
    assert_eq!(
        coerce::transfer_client(coerce::transfer_client_alias("default")),
        Some(TransferClient::Classic)
    );
    for text in ["", "Auto", "CRT", "default", " crt", "s3transfer"] {
        assert_eq!(coerce::transfer_client(text), None, "{text:?}");
    }
}
#[test]
fn transfer_client_choice_reaches_the_persona_or_python() -> Result<(), PythonReason> {
    for (text, persona) in [
        ("auto", Persona::NewlyEligible),
        ("crt", Persona::CrtPreferred),
    ] {
        let block = format!("[default]\ns3 =\n  preferred_transfer_client = {text}\n");
        assert_eq!(
            resolved(&block, &[], Command::Cp)?.persona,
            Some(Resolved::new(
                persona,
                Source::S3("preferred_transfer_client")
            ))
        );
    }
    for text in [
        "default",
        "classic",
        "Auto",
        "CRT",
        "Default",
        "s3transfer",
        "\"crt\"",
    ] {
        let block = format!("[default]\ns3 =\n  preferred_transfer_client = {text}\n");
        assert_eq!(
            resolved(&block, &[], Command::Cp),
            Err(PythonReason::TransferSetting),
            "{text:?}"
        );
    }
    Ok(())
}
#[test]
fn transfer_pipeline_converts_every_key_and_leaves_unset_keys_none() -> Result<(), coerce::Stage> {
    let result = coerce::transfer(&coerce::TransferInputs {
        multipart_threshold: Some("64MB"),
        multipart_chunksize: Some("16MiB"),
        max_concurrent_requests: Some("20"),
        max_queue_size: Some("1_000"),
        max_bandwidth: Some("50MB/s"),
        preferred_transfer_client: Some("default"),
        target_bandwidth: Some("100Gb/s"),
        io_chunksize: Some("1MB"),
        should_stream: Some("TRUE"),
        disk_throughput: Some("1GB/s"),
        direct_io: Some("no"),
    })?;
    assert_eq!(
        result,
        coerce::Transfer {
            multipart_threshold: Some(64 << 20),
            multipart_chunksize: Some(16 << 20),
            max_concurrent_requests: Some(20),
            max_queue_size: Some(1000),
            max_bandwidth: Some(50 << 20),
            preferred_transfer_client: coerce::TransferClient::Classic,
            target_bandwidth: Some((100 << 30) / 8),
            io_chunksize: Some(1 << 20),
            should_stream: Some(true),
            disk_throughput: Some(1 << 30),
            direct_io: Some(false),
        }
    );
    let empty = coerce::transfer(&coerce::TransferInputs::default())?;
    assert_eq!(empty, coerce::Transfer::default());
    assert_eq!(
        empty.preferred_transfer_client,
        coerce::TransferClient::Auto
    );
    assert_eq!(counted_fields(&empty), [None; 8]);
    Ok(())
}
#[test]
fn transfer_pipeline_reports_the_first_failing_stage_in_upstreams_order() {
    use coerce::Stage;
    let block = |entries: &[(&str, &'static str)]| {
        let entries = entries.to_vec();
        coerce::TransferInputs::read(move |key| {
            entries
                .iter()
                .find(|(name, _)| *name == key)
                .map(|(_, value)| *value)
        })
    };
    for (entries, stage) in [
        (
            &[("io_chunksize", "8M"), ("target_bandwidth", "fast")][..],
            Stage::Size,
        ),
        (
            &[("multipart_chunksize", "0"), ("max_bandwidth", "fast")],
            Stage::Rate,
        ),
        (
            &[
                ("preferred_transfer_client", "bogus"),
                ("max_queue_size", "0"),
            ],
            Stage::Positive,
        ),
        (&[("max_concurrent_requests", "ten")], Stage::Positive),
        (&[("target_bandwidth", "1b/s")], Stage::Positive),
        (&[("preferred_transfer_client", "Crt")], Stage::Choice),
        (
            &[("direct_io", "maybe"), ("max_queue_size", "-5")],
            Stage::Positive,
        ),
    ] {
        assert_eq!(coerce::transfer(&block(entries)), Err(stage), "{entries:?}");
        assert_eq!(PythonReason::from(stage), PythonReason::TransferSetting);
    }
}
#[test]
fn transfer_key_lists_reach_their_stages_and_fields() {
    use coerce::{Stage, TransferInputs};
    let mut asked = Vec::new();
    let _ = TransferInputs::read(|key| {
        asked.push(key);
        None
    });
    assert_eq!(asked, coerce::TRANSFER_KEYS);
    let only = |key: &str, value: &'static str| {
        coerce::transfer(&TransferInputs::read(|name| (name == key).then_some(value)))
    };
    for (keys, failing, stage) in [
        (&coerce::SIZE_KEYS[..], "8M", Stage::Size),
        (&coerce::RATE_KEYS, "fast", Stage::Rate),
        (&coerce::POSITIVE_KEYS, "0", Stage::Positive),
    ] {
        for key in keys {
            assert_eq!(only(key, failing), Err(stage), "{key}");
        }
    }
    let mut positions: Vec<usize> = coerce::POSITIVE_KEYS
        .iter()
        .filter_map(|key| single_counted_field(only(key, "7"), 7))
        .collect();
    positions.sort_unstable();
    assert_eq!(positions, (0..8).collect::<Vec<_>>());
    for key in coerce::BOOLEAN_KEYS {
        let result = only(key, "TRUE");
        let flags = result.map(|result| [result.should_stream, result.direct_io]);
        assert_eq!(flags.map(|f| f.iter().flatten().count()), Ok(1), "{key}");
    }
}
fn single_counted_field(
    result: Result<coerce::Transfer, coerce::Stage>,
    value: u64,
) -> Option<usize> {
    let fields = counted_fields(&result.ok()?);
    let mut set = (0..fields.len()).filter(|index| fields[*index].is_some());
    let first = set.next()?;
    (set.next().is_none() && fields[first] == Some(value)).then_some(first)
}
fn counted_fields(result: &coerce::Transfer) -> [Option<u64>; 8] {
    [
        result.multipart_threshold,
        result.multipart_chunksize,
        result.max_concurrent_requests,
        result.max_queue_size,
        result.max_bandwidth,
        result.target_bandwidth,
        result.io_chunksize,
        result.disk_throughput,
    ]
}
#[test]
fn memory_tiers_match_the_current_crt_graph() {
    for (throughput, bytes) in [
        (0.1, 256 << 20),
        (4.999, 256 << 20),
        (5.0, 512 << 20),
        (9.999, 512 << 20),
        (10.0, 2 << 30),
        (24.999, 2 << 30),
        (25.0, 4 << 30),
        (74.999, 4 << 30),
        (75.0, 8 << 30),
        (100.0, 16 << 30),
        (200.0, 24 << 30),
    ] {
        assert_eq!(
            memory_limit_for_throughput(throughput),
            bytes,
            "{throughput}"
        );
    }
}
#[test]
fn nested_blocks_and_scalar_s3_keep_their_distinct_fallback_reasons() {
    for (key, reason) in [
        ("max_attempts", PythonReason::RetrySetting),
        ("retry_mode", PythonReason::RetrySetting),
        ("tcp_keepalive", PythonReason::NetworkSetting),
        ("ca_bundle", PythonReason::NetworkSetting),
        (
            "request_checksum_calculation",
            PythonReason::TransferSetting,
        ),
        (
            "response_checksum_validation",
            PythonReason::TransferSetting,
        ),
        ("sdk_ua_app_id", PythonReason::UserAgentSetting),
    ] {
        for command in [Command::Ls, Command::Cp] {
            assert_eq!(
                resolved(
                    &format!("[default]\n{key} =\n  key = value\n"),
                    &[],
                    command
                ),
                Err(reason)
            );
        }
    }
    for value in ["", "true", "auto"] {
        assert_eq!(
            resolved(&format!("[default]\ns3 = {value}\n"), &[], Command::Ls),
            Err(PythonReason::EndpointSetting)
        );
    }
}

fn assert_transfer_pipeline_values(config: &ClientConfig) {
    assert_eq!(
        config.multipart_threshold.as_ref().map(|v| v.value),
        Some(64 << 20)
    );
    assert_eq!(config.part_size.value, 16 << 20);
    assert_eq!(config.max_connections.as_ref().map(|v| v.value), Some(20));
    assert_eq!(
        config.target_gbps.value,
        coerce::bytes_to_gbps((100 << 30) / 8)
    );
}

fn assert_transfer_pipeline_io(config: &ClientConfig) {
    assert_eq!(
        config.disk_throughput_gbps.as_ref().map(|v| v.value),
        Some(coerce::bytes_to_gbps(1 << 30))
    );
    assert_eq!(config.should_stream.as_ref().map(|v| v.value), Some(false));
    assert_eq!(config.direct_io.as_ref().map(|v| v.value), Some(false));
    assert!(config.ignored.max_queue_size);
    assert!(config.ignored.io_chunksize);
    assert!(config.ignored.max_bandwidth);
}

fn assert_unset_transfer_pipeline(crt: &ClientConfig) {
    assert_eq!(crt.part_size.value, 0);
    assert!(crt.multipart_threshold.is_none());
    assert!(crt.max_connections.is_none());
    assert!(crt.should_stream.is_none());
    assert!(crt.disk_throughput_gbps.is_none());
    assert!(crt.direct_io.is_none());
}
