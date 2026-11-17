use super::support;
use pyload::format::{
    flags,
    testing::{self, TestEntry, entry},
};
use std::error::Error;
use std::sync::OnceLock;

static PAYLOAD: OnceLock<Vec<u8>> = OnceLock::new();
static REPLACEMENT: OnceLock<Vec<u8>> = OnceLock::new();
static ALTERNATE: OnceLock<Vec<u8>> = OnceLock::new();
static EDGES: OnceLock<Vec<u8>> = OnceLock::new();
static UNSORTED: [OnceLock<Vec<u8>>; 2] = [OnceLock::new(), OnceLock::new()];

pub fn payload() -> Result<&'static [u8], Box<dyn Error>> {
    let plain = support::marshal_code(c"VALUE = 11\n")?;
    let package = support::marshal_code(c"PACKAGE_VALUE = 22\n")?;
    let child = support::marshal_code(c"CHILD_VALUE = 23\n")?;
    let compressed = support::marshal_code(c"VALUE = 33\n")?;
    let alias = support::marshal_code(c"ALIAS_VALUE = 'botocore'\n")?;
    let vendored = support::marshal_code(c"VENDORED_VALUE = 44\n")?;
    let noncode = support::marshal_none()?;
    let code_frame = raw_zstd(&compressed);
    let resource_frame = raw_zstd(b"compressed resource bytes");
    let mut entries = resources();
    entries.extend([
        entry(b"awscli.botocore", &alias, flags::BYTECODE | flags::PACKAGE),
        compressed_entry(b"bad_compressed_mod", b"not-zstd", flags::BYTECODE, 20),
        compressed_entry(
            b"compressed_mod",
            &code_frame,
            flags::BYTECODE,
            compressed.len(),
        ),
        entry(b"malformed_mod", b"not-marshal", flags::BYTECODE),
        entry(b"noncode_mod", &noncode, flags::BYTECODE),
        entry(b"pkg", &package, flags::BYTECODE | flags::PACKAGE),
        entry(b"pkg.child", &child, flags::BYTECODE),
        entry(b"plain", &plain, flags::BYTECODE),
        compressed_entry(
            b"resources/compressed.txt",
            &resource_frame,
            flags::RESOURCE,
            25,
        ),
        entry(b"vendor.root.child", &vendored, flags::BYTECODE),
    ]);
    assert_eq!(entries.len(), 20);
    let payload = testing::blob(&entries, false, 2);
    pyload::parse(&payload)?;
    Ok(PAYLOAD.get_or_init(|| payload))
}

fn resources() -> Vec<TestEntry<'static>> {
    [
        (b"dir/a.txt".as_slice(), b"a".as_slice()),
        (b"dir/sub/b.txt", b"b"),
        (b"dir/sub/c.txt", b"c"),
        (b"dir/z.txt", b"z"),
        (b"models/ec2/2015-01-01/service-2.json", b"{}"),
        (b"models/ec2/2016-11-15/service-2.json", b"{}"),
        (b"models/ignored/2020-01-01/other.json", b"{}"),
        (b"models/s3/2006-03-01/service-2.json", b"{}"),
        (b"models/s3/2006-03-01/waiters-2.json", b"{}"),
        (b"resources/raw.txt", b"raw resource bytes"),
    ]
    .into_iter()
    .map(|(name, bytes)| entry(name, bytes, flags::RESOURCE))
    .collect()
}

fn compressed_entry<'a>(
    name: &'a [u8],
    stored: &'a [u8],
    flags: u32,
    length: usize,
) -> TestEntry<'a> {
    let mut entry = entry(name, stored, flags | flags::COMPRESSED);
    assert!(u32::try_from(length).is_ok());
    entry.raw_len = length as u32;
    entry
}

fn raw_zstd(raw: &[u8]) -> Vec<u8> {
    assert!(raw.len() <= 255);
    let mut frame = vec![0x28, 0xb5, 0x2f, 0xfd, 0x20, raw.len() as u8];
    let block = ((raw.len() as u32) << 3) | 1;
    frame.extend_from_slice(&block.to_le_bytes()[..3]);
    frame.extend_from_slice(raw);
    frame
}

pub fn replacement() -> &'static [u8] {
    REPLACEMENT
        .get_or_init(|| testing::minimal(b"replacement.txt", b"replacement", flags::RESOURCE))
}

pub fn alternate() -> &'static [u8] {
    ALTERNATE.get_or_init(|| testing::minimal(b"alternate.txt", b"alternate", flags::RESOURCE))
}

pub fn edges() -> Result<&'static [u8], Box<dyn Error>> {
    let package = support::marshal_code(c"VALUE = 55\n")?;
    let file_allocation = support::marshal_code(c"FILE_ALLOCATION_VALUE = 66\n")?;
    let empty = raw_zstd(b"");
    let long_name = vec![b'm'; 1024];
    let file_allocation_name = vec![b'n'; 512];
    let entries = [
        entry(
            b"awscli.s3transfer",
            &package,
            flags::BYTECODE | flags::PACKAGE,
        ),
        entry(
            b"vendor.root.pkg",
            &package,
            flags::BYTECODE | flags::PACKAGE,
        ),
        entry(b"empty", b"", flags::RESOURCE),
        compressed_entry(b"compressed-empty", &empty, flags::RESOURCE, 0),
        entry(&long_name, &package, flags::BYTECODE),
        entry(&file_allocation_name, &file_allocation, flags::BYTECODE),
    ];
    let bytes = testing::blob(&entries, false, 2);
    pyload::parse(&bytes)?;
    Ok(EDGES.get_or_init(|| bytes))
}

pub fn unsorted() -> Result<[&'static [u8]; 2], Box<dyn Error>> {
    let short_name = [
        b"models/a/v/other.json".as_slice(),
        b"models/a/v",
        b"models/a",
    ];
    let backward_group = [
        b"models/a/x".as_slice(),
        b"models/a/y",
        b"models/a/b/other.json",
        b"models/x",
        b"models/y",
        b"models/c/v/other.json",
    ];
    let mut payloads: [&'static [u8]; 2] = [&[], &[]];
    for ((names, storage), payload) in [short_name.as_slice(), backward_group.as_slice()]
        .into_iter()
        .zip(&UNSORTED)
        .zip(&mut payloads)
    {
        let entries: Vec<_> = names
            .iter()
            .map(|name| entry(name, b"{}", flags::RESOURCE))
            .collect();
        let bytes = testing::build_unsorted(&entries)?;
        *payload = storage.get_or_init(|| bytes);
    }
    Ok(payloads)
}
