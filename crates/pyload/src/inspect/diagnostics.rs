use crate::{container, format};

pub fn container_error(path: &[u8], error: container::Error) -> Vec<u8> {
    use container::Error::*;
    let missing: String;
    let (before, after) = match error {
        NotExecutable => ("", " is not an ELF or Mach-O executable"),
        UnsupportedElf => ("unsupported ELF layout in ", ""),
        TruncatedElf => ("truncated ELF executable: ", ""),
        UnsupportedMachO => ("unsupported Mach-O layout in ", ""),
        TruncatedMachO => ("truncated Mach-O executable: ", ""),
        UnsupportedPe => ("unsupported PE layout in ", ""),
        TruncatedPe => ("truncated PE executable: ", ""),
        Overflow => ("executable offsets overflow while reading ", ""),
        MissingPayloadSection => {
            missing = format!(
                "no Python payload section ({}) found in ",
                container::PAYLOAD_SECTION_DESCRIPTION
            );
            (missing.as_str(), "")
        }
        InvalidPayloadSection => ("Python payload section points outside ", ""),
        DuplicatePayloadSection => ("multiple Python payload sections found in ", ""),
        PayloadSectionWritable => return b"error: .pyload is writable\n".to_vec(),
        PayloadSectionNotAllocated => return b"error: .pyload is not allocated\n".to_vec(),
        ArtifactLimitExceeded => ("", " exceeds the maximum artifact size of 1024 MiB"),
        ContainerLimitExceeded => (
            "",
            " exceeds the container metadata budget (1 MiB / 4096 items)",
        ),
        NotRegularFile => ("", " is not a regular file"),
        UnexpectedEndOfFile => ("failed to read ", ": UnexpectedEndOfFile"),
    };
    [b"error: ", before.as_bytes(), path, after.as_bytes(), b"\n"].concat()
}
pub fn payload_error(section: &str, error: format::Error) -> String {
    use format::Error::*;
    if error == OutOfMemory {
        return format!("error: out of memory while parsing {section}\n");
    }
    let reason = match error {
        BadMagic => "is not a valid ZIPPY003 payload",
        TruncatedHeader => "has a truncated ZIPPY003 header",
        EmptyEntryTable => "has an empty entry table",
        TruncatedControl => "has truncated lookup control bytes",
        TruncatedLookupIndex => "has truncated lookup index",
        TruncatedEntryMeta => "has truncated entry metadata",
        TruncatedStringTable => "has truncated string table",
        PayloadOutsideData => "entry payload extends past data section",
        UnknownFlags => "has unknown entry flags",
        ReservedFieldSet => "has nonzero reserved entry fields",
        InvalidKindFlags => "has invalid bytecode/resource flags",
        InvalidCompressionLengths => "has invalid compression lengths",
        NameOutsideStringTable => "entry name extends past string table",
        HashMismatch => "lookup control hash mismatch",
        UnsortedNames => "entry names are not sorted",
        InvalidIndexWidth => "has invalid lookup index width",
        InvalidBucketCount => "has invalid lookup bucket count",
        BadControlByte => "has invalid lookup control bytes",
        BadControlTail => "lookup control tail does not match",
        InvalidIndex => "has invalid lookup index references",
        DuplicateIndex => "has duplicate lookup index references",
        DuplicateName => "has duplicate entry names",
        OverlappingData => "has partially overlapping payload data",
        MissingIndex => "is missing lookup index references",
        InvalidProbeChain => "has unreachable lookup probe chains",
        ExtraBytes => "has trailing bytes after ZIPPY003 payload",
        InvalidSectionLayout => "has invalid ZIPPY003 section offsets",
        Overflow => "offset arithmetic overflowed",
        OutOfMemory => "could not be allocated",
        PayloadLimitExceeded => "exceeds the maximum payload size of 256 MiB",
        EntryLimitExceeded => "exceeds the entry count budget (65536)",
        BucketLimitExceeded => "exceeds the bucket count budget (131072)",
        AllocationLimitExceeded => "exceeds the validation allocation budget (8 MiB)",
        NameLimitExceeded => "exceeds the name budget (1024 bytes/name, 16 MiB total)",
        DecompressedLimitExceeded => {
            "exceeds the declared decompression budget (64 MiB/entry, 256 MiB total)"
        }
        ProbeLimitExceeded => "exceeds the probe budget (64 groups/entry, 1048576 total)",
        ComparisonLimitExceeded => "exceeds the candidate comparison budget (128 MiB)",
    };
    format!("error: {section} {reason}\n")
}
