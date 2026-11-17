//! Reads an S3 error response body the way botocore's REST-XML parser does.
//! botocore hands the body to expat as UTF-8, whatever its declaration says,
//! and when expat rejects the document it reports the HTTP status instead of
//! the body's code and message. The CRT's XML parser cannot make that call:
//! it rejects legal syntax, such as whitespace before an end tag's `>`, and
//! accepts documents expat rejects, such as a mismatched end tag.
//!
//! [`read`] accepts the documents expat accepts and finds the `<Code>` and
//! `<Message>` children of an `<Error>` root; [`Field::text`] decodes one as
//! ElementTree's `text` reads it. Recorded gaps, none of which S3 sends: a
//! reference to an entity a document type declares, or nesting deeper than
//! `DEPTH_MAX`, is rejected though expat accepts it; and a non-ASCII name
//! character, a namespace prefix, a duplicate attribute, or an XML or
//! document type declaration that expat rejects is accepted.

const DEPTH_MAX: usize = 256;

const CDATA_OPEN: &[u8] = b"<![CDATA[";
const CDATA_CLOSE: &[u8] = b"]]>";
const COMMENT_OPEN: &[u8] = b"<!--";
const COMMENT_CLOSE: &[u8] = b"-->";
const DOCTYPE_OPEN: &[u8] = b"<!DOCTYPE";
const PI_OPEN: &[u8] = b"<?";
const PI_CLOSE: &[u8] = b"?>";

/// The raw content of one of the root's children, borrowed from the body.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Field<'a> {
    content: &'a [u8],
}
impl Field<'_> {
    /// The field as ElementTree's `text` reads it: the character data before
    /// the first child element, with references decoded, CDATA read
    /// literally, comments and processing instructions dropped, and line ends
    /// normalized to LF.
    pub fn text(self) -> Vec<u8> {
        let mut out = Vec::with_capacity(self.content.len());
        let mut rest = self.content;
        while let Some(after) = write_construct(rest, &mut out) {
            rest = after;
        }
        out
    }
}
fn write_construct<'a>(rest: &'a [u8], out: &mut Vec<u8>) -> Option<&'a [u8]> {
    match rest.first()? {
        b'&' => {
            let reference = parse_reference(rest)?;
            let mut bytes = [0; 4];
            out.extend_from_slice(reference.character.encode_utf8(&mut bytes).as_bytes());
            rest.get(reference.len..)
        }
        b'<' => write_markup(rest, out),
        _ => {
            let end = text_end(rest);
            push_normalizing_line_ends(out, &rest[..end]);
            Some(&rest[end..])
        }
    }
}
fn write_markup<'a>(rest: &'a [u8], out: &mut Vec<u8>) -> Option<&'a [u8]> {
    if let Some(section) = rest.strip_prefix(CDATA_OPEN) {
        let (literal, after) = split_at_close(section, CDATA_CLOSE)?;
        push_normalizing_line_ends(out, literal);
        Some(after)
    } else if let Some(comment) = rest.strip_prefix(COMMENT_OPEN) {
        split_at_close(comment, COMMENT_CLOSE).map(|(_, after)| after)
    } else if rest.starts_with(PI_OPEN) {
        split_at_close(rest, PI_CLOSE).map(|(_, after)| after)
    } else {
        None
    }
}
/// The fields an `<Error>` root's children carry; a child that appears more
/// than once is read from its last occurrence.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Fields<'a> {
    /// The `<Code>` child, `None` when the root has none or is not `<Error>`.
    pub code: Option<Field<'a>>,
    /// The `<Message>` child, `None` when the root has none or is not
    /// `<Error>`.
    pub message: Option<Field<'a>>,
}
/// The fields of `body`, or `None` when expat would reject it: when it is not
/// UTF-8, holds a character XML 1.0 does not allow, or is not a well-formed
/// document.
pub fn read(body: &[u8]) -> Option<Fields<'_>> {
    let text = std::str::from_utf8(body).ok()?;
    if !text.chars().all(is_char) {
        return None;
    }
    Reader { doc: body, pos: 0 }.document().ok()
}
/// Testing only: reads `bytes` both as a body and inside an `<Error>` root,
/// then decodes any fields [`read`] accepts, which must be UTF-8. The fuzz
/// target and the corpus replay run it.
#[cfg(any(test, feature = "testing"))]
pub fn fuzz_read(bytes: &[u8]) {
    let mut wrapped = b"<Error>".to_vec();
    wrapped.extend_from_slice(bytes);
    wrapped.extend_from_slice(b"</Error>");
    for body in [bytes, wrapped.as_slice()] {
        let Some(fields) = read(body) else {
            continue;
        };
        for field in [fields.code, fields.message].into_iter().flatten() {
            assert!(std::str::from_utf8(&field.text()).is_ok());
        }
    }
}
#[derive(Debug)]
struct NotWellFormed;

type Checked<T> = Result<T, NotWellFormed>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Place {
    Prolog,
    Epilog,
}
#[derive(Debug, Clone, Copy)]
struct Tag<'a> {
    name: &'a [u8],
    empty: bool,
}
#[derive(Debug)]
struct Reader<'a> {
    doc: &'a [u8],
    pos: usize,
}
impl<'a> Reader<'a> {
    fn document(&mut self) -> Checked<Fields<'a>> {
        self.consume(b"\xef\xbb\xbf");
        // Only the XML declaration may start with the reserved target.
        if self.starts_with(b"<?xml") && self.doc.get(self.pos + 5).is_some_and(|b| is_space(*b)) {
            self.skip_past(PI_CLOSE)?;
        }
        self.misc(Place::Prolog)?;
        if !self.starts_with(b"<") {
            return Err(NotWellFormed);
        }
        let fields = self.element()?;
        self.misc(Place::Epilog)?;
        if self.pos != self.doc.len() {
            return Err(NotWellFormed);
        }
        Ok(fields)
    }
    fn misc(&mut self, place: Place) -> Checked<()> {
        let mut doctype_seen = false;
        while self.pos < self.doc.len() {
            if self.skip_space() {
                continue;
            }
            if self.starts_with(COMMENT_OPEN) {
                self.comment()?;
            } else if self.starts_with(PI_OPEN) {
                self.processing_instruction()?;
            } else if place == Place::Prolog && !doctype_seen && self.starts_with(DOCTYPE_OPEN) {
                self.doctype()?;
                doctype_seen = true;
            } else {
                return Ok(());
            }
        }
        Ok(())
    }
    fn element(&mut self) -> Checked<Fields<'a>> {
        let root = self.start_tag()?;
        if root.empty {
            return Ok(Fields::default());
        }
        let mut tree = Tree::new(root.name == b"Error");
        tree.open(root, self.pos)?;
        while self.pos < self.doc.len() {
            if self.content_item(&mut tree)? {
                return Ok(tree.fields);
            }
        }
        Err(NotWellFormed)
    }
    fn content_item(&mut self, tree: &mut Tree<'a>) -> Checked<bool> {
        if self.starts_with(b"&") {
            self.reference()?;
        } else if !self.starts_with(b"<") {
            self.char_data()?;
        } else if self.starts_with(COMMENT_OPEN) {
            self.comment()?;
        } else if self.starts_with(PI_OPEN) {
            self.processing_instruction()?;
        } else if self.starts_with(CDATA_OPEN) {
            self.pos += CDATA_OPEN.len();
            self.skip_past(CDATA_CLOSE)?;
        } else if self.starts_with(b"</") {
            let content_end = self.pos;
            let name = self.end_tag()?;
            tree.close(name, self.doc, content_end)?;
            return Ok(tree.names.is_empty());
        } else {
            let tag = self.start_tag()?;
            tree.open(tag, self.pos)?;
        }
        Ok(false)
    }
    fn start_tag(&mut self) -> Checked<Tag<'a>> {
        debug_assert!(self.starts_with(b"<"));
        self.pos += 1;
        let name = self.name()?;
        while self.pos < self.doc.len() {
            let spaced = self.skip_space();
            if self.consume(b"/>") {
                return Ok(Tag { name, empty: true });
            }
            if self.consume(b">") {
                return Ok(Tag { name, empty: false });
            }
            if !spaced {
                return Err(NotWellFormed);
            }
            self.attribute()?;
        }
        Err(NotWellFormed)
    }
    fn attribute(&mut self) -> Checked<()> {
        self.name()?;
        self.skip_space();
        if !self.consume(b"=") {
            return Err(NotWellFormed);
        }
        self.skip_space();
        let Some(&quote @ (b'"' | b'\'')) = self.doc.get(self.pos) else {
            return Err(NotWellFormed);
        };
        self.pos += 1;
        while let Some(&byte) = self.doc.get(self.pos) {
            match byte {
                b'<' => return Err(NotWellFormed),
                b'&' => self.reference()?,
                _ => {
                    self.pos += 1;
                    if byte == quote {
                        return Ok(());
                    }
                }
            }
        }
        Err(NotWellFormed)
    }
    fn end_tag(&mut self) -> Checked<&'a [u8]> {
        self.pos += b"</".len();
        let name = self.name()?;
        self.skip_space();
        if !self.consume(b">") {
            return Err(NotWellFormed);
        }
        Ok(name)
    }
    fn char_data(&mut self) -> Checked<()> {
        let rest = &self.doc[self.pos..];
        let end = text_end(rest);
        if find(&rest[..end], CDATA_CLOSE).is_some() {
            return Err(NotWellFormed);
        }
        self.pos += end;
        Ok(())
    }
    fn reference(&mut self) -> Checked<()> {
        let parsed = parse_reference(&self.doc[self.pos..]).ok_or(NotWellFormed)?;
        self.pos += parsed.len;
        Ok(())
    }
    fn comment(&mut self) -> Checked<()> {
        self.pos += COMMENT_OPEN.len();
        let dashes = find(&self.doc[self.pos..], b"--").ok_or(NotWellFormed)?;
        self.pos += dashes;
        if !self.consume(COMMENT_CLOSE) {
            return Err(NotWellFormed);
        }
        Ok(())
    }
    fn processing_instruction(&mut self) -> Checked<()> {
        self.pos += PI_OPEN.len();
        if self.name()?.eq_ignore_ascii_case(b"xml") {
            return Err(NotWellFormed);
        }
        if self.consume(PI_CLOSE) {
            return Ok(());
        }
        if !self.skip_space() {
            return Err(NotWellFormed);
        }
        self.skip_past(PI_CLOSE)
    }
    fn doctype(&mut self) -> Checked<()> {
        self.pos += DOCTYPE_OPEN.len();
        if !self.skip_space() {
            return Err(NotWellFormed);
        }
        let mut subset = false;
        while let Some(&byte) = self.doc.get(self.pos) {
            if byte == b'"' || byte == b'\'' {
                self.quoted()?;
            } else if subset {
                subset = self.subset_item()?;
            } else {
                self.pos += 1;
                match byte {
                    b'[' => subset = true,
                    b'>' => return Ok(()),
                    _ => {}
                }
            }
        }
        Err(NotWellFormed)
    }
    fn subset_item(&mut self) -> Checked<bool> {
        if self.starts_with(COMMENT_OPEN) {
            self.comment()?;
        } else if self.starts_with(PI_OPEN) {
            self.skip_past(PI_CLOSE)?;
        } else {
            self.pos += 1;
            return Ok(self.doc[self.pos - 1] != b']');
        }
        Ok(true)
    }
    fn quoted(&mut self) -> Checked<()> {
        let quote = [self.doc[self.pos]];
        self.pos += 1;
        self.skip_past(&quote)
    }
    fn name(&mut self) -> Checked<&'a [u8]> {
        let start = self.pos;
        if !self.doc.get(self.pos).is_some_and(|b| is_name_start(*b)) {
            return Err(NotWellFormed);
        }
        self.pos += 1;
        while self.doc.get(self.pos).is_some_and(|b| is_name_byte(*b)) {
            self.pos += 1;
        }
        Ok(&self.doc[start..self.pos])
    }
    fn skip_past(&mut self, delimiter: &[u8]) -> Checked<()> {
        let found = find(&self.doc[self.pos..], delimiter).ok_or(NotWellFormed)?;
        self.pos += found + delimiter.len();
        Ok(())
    }
    fn skip_space(&mut self) -> bool {
        let start = self.pos;
        while self.doc.get(self.pos).is_some_and(|b| is_space(*b)) {
            self.pos += 1;
        }
        self.pos != start
    }
    fn consume(&mut self, text: &[u8]) -> bool {
        if !self.starts_with(text) {
            return false;
        }
        self.pos += text.len();
        true
    }
    fn starts_with(&self, text: &[u8]) -> bool {
        self.doc[self.pos..].starts_with(text)
    }
}
#[derive(Debug)]
struct Tree<'a> {
    error_root: bool,
    names: Vec<&'a [u8]>,
    fields: Fields<'a>,
    field: Option<FieldName>,
    field_start: usize,
}
impl<'a> Tree<'a> {
    fn new(error_root: bool) -> Self {
        Self {
            error_root,
            names: Vec::new(),
            fields: Fields::default(),
            field: None,
            field_start: 0,
        }
    }
    fn open(&mut self, tag: Tag<'a>, content_start: usize) -> Checked<()> {
        let field = if self.error_root && self.names.len() == 1 {
            FieldName::of(tag.name)
        } else {
            None
        };
        if tag.empty {
            if let Some(name) = field {
                self.record(name, b"");
            }
            return Ok(());
        }
        if self.names.len() == DEPTH_MAX {
            return Err(NotWellFormed);
        }
        if self.names.len() == 1 {
            self.field = field;
            self.field_start = content_start;
        }
        self.names.push(tag.name);
        Ok(())
    }
    fn close(&mut self, name: &[u8], doc: &'a [u8], content_end: usize) -> Checked<()> {
        if self.names.pop() != Some(name) {
            return Err(NotWellFormed);
        }
        if self.names.len() != 1 {
            return Ok(());
        }
        if let Some(field) = self.field.take() {
            self.record(field, &doc[self.field_start..content_end]);
        }
        Ok(())
    }
    fn record(&mut self, name: FieldName, content: &'a [u8]) {
        let field = Some(Field { content });
        match name {
            FieldName::Code => self.fields.code = field,
            FieldName::Message => self.fields.message = field,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FieldName {
    Code,
    Message,
}
impl FieldName {
    fn of(name: &[u8]) -> Option<Self> {
        match name {
            b"Code" => Some(Self::Code),
            b"Message" => Some(Self::Message),
            _ => None,
        }
    }
}
#[derive(Debug, Clone, Copy)]
struct Reference {
    len: usize,
    character: char,
}
fn parse_reference(text: &[u8]) -> Option<Reference> {
    debug_assert_eq!(text.first(), Some(&b'&'));
    let end = text.iter().position(|byte| *byte == b';')?;
    let body = &text[1..end];
    let character = match body.strip_prefix(b"#") {
        Some(digits) => character_reference(digits)?,
        None => predefined_entity(body)?,
    };
    Some(Reference {
        len: end + 1,
        character,
    })
}
fn predefined_entity(name: &[u8]) -> Option<char> {
    match name {
        b"lt" => Some('<'),
        b"gt" => Some('>'),
        b"amp" => Some('&'),
        b"apos" => Some('\''),
        b"quot" => Some('"'),
        _ => None,
    }
}
fn character_reference(digits: &[u8]) -> Option<char> {
    let (number, radix) = match digits.strip_prefix(b"x") {
        Some(hex) => (hex, 16),
        None => (digits, 10),
    };
    if number.is_empty() {
        return None;
    }
    let mut value: u32 = 0;
    for digit in number {
        value = value
            .checked_mul(radix)?
            .checked_add(char::from(*digit).to_digit(radix)?)?;
    }
    char::from_u32(value).filter(|character| is_char(*character))
}
fn is_char(character: char) -> bool {
    matches!(
        character,
        '\t' | '\n' | '\r' | '\u{20}'..='\u{FFFD}' | '\u{10000}'..='\u{10FFFF}'
    )
}
fn is_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\r' | b'\n')
}
fn is_name_start(byte: u8) -> bool {
    byte.is_ascii_alphabetic() || byte == b'_' || byte == b':' || byte >= 0x80
}
fn is_name_byte(byte: u8) -> bool {
    is_name_start(byte) || byte.is_ascii_digit() || byte == b'-' || byte == b'.'
}
fn text_end(text: &[u8]) -> usize {
    text.iter()
        .position(|byte| matches!(byte, b'<' | b'&'))
        .unwrap_or(text.len())
}
fn push_normalizing_line_ends(out: &mut Vec<u8>, text: &[u8]) {
    let mut rest = text;
    while let Some(cr) = rest.iter().position(|byte| *byte == b'\r') {
        out.extend_from_slice(&rest[..cr]);
        out.push(b'\n');
        rest = &rest[cr + 1..];
        if let Some(after) = rest.strip_prefix(b"\n") {
            rest = after;
        }
    }
    out.extend_from_slice(rest);
}
fn split_at_close<'a>(text: &'a [u8], close: &[u8]) -> Option<(&'a [u8], &'a [u8])> {
    let end = find(text, close)?;
    Some((&text[..end], &text[end + close.len()..]))
}
fn find(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}
#[cfg(test)]
mod tests;
