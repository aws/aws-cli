use super::*;
use crate::testing::{Script, sweep};

/// Every text byte of a page spelled the same way: 0 literally, 1 as a
/// decimal reference and 2 as a hex reference.
fn spelled(script: Script, count: usize, spelling: usize) -> Script {
    script.repeat(count, |script| script.range(0, 2, spelling))
}

#[test]
fn fuzz_listing_xml_semantic_values() {
    let _library = Library::acquire();
    // A bucket named for one `%26amp%3B` atom (10 bytes with its slash),
    // created at 12:00:01, with more results: its name, date and token.
    let bucket = Script::new().flag(true).flag(true).flag(true);
    let bucket = bucket.range(0, 59, 1).range(1, 12, 1).index(ATOMS.len(), 1);
    let bucket = spelled(bucket, 10 + 20 + 10, 1);
    // The same atom as an object of size 1 in the archive, with more
    // results: its key, date, size, storage class, prefix, encoding,
    // truncation and token.
    let object = Script::new().flag(false).flag(true).flag(true);
    let object = object.range(0, 59, 1).range(1, 12, 1).index(ATOMS.len(), 1);
    let object = spelled(
        object.word(1).flag(true),
        10 + 20 + 1 + 7 + 10 + 3 + 4 + 10,
        1,
    );
    // Two `&<>'"` atoms (12 bytes) as an object of size 2 out of the
    // archive, with no more results.
    let hex = Script::new().flag(false).flag(false).flag(false);
    let hex = hex.range(0, 59, 2).range(1, 12, 2).index(ATOMS.len(), 2);
    let hex = hex.index(ATOMS.len(), 2).word(2).flag(false);
    let hex = spelled(hex, 12 + 20 + 1 + 10 + 12 + 3 + 5 + 12, 2);
    let scripts = [Script::new(), bucket, object, hex, largest_size()];
    for (index, script) in scripts.iter().enumerate() {
        script.replay(|input| check_semantic(&semantic(input), &format!("script {index}")));
    }
    sweep(768, |bytes| {
        check_semantic(&semantic(&mut Choices::new(bytes)), "sweep case");
    });
}

fn largest_size() -> Script {
    let script = Script::new().flag(false).flag(false).flag(false);
    let script = script.range(0, 59, 0).range(1, 12, 1).index(ATOMS.len(), 0);
    script.word(u64::MAX)
}
#[test]
fn the_largest_size_script_reaches_the_largest_size() {
    largest_size().replay(|input| assert_eq!(semantic(input).entries[1].size, u64::MAX));
}

#[test]
fn fuzz_malformed_listing_page_emits_nothing() {
    let _library = Library::acquire();
    for count in [1, 32] {
        for bad in 0..BAD_ENTRIES.len() {
            let script = Script::new()
                .range(1, 32, count)
                .index(BAD_ENTRIES.len(), bad);
            script.replay(|input| {
                let label = format!("{count} entries, bad entry {bad}");
                check_malformed(&malformed(input), &label);
            });
        }
    }
    sweep(16, |bytes| {
        check_malformed(&malformed(&mut Choices::new(bytes)), "sweep case");
    });
}

#[test]
fn fuzz_raw_listing_xml() {
    let _library = Library::acquire();
    let bodies: [&[u8]; 4] = [
        b"",
        b"<Contents><Key>a&amp;b</Key><Size>13</Size></Contents>",
        b"<Contents><Key>&#x110000;</Key></Contents>",
        b"<Contents><Key>a</Key></Contents><broken",
    ];
    for (index, body) in bodies.iter().enumerate() {
        let script = Script::new().bytes(RAW_BYTES_MAX, body);
        script.replay(|input| check_raw(input.bytes(RAW_BYTES_MAX), &format!("script {index}")));
    }
    sweep(1024, |bytes| {
        check_raw(&mutated(&mut Choices::new(bytes)), "sweep case");
    });
}

#[test]
fn a_raw_body_wrapped_in_a_root_yields_its_object() {
    let _library = Library::acquire();
    let wrapped = [
        b"<ListBucketResult>".as_slice(),
        b"<Contents><Key>a&amp;b</Key><Size>13</Size></Contents>",
        b"</ListBucketResult>",
    ]
    .concat();
    let outcome = parse_body(&wrapped, Operation::ListObjectsV2);
    assert_eq!(outcome.result, Ok(()));
    assert_eq!(outcome.entries.len(), 1);
    assert_eq!(outcome.entries[0].name, b"a&b");
    assert_eq!(outcome.entries[0].size, 13);
}
