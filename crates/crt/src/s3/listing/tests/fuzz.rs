use super::*;
use crate::s3::{ArchiveState, ListLocalError};
use crate::testing::Choices;

mod tests;

const RAW_BYTES_MAX: usize = 4096;
const EPOCH_BASE: i64 = 1_622_548_800;
const ATOMS: [(&str, &str); 12] = [
    ("a+%2Bb", "a +b"),
    ("%26amp%3B", "&amp;"),
    ("&<>'\"", "&<>'\""),
    ("%E9%9B%AA", "\u{96ea}"),
    ("%FF", "\u{fffd}"),
    ("%F0%9F%93", "\u{fffd}"),
    ("%ED%A0%80", "\u{fffd}\u{fffd}\u{fffd}"),
    ("%00", "\0"),
    ("%2", "%2"),
    ("%zz", "%zz"),
    ("%%41", "%A"),
    ("%252B", "%2B"),
];
const BAD_ENTRIES: [&str; 4] = [
    "<Contents><Key>&undefined;</Key></Contents>",
    "<Contents><Size>18446744073709551616</Size></Contents>",
    "<Contents><LastModified>not-a-date</LastModified></Contents>",
    "<CommonPrefixes><Prefix>&undefined;</Prefix></CommonPrefixes>",
];
const FRAGMENTS: [&str; 24] = [
    "<ListBucketResult>",
    "</ListBucketResult>",
    "<Contents>",
    "</Contents>",
    "<Key>",
    "</Key>",
    "<Size>",
    "</Size>",
    "<CommonPrefixes><Prefix>",
    "</Prefix></CommonPrefixes>",
    "<LastModified>2021-06-01T12:00:00Z</LastModified>",
    "<StorageClass>GLACIER</StorageClass>",
    "<EncodingType>url</EncodingType>",
    "<IsTruncated>true</IsTruncated>",
    "<NextContinuationToken>",
    "</NextContinuationToken>",
    "<![CDATA[",
    "]]>",
    "&amp;",
    "&undefined;",
    "&#x110000;",
    "&#0;",
    "18446744073709551616",
    "<s:Key xmlns:s=\"x\">",
];

#[derive(Debug, Clone, PartialEq, Eq)]
struct Fields {
    kind: EntryKind,
    name: Vec<u8>,
    size: u64,
    epoch: Option<i64>,
    archive: ArchiveState,
}
impl From<&ListEntry> for Fields {
    fn from(entry: &ListEntry) -> Self {
        Self {
            kind: entry.kind,
            name: entry.name.clone(),
            size: entry.size,
            epoch: entry.date.map(|date| date.epoch_seconds),
            archive: entry.archive,
        }
    }
}
#[derive(Debug)]
struct Semantic {
    body: Vec<u8>,
    operation: Operation,
    entries: Vec<Fields>,
    more: bool,
    token: Option<Vec<u8>>,
}
#[derive(Debug)]
struct Outcome {
    entries: Vec<ListEntry>,
    parsed: parse::State,
    result: Result<(), i32>,
}
fn parse_body(body: &[u8], operation: Operation) -> Outcome {
    let mut parsed = parse::State::default();
    let mut entries = Vec::new();
    let result = parse::parse_page(body, operation, &mut parsed, &mut |entry| {
        entries.push(entry);
        0
    });
    Outcome {
        entries,
        parsed,
        result,
    }
}

fn write_text(out: &mut Vec<u8>, input: &mut Choices<'_>, text: &[u8]) {
    for &byte in text {
        match input.range(0, 2) {
            0 => match byte {
                b'&' => out.extend_from_slice(b"&amp;"),
                b'<' => out.extend_from_slice(b"&lt;"),
                b'>' => out.extend_from_slice(b"&gt;"),
                _ => out.push(byte),
            },
            1 => out.extend_from_slice(format!("&#{byte};").as_bytes()),
            _ => out.extend_from_slice(format!("&#x{byte:x};").as_bytes()),
        }
    }
}
fn write_field(out: &mut Vec<u8>, input: &mut Choices<'_>, tag: &str, text: &[u8]) {
    out.extend_from_slice(format!("<{tag}>").as_bytes());
    write_text(out, input, text);
    out.extend_from_slice(format!("</{tag}>").as_bytes());
}
fn listing_name(input: &mut Choices<'_>) -> (Vec<u8>, Vec<u8>) {
    let mut encoded = Vec::new();
    let mut decoded = Vec::new();
    for _ in 0..input.range(1, 12) {
        let (atom, value) = ATOMS[input.index(ATOMS.len())];
        encoded.extend_from_slice(atom.as_bytes());
        encoded.push(b'/');
        decoded.extend_from_slice(value.as_bytes());
        decoded.push(b'/');
    }
    (encoded, decoded)
}

fn semantic(input: &mut Choices<'_>) -> Semantic {
    let buckets = input.flag();
    let url = input.flag();
    let more = input.flag();
    let second = input.range(0, 59);
    let (encoded, decoded) = listing_name(input);
    let date = format!("2021-06-01T12:00:{second:02}Z");
    let epoch = Some(EPOCH_BASE + second as i64);
    let root = if buckets {
        "ListAllMyBucketsResult"
    } else {
        "ListBucketResult"
    };
    let mut body = format!("<{root}>").into_bytes();
    let entries = if buckets {
        body.extend_from_slice(b"<Buckets><Bucket>");
        write_field(&mut body, input, "Name", &encoded);
        write_field(&mut body, input, "CreationDate", date.as_bytes());
        body.extend_from_slice(b"</Bucket></Buckets>");
        if more {
            write_field(&mut body, input, "ContinuationToken", &encoded);
        }
        vec![Fields {
            kind: EntryKind::Bucket,
            name: encoded.clone(),
            size: 0,
            epoch,
            archive: ArchiveState::default(),
        }]
    } else {
        let name = if url { &decoded } else { &encoded };
        let mut object = write_object(&mut body, input, &encoded, date.as_bytes(), url, more);
        object.name.clone_from(name);
        object.epoch = epoch;
        let prefix = Fields {
            kind: EntryKind::CommonPrefix,
            name: [b"p/".as_slice(), name].concat(),
            size: 0,
            epoch: None,
            archive: ArchiveState::default(),
        };
        vec![prefix, object]
    };
    body.extend_from_slice(format!("</{root}>").as_bytes());
    Semantic {
        body,
        operation: if buckets {
            Operation::ListBuckets
        } else {
            Operation::ListObjectsV2
        },
        entries,
        more,
        token: (!buckets || more).then_some(encoded),
    }
}
fn write_object(
    out: &mut Vec<u8>,
    input: &mut Choices<'_>,
    name: &[u8],
    date: &[u8],
    url: bool,
    more: bool,
) -> Fields {
    let size = input.word();
    let archived = input.flag();
    out.extend_from_slice(b"<Contents>");
    write_field(out, input, "Key", name);
    write_field(out, input, "LastModified", date);
    write_field(out, input, "Size", size.to_string().as_bytes());
    let storage = if archived { "GLACIER" } else { "GLACIER_IR" };
    write_field(out, input, "StorageClass", storage.as_bytes());
    out.extend_from_slice(b"</Contents><CommonPrefixes><Prefix>p/");
    write_text(out, input, name);
    out.extend_from_slice(b"</Prefix></CommonPrefixes>");
    let encoding = if url { "url" } else { "URL" };
    write_field(out, input, "EncodingType", encoding.as_bytes());
    let truncated = if more { "true" } else { "false" };
    write_field(out, input, "IsTruncated", truncated.as_bytes());
    write_field(out, input, "NextContinuationToken", name);
    Fields {
        kind: EntryKind::Object,
        name: Vec::new(),
        size,
        epoch: None,
        archive: ArchiveState {
            archived,
            restored: false,
        },
    }
}
fn check_semantic(case: &Semantic, label: &str) {
    let body = case.body.escape_ascii();
    let outcome = parse_body(&case.body, case.operation);
    assert_eq!(outcome.result, Ok(()), "{label}: {body}");
    assert_eq!(outcome.parsed.local_error, None, "{label}: {body}");
    let entries: Vec<Fields> = outcome.entries.iter().map(Fields::from).collect();
    assert_eq!(entries, case.entries, "{label}: {body}");
    assert_eq!(
        outcome.parsed.entries_emitted,
        entries.len() as u64,
        "{label}: {body}"
    );
    assert_eq!(
        outcome.parsed.has_more_results, case.more,
        "{label}: {body}"
    );
    assert_eq!(outcome.parsed.next_token, case.token, "{label}: {body}");
}

fn malformed(input: &mut Choices<'_>) -> Vec<u8> {
    let mut body = b"<ListBucketResult>".to_vec();
    for index in 0..input.range(1, 32) {
        body.extend_from_slice(
            format!("<Contents><Key>key{index}</Key><Size>{index}</Size></Contents>").as_bytes(),
        );
    }
    body.extend_from_slice(BAD_ENTRIES[input.index(BAD_ENTRIES.len())].as_bytes());
    body.extend_from_slice(b"</ListBucketResult>");
    body
}
fn check_malformed(body: &[u8], label: &str) {
    let outcome = parse_body(body, Operation::ListObjectsV2);
    let body = body.escape_ascii();
    assert!(outcome.result.is_err(), "{label}: {body}");
    assert!(
        matches!(
            outcome.parsed.local_error,
            Some(
                ListLocalError::CrtFailure
                    | ListLocalError::InvalidNumber
                    | ListLocalError::InvalidXmlText
            )
        ),
        "{label}: {:?} {body}",
        outcome.parsed.local_error
    );
    assert!(outcome.entries.is_empty(), "{label}: {body}");
    assert_eq!(outcome.parsed.entries_emitted, 0, "{label}: {body}");
}

fn mutated(input: &mut Choices<'_>) -> Vec<u8> {
    let mut body = if input.flag() {
        semantic(input).body
    } else {
        malformed(input)
    };
    if input.flag() {
        let start = body
            .iter()
            .position(|byte| *byte == b'>')
            .map_or(0, |end| end + 1);
        let end = body
            .iter()
            .rposition(|byte| *byte == b'<')
            .unwrap_or(body.len());
        body = body[start..end.max(start)].to_vec();
    }
    for _ in 0..input.range(0, 4) {
        let at = input.index(body.len() + 1);
        match input.range(0, 3) {
            0 => body.truncate(at),
            1 => {
                let end = at + input.index(body.len() - at + 1);
                body.drain(at..end);
            }
            2 => {
                let fragment = FRAGMENTS[input.index(FRAGMENTS.len())];
                body.splice(at..at, fragment.bytes());
            }
            _ => {
                let bytes = input.bytes(8);
                body.splice(at..at, bytes.iter().copied());
            }
        }
    }
    body.truncate(RAW_BYTES_MAX);
    body
}
fn expected_local_error(body: &[u8]) -> Option<ListLocalError> {
    let excluded = [
        '\0'..='\u{8}',
        '\u{b}'..='\u{c}',
        '\u{e}'..='\u{1f}',
        '\u{fffe}'..='\u{ffff}',
    ];
    match std::str::from_utf8(body) {
        Err(_) => Some(ListLocalError::InvalidUtf8),
        Ok(text) => text
            .chars()
            .any(|c| excluded.iter().any(|range| range.contains(&c)))
            .then_some(ListLocalError::InvalidXmlText),
    }
}
fn check_raw(bytes: &[u8], label: &str) {
    let wrapped = [b"<ListBucketResult>", bytes, b"</ListBucketResult>"].concat();
    for body in [bytes, &wrapped] {
        let outcome = parse_body(body, Operation::ListObjectsV2);
        let expected = expected_local_error(body);
        let body = body.escape_ascii();
        if expected.is_some() {
            assert_eq!(outcome.parsed.local_error, expected, "{label}: {body}");
        }
        if outcome.result.is_err() {
            assert!(
                matches!(
                    outcome.parsed.local_error,
                    Some(
                        ListLocalError::CrtFailure
                            | ListLocalError::InvalidNumber
                            | ListLocalError::UnexpectedRoot
                            | ListLocalError::InvalidUtf8
                            | ListLocalError::InvalidXmlText
                            | ListLocalError::MalformedXml
                    )
                ),
                "{label}: {:?} {body}",
                outcome.parsed.local_error
            );
            assert!(outcome.entries.is_empty(), "{label}: {body}");
        }
        assert_eq!(
            outcome.parsed.entries_emitted,
            outcome.entries.len() as u64,
            "{label}: {body}"
        );
        assert_eq!(outcome.parsed.callback_error, 0, "{label}: {body}");
    }
}
