use super::*;
use crate::s3::ListLocalError;

struct Page {
    entries: Vec<ListEntry>,
    parsed: parse::State,
    result: Result<(), i32>,
}
impl Page {
    fn names(&self) -> Vec<u8> {
        self.entries
            .iter()
            .flat_map(|entry| entry.name.iter().copied().chain([b'\n']))
            .collect()
    }
}
fn parse_page(body: &[u8], operation: Operation) -> Page {
    let _library = Library::acquire();
    let mut parsed = parse::State::default();
    let mut entries = Vec::new();
    let result = parse::parse_page(body, operation, &mut parsed, &mut |entry| {
        entries.push(entry);
        0
    });
    Page {
        entries,
        parsed,
        result,
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test checks every field the page yields"
)]
fn list_bucket_result_yields_decoded_objects_prefixes_and_the_continuation() {
    let page = parse_page(
        concat!(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<ListBucketResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\">",
            "<Name>bucket</Name><Prefix>dir+1/</Prefix><KeyCount>2</KeyCount><MaxKeys>2</MaxKeys>",
            "<EncodingType>url</EncodingType><IsTruncated>true</IsTruncated>",
            "<NextContinuationToken>1dMBcpc/token+value=&amp;%2F&lt;</NextContinuationToken>",
            "<Contents><Key>dir+1/a%2Bb%20c.txt</Key>",
            "<LastModified>2021-06-01T12:00:00.000Z</LastModified>",
            "<ETag>&quot;abc&quot;</ETag><Size>42</Size><StorageClass>STANDARD</StorageClass>",
            "</Contents>",
            "<CommonPrefixes><Prefix>dir+1/sub%2F/</Prefix></CommonPrefixes>",
            "</ListBucketResult>",
        )
        .as_bytes(),
        Operation::ListObjectsV2,
    );
    assert_eq!(page.result, Ok(()));
    assert_eq!(page.entries.len(), 2);
    let object = &page.entries[1];
    assert_eq!(object.kind, EntryKind::Object);
    assert_eq!(object.name, b"dir 1/a+b c.txt");
    assert_eq!(object.size, 42);
    assert_eq!(
        object.date.map(|date| date.epoch_seconds),
        Some(1_622_548_800)
    );
    let prefix = &page.entries[0];
    assert_eq!(prefix.kind, EntryKind::CommonPrefix);
    assert_eq!(prefix.name, b"dir 1/sub//");
    assert_eq!(prefix.date, None);
    assert_eq!(
        page.parsed.next_token.as_deref(),
        Some(b"1dMBcpc/token+value=&%2F<".as_slice())
    );
    assert!(page.parsed.has_more_results);
    assert_eq!(page.parsed.local_error, None);
    assert_eq!(page.parsed.entries_emitted, 2);
}

#[test]
fn common_prefixes_come_before_objects_in_any_document_order() {
    let page = parse_page(
        concat!(
            "<ListBucketResult><EncodingType>url</EncodingType>",
            "<Contents><Key>a</Key><Size>1</Size></Contents>",
            "<CommonPrefixes><Prefix>p/</Prefix></CommonPrefixes>",
            "<Contents><Key>b</Key><Size>2</Size></Contents>",
            "<CommonPrefixes><Prefix>q/</Prefix></CommonPrefixes>",
            "<IsTruncated>false</IsTruncated></ListBucketResult>",
        )
        .as_bytes(),
        Operation::ListObjectsV2,
    );
    assert_eq!(page.names(), b"p/\nq/\na\nb\n");
    assert_eq!(
        page.entries.iter().map(|e| e.kind).collect::<Vec<_>>(),
        [
            EntryKind::CommonPrefix,
            EntryKind::CommonPrefix,
            EntryKind::Object,
            EntryKind::Object
        ]
    );
    assert_eq!(page.entries[3].size, 2);
}

#[test]
fn names_are_url_decoded_only_when_the_page_encoding_type_is_url() {
    for (encoding, expected) in [
        ("<EncodingType>url</EncodingType>", "sp ace/\na+b c\n"),
        ("", "sp+ace/\na%2Bb+c\n"),
        ("<EncodingType>URL</EncodingType>", "sp+ace/\na%2Bb+c\n"),
        ("<EncodingType>u&#114;l</EncodingType>", "sp ace/\na+b c\n"),
    ] {
        let body = format!(
            "<ListBucketResult><Contents><Key>a%2Bb+c</Key></Contents>\
             <CommonPrefixes><Prefix>sp+ace/</Prefix></CommonPrefixes>{encoding}\
             </ListBucketResult>"
        );
        let page = parse_page(body.as_bytes(), Operation::ListObjectsV2);
        assert_eq!(page.names(), expected.as_bytes(), "{encoding}");
    }
}

#[test]
fn names_decode_xml_entities_before_any_url_decoding() {
    for (encoding, expected) in [
        ("", "p&q/\na&b<c>\"'\u{e9}%26amp%3B\n"),
        (
            "<EncodingType>url</EncodingType>",
            "p&q/\na&b<c>\"'\u{e9}&amp;\n",
        ),
    ] {
        let body = format!(
            "<ListBucketResult>{encoding}\
             <Contents><Key>a&amp;b&lt;c&gt;&quot;&apos;&#233;%26amp%3B</Key></Contents>\
             <CommonPrefixes><Prefix>p&#x26;q/</Prefix></CommonPrefixes></ListBucketResult>"
        );
        let page = parse_page(body.as_bytes(), Operation::ListObjectsV2);
        assert_eq!(page.names(), expected.as_bytes(), "{encoding}");
    }
    let page = parse_page(
        b"<ListAllMyBucketsResult><Buckets><Bucket><Name>team&amp;a&#45;1</Name></Bucket>\
          </Buckets></ListAllMyBucketsResult>",
        Operation::ListBuckets,
    );
    assert_eq!(page.names(), b"team&a-1\n");
    for (body, operation) in [
        (
            b"<ListBucketResult><CommonPrefixes><Prefix>p/</Prefix></CommonPrefixes>\
              <Contents><Key>a</Key></Contents><Contents><Key>b&nbsp;c</Key></Contents>\
              </ListBucketResult>"
                .as_slice(),
            Operation::ListObjectsV2,
        ),
        (
            b"<ListAllMyBucketsResult><Buckets><Bucket><Name>a</Name></Bucket>\
              <Bucket><Name>b&nbsp;c</Name></Bucket></Buckets></ListAllMyBucketsResult>",
            Operation::ListBuckets,
        ),
    ] {
        assert_fails_whole(body, operation, ListLocalError::InvalidXmlText);
    }
}

#[test]
fn mixed_cdata_and_entities_preserve_literal_text_in_names_and_scalar_fields() {
    let page = parse_page(
        concat!(
            "<s:ListBucketResult xmlns:s=\"http://s3.amazonaws.com/doc/2006-03-01/\">",
            "<s:Contents><s:Key>head&amp;<![CDATA[a&amp;<b>%2F]]>tail&#33;<![CDATA[<>]]></s:Key>",
            "<s:Size> \n<![CDATA[13]]>\t </s:Size>",
            "<s:LastModified><![CDATA[2021-06-01T12:00:00.000Z]]></s:LastModified>",
            "<s:StorageClass>GLACIE<![CDATA[R]]></s:StorageClass></s:Contents>",
            "<s:CommonPrefixes><s:Prefix>p&amp;<![CDATA[%2F]]></s:Prefix></s:CommonPrefixes>",
            "<s:EncodingType>u<![CDATA[r]]>l</s:EncodingType>",
            "<s:IsTruncated><![CDATA[true]]></s:IsTruncated>",
            "<s:NextContinuationToken><![CDATA[next&amp;</s:NextContinuationToken>]]>&amp;tail",
            "</s:NextContinuationToken></s:ListBucketResult>",
        )
        .as_bytes(),
        Operation::ListObjectsV2,
    );
    assert_eq!(page.result, Ok(()));
    assert_eq!(page.names(), b"p&/\nhead&a&amp;<b>/tail!<>\n");
    let object = &page.entries[1];
    assert_eq!(object.size, 13);
    assert_eq!(
        object.date.map(|date| date.epoch_seconds),
        Some(1_622_548_800)
    );
    assert!(object.archive.archived);
    assert!(page.parsed.has_more_results);
    assert_eq!(
        page.parsed.next_token.as_deref(),
        Some(b"next&amp;</s:NextContinuationToken>&tail".as_slice())
    );
}

#[test]
fn names_drop_comments_and_processing_instructions_whose_openers_start_no_section() {
    let page = parse_page(
        b"<ListBucketResult><Contents><Key>a<!-- <![CDATA[ & -->b<?pi <![CDATA[ ?>c\
            <![CDATA[&]]></Key><Size>1</Size></Contents></ListBucketResult>",
        Operation::ListObjectsV2,
    );
    assert_eq!(page.result, Ok(()));
    assert_eq!(page.names(), b"abc&\n");
}
#[test]
fn scalar_fields_decode_xml_entities_like_names() {
    let page = parse_page(
        b"<ListBucketResult><IsTruncated>tru&#101;</IsTruncated>\
          <Contents><Key>a</Key><Size>&#49;3</Size>\
          <LastModified>2021-06-01T12:00:00.000&#90;</LastModified>\
          <StorageClass>GLACIE&#82;</StorageClass></Contents></ListBucketResult>",
        Operation::ListObjectsV2,
    );
    let entry = &page.entries[0];
    assert_eq!(entry.size, 13);
    assert_eq!(
        entry.date.map(|date| date.epoch_seconds),
        Some(1_622_548_800)
    );
    assert!(entry.archive.archived);
    assert!(page.parsed.has_more_results);
    let page = parse_page(
        b"<ListAllMyBucketsResult><Buckets><Bucket><Name>b</Name>\
          <CreationDate>2021-06-01T12:00:00.000&#90;</CreationDate></Bucket>\
          </Buckets></ListAllMyBucketsResult>",
        Operation::ListBuckets,
    );
    assert_eq!(
        page.entries[0].date.map(|date| date.epoch_seconds),
        Some(1_622_548_800)
    );
}

#[test]
fn bucket_listing_yields_buckets_and_an_entity_decoded_continuation_token() {
    let page = parse_page(
        b"<ListAllMyBucketsResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\">\
          <Owner><ID>owner</ID></Owner><Buckets>\
          <Bucket><Name>alpha</Name>\
          <CreationDate>2021-06-01T12:00:00.000Z</CreationDate></Bucket>\
          <Bucket><Name>beta</Name></Bucket>\
          </Buckets><ContinuationToken>next&amp;&#47;</ContinuationToken>\
          </ListAllMyBucketsResult>",
        Operation::ListBuckets,
    );
    assert_eq!(page.names(), b"alpha\nbeta\n");
    assert_eq!(page.entries[0].kind, EntryKind::Bucket);
    assert_eq!(
        page.entries[0].date.map(|date| date.epoch_seconds),
        Some(1_622_548_800)
    );
    assert_eq!(page.entries[1].date, None);
    assert_eq!(
        page.parsed.next_token.as_deref(),
        Some(b"next&/".as_slice())
    );
    assert!(page.parsed.has_more_results);
}

#[test]
fn a_stopping_sink_receives_entries_only_after_the_whole_page_is_read() {
    let _library = Library::acquire();
    let mut parsed = parse::State::default();
    let mut names = Vec::new();
    let result = parse::parse_page(
        b"<ListBucketResult><Contents><Key>a</Key></Contents>\
          <Contents><Key>b</Key></Contents><IsTruncated>true</IsTruncated>\
          <NextContinuationToken>next</NextContinuationToken></ListBucketResult>",
        Operation::ListObjectsV2,
        &mut parsed,
        &mut |entry| {
            names.push(entry.name);
            17
        },
    );
    assert_eq!(result, Err(crate::s3::CANCELED_ERROR_CODE));
    assert_eq!(parsed.callback_error, 17);
    assert_eq!(names, [b"a"]);
    assert_eq!(parsed.next_token.as_deref(), Some(b"next".as_slice()));
    assert!(parsed.has_more_results);
}

#[test]
fn an_empty_continuation_token_is_kept_and_a_bad_size_is_rejected() {
    let page = parse_page(
        b"<ListBucketResult><NextContinuationToken></NextContinuationToken>\
          <IsTruncated>TRUE</IsTruncated></ListBucketResult>",
        Operation::ListObjectsV2,
    );
    assert_eq!(page.parsed.next_token.as_deref(), Some(b"".as_slice()));
    assert!(page.parsed.has_more_results);
    for size in ["big", "", "_1", "1_", "-1", "18446744073709551616", "1 2"] {
        let body = format!(
            "<ListBucketResult><Contents><Key>a</Key><Size>{size}</Size></Contents>\
             </ListBucketResult>"
        );
        let page = parse_page(body.as_bytes(), Operation::ListObjectsV2);
        assert_eq!(
            page.result,
            Err(crate::s3::INVALID_ARGUMENT_ERROR_CODE),
            "{size}"
        );
        assert_eq!(page.parsed.local_error, Some(ListLocalError::InvalidNumber));
        assert!(page.entries.is_empty());
    }
    for (size, expected) in [
        ("+13", 13),
        ("-0", 0),
        ("1_3", 13),
        ("\t 13\r\n", 13),
        ("18446744073709551615", u64::MAX),
    ] {
        let body = format!(
            "<ListBucketResult><Contents><Key>a</Key><Size>{size}</Size></Contents>\
             </ListBucketResult>"
        );
        assert_eq!(
            parse_page(body.as_bytes(), Operation::ListObjectsV2).entries[0].size,
            expected,
            "{size:?}"
        );
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test keeps each body case beside the one it contrasts with"
)]
fn an_empty_body_is_an_empty_final_page_but_whitespace_is_parsed() {
    for operation in [Operation::ListObjectsV2, Operation::ListBuckets] {
        let page = parse_page(b"", operation);
        assert_eq!(page.result, Ok(()));
        assert!(page.entries.is_empty());
        assert_eq!(page.parsed.entries_emitted, 0);
        assert!(!page.parsed.has_more_results);
        assert_eq!(page.parsed.next_token, None);
        assert_eq!(page.parsed.local_error, None);
        let page = parse_page(b" \n", operation);
        assert!(page.result.is_err());
        assert_eq!(page.parsed.local_error, Some(ListLocalError::MalformedXml));
        assert!(page.parsed.document_malformed());
    }
}

#[test]
fn a_bad_scalar_after_valid_entries_emits_nothing_from_the_page() {
    for bad in [
        "<Contents><Key>&undefined;</Key></Contents>",
        "<Contents><Size>18446744073709551616</Size></Contents>",
        "<Contents><LastModified>not-a-date</LastModified></Contents>",
        "<CommonPrefixes><Prefix>&undefined;</Prefix></CommonPrefixes>",
        "<Contents><Key><![CDATA[open</Key></Contents>",
    ] {
        let body = format!(
            "<ListBucketResult><Contents><Key>key0</Key><Size>0</Size></Contents>\
             <CommonPrefixes><Prefix>p/</Prefix></CommonPrefixes>{bad}</ListBucketResult>"
        );
        let page = parse_page(body.as_bytes(), Operation::ListObjectsV2);
        assert!(page.result.is_err(), "{bad}");
        assert!(page.entries.is_empty(), "{bad}");
        assert_eq!(page.parsed.entries_emitted, 0);
    }
}

fn objects_around(bad: &[u8]) -> Vec<u8> {
    [
        b"<ListBucketResult><Contents><Key>p/a.txt</Key><Size>3</Size></Contents>\
          <CommonPrefixes><Prefix>p/sub/</Prefix></CommonPrefixes>"
            .as_slice(),
        bad,
        b"<Contents><Key>p/z.txt</Key><Size>3</Size></Contents></ListBucketResult>",
    ]
    .concat()
}
fn assert_fails_as_not_utf8(body: &[u8], operation: Operation) {
    assert_fails_whole(body, operation, ListLocalError::InvalidUtf8);
}
fn assert_fails_whole(body: &[u8], operation: Operation, error: ListLocalError) {
    let page = parse_page(body, operation);
    assert_eq!(
        (
            page.result,
            page.parsed.local_error,
            page.entries.len(),
            page.parsed.entries_emitted,
            page.parsed.callback_error,
        ),
        (
            Err(parse::ListingError::InvalidXml.code()),
            Some(error),
            0,
            0,
            0
        ),
        "{}",
        body.escape_ascii()
    );
}

#[test]
fn an_object_page_that_is_not_utf8_fails_whole_before_any_entry() {
    for bad in [
        b"<Contents><Key>p/k\xff</Key><Size>3</Size></Contents>".as_slice(),
        b"<Contents><Key>p/k\xff/</Key><Size>0</Size></Contents>",
        b"<Contents><Key>p/k</Key><ETag>\xc3</ETag></Contents>",
    ] {
        assert_fails_as_not_utf8(&objects_around(bad), Operation::ListObjectsV2);
    }
    for bad in [
        b"<Contents><Key>p/k&#xD800;</Key><Size>3</Size></Contents>".as_slice(),
        b"<CommonPrefixes><Prefix>p/&#56320;/</Prefix></CommonPrefixes>",
        b"<EncodingType>url</EncodingType><Contents><Key>p/k&#xD800;</Key></Contents>",
    ] {
        assert_fails_whole(
            &objects_around(bad),
            Operation::ListObjectsV2,
            ListLocalError::InvalidXmlText,
        );
    }
    let page = parse_page(
        &objects_around(
            b"<EncodingType>url</EncodingType>\
              <Contents><Key>p/caf&#xE9;%FF</Key><Size>3</Size></Contents>",
        ),
        Operation::ListObjectsV2,
    );
    assert_eq!(page.result, Ok(()));
    assert_eq!(
        page.names(),
        "p/sub/\np/a.txt\np/caf\u{e9}\u{fffd}\np/z.txt\n".as_bytes()
    );
}

#[test]
fn a_bucket_page_that_is_not_utf8_fails_whole_before_any_entry() {
    for (bad, error) in [
        (
            b"<Bucket><Name>b\xff</Name></Bucket>".as_slice(),
            ListLocalError::InvalidUtf8,
        ),
        (
            b"<Bucket><Name>b&#xDFFF;</Name></Bucket>",
            ListLocalError::InvalidXmlText,
        ),
    ] {
        let body = [
            b"<ListAllMyBucketsResult><Buckets><Bucket><Name>a</Name></Bucket>".as_slice(),
            bad,
            b"</Buckets></ListAllMyBucketsResult>",
        ]
        .concat();
        assert_fails_whole(&body, Operation::ListBuckets, error);
    }
}

#[test]
fn a_page_that_is_not_utf8_fails_whole() {
    const GOOD_OBJECT: &[u8] = b"<Contents><Key>p/good</Key><Size>1</Size></Contents>";
    const GOOD_BUCKET: &[u8] = b"<Bucket><Name>good</Name></Bucket>";
    for bad in [
        b"<Contents><Key>p/k\xff</Key></Contents>".as_slice(),
        b"<Contents><Key>p/b</Key><ETag>\xc0\xaf</ETag></Contents>",
    ] {
        let body = [
            b"<ListBucketResult>",
            GOOD_OBJECT,
            bad,
            b"</ListBucketResult>",
        ]
        .concat();
        assert_fails_as_not_utf8(&body, Operation::ListObjectsV2);
    }
    let body = [
        b"<ListAllMyBucketsResult><Buckets>".as_slice(),
        GOOD_BUCKET,
        b"<Bucket><Name>b\xed\xa0\x80</Name></Bucket>",
        b"</Buckets></ListAllMyBucketsResult>",
    ]
    .concat();
    assert_fails_as_not_utf8(&body, Operation::ListBuckets);
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "one table keeps every disallowed character in both spellings"
)]
fn a_character_xml_does_not_allow_fails_the_whole_page_raw_or_by_reference() {
    let spellings: [&[u8]; 24] = [
        b"a\x01b",
        b"a\x0bb",
        "a\u{fffe}b".as_bytes(),
        b"a<![CDATA[\x1f]]>b",
        "a<!-- \u{ffff} -->b".as_bytes(),
        b"a&#x1;b",
        b"a&#1;b",
        b"a&#0;b",
        b"a&#xFFFE;b",
        b"a&#65535;b",
        b"a&#xD800;b",
        b"a&#57343;b",
        b"a&#x110000;b",
        b"a&#99999999999999999999;b",
        b"a&#XD800;b",
        b"a&#X41;b",
        b"a&#;b",
        b"a&#x;b",
        b"a&#x1_0;b",
        b"a&#65 b",
        b"a&#x41",
        b"a&nbsp;b",
        b"a & b",
        b"a&amp b",
    ];
    for spelling in spellings {
        for element in [b"Key".as_slice(), b"ETag"] {
            let body = [
                b"<ListBucketResult><Contents><Key>p/good</Key><Size>1</Size></Contents>\
                  <Contents><Key>p/b</Key><"
                    .as_slice(),
                element,
                b">",
                spelling,
                b"</",
                element,
                b"></Contents></ListBucketResult>",
            ]
            .concat();
            assert_fails_whole(
                &body,
                Operation::ListObjectsV2,
                ListLocalError::InvalidXmlText,
            );
        }
    }
    for (body, operation) in [
        (
            b"<ListBucketResult><Contents><Key x=\"&#x1;\">p/b</Key></Contents>\
              </ListBucketResult>"
                .as_slice(),
            Operation::ListObjectsV2,
        ),
        (
            b"<ListBucketResult><Contents><Key>p/b</Key></Contents>\
              <CommonPrefixes><Prefix>p&#xB;/</Prefix></CommonPrefixes></ListBucketResult>",
            Operation::ListObjectsV2,
        ),
        (
            b"<ListAllMyBucketsResult><Buckets><Bucket><Name>good</Name></Bucket>\
              <Bucket><Name>b\x7f\x08</Name></Bucket></Buckets></ListAllMyBucketsResult>",
            Operation::ListBuckets,
        ),
        (
            b"<ListAllMyBucketsResult><Buckets><Bucket><Name>good</Name></Bucket>\
              <Bucket><Name>b&#xDC00;</Name></Bucket></Buckets></ListAllMyBucketsResult>",
            Operation::ListBuckets,
        ),
        (
            b"<ListBucketResult><Contents><Key>p/b</Key></Contents></ListBucketResult>&#x",
            Operation::ListObjectsV2,
        ),
    ] {
        assert_fails_whole(body, operation, ListLocalError::InvalidXmlText);
    }
}

#[test]
fn characters_and_references_xml_allows_still_list() {
    let page = parse_page(
        "<ListBucketResult><Contents><Key>caf\u{e9}</Key>\
         <ETag>\t\r\n&#x9;&#xA;&#xD;&#13;</ETag></Contents>\
         <Contents><Key>&#xE9;&#x1F600;&#x0041;&#x10FFFF;\u{7f}\u{85}\u{fffd}</Key></Contents>\
         <Contents><Key>&lt;&gt;&amp;&apos;&quot;</Key></Contents>\
         <Contents><Key>c<![CDATA[&#xD800;&#X1;&nbsp;&]]></Key>\
         <ETag><!-- &#xD800; &bogus; & --><?pi &#x1;?></ETag></Contents></ListBucketResult>"
            .as_bytes(),
        Operation::ListObjectsV2,
    );
    assert_eq!(page.result, Ok(()));
    assert_eq!(
        page.names(),
        "caf\u{e9}\n\u{e9}\u{1f600}A\u{10ffff}\u{7f}\u{85}\u{fffd}\n<>&'\"\n\
         c&#xD800;&#X1;&nbsp;&\n"
            .as_bytes()
    );
}

#[test]
fn an_object_page_with_a_character_xml_does_not_allow_fails_whole_before_any_entry() {
    for bad in [
        b"<Contents><Key>p/a\x01b</Key><Size>3</Size></Contents>".as_slice(),
        b"<Contents><Key>p/&#1;b</Key><Size>3</Size></Contents>",
        b"<Contents><Key>p/a&#xFFFE;</Key><Size>3</Size></Contents>",
        b"<Contents><Key>p/a\xef\xbf\xbf</Key><Size>3</Size></Contents>",
        b"<Contents><Key>p/a&#0;</Key><Size>3</Size></Contents>",
        b"<Contents><Key>p/<![CDATA[a\x1f]]></Key><Size>3</Size></Contents>",
        b"<CommonPrefixes><Prefix>p/&#x1B;/</Prefix></CommonPrefixes>",
        b"<EncodingType>url</EncodingType><Contents><Key>p/k&#x7;</Key></Contents>",
        b"<Contents><Key>p/k</Key><Size>&#11;3</Size></Contents>",
        b"<Contents><Key>p/k</Key><Size>\x0b3</Size></Contents>",
        b"<Contents><Key>p/k</Key><ETag>\x0c</ETag></Contents>",
        b"<NextContinuationToken>t&#xFFFF;</NextContinuationToken>",
    ] {
        assert_fails_whole(
            &objects_around(bad),
            Operation::ListObjectsV2,
            ListLocalError::InvalidXmlText,
        );
    }
    assert_fails_whole(
        b"<html>\x01",
        Operation::ListObjectsV2,
        ListLocalError::InvalidXmlText,
    );
    let page = parse_page(
        &objects_around(
            "<Contents><Key>p/\t\n&#9;&#xA;&#13;\u{fffd}&#xE000;&#x10000;</Key>\
             <Size>3</Size></Contents>"
                .as_bytes(),
        ),
        Operation::ListObjectsV2,
    );
    assert_eq!(page.result, Ok(()));
    assert_eq!(
        page.names(),
        "p/sub/\np/a.txt\np/\t\n\t\n\r\u{fffd}\u{e000}\u{10000}\np/z.txt\n".as_bytes()
    );
}

#[test]
fn a_bucket_page_with_a_character_xml_does_not_allow_fails_whole_before_any_entry() {
    for bad in [
        b"<Buckets><Bucket><Name>b\x02</Name></Bucket></Buckets>".as_slice(),
        b"<Buckets><Bucket><Name>b&#x2;</Name></Bucket></Buckets>",
        b"<ContinuationToken>&#xFFFE;</ContinuationToken>",
    ] {
        let body = [
            b"<ListAllMyBucketsResult><Buckets><Bucket><Name>a</Name></Bucket></Buckets>"
                .as_slice(),
            bad,
            b"</ListAllMyBucketsResult>",
        ]
        .concat();
        assert_fails_whole(
            &body,
            Operation::ListBuckets,
            ListLocalError::InvalidXmlText,
        );
    }
}

#[test]
fn percent_decoding_matches_botocore_unquote_plus() {
    for (encoded, expected) in [
        ("", ""),
        ("a+b%2Bc+%20d%2fe", "a b+c  d/e"),
        ("%E9%9B%AA%e9%9b%aa%00%7e", "\u{96ea}\u{96ea}\0~"),
        ("%", "%"),
        ("a%", "a%"),
        ("%4", "%4"),
        ("%zz", "%zz"),
        ("%2 x", "%2 x"),
        ("a%+1", "a% 1"),
        ("%%41", "%A"),
        ("%25zz", "%zz"),
        ("%FF", "\u{fffd}"),
        ("%C3%28", "\u{fffd}("),
        ("a%FFb%20c", "a\u{fffd}b c"),
        ("%F0%9F%93", "\u{fffd}"),
        ("%C0%AF", "\u{fffd}\u{fffd}"),
        ("%ED%A0%80", "\u{fffd}\u{fffd}\u{fffd}"),
        (
            "x%F8%88%80%80%80",
            "x\u{fffd}\u{fffd}\u{fffd}\u{fffd}\u{fffd}",
        ),
    ] {
        assert_eq!(
            parse::url_decoded(encoded.as_bytes()),
            expected.as_bytes(),
            "{encoded}"
        );
    }
}

#[test]
fn the_token_probe_leaves_xml_encoded_and_empty_tokens_to_the_parse() {
    for body in [
        b"<NextContinuationToken>a&amp;b</NextContinuationToken>".as_slice(),
        b"<NextContinuationToken><![CDATA[next]]></NextContinuationToken>",
        b"<NextContinuationToken></NextContinuationToken>",
    ] {
        assert_eq!(TokenProbe::default().scan(body), ProbeState::Unresolved);
    }
    let mut probe = TokenProbe::default();
    assert_eq!(
        probe.scan(b"<Error><Code>AccessDenied</Code></Error>"),
        ProbeState::Scanning
    );
    probe.finish();
    assert_eq!(probe.state(), ProbeState::Unresolved);
}

#[test]
fn a_wrong_root_stops_with_the_crts_invalid_xml_code() {
    for (operation, body) in [
        (
            Operation::ListObjectsV2,
            b"<Error><Code>AccessDenied</Code></Error>".as_slice(),
        ),
        (Operation::ListObjectsV2, b"<html>oops</html>"),
        (Operation::ListObjectsV2, b"<html><html/>oops</html>"),
        (Operation::ListBuckets, b"<ListBucketResult/>"),
    ] {
        assert_fails_whole(body, operation, ListLocalError::UnexpectedRoot);
        assert!(!parse_page(body, operation).parsed.document_malformed());
    }
}
#[test]
fn a_document_that_does_not_parse_is_malformed_whatever_its_root() {
    for (operation, body) in [
        (Operation::ListObjectsV2, b"<html>oops".as_slice()),
        (Operation::ListObjectsV2, b"<html><html>oops</html>"),
        (Operation::ListObjectsV2, b"<?xml version=\"1.0\"?>"),
        (Operation::ListObjectsV2, b"<ListBucketResult><Contents>"),
        (
            Operation::ListObjectsV2,
            b"<ListBucketResult><Contents><Key>a</Key></Contents><Contents><Key>b",
        ),
        (Operation::ListBuckets, b"<html>oops"),
        (
            Operation::ListBuckets,
            b"<ListAllMyBucketsResult><Buckets><Bucket><Name>a</Name>",
        ),
    ] {
        let page = parse_page(body, operation);
        assert!(page.result.is_err(), "{}", body.escape_ascii());
        assert_eq!(
            page.parsed.local_error,
            Some(ListLocalError::MalformedXml),
            "{}",
            body.escape_ascii()
        );
        assert!(page.parsed.document_malformed());
        assert!(page.entries.is_empty());
    }
}
#[test]
fn botocore_retries_a_page_whose_characters_it_rejects_not_one_it_cannot_use() {
    for (field, error, malformed) in [
        (
            b"<ETag>\xff</ETag>".as_slice(),
            ListLocalError::InvalidUtf8,
            true,
        ),
        (b"<ETag>&#x1;</ETag>", ListLocalError::InvalidXmlText, true),
        (b"<Size>x</Size>", ListLocalError::InvalidNumber, false),
        (
            b"<LastModified>not-a-date</LastModified>",
            ListLocalError::CrtFailure,
            false,
        ),
    ] {
        let body = [
            b"<ListBucketResult><Contents><Key>k</Key>".as_slice(),
            field,
            b"</Contents></ListBucketResult>",
        ]
        .concat();
        let page = parse_page(&body, Operation::ListObjectsV2);
        let field = field.escape_ascii();
        assert!(page.result.is_err(), "{field}");
        assert_eq!(page.parsed.local_error, Some(error), "{field}");
        assert_eq!(page.parsed.document_malformed(), malformed, "{field}");
        assert!(page.entries.is_empty(), "{field}");
    }
}
