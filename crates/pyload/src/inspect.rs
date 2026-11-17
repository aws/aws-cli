//! Payload inspector modes and byte-exact output shared by the standalone tool.
#![forbid(unsafe_code)]
mod diagnostics;
mod sha256;
use crate::{Payload, container, format};
use std::ffi::OsString;
use std::io::{self, Write};

pub use diagnostics::{container_error, payload_error};
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Mode {
    Summary,
    List,
    ExpectModelOnly,
}
pub fn run_mode(args: &[OsString]) -> Option<Mode> {
    let flag = || args[2].as_encoded_bytes();
    match args.len() {
        2 => Some(Mode::Summary),
        3 if flag() == b"--list" => Some(Mode::List),
        4.. if flag() == b"--expect-model-only" => Some(Mode::ExpectModelOnly),
        _ => None,
    }
}
pub fn usage(out: &mut dyn Write) -> io::Result<()> {
    writeln!(
        out,
        "usage: aws-python-payload-inspect <path-to-aws-executable> [--list]"
    )?;
    writeln!(
        out,
        "       aws-python-payload-inspect <path-to-aws-executable> \
        --expect-model-only <service>..."
    )
}
pub fn exact_payload_bytes(located: container::Located<'_>) -> Result<&[u8], format::Error> {
    if located.container == "mach-o-section" {
        Ok(&located.bytes[..format::payload_extent(located.bytes)?])
    } else {
        Ok(located.bytes)
    }
}
pub fn summary(
    out: &mut dyn Write,
    located: container::Located<'_>,
    payload: &Payload<'_>,
) -> io::Result<()> {
    writeln!(out, "format=ZIPPY003")?;
    writeln!(out, "container={}", located.container)?;
    writeln!(out, "container_name={}", located.name)?;
    writeln!(out, "payload_offset={}", located.offset)?;
    writeln!(out, "payload_bytes={}", payload.bytes.len())?;
    write!(out, "payload_sha256=")?;
    for byte in sha256::digest(payload.bytes) {
        write!(out, "{byte:02x}")?;
    }
    writeln!(out)?;
    let s = payload.summary;
    for (name, count) in [
        ("entries", s.entries),
        ("bytecode_entries", s.bytecode_entries),
        ("resource_entries", s.resource_entries),
        ("package_entries", s.package_entries),
        ("compressed_entries", s.compressed_entries),
    ] {
        writeln!(out, "{name}={count}")?;
    }
    for (name, count) in [
        ("raw_bytecode_bytes", s.raw_bytecode_bytes),
        ("raw_resource_bytes", s.raw_resource_bytes),
        ("compressed_stored_bytes", s.compressed_stored_bytes),
        (
            "compressed_uncompressed_bytes",
            s.compressed_uncompressed_bytes,
        ),
    ] {
        writeln!(out, "{name}={count}")?;
    }
    writeln!(out, "bucket_count={}", s.lookup.bucket_count)?;
    writeln!(
        out,
        "load_factor={}",
        format_ratio_half_up(s.entries as f64 / f64::from(s.lookup.bucket_count))
    )?;
    writeln!(out, "index_width={}", s.lookup.index_width)?;
    writeln!(out, "lookup_control_bytes={}", s.lookup.control_bytes)?;
    writeln!(out, "lookup_index_bytes={}", s.lookup.index_bytes)?;
    writeln!(out, "max_probe_groups={}", s.lookup.max_probe_groups)?;
    writeln!(
        out,
        "avg_probe_groups={}",
        format_ratio_half_up(s.lookup.total_probe_groups as f64 / s.entries as f64)
    )?;
    writeln!(
        out,
        "candidate_name_checks={}",
        s.lookup.candidate_name_checks
    )
}
const RATIO_DECIMALS: usize = 3;

fn format_ratio_half_up(value: f64) -> String {
    if !value.is_finite() {
        let sign = if value.is_sign_negative() { "-" } else { "" };
        let name = if value.is_nan() { "nan" } else { "inf" };
        return format!("{sign}{name}");
    }
    let shortest = format!("{:e}", value.abs());
    let (mantissa, exponent) = shortest.split_once('e').unwrap_or((shortest.as_str(), "0"));
    let integer = exponent.parse::<isize>().unwrap_or(0) + 1;
    let leading = usize::try_from(1 - integer).unwrap_or(0);
    let mut digits: Vec<u8> = std::iter::repeat_n(b'0', leading)
        .chain(mantissa.bytes().filter(u8::is_ascii_digit))
        .collect();
    let mut integer = usize::try_from(integer).unwrap_or(0).max(1);
    let kept = integer + RATIO_DECIMALS;
    digits.resize(digits.len().max(kept + 1), b'0');
    let round_up = digits[kept] >= b'5';
    digits.truncate(kept);
    if round_up && !increment(&mut digits) {
        digits.insert(0, b'1');
        integer += 1;
    }
    let sign = if value.is_sign_negative() { "-" } else { "" };
    let (whole, fraction) = digits.split_at(integer);
    format!(
        "{sign}{}.{}",
        String::from_utf8_lossy(whole),
        String::from_utf8_lossy(fraction)
    )
}

fn increment(digits: &mut [u8]) -> bool {
    for digit in digits.iter_mut().rev() {
        if *digit == b'9' {
            *digit = b'0';
        } else {
            *digit += 1;
            return true;
        }
    }
    false
}

pub fn list(out: &mut dyn Write, payload: &Payload<'_>) -> io::Result<()> {
    for entry in &payload.entries {
        out.write_all(entry.name)?;
        writeln!(
            out,
            " kind={} package={} compressed={} stored={} raw={}",
            entry.kind(),
            entry.is_package(),
            entry.is_compressed(),
            entry.compressed_len,
            entry.uncompressed_len
        )?;
    }
    Ok(())
}
pub fn valid_service_name(service: &[u8]) -> bool {
    !service.is_empty()
        && service
            .iter()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'-')
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResourceKind {
    ServiceModel,
    EndpointRules,
}
pub fn service_resource(name: &[u8]) -> Option<(&[u8], ResourceKind)> {
    let middle = name.strip_prefix(b"awscli/botocore/data/")?;
    let (middle, kind) = if let Some(middle) = middle.strip_suffix(b"/service-2.json") {
        (middle, ResourceKind::ServiceModel)
    } else {
        (
            middle.strip_suffix(b"/endpoint-rule-set-1.json")?,
            ResourceKind::EndpointRules,
        )
    };
    let separator = middle.iter().position(|&b| b == b'/')?;
    let service = &middle[..separator];
    let version = &middle[separator + 1..];
    if !valid_service_name(service) || version.is_empty() || version.contains(&b'/') {
        return None;
    }
    Some((service, kind))
}
/// Check that the payload holds exactly the model resources of `services`.
pub fn expect_model_only(payload: &Payload<'_>, services: &[OsString]) -> Result<(), Vec<u8>> {
    let services: Vec<&[u8]> = services.iter().map(|s| s.as_encoded_bytes()).collect();
    validate_services(&services)?;
    let mut models = vec![false; services.len()];
    let mut rules = vec![false; services.len()];
    let mut partitions = false;
    for entry in &payload.entries {
        if !entry.is_resource() || entry.is_bytecode() || entry.is_package() {
            return Err(line(
                "error: model payload contains non-resource entry: ",
                entry.name,
            ));
        }
        if entry.name == b"awscli/botocore/data/partitions.json" {
            partitions = true;
            continue;
        }
        let (service, kind) = service_resource(entry.name)
            .ok_or_else(|| line("error: unexpected model payload entry: ", entry.name))?;
        let index = services
            .iter()
            .position(|candidate| *candidate == service)
            .ok_or_else(|| {
                line(
                    "error: model payload contains unconfigured service: ",
                    service,
                )
            })?;
        match kind {
            ResourceKind::ServiceModel => models[index] = true,
            ResourceKind::EndpointRules => rules[index] = true,
        }
    }
    for (index, service) in services.iter().enumerate() {
        if !models[index] || !rules[index] {
            return Err(line(
                "error: model payload is missing endpoint resources for service: ",
                service,
            ));
        }
    }
    if !partitions {
        return Err(b"error: model payload is missing partitions.json\n".to_vec());
    }
    Ok(())
}
fn validate_services(services: &[&[u8]]) -> Result<(), Vec<u8>> {
    for (index, service) in services.iter().enumerate() {
        if !valid_service_name(service) {
            return Err(line("error: invalid expected service name: ", service));
        }
        if services[..index].contains(service) {
            return Err(line("error: duplicate expected service: ", service));
        }
    }
    Ok(())
}
fn line(text: &str, name: &[u8]) -> Vec<u8> {
    [text.as_bytes(), name, b"\n"].concat()
}

pub fn locate_error(path: &[u8], error: &container::LocateFileError) -> Vec<u8> {
    match error {
        container::LocateFileError::Container(error) => container_error(path, *error),
        container::LocateFileError::Io(error) => [
            b"error: failed to read ",
            path,
            b": ",
            read_error_name(error).as_bytes(),
            b"\n",
        ]
        .concat(),
    }
}

pub fn section_read_error(section: &str, error: &container::ReadPayloadError) -> String {
    match error {
        container::ReadPayloadError::Payload(error) => payload_error(section, *error),
        container::ReadPayloadError::Io(error) => {
            format!(
                "error: failed to read {section}: {}\n",
                read_error_name(error)
            )
        }
    }
}

pub fn open_error_name(error: &io::Error) -> &'static str {
    match error.raw_os_error() {
        #[cfg(target_os = "linux")]
        Some(code) => errno::open_name(code),
        _ => kind_error_name(error),
    }
}

pub fn read_error_name(error: &io::Error) -> &'static str {
    match error.raw_os_error() {
        #[cfg(target_os = "linux")]
        Some(code) => errno::read_name(code),
        _ => kind_error_name(error),
    }
}

fn kind_error_name(error: &io::Error) -> &'static str {
    match error.kind() {
        io::ErrorKind::NotFound => "FileNotFound",
        io::ErrorKind::PermissionDenied => "AccessDenied",
        io::ErrorKind::UnexpectedEof => "UnexpectedEndOfFile",
        io::ErrorKind::OutOfMemory => "OutOfMemory",
        _ if error.raw_os_error().is_some() => "InputOutput",
        _ => "Unexpected",
    }
}

#[cfg(target_os = "linux")]
mod errno {
    pub const EPERM: i32 = 1;
    pub const ENOENT: i32 = 2;
    pub const ESRCH: i32 = 3;
    pub const EIO: i32 = 5;
    pub const ENXIO: i32 = 6;
    pub const EBADF: i32 = 9;
    pub const EAGAIN: i32 = 11;
    pub const ENOMEM: i32 = 12;
    pub const EACCES: i32 = 13;
    pub const EBUSY: i32 = 16;
    pub const EEXIST: i32 = 17;
    pub const ENODEV: i32 = 19;
    pub const ENOTDIR: i32 = 20;
    pub const EISDIR: i32 = 21;
    pub const EINVAL: i32 = 22;
    pub const ENFILE: i32 = 23;
    pub const EMFILE: i32 = 24;
    pub const ETXTBSY: i32 = 26;
    pub const EFBIG: i32 = 27;
    pub const ENOSPC: i32 = 28;
    pub const ESPIPE: i32 = 29;
    pub const EROFS: i32 = 30;
    pub const ENAMETOOLONG: i32 = 36;
    pub const ELOOP: i32 = 40;
    pub const EOVERFLOW: i32 = 75;
    pub const EILSEQ: i32 = 84;
    pub const EOPNOTSUPP: i32 = 95;
    pub const ENOBUFS: i32 = 105;

    pub fn open_name(code: i32) -> &'static str {
        match code {
            EINVAL | EILSEQ => "BadPathName",
            EACCES => "AccessDenied",
            EFBIG | EOVERFLOW => "FileTooBig",
            EISDIR => "IsDir",
            ELOOP => "SymLinkLoop",
            EMFILE => "ProcessFdQuotaExceeded",
            ENAMETOOLONG => "NameTooLong",
            ENFILE => "SystemFdQuotaExceeded",
            ENODEV | ENXIO => "NoDevice",
            ENOENT | ESRCH => "FileNotFound",
            ENOMEM => "SystemResources",
            ENOSPC => "NoSpaceLeft",
            ENOTDIR => "NotDir",
            EPERM => "PermissionDenied",
            EEXIST => "PathAlreadyExists",
            EBUSY => "DeviceBusy",
            EOPNOTSUPP => "FileLocksUnsupported",
            EAGAIN => "WouldBlock",
            ETXTBSY => "FileBusy",
            EROFS => "ReadOnlyFileSystem",
            _ => "Unexpected",
        }
    }

    pub fn read_name(code: i32) -> &'static str {
        match code {
            ENXIO | ESPIPE | EOVERFLOW => "Unseekable",
            ENOBUFS | ENOMEM => "SystemResources",
            EAGAIN => "WouldBlock",
            EIO => "InputOutput",
            EISDIR => "IsDir",
            EBADF => "NotOpenForReading",
            _ => "Unexpected",
        }
    }
}

#[cfg(test)]
mod tests;
