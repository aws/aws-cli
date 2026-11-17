use super::*;
#[test]
fn model_service_name_accepts_one_service_and_version_segment() {
    assert_eq!(
        service_resource(b"awscli/botocore/data/lambda/2015-03-31/service-2.json"),
        Some((b"lambda".as_slice(), ResourceKind::ServiceModel))
    );
}
#[test]
fn model_service_name_rejects_unrelated_and_nested_resources() {
    for name in [
        b"awscli/__init__.py".as_slice(),
        b"awscli/botocore/data/lambda/2015-03-31/paginators-1.json",
        b"awscli/botocore/data/lambda/nested/version/service-2.json",
    ] {
        assert_eq!(service_resource(name), None);
    }
}
#[test]
fn service_names_use_lowercase_model_directory_characters() {
    assert!(valid_service_name(b"bedrock-runtime"));
    assert!(!valid_service_name(b"BedrockRuntime"));
    assert!(!valid_service_name(b"../lambda"));
}
#[test]
fn modes_require_the_expected_argument_counts() {
    let cases: &[(&[&str], Option<Mode>)] = &[
        (&["inspect", "aws"], Some(Mode::Summary)),
        (&["inspect", "aws", "--list"], Some(Mode::List)),
        (
            &["inspect", "aws", "--expect-model-only", "s3", "ec2"],
            Some(Mode::ExpectModelOnly),
        ),
        (&["inspect", "aws", "--expect-model-only"], None),
        (&["inspect", "aws", "--list", "s3"], None),
        (&["inspect", "aws", "--unknown"], None),
    ];
    for (args, expected) in cases {
        assert_eq!(
            run_mode(&args.iter().map(|s| (*s).into()).collect::<Vec<_>>()),
            *expected
        );
    }
}
#[test]
fn sha256_standard_vectors_and_padding_boundary() {
    for (bytes, expected) in [
        (
            b"".as_slice(),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ),
        (
            b"abc",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
        ),
    ] {
        let actual: String = sha256::digest(bytes)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        assert_eq!(actual, expected);
    }
}

#[test]
fn model_only_payload_requires_exact_resources_for_each_service() -> Result<(), crate::Error> {
    use crate::format::{
        flags,
        testing::{blob, entry},
    };
    let fixtures = [
        entry(
            b"awscli/botocore/data/partitions.json",
            b"{}",
            flags::RESOURCE,
        ),
        entry(
            b"awscli/botocore/data/s3/2006-03-01/service-2.json",
            b"{}",
            flags::RESOURCE,
        ),
        entry(
            b"awscli/botocore/data/s3/2006-03-01/endpoint-rule-set-1.json",
            b"{}",
            flags::RESOURCE,
        ),
    ];
    let bytes = blob(&fixtures, false, 2);
    let payload = crate::parse(&bytes)?;
    assert_eq!(expect_model_only(&payload, &["s3".into()]), Ok(()));
    assert!(expect_model_only(&payload, &["ec2".into()]).is_err());
    assert!(expect_model_only(&payload, &["s3".into(), "s3".into()]).is_err());
    assert!(expect_model_only(&payload, &["S3".into()]).is_err());
    for omitted in 0..3 {
        let entries: Vec<_> = fixtures
            .iter()
            .enumerate()
            .filter_map(|(i, e)| (i != omitted).then_some(*e))
            .collect();
        let bytes = blob(&entries, false, 2);
        assert!(expect_model_only(&crate::parse(&bytes)?, &["s3".into()]).is_err());
    }
    Ok(())
}

#[test]
fn model_only_errors_name_the_entry_or_service() -> Result<(), crate::Error> {
    use crate::format::{
        flags,
        testing::{blob, entry},
    };
    let partitions = entry(
        b"awscli/botocore/data/partitions.json",
        b"{}",
        flags::RESOURCE,
    );
    let model = entry(
        b"awscli/botocore/data/s3/2006-03-01/service-2.json",
        b"{}",
        flags::RESOURCE,
    );
    let bytes = blob(&[partitions, model], false, 2);
    let payload = crate::parse(&bytes)?;
    for (services, message) in [
        (
            ["ec2"].as_slice(),
            "error: model payload contains unconfigured service: s3\n",
        ),
        (
            &["s3"],
            "error: model payload is missing endpoint resources for service: s3\n",
        ),
        (&["S3"], "error: invalid expected service name: S3\n"),
        (&["s3", "s3"], "error: duplicate expected service: s3\n"),
    ] {
        let services: Vec<_> = services.iter().map(|s| (*s).into()).collect();
        assert_eq!(
            expect_model_only(&payload, &services),
            Err(message.as_bytes().to_vec())
        );
    }
    let bytes = blob(&[model], false, 2);
    assert_eq!(
        expect_model_only(&crate::parse(&bytes)?, &["s3".into()]),
        Err(b"error: model payload is missing endpoint resources for service: s3\n".to_vec())
    );
    Ok(())
}

#[test]
fn model_only_errors_copy_raw_entry_and_service_name_bytes() -> Result<(), crate::Error> {
    use crate::format::{
        flags,
        testing::{entry, minimal},
    };
    let bytes = minimal(b"awscli/\xff", b"\0", flags::BYTECODE);
    assert_eq!(
        expect_model_only(&crate::parse(&bytes)?, &["s3".into()]),
        Err(b"error: model payload contains non-resource entry: awscli/\xff\n".to_vec())
    );
    let bytes = crate::format::testing::blob(
        &[entry(b"awscli/\xfe.json", b"{}", flags::RESOURCE)],
        false,
        2,
    );
    assert_eq!(
        expect_model_only(&crate::parse(&bytes)?, &["s3".into()]),
        Err(b"error: unexpected model payload entry: awscli/\xfe.json\n".to_vec())
    );
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStringExt;
        let service = OsString::from_vec(b"s\xff3".to_vec());
        assert_eq!(
            expect_model_only(&crate::parse(&bytes)?, &[service]),
            Err(b"error: invalid expected service name: s\xff3\n".to_vec())
        );
    }
    Ok(())
}

#[test]
#[cfg(unix)]
fn modes_compare_raw_argument_bytes() {
    use std::os::unix::ffi::OsStringExt;
    let args = |flag: &[u8]| {
        vec![
            OsString::from("inspect"),
            OsString::from("aws"),
            OsString::from_vec(flag.to_vec()),
        ]
    };
    assert_eq!(run_mode(&args(b"--list")), Some(Mode::List));
    assert_eq!(run_mode(&args(b"--list\xff")), None);
}

#[test]
#[cfg(target_os = "linux")]
fn open_errors_name_each_openat_errno() {
    use errno::*;
    for (code, name) in [
        (ENOENT, "FileNotFound"),
        (ESRCH, "FileNotFound"),
        (EACCES, "AccessDenied"),
        (EPERM, "PermissionDenied"),
        (ENOTDIR, "NotDir"),
        (EISDIR, "IsDir"),
        (ENAMETOOLONG, "NameTooLong"),
        (ELOOP, "SymLinkLoop"),
        (ENOMEM, "SystemResources"),
        (EMFILE, "ProcessFdQuotaExceeded"),
        (ENFILE, "SystemFdQuotaExceeded"),
        (EINVAL, "BadPathName"),
        (EILSEQ, "BadPathName"),
        (EFBIG, "FileTooBig"),
        (EOVERFLOW, "FileTooBig"),
        (ENODEV, "NoDevice"),
        (ENXIO, "NoDevice"),
        (ENOSPC, "NoSpaceLeft"),
        (EEXIST, "PathAlreadyExists"),
        (EBUSY, "DeviceBusy"),
        (EOPNOTSUPP, "FileLocksUnsupported"),
        (EAGAIN, "WouldBlock"),
        (ETXTBSY, "FileBusy"),
        (EROFS, "ReadOnlyFileSystem"),
        (EIO, "Unexpected"),
        (EBADF, "Unexpected"),
    ] {
        let error = io::Error::from_raw_os_error(code);
        assert_eq!(open_error_name(&error), name, "errno {code}");
    }
}

#[test]
#[cfg(target_os = "linux")]
fn read_errors_name_each_pread_errno() {
    use errno::*;
    for (code, name) in [
        (EIO, "InputOutput"),
        (EISDIR, "IsDir"),
        (ENXIO, "Unseekable"),
        (ESPIPE, "Unseekable"),
        (EOVERFLOW, "Unseekable"),
        (ENOBUFS, "SystemResources"),
        (ENOMEM, "SystemResources"),
        (EAGAIN, "WouldBlock"),
        (EBADF, "NotOpenForReading"),
        (EACCES, "Unexpected"),
        (ENOENT, "Unexpected"),
    ] {
        let error = io::Error::from_raw_os_error(code);
        assert_eq!(read_error_name(&error), name, "errno {code}");
    }
}

#[test]
fn reader_errors_without_an_errno_are_named_by_their_kind() {
    for (kind, name) in [
        (io::ErrorKind::UnexpectedEof, "UnexpectedEndOfFile"),
        (io::ErrorKind::OutOfMemory, "OutOfMemory"),
        (io::ErrorKind::Other, "Unexpected"),
    ] {
        let error = io::Error::from(kind);
        assert_eq!(open_error_name(&error), name);
        assert_eq!(read_error_name(&error), name);
    }
}

#[test]
fn summary_ratios_round_shortest_digits_half_up() {
    for (value, expected) in [
        (0.5625, "0.563"),
        (0.0625, "0.063"),
        (1.0005, "1.001"),
        (10005.0 / 10000.0, "1.001"),
        (0.5, "0.500"),
        (0.9995, "1.000"),
        (2.0, "2.000"),
        (0.0, "0.000"),
        (0.0005, "0.001"),
        (0.0004999, "0.000"),
        (0.00095, "0.001"),
        (0.00009, "0.000"),
        (1e-7, "0.000"),
        (0.0015, "0.002"),
        (0.0025, "0.003"),
        (1.0625, "1.063"),
        (0.3125, "0.313"),
        (0.4375, "0.438"),
        (33.0 / 64.0, "0.516"),
        (1.2345, "1.235"),
        (2.675, "2.675"),
        (9.9995, "10.000"),
        (99.9995, "100.000"),
        (63.9999, "64.000"),
        (0.875, "0.875"),
        (0.999, "0.999"),
        (1e20, "100000000000000000000.000"),
        (123456.0005, "123456.001"),
    ] {
        assert_eq!(format_ratio_half_up(value), expected, "{value:e}");
    }
    assert_eq!(format!("{:.3}", 0.5625), "0.562");
    assert_eq!(format!("{:.3}", 1.0005), "1.000");
}

#[test]
fn summary_prints_the_half_up_rounded_load_factor() -> Result<(), crate::Error> {
    use crate::format::{flags, testing::blob, testing::entry};
    let names: Vec<_> = (0..9216).map(|index| format!("e{index:05}")).collect();
    let entries: Vec<_> = names
        .iter()
        .map(|name| entry(name.as_bytes(), b"\0", flags::RESOURCE))
        .collect();
    let bytes = blob(&entries, false, 2);
    let payload = crate::parse(&bytes)?;
    assert_eq!(payload.summary.lookup.bucket_count, 16384);
    let located = container::Located {
        container: "elf-section",
        name: ".pyload",
        offset: 0,
        bytes: &bytes,
    };
    let mut out = Vec::new();
    assert!(summary(&mut out, located, &payload).is_ok());
    let text = String::from_utf8_lossy(&out);
    assert!(text.contains("\nload_factor=0.563\n"), "{text}");
    Ok(())
}

#[test]
fn section_read_failures_print_payload_and_read_errors() {
    use container::ReadPayloadError::{Io, Payload};
    for (error, expected) in [
        (
            Payload(format::Error::OutOfMemory),
            "error: out of memory while parsing .pyload\n",
        ),
        (
            Payload(format::Error::PayloadLimitExceeded),
            "error: .pyload exceeds the maximum payload size of 256 MiB\n",
        ),
        (
            Io(io::Error::from(io::ErrorKind::UnexpectedEof)),
            "error: failed to read .pyload: UnexpectedEndOfFile\n",
        ),
    ] {
        assert_eq!(section_read_error(".pyload", &error), expected);
    }
}

#[test]
fn locate_failures_name_allocation_container_and_read_errors() {
    use container::LocateFileError::{Container, Io};
    #[cfg_attr(
        not(target_os = "linux"),
        expect(unused_mut, reason = "only Linux appends an errno case")
    )]
    let mut cases = vec![
        (
            Io(io::Error::from(io::ErrorKind::OutOfMemory)),
            "error: failed to read aws: OutOfMemory\n",
        ),
        (
            Container(container::Error::TruncatedElf),
            "error: truncated ELF executable: aws\n",
        ),
    ];
    #[cfg(target_os = "linux")]
    cases.push((
        Io(io::Error::from_raw_os_error(errno::ENOMEM)),
        "error: failed to read aws: SystemResources\n",
    ));
    for (error, expected) in cases {
        assert_eq!(locate_error(b"aws", &error), expected.as_bytes());
    }
}

#[test]
fn service_resources_overlapping_the_prefix_are_not_models() -> Result<(), crate::Error> {
    use crate::format::{flags, testing::blob, testing::entry};
    for name in [
        b"awscli/botocore/data/service-2.json".as_slice(),
        b"awscli/botocore/data/endpoint-rule-set-1.json",
    ] {
        assert_eq!(service_resource(name), None);
    }
    let bytes = blob(
        &[
            entry(
                b"awscli/botocore/data/partitions.json",
                b"{}",
                flags::RESOURCE,
            ),
            entry(
                b"awscli/botocore/data/service-2.json",
                b"{}",
                flags::RESOURCE,
            ),
        ],
        false,
        2,
    );
    assert_eq!(
        expect_model_only(&crate::parse(&bytes)?, &["s3".into()]),
        Err(
            b"error: unexpected model payload entry: awscli/botocore/data/service-2.json\n"
                .to_vec()
        )
    );
    Ok(())
}
