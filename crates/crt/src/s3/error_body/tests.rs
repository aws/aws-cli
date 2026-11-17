use super::*;

type Text = Option<Vec<u8>>;

fn read_text(body: &[u8]) -> Option<(Text, Text)> {
    let fields = read(body)?;
    Some((
        fields.code.map(Field::text),
        fields.message.map(Field::text),
    ))
}

#[test]
fn well_formed_documents_keep_their_code_and_message() {
    let bodies: [&[u8]; 10] = [
        b"<Error><Code>AccessDenied</Code><Message>denied</Message>\
            <RequestId>id</RequestId ></Error>",
        b"<Error><Code>AccessDenied</Code\n><Message>denied</Message\t></Error >",
        b"<Error\n><Code\r\n>AccessDenied</Code><Message\t>denied</Message></Error>",
        b"<Error a=\"x>y\" b = 'z'><Code>AccessDenied</Code><Message>denied</Message></Error>",
        b"<?xml version='1.0' encoding='UTF-8'?>\n<!-- a > b --><?pi x?>\
            <Error><Code>AccessDenied</Code><Message>denied</Message></Error>\n<!-- c --><?pi?>\n",
        b"\xef\xbb\xbf<!DOCTYPE Error [<!-- ' --><!ENTITY e \"]>\">]>\
            <Error><Code>AccessDenied</Code><Message>denied</Message></Error>",
        b"<Error><Code><![CDATA[AccessDenied]]></Code>\
            <Message>de<![CDATA[n]]>ied</Message></Error>",
        b"<Error><Code>Access<!-- & -->Denied</Code><Message>de<?pi x?>nied</Message></Error>",
        b"<Error><Code>Access&#68;enied</Code><Message>&#x64;e&#110;ied</Message>\
            <a><b><c/></b></a><Extra x='1' /></Error>",
        b"<Error><Code>Stale</Code><Code>AccessDenied</Code>\
            <Message>denied<x>child</x>!</Message></Error>",
    ];
    for body in bodies {
        let fields = read_text(body);
        assert_eq!(
            fields,
            Some((Some(b"AccessDenied".to_vec()), Some(b"denied".to_vec()))),
            "{}",
            String::from_utf8_lossy(body)
        );
    }
}

#[test]
fn text_decodes_references_reads_cdata_literally_and_normalizes_line_ends() {
    let fields = read_text(
        b"<Error><Message>&lt;&gt;&amp;&apos;&quot; &#x1F600;&#9;\r\nb\rc\
            <![CDATA[ & <x> \r\n]]>&#13;</Message><Code/></Error>",
    );
    assert_eq!(
        fields,
        Some((
            Some(Vec::new()),
            Some("<>&'\" \u{1F600}\t\nb\nc & <x> \n\r".as_bytes().to_vec())
        ))
    );
    assert_eq!(
        read_text(b"<ErrorResponse><Code>X</Code></ErrorResponse>"),
        Some((None, None))
    );
    assert_eq!(
        read_text(b"<Error><Detail><Code>X</Code></Detail></Error>"),
        Some((None, None))
    );
    assert_eq!(read_text(b"<Error/>"), Some((None, None)));
}

#[test]
fn documents_expat_rejects_have_no_fields() {
    let nested_too_deep = format!(
        "<Error>{}{}</Error>",
        "<a>".repeat(DEPTH_MAX),
        "</a>".repeat(DEPTH_MAX)
    );
    let bodies: [&[u8]; 43] = [
        b"",
        b"  \n",
        b"<Error><Code>AccessDenied</Code><Message>denied</Message>",
        b"<Error><Code>AccessDenied</Code><Message>denied</Message></Wrong>",
        b"<Error><Code>Bad\xffCode</Code></Error>",
        b"<Error><Code>AccessDenied</Code><RequestId>\xed\xa0\x80</RequestId></Error>",
        b"<Error><Message>a\x01b</Message></Error>",
        b"<Error><Message>a\xef\xbf\xbeb</Message></Error>",
        b"<Error><Message>a &nbsp; b</Message></Error>",
        b"<Error><Message>a & b</Message></Error>",
        b"<Error><Message>&lt</Message></Error>",
        b"<Error><Message>&#0;&#1;</Message></Error>",
        b"<Error><Message>&#X41;</Message></Error>",
        b"<Error><Message>&#xD800;</Message></Error>",
        b"<Error><Message>&#xFFFE;</Message></Error>",
        b"<Error><Message>&#x110000;</Message></Error>",
        b"<Error><Message>&#99999999999;</Message></Error>",
        b"<Error><Message>a]]>b</Message></Error>",
        b"<Error><Message><![CDATA[open</Message></Error>",
        b"<Error><!-- a -- b --></Error>",
        b"<Error><!-- a ---></Error>",
        b"<Error a=\"<\"/>",
        b"<Error a=b/>",
        b"<Error a=\"1\"b=\"2\"/>",
        b"<Error a=\"1/>",
        b"< Error/>",
        b"<1Error/>",
        b"<Error></Error",
        b"<Error><Code>A</Code></Error><Error/>",
        b"<Error/>junk",
        b"junk<Error/>",
        b" <?xml version='1.0'?><Error/>",
        b"<?xml?><Error/>",
        b"<?XML version='1.0'?><Error/>",
        b"<Error><?xml x?></Error>",
        b"<Error><? pi?></Error>",
        b"<Error><?pi</Error>",
        b"<!DOCTYPE Error><!DOCTYPE Error><Error/>",
        b"<Error/><!DOCTYPE Error>",
        b"<!DOCTYPEError><Error/>",
        b"<!DOCTYPE Error [<!ENTITY e 'x'>",
        b"<Error><!DOCTYPE Error></Error>",
        nested_too_deep.as_bytes(),
    ];
    for body in bodies {
        assert_eq!(read_text(body), None, "{}", String::from_utf8_lossy(body));
    }
    let nested = DEPTH_MAX - 1;
    let deepest = format!(
        "<Error>{}{}</Error>",
        "<a>".repeat(nested),
        "</a>".repeat(nested)
    );
    assert!(read_text(deepest.as_bytes()).is_some());
}

const FUZZ_CORPUS: [&[u8]; 3] = [
    b"<Code>a&amp;b<![CDATA[x]]></Code><Message>m<!--c--></Message>",
    b"<Message>&#x110000;</Message>",
    b"<Code>a</Code ><broken",
];

#[test]
fn fuzz_read_and_text_replay_the_corpus_and_a_seeded_sweep() {
    let curated = crate::testing::curated_inputs("error_body");
    for seed in FUZZ_CORPUS {
        assert!(curated.iter().any(|(_, bytes)| bytes == seed));
    }
    for (_, seed) in &curated {
        for end in 0..=seed.len() {
            fuzz_read(&seed[..end]);
        }
    }
    crate::testing::sweep(256, fuzz_read);
}
