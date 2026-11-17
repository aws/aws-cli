use super::*;
use std::path::Path;

const TEST_ALGORITHM_OBJECT: [u8; 10] =
    [0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x04, 0x03, 0x02];
const TEST_ALGORITHM: [u8; 12] = [
    0x30, 0x0a, 0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x04, 0x03, 0x02,
];
const TEST_BITS: [u8; 3] = [0x03, 0x01, 0x00];

fn expect_holds(expected: bool, bytes: &[u8]) {
    assert_eq!(
        holds_only_certificates(bytes),
        expected,
        "{}",
        bytes.escape_ascii()
    );
}

fn test_certificate_body() -> &'static str {
    let pem = TEST_CERTIFICATE_PEM;
    &pem[BEGIN.len() + 1..pem.len() - END.len() - 1]
}

fn test_base64(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut text = String::new();
    for chunk in bytes.chunks(3) {
        let mut group = [0; 4];
        group[1..=chunk.len()].copy_from_slice(chunk);
        let bits = u32::from_be_bytes(group);
        for index in 0..4 {
            let symbol = ALPHABET[((bits >> (18 - 6 * index)) & 0x3f) as usize];
            text.push(if index <= chunk.len() {
                char::from(symbol)
            } else {
                '='
            });
        }
    }
    text
}

fn test_pem_from_der(der: &[u8]) -> Vec<u8> {
    format!("{BEGIN}\n{}\n{END}\n", test_base64(der)).into_bytes()
}

fn test_certificate_der() -> Vec<u8> {
    let mut body = Body::default();
    for line in test_certificate_body().lines() {
        assert!(body.append(line.as_bytes()), "{line}");
    }
    body.finish().map(<[u8]>::to_vec).unwrap_or_default()
}

fn test_signed_fields(der: &[u8]) -> Option<[&[u8]; 8]> {
    let certificate = Element::parse(der)?;
    let signed = Element::parse(certificate.content)?;
    let mut fields: [&[u8]; 8] = [&[]; 8];
    let mut rest = signed.content;
    for field in &mut fields {
        let element = Element::parse(rest)?;
        *field = &rest[..rest.len() - element.rest.len()];
        rest = element.rest;
    }
    rest.is_empty().then_some(fields)
}

fn test_pem_from_fields(signed: &[&[u8]], algorithm: &[u8]) -> Vec<u8> {
    let signed = test_element(Identifier::SEQUENCE, signed);
    let der = test_element(Identifier::SEQUENCE, &[&signed, algorithm, &TEST_BITS]);
    test_pem_from_der(&der)
}

fn test_element(identifier: Identifier, parts: &[&[u8]]) -> Vec<u8> {
    let content = parts.concat();
    let length = u16::try_from(content.len());
    assert!(length.is_ok(), "{} content octets", content.len());
    let [high, low] = length.unwrap_or_default().to_be_bytes();
    let mut element = vec![identifier.0];
    match (high, low) {
        (0, 0..0x80) => element.push(low),
        (0, _) => element.extend([0x81, low]),
        _ => element.extend([0x82, high, low]),
    }
    element.extend(content);
    element
}

fn test_algorithm(identifier: &[u8]) -> Vec<u8> {
    let object = test_element(Identifier::OBJECT_IDENTIFIER, &[identifier]);
    test_element(Identifier::SEQUENCE, &[&object])
}

fn test_name(identifier: u8, value: &[u8]) -> Vec<u8> {
    let common_name = [0x06, 0x03, 0x55, 0x04, 0x03];
    let value = test_element(Identifier(identifier), &[value]);
    let attribute = test_element(Identifier::SEQUENCE, &[&common_name, &value]);
    let relative = test_element(Identifier::SET, &[&attribute]);
    test_element(Identifier::SEQUENCE, &[&relative])
}

fn test_nested_algorithm(depth: usize) -> Vec<u8> {
    assert!(depth >= 1);
    let mut parameters = test_element(Identifier::SEQUENCE, &[]);
    for _ in 1..depth {
        parameters = test_element(Identifier::SEQUENCE, &[&parameters]);
    }
    test_element(Identifier::SEQUENCE, &[&TEST_ALGORITHM_OBJECT, &parameters])
}

#[test]
fn certificates_and_the_text_between_them_hold_only_certificates() {
    let certificate = TEST_CERTIFICATE_PEM;
    expect_holds(true, certificate.as_bytes());
    let certifi = format!("# Issuer: CN=one\n\n{certificate}\n# Issuer: CN=two\n{certificate}");
    expect_holds(true, certifi.as_bytes());
    expect_holds(true, &certificate.as_bytes()[..certificate.len() - 1]);
    expect_holds(true, certificate.replace('\n', "\r\n").as_bytes());
}

#[test]
fn botocore_s_bundle_holds_only_certificates() -> std::io::Result<()> {
    let path =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../aws-cli/awscli/botocore/cacert.pem");
    expect_holds(true, &std::fs::read(path)?);
    Ok(())
}

#[test]
fn a_bundle_without_certificates_or_with_another_block_is_not_plain() {
    let certificate = TEST_CERTIFICATE_PEM;
    let body = test_certificate_body();
    let relabel = |label: &str| format!("-----BEGIN {label}-----\n{body}-----END {label}-----\n");
    for bundle in [
        String::new(),
        "not a certificate\n".to_owned(),
        TEST_KEY_PEM.to_owned(),
        format!("{certificate}{TEST_KEY_PEM}"),
        format!("{TEST_KEY_PEM}{certificate}"),
        relabel("TRUSTED CERTIFICATE"),
        relabel("X509 CERTIFICATE"),
        format!("{certificate}{}", relabel("X509 CRL")),
        format!("{BEGIN}\n{body}"),
        format!("# {BEGIN}\n{certificate}"),
        format!("{certificate}{END}\n"),
        format!("{BEGIN} \n{body}{END}\n"),
    ] {
        expect_holds(false, bundle.as_bytes());
    }
}

#[test]
fn a_certificate_block_whose_body_is_no_certificate_is_not_plain() {
    let body = test_certificate_body();
    let first_line_end = body.find('\n').map_or(0, |at| at + 1);
    let blank_first = format!("\n{body}");
    for case in [
        "",
        "not a certificate\n",
        "AAAA\n",
        &blank_first,
        "QQ==QQ==\n",
        "QR==\n",
        "QQ\n",
        &body[first_line_end..],
    ] {
        expect_holds(false, format!("{BEGIN}\n{case}{END}\n").as_bytes());
    }
}

#[test]
fn der_laid_out_as_a_certificate_only_outside_is_not_plain() {
    let outside = [
        0x30, 0x0b, 0x30, 0x04, 0x30, 0x02, 0x02, 0x00, 0x30, 0x00, 0x03, 0x01, 0x00,
    ];
    expect_holds(false, &test_pem_from_der(&outside));
}

const VERSION: usize = 0;
const SERIAL: usize = 1;
const SIGNATURE: usize = 2;
const ISSUER: usize = 3;
const VALIDITY: usize = 4;
const SUBJECT: usize = 5;
const KEY: usize = 6;
const EXTENSIONS: usize = 7;

#[test]
fn der_is_a_certificate_only_when_laid_out_as_openssl_decodes_one() -> Result<(), &'static str> {
    let der = test_certificate_der();
    let fields = test_signed_fields(&der).ok_or("the test certificate's fields")?;
    expect_holds(true, &test_pem_from_fields(&fields, &TEST_ALGORITHM));
    let v1 = [SERIAL, SIGNATURE, ISSUER, VALIDITY, SUBJECT, KEY].map(|index| fields[index]);
    expect_holds(true, &test_pem_from_fields(&v1, &TEST_ALGORITHM));
    let rsa = [
        0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x0b, 0x05, 0x00,
    ];
    expect_holds(true, &test_pem_from_fields(&fields, &rsa));
    let unique_identifier = [0x81, 0x01, 0x00];
    let mut unique = fields.to_vec();
    unique.insert(EXTENSIONS, &unique_identifier);
    expect_holds(false, &test_pem_from_fields(&unique, &TEST_ALGORITHM));
    for (field, bytes) in field_replacements() {
        let mut replaced = fields;
        replaced[field] = &bytes;
        expect_holds(false, &test_pem_from_fields(&replaced, &TEST_ALGORITHM));
    }
    Ok(())
}

fn field_replacements() -> Vec<(usize, Vec<u8>)> {
    let mut short_time = vec![0x17, 12];
    short_time.extend_from_slice(b"260926200931");
    vec![
        (VERSION, vec![0xa0, 0x02, 0x05, 0x00]),
        (SERIAL, vec![0x02, 0x02, 0x00, 0x01]),
        (SIGNATURE, vec![0x30, 0x03, 0x06, 0x01, 0x81]),
        (ISSUER, test_name(0x1a, b"ca")),
        (ISSUER, test_name(0x0c, b"\xff")),
        (
            VALIDITY,
            test_element(Identifier::SEQUENCE, &[&short_time, &short_time]),
        ),
        (
            KEY,
            vec![
                0x30, 0x0e, 0x30, 0x09, 0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, 0x03,
                0x01, 0x08,
            ],
        ),
        (
            EXTENSIONS,
            vec![
                0xa3, 0x0f, 0x30, 0x0d, 0x30, 0x0b, 0x06, 0x03, 0x55, 0x1d, 0x13, 0x01, 0x02, 0xff,
                0xff, 0x04, 0x00,
            ],
        ),
        (ISSUER, test_name(0x1e, b"\x00c")),
        (ISSUER, vec![0x30, 0x02, 0x31, 0x00]),
        (
            SIGNATURE,
            vec![0x30, 0x06, 0x06, 0x01, 0x2a, 0x01, 0x01, 0xff],
        ),
        (EXTENSIONS, vec![0xa3, 0x02, 0x30, 0x00]),
    ]
}

#[test]
fn a_key_s_algorithm_is_a_certificate_s_only_as_long_as_openssl_converts_one()
-> Result<(), &'static str> {
    let der = test_certificate_der();
    let fields = test_signed_fields(&der).ok_or("the test certificate's fields")?;
    let mut identifier = vec![0x01; OBJECT_IDENTIFIER_TEXT_BYTES_MAX + 1];
    identifier[0] = 0x2a;
    let longest = &identifier[..OBJECT_IDENTIFIER_TEXT_BYTES_MAX];
    for (expected, object) in [(true, longest), (false, &identifier[..])] {
        let key = test_element(Identifier::SEQUENCE, &[&test_algorithm(object), &TEST_BITS]);
        let mut replaced = fields;
        replaced[KEY] = &key;
        expect_holds(expected, &test_pem_from_fields(&replaced, &TEST_ALGORITHM));
    }
    let signature = test_algorithm(&identifier);
    let mut replaced = fields;
    replaced[SIGNATURE] = &signature;
    expect_holds(true, &test_pem_from_fields(&replaced, &TEST_ALGORITHM));
    Ok(())
}

#[test]
fn der_is_a_certificate_only_when_its_every_element_is_whole() -> Result<(), &'static str> {
    let certificate = test_certificate_der();
    let trailing = [&certificate[..], &[0x05, 0x00]].concat();
    expect_holds(false, &test_pem_from_der(&trailing));
    let mut indefinite = certificate.clone();
    indefinite[1] = 0x80;
    expect_holds(false, &test_pem_from_der(&indefinite));
    let fields = test_signed_fields(&certificate).ok_or("the test certificate's fields")?;
    let deepest = test_nested_algorithm(DER_DEPTH_MAX);
    expect_holds(true, &test_pem_from_fields(&fields, &deepest));
    let deeper = test_nested_algorithm(DER_DEPTH_MAX + 1);
    expect_holds(false, &test_pem_from_fields(&fields, &deeper));
    Ok(())
}

#[test]
fn a_certificate_past_der_bytes_max_is_not_plain() {
    let body = "A".repeat((DER_BYTES_MAX / 3 + 1) * 4);
    let lines = body.as_bytes().chunks(64).map(String::from_utf8_lossy);
    let bundle = format!("{BEGIN}\n{}\n{END}\n", lines.collect::<Vec<_>>().join("\n"));
    expect_holds(false, bundle.as_bytes());
}

#[test]
fn a_line_longer_than_the_reader_s_buffer_is_not_plain() {
    let certificate = TEST_CERTIFICATE_PEM;
    let comment = |len| format!("{}\n{certificate}", "#".repeat(len));
    expect_holds(true, comment(LINE_BUFFER_BYTES - 1).as_bytes());
    expect_holds(false, comment(LINE_BUFFER_BYTES).as_bytes());
    let last = format!("{certificate}{}", "#".repeat(LINE_BUFFER_BYTES));
    expect_holds(true, last.as_bytes());
    expect_holds(false, format!("{last}#").as_bytes());
}
