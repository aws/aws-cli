//! Whether a CA bundle holds nothing but certificates, the one kind of bundle
//! the CRT's trust store and upstream's read alike. Upstream's botocore client
//! hands the bundle to OpenSSL (`load_verify_locations`, through urllib3),
//! whose reader (`X509_load_cert_crl_file_ex`) takes a certificate under any
//! of its labels, adds CRLs, skips other objects, and fails only on a block
//! it cannot decode or a file with no certificate or CRL. The CRT is
//! stricter: aws-c-io keeps the file's PEM blocks (`aws_sanitize_pem`), then
//! s2n adds each to its store as a `CERTIFICATE` that `d2i_X509` decodes
//! (`s2n_x509_trust_store_add_pem`), and the Darwin and Windows backends
//! import every block as a certificate; any other block fails the client's TLS
//! context before a request. So a bundle that also holds a key, or labels a
//! certificate `TRUSTED CERTIFICATE`, loads upstream and fails natively, and a
//! bundle neither loads fails with a different error in each, or natively
//! alone over HTTP, where upstream never loads it.
//!
//! The recognizer accepts only what both read the same way: each block framed
//! exactly as OpenSSL writes a certificate, a body in strict base64, and DER
//! that `d2i_X509`, the decoder s2n and OpenSSL's reader both call, decodes.
//! That DER is laid out as RFC 5280 lays out a certificate (section 4.1) and
//! OpenSSL's templates decode one, each value as OpenSSL's decoder reads it.
//! A form those templates decode but CAs do not issue, such as a name in a
//! BMPString, is the fallback's. Text between blocks is
//! skipped, as both readers skip it, unless it holds a run of five dashes,
//! which either reader could take for a marker.
use std::io::{BufRead, Read};

const BEGIN: &str = "-----BEGIN CERTIFICATE-----";
const END: &str = "-----END CERTIFICATE-----";
const DASHES: &str = "-----";
const DER_BYTES_MAX: usize = 16 * 1024;
const DER_LENGTH_BYTES_MAX: usize = 2;
/// The octets of an object identifier OpenSSL converts to text: 128
/// subidentifiers of 32 bits, the most RFC 2578 allows.
const OBJECT_IDENTIFIER_TEXT_BYTES_MAX: usize = 586;
/// How deep an algorithm's parameters may nest, counting their own SEQUENCE.
/// OpenSSL keeps them encoded, so the bound only keeps
/// their walk shallow; it is OpenSSL's bound on what it decodes
/// (`ASN1_MAX_CONSTRUCTED_NEST`), past the four levels of
/// RSA-PSS parameters.
const DER_DEPTH_MAX: usize = 30;
pub(super) const LINE_BUFFER_BYTES: usize = 4096;
const LINE_COUNT_MAX: usize = 1 << 20;
const _: () = {
    assert!(DER_BYTES_MAX < 1 << (8 * DER_LENGTH_BYTES_MAX));
    assert!(LINE_BUFFER_BYTES > END.len());
};

pub(super) fn holds_only_certificates(mut reader: impl BufRead) -> bool {
    const READ_LIMIT: u64 = LINE_BUFFER_BYTES as u64 + 1;
    let mut bundle = Bundle::default();
    let mut line = Vec::with_capacity(LINE_BUFFER_BYTES + 1);
    for _ in 0..LINE_COUNT_MAX {
        line.clear();
        let Ok(read) = reader
            .by_ref()
            .take(READ_LIMIT)
            .read_until(b'\n', &mut line)
        else {
            return false;
        };
        if read == 0 {
            return bundle.finish();
        }
        if line.len() > LINE_BUFFER_BYTES {
            return false;
        }
        let text = line.strip_suffix(b"\n").unwrap_or(&line);
        // OpenSSL ends a line at its carriage return and s2n skips it as
        // whitespace, so a CRLF bundle reads as an LF one.
        let text = text.strip_suffix(b"\r").unwrap_or(text);
        if !bundle.read(text) {
            return false;
        }
    }
    false
}

#[derive(Default)]
struct Bundle {
    body: Body,
    in_block: bool,
    certificates: usize,
}
impl Bundle {
    fn read(&mut self, line: &[u8]) -> bool {
        if !self.in_block {
            return self.read_text(line);
        }
        if line != END.as_bytes() {
            return self.body.append(line);
        }
        let Some(der) = self.body.finish() else {
            return false;
        };
        if !is_certificate(der) {
            return false;
        }
        self.certificates += 1;
        self.in_block = false;
        true
    }
    fn read_text(&mut self, line: &[u8]) -> bool {
        debug_assert!(!self.in_block);
        if line == BEGIN.as_bytes() {
            self.body.reset();
            self.in_block = true;
            return true;
        }
        !line
            .windows(DASHES.len())
            .any(|window| window == DASHES.as_bytes())
    }
    fn finish(&self) -> bool {
        !self.in_block && self.certificates > 0
    }
}

#[derive(Default)]
struct Body {
    der: Vec<u8>,
    group: [u8; 4],
    group_len: usize,
    padded: bool,
}
impl Body {
    fn reset(&mut self) {
        self.der.clear();
        self.group_len = 0;
        self.padded = false;
    }
    fn append(&mut self, line: &[u8]) -> bool {
        debug_assert!(self.group_len < self.group.len());
        if line.is_empty() {
            return false;
        }
        for &symbol in line {
            if self.padded {
                return false;
            }
            self.group[self.group_len] = symbol;
            self.group_len += 1;
            if self.group_len < self.group.len() {
                continue;
            }
            self.group_len = 0;
            let size = group_size(&self.group);
            if size > DER_BYTES_MAX - self.der.len() {
                return false;
            }
            if !decode_group(&self.group, &mut self.der) {
                return false;
            }
            self.padded = size < 3;
        }
        true
    }
    fn finish(&self) -> Option<&[u8]> {
        (self.group_len == 0).then_some(&self.der)
    }
}

fn group_size(group: &[u8; 4]) -> usize {
    3 - group[2..].iter().filter(|&&symbol| symbol == b'=').count()
}

fn decode_group(group: &[u8; 4], der: &mut Vec<u8>) -> bool {
    let size = group_size(group);
    let (symbols, padding) = group.split_at(size + 1);
    if padding.iter().any(|&symbol| symbol != b'=') {
        return false;
    }
    let mut bits = 0u32;
    for &symbol in symbols {
        let Some(value) = sextet(symbol) else {
            return false;
        };
        bits = bits << 6 | u32::from(value);
    }
    let spare = 6 * symbols.len() - 8 * size;
    if bits & ((1 << spare) - 1) != 0 {
        return false;
    }
    der.extend_from_slice(&(bits >> spare).to_be_bytes()[4 - size..]);
    true
}

fn sextet(symbol: u8) -> Option<u8> {
    match symbol {
        b'A'..=b'Z' => Some(symbol - b'A'),
        b'a'..=b'z' => Some(symbol - b'a' + 26),
        b'0'..=b'9' => Some(symbol - b'0' + 52),
        b'+' => Some(62),
        b'/' => Some(63),
        _ => None,
    }
}

fn is_certificate(der: &[u8]) -> bool {
    holds_fields(der, &[CERTIFICATE])
}

/// A certificate (X509): the to-be-signed part, then the
/// algorithm and signature that sign it.
const CERTIFICATE: Shape =
    Shape::sequence(&[SIGNED, ALGORITHM, Shape::value(&[Identifier::BIT_STRING])]);
/// The to-be-signed part (X509_CINF): a version, which a v1
/// certificate leaves out, the serial number, signature algorithm, issuer,
/// validity, subject, and public key, then the extensions. The issuer and
/// subject unique identifiers between the last two, which CAs do not issue,
/// are not part of the layout.
const SIGNED: Shape = Shape::sequence(&[
    Shape::optional(Shape::explicit(
        &Identifier::CONTEXT_0,
        &Shape::value(&[Identifier::INTEGER]),
    )),
    Shape::value(&[Identifier::INTEGER]),
    ALGORITHM,
    NAME,
    Shape::sequence(&[TIME, TIME]),
    NAME,
    Shape::sequence(&[KEY_ALGORITHM, Shape::value(&[Identifier::BIT_STRING])]),
    Shape::optional(Shape::explicit(
        &Identifier::CONTEXT_3,
        &Shape::sequence_of(&EXTENSION),
    )),
]);
/// An algorithm (X509_ALGOR) and its parameters.
const ALGORITHM: Shape =
    Shape::sequence(&[Shape::value(&[Identifier::OBJECT_IDENTIFIER]), PARAMETERS]);
/// A public key's algorithm, whose identifier OpenSSL converts to text to
/// find a decoder for a key it has none built in for, failing `d2i_X509` on
/// one too long to convert. No other identifier is
/// converted as a certificate decodes.
const KEY_ALGORITHM: Shape = Shape::sequence(&[
    Shape::bounded(
        Shape::value(&[Identifier::OBJECT_IDENTIFIER]),
        OBJECT_IDENTIFIER_TEXT_BYTES_MAX,
    ),
    PARAMETERS,
]);
const PARAMETERS: Shape = Shape::optional(Shape::value(&[
    Identifier::NULL,
    Identifier::OBJECT_IDENTIFIER,
    Identifier::SEQUENCE,
]));
/// A name (X509_NAME): relative names of attributes, each
/// value in a string type CAs issue that OpenSSL decodes a name's value as
/// (`ASN1_PRINTABLE`).
const NAME: Shape = Shape::sequence_of(&Shape::set_of(&Shape::sequence(&[
    Shape::value(&[Identifier::OBJECT_IDENTIFIER]),
    Shape::value(&[
        Identifier::UTF8_STRING,
        Identifier::PRINTABLE_STRING,
        Identifier::T61_STRING,
        Identifier::IA5_STRING,
        Identifier::NUMERIC_STRING,
    ]),
])));
/// A time (ASN1_TIME).
const TIME: Shape = Shape::value(&[Identifier::UTC_TIME, Identifier::GENERALIZED_TIME]);
/// An extension (X509_EXTENSION).
const EXTENSION: Shape = Shape::sequence(&[
    Shape::value(&[Identifier::OBJECT_IDENTIFIER]),
    Shape::optional(Shape::value(&[Identifier::BOOLEAN])),
    Shape::value(&[Identifier::OCTET_STRING]),
]);

#[derive(Clone, Copy)]
struct Shape {
    identifiers: &'static [Identifier],
    contents: Contents,
    required: bool,
    content_bytes_max: usize,
}
#[derive(Clone, Copy)]
enum Contents {
    Value,
    Fields(&'static [Shape]),
    Each(&'static Shape),
}
impl Shape {
    const fn value(identifiers: &'static [Identifier]) -> Self {
        Self {
            identifiers,
            contents: Contents::Value,
            required: true,
            content_bytes_max: DER_BYTES_MAX,
        }
    }
    const fn sequence(fields: &'static [Self]) -> Self {
        Self {
            contents: Contents::Fields(fields),
            ..Self::value(&[Identifier::SEQUENCE])
        }
    }
    const fn sequence_of(item: &'static Self) -> Self {
        Self {
            contents: Contents::Each(item),
            ..Self::value(&[Identifier::SEQUENCE])
        }
    }
    const fn set_of(item: &'static Self) -> Self {
        Self {
            contents: Contents::Each(item),
            ..Self::value(&[Identifier::SET])
        }
    }
    const fn explicit(identifier: &'static Identifier, inner: &'static Self) -> Self {
        Self {
            contents: Contents::Fields(std::slice::from_ref(inner)),
            ..Self::value(std::slice::from_ref(identifier))
        }
    }
    const fn optional(shape: Self) -> Self {
        Self {
            required: false,
            ..shape
        }
    }
    const fn bounded(shape: Self, content_bytes_max: usize) -> Self {
        Self {
            content_bytes_max,
            ..shape
        }
    }
    fn carries(&self, identifier: Identifier) -> bool {
        self.identifiers.contains(&identifier)
    }
    fn holds(&self, element: Element<'_>) -> bool {
        debug_assert!(self.carries(element.identifier));
        if element.content.len() > self.content_bytes_max {
            return false;
        }
        match self.contents {
            Contents::Value if element.identifier.constructed() => well_formed(element.content, 1),
            Contents::Value => is_value(element),
            Contents::Fields(fields) => holds_fields(element.content, fields),
            Contents::Each(item) => holds_each(element.content, item),
        }
    }
}

/// Whether `bytes` are one element of each of `fields` in turn. A field that
/// need not be held is left out where the next element carries none of its
/// identifiers, as OpenSSL's template decoder leaves it out.
fn holds_fields(bytes: &[u8], fields: &[Shape]) -> bool {
    let mut rest = bytes;
    for field in fields {
        let present = Element::parse(rest).filter(|next| field.carries(next.identifier));
        let Some(element) = present else {
            if field.required {
                return false;
            }
            continue;
        };
        if !field.holds(element) {
            return false;
        }
        rest = element.rest;
    }
    rest.is_empty()
}

fn holds_each(bytes: &[u8], item: &Shape) -> bool {
    let mut rest = bytes;
    for _ in 0..bytes.len() / 2 {
        let Some(element) = Element::parse(rest) else {
            return false;
        };
        if !item.carries(element.identifier) || !item.holds(element) {
            return false;
        }
        rest = element.rest;
        if rest.is_empty() {
            return true;
        }
    }
    false
}

fn well_formed(bytes: &[u8], depth: usize) -> bool {
    debug_assert!((1..=DER_DEPTH_MAX).contains(&depth));
    let mut rest = bytes;
    for _ in 0..bytes.len() / 2 {
        let Some(element) = Element::parse(rest) else {
            return false;
        };
        if element.identifier.constructed()
            && (depth == DER_DEPTH_MAX || !well_formed(element.content, depth + 1))
        {
            return false;
        }
        rest = element.rest;
        if rest.is_empty() {
            return true;
        }
    }
    rest.is_empty()
}

/// Whether the contents of `element`, a primitive, are a value of its
/// universal type as OpenSSL decodes one. OpenSSL copies
/// an OCTET STRING and the other strings whole.
fn is_value(element: Element<'_>) -> bool {
    debug_assert!(!element.identifier.constructed());
    let content = element.content;
    match element.identifier {
        Identifier::BOOLEAN => content.len() == 1,
        Identifier::INTEGER => is_integer(content),
        Identifier::BIT_STRING => is_bit_string(content),
        Identifier::NULL => content.is_empty(),
        Identifier::OBJECT_IDENTIFIER => is_object_identifier(content),
        // A name's UTF-8 is converted to compare names.
        Identifier::UTF8_STRING => std::str::from_utf8(content).is_ok(),
        // A time is at least its seconds and zone.
        Identifier::UTC_TIME => content.len() >= "YYMMDDHHMMSSZ".len(),
        Identifier::GENERALIZED_TIME => content.len() >= "YYYYMMDDHHMMSSZ".len(),
        _ => true,
    }
}

/// Whether `content` is an INTEGER as OpenSSL decodes one:
/// at least one octet, its first nine bits not all equal.
fn is_integer(content: &[u8]) -> bool {
    match content {
        [] => false,
        [_] => true,
        [first, second, ..] => {
            let padded = *first == 0x00 && second & 0x80 == 0;
            let padded_negative = *first == 0xff && second & 0x80 != 0;
            !padded && !padded_negative
        }
    }
}

/// Whether `content` is a BIT STRING as OpenSSL decodes one: an octet
/// counting at most seven unused bits, then the bits.
fn is_bit_string(content: &[u8]) -> bool {
    content.first().is_some_and(|&unused| unused <= 7)
}

/// Whether `content` is an object identifier as OpenSSL decodes one:
/// subidentifiers, each ending on an octet without the continuation bit and
/// none starting on the octet that adds nothing (0x80).
fn is_object_identifier(content: &[u8]) -> bool {
    let Some(last) = content.last() else {
        return false;
    };
    if last & 0x80 != 0 {
        return false;
    }
    let mut starts = true;
    for &byte in content {
        if starts && byte == 0x80 {
            return false;
        }
        starts = byte & 0x80 == 0;
    }
    true
}

#[derive(Clone, Copy, PartialEq, Eq)]
struct Identifier(u8);
impl Identifier {
    const BOOLEAN: Self = Self(0x01);
    const INTEGER: Self = Self(0x02);
    const BIT_STRING: Self = Self(0x03);
    const OCTET_STRING: Self = Self(0x04);
    const NULL: Self = Self(0x05);
    const OBJECT_IDENTIFIER: Self = Self(0x06);
    const UTF8_STRING: Self = Self(0x0c);
    const NUMERIC_STRING: Self = Self(0x12);
    const PRINTABLE_STRING: Self = Self(0x13);
    const T61_STRING: Self = Self(0x14);
    const IA5_STRING: Self = Self(0x16);
    const UTC_TIME: Self = Self(0x17);
    const GENERALIZED_TIME: Self = Self(0x18);
    const SEQUENCE: Self = Self(0x30);
    const SET: Self = Self(0x31);
    const CONTEXT_0: Self = Self(0xa0);
    const CONTEXT_3: Self = Self(0xa3);
    const CONSTRUCTED: u8 = 0x20;
    /// The tag-number bits; all set, the tag continues in more octets, which
    /// no certificate uses.
    const TAG_NUMBER: u8 = 0x1f;
    fn constructed(self) -> bool {
        self.0 & Self::CONSTRUCTED != 0
    }
}

#[derive(Clone, Copy)]
struct Element<'a> {
    identifier: Identifier,
    content: &'a [u8],
    rest: &'a [u8],
}
impl<'a> Element<'a> {
    fn parse(bytes: &'a [u8]) -> Option<Self> {
        let [identifier, first, after @ ..] = bytes else {
            return None;
        };
        if identifier & Identifier::TAG_NUMBER == Identifier::TAG_NUMBER {
            return None;
        }
        let (length, body) = if first & 0x80 == 0 {
            (usize::from(*first), after)
        } else {
            // The long form counts its length octets in the low bits; zero
            // is the indefinite length, which DER forbids.
            let length_bytes = usize::from(first & 0x7f);
            if length_bytes == 0 || length_bytes > DER_LENGTH_BYTES_MAX {
                return None;
            }
            let (octets, body) = after.split_at_checked(length_bytes)?;
            let length = octets
                .iter()
                .fold(0, |length, &byte| length << 8 | usize::from(byte));
            (length, body)
        };
        let (content, rest) = body.split_at_checked(length)?;
        Some(Self {
            identifier: Identifier(*identifier),
            content,
            rest,
        })
    }
}

#[cfg(test)]
pub(super) const TEST_CERTIFICATE_PEM: &str = "-----BEGIN CERTIFICATE-----
MIIBrTCCAVOgAwIBAgIUGyS+45aMdcm5k6I4oD56yXXBcRgwCgYIKoZIzj0EAwIw
KzEpMCcGA1UEAwwgYXdzLWNsaS1uYXRpdmUgdGVzdCB0cnVzdCBhbmNob3IwIBcN
MjYwOTI2MjAwOTMxWhgPMjEyNjA5MDIyMDA5MzFaMCsxKTAnBgNVBAMMIGF3cy1j
bGktbmF0aXZlIHRlc3QgdHJ1c3QgYW5jaG9yMFkwEwYHKoZIzj0CAQYIKoZIzj0D
AQcDQgAE+rhKZyZT/PHMlVhRN2uT62dqWRVpZ0CbwgkgtTXA5z/rkjkKntt5ORRz
LC1HdP7a1uK4CpiioVt2eXliPgddSqNTMFEwHQYDVR0OBBYEFIb7DPiRbC8VzcJp
z7HO4ebzKlf8MB8GA1UdIwQYMBaAFIb7DPiRbC8VzcJpz7HO4ebzKlf8MA8GA1Ud
EwEB/wQFMAMBAf8wCgYIKoZIzj0EAwIDSAAwRQIgLei1GtPk8KOX+yP/lJrmRnvI
PjSCNrEQ27gApNYCu08CIQDDkSjlRY+Fi8/FF0OnsZ3D+8eF3oMpGoRRsPeYrsGm
GA==
-----END CERTIFICATE-----
";
#[cfg(test)]
pub(super) const TEST_KEY_PEM: &str =
    "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIA==\n-----END PRIVATE KEY-----\n";

#[cfg(test)]
mod tests;
