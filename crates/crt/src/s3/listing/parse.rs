use super::request::Operation;
use super::{EntryKind, ListEntry, list_date_or_error};
use crate::crt_error::check;
use crate::s3::{
    ArchiveState, CANCELED_ERROR_CODE, FullObjectChecksum, INVALID_ARGUMENT_ERROR_CODE,
    ListLocalError,
};
use crt_sys::{self as ffi, native as c};
use std::ffi::c_void;
use std::marker::PhantomData;
use std::time::Instant;

#[derive(Debug, Default)]
pub(super) struct State {
    pub local_error: Option<ListLocalError>,
    pub next_token: Option<Vec<u8>>,
    pub has_more_results: bool,
    pub callback_error: i32,
    pub entries_emitted: u64,
    pub on_entry_ns: u64,
    pub object_conditions: bool,
}
impl State {
    pub(super) fn document_malformed(&self) -> bool {
        matches!(
            self.local_error,
            Some(
                ListLocalError::InvalidUtf8
                    | ListLocalError::InvalidXmlText
                    | ListLocalError::MalformedXml
            )
        )
    }
}
/// The CRT error codes the listing raises for its own failures, by the
/// shim's `zaws_listing_error` selector, which pins each constant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub(super) enum ListingError {
    InvalidXml = 0,
    ExceedsMemoryLimit = 2,
}
impl ListingError {
    pub(super) fn code(self) -> i32 {
        // SAFETY: translates the selector to a pinned CRT error constant.
        unsafe { c::zaws_listing_error(self as u32) }
    }
}
pub(super) fn parse_page(
    body: &[u8],
    operation: Operation,
    state: &mut State,
    callback: &mut dyn FnMut(ListEntry) -> i32,
) -> Result<(), i32> {
    if body.is_empty() {
        return Ok(());
    }
    check_body(body, state)?;
    let mut root = |node: Node<'_>| {
        let expected = if operation == Operation::ListObjectsV2 {
            b"ListBucketResult".as_slice()
        } else {
            b"ListAllMyBucketsResult"
        };
        if !node.name_is(expected) {
            return unexpected_root(&node, state);
        }
        let mut page = Page::default();
        node.children(&mut |child| {
            if operation == Operation::ListObjectsV2 {
                object_child(child, state, &mut page)
            } else {
                bucket_child(child, state, &mut page)
            }
        })?;
        page.emit(state, callback)
    };
    parse_document(body, &mut root).inspect_err(|_| {
        if state.callback_error == 0 {
            state
                .local_error
                .get_or_insert(ListLocalError::MalformedXml);
        }
    })
}
fn unexpected_root(node: &Node<'_>, state: &mut State) -> Result<(), i32> {
    node.body()?;
    state.local_error = Some(ListLocalError::UnexpectedRoot);
    Err(ListingError::InvalidXml.code())
}
pub(in crate::s3) fn parse_document(
    body: &[u8],
    root: &mut dyn for<'p> FnMut(Node<'p>) -> Result<(), i32>,
) -> Result<(), i32> {
    let mut handler = Handler {
        callback: root,
        error: None,
    };
    // SAFETY: parser traversal is synchronous; handler and body outlive every callback.
    let parsed = check(unsafe {
        c::zaws_xml_parse(
            ffi::AwsByteCursor::from_bytes(body),
            Some(visit),
            (&mut handler as *mut Handler<'_>).cast(),
        )
    });
    parsed.map_err(|code| handler.error.unwrap_or(code))
}
#[derive(Default)]
struct Page {
    prefixes: Vec<ListEntry>,
    objects: Vec<ListEntry>,
    buckets: Vec<ListEntry>,
    url_encoded: bool,
}
impl Page {
    fn emit(self, state: &mut State, sink: &mut dyn FnMut(ListEntry) -> i32) -> Result<(), i32> {
        // Upstream prints a page's common prefixes before its objects,
        // whatever their order in the document.
        for mut entry in self.prefixes.into_iter().chain(self.objects) {
            if self.url_encoded {
                entry.name = url_decoded(&entry.name);
            }
            emit(entry, state, sink)?;
        }
        for entry in self.buckets {
            emit(entry, state, sink)?;
        }
        Ok(())
    }
}
fn object_child(node: Node<'_>, state: &mut State, page: &mut Page) -> Result<(), i32> {
    let name = node.name();
    let name = local_name(&name);
    if name.eq_ignore_ascii_case(b"Contents") {
        let mut entry = ListEntry::new(EntryKind::Object);
        let mut checksum = ListedChecksum::default();
        node.children(&mut |field| contents_child(field, state, &mut entry, &mut checksum))?;
        entry.name = xml_decoded_utf8(&entry.name, state)?;
        if state.object_conditions {
            entry.full_object_checksum = FullObjectChecksum::from_listing(
                checksum.checksum_type.as_deref(),
                checksum.algorithm_listed,
            );
        }
        page.objects.push(entry);
    } else if name.eq_ignore_ascii_case(b"CommonPrefixes") {
        let mut entry = ListEntry::new(EntryKind::CommonPrefix);
        node.children(&mut |field| {
            if field.name_is(b"Prefix") {
                entry.name = field.body()?;
            }
            Ok(())
        })?;
        entry.name = xml_decoded_utf8(&entry.name, state)?;
        page.prefixes.push(entry);
    } else if name.eq_ignore_ascii_case(b"EncodingType") {
        page.url_encoded = node.text(state)? == b"url";
    } else if name.eq_ignore_ascii_case(b"NextContinuationToken") {
        // The token goes back to the service verbatim, so it keeps only the
        // XML decoding botocore's parser applies.
        state.next_token = Some(node.text(state)?);
    } else if name.eq_ignore_ascii_case(b"IsTruncated") {
        state.has_more_results = node.text(state)?.eq_ignore_ascii_case(b"true");
    }
    Ok(())
}
#[derive(Default)]
struct ListedChecksum {
    checksum_type: Option<Vec<u8>>,
    algorithm_listed: bool,
}
fn contents_child(
    field: Node<'_>,
    state: &mut State,
    entry: &mut ListEntry,
    checksum: &mut ListedChecksum,
) -> Result<(), i32> {
    let name = field.name();
    let name = local_name(&name);
    if state.object_conditions {
        if name.eq_ignore_ascii_case(b"ETag") {
            entry.etag = Some(field.text(state)?);
            return Ok(());
        } else if name.eq_ignore_ascii_case(b"ChecksumType") {
            checksum.checksum_type = Some(field.text(state)?);
            return Ok(());
        } else if name.eq_ignore_ascii_case(b"ChecksumAlgorithm") {
            checksum.algorithm_listed = true;
            return Ok(());
        }
    }
    if name.eq_ignore_ascii_case(b"Key") {
        entry.name = field.body()?;
    } else if name.eq_ignore_ascii_case(b"Size") {
        let text = field.text(state)?;
        entry.size = parse_size(text.trim_ascii()).ok_or_else(|| {
            state.local_error = Some(ListLocalError::InvalidNumber);
            INVALID_ARGUMENT_ERROR_CODE
        })?;
    } else if name.eq_ignore_ascii_case(b"LastModified") {
        entry.date = Some(list_date(&field.text(state)?, state)?);
    } else if name.eq_ignore_ascii_case(b"StorageClass") {
        entry.archive = ArchiveState::from_storage_class(&field.text(state)?);
    }
    Ok(())
}
fn bucket_child(node: Node<'_>, state: &mut State, page: &mut Page) -> Result<(), i32> {
    let name = node.name();
    let name = local_name(&name);
    if name.eq_ignore_ascii_case(b"ContinuationToken") {
        state.next_token = Some(node.text(state)?);
        state.has_more_results = true;
        return Ok(());
    }
    if !name.eq_ignore_ascii_case(b"Buckets") {
        return Ok(());
    }
    node.children(&mut |bucket| {
        if !bucket.name_is(b"Bucket") {
            return Ok(());
        }
        let mut entry = ListEntry::new(EntryKind::Bucket);
        bucket.children(&mut |field| {
            let name = field.name();
            let name = local_name(&name);
            if name.eq_ignore_ascii_case(b"Name") {
                entry.name = field.body()?;
            } else if name.eq_ignore_ascii_case(b"CreationDate") {
                entry.date = Some(list_date(&field.text(state)?, state)?);
            }
            Ok(())
        })?;
        entry.name = xml_decoded_utf8(&entry.name, state)?;
        page.buckets.push(entry);
        Ok(())
    })
}
fn list_date(text: &[u8], state: &mut State) -> Result<super::LastModified, i32> {
    list_date_or_error(text).inspect_err(|_| {
        state.local_error = Some(ListLocalError::CrtFailure);
    })
}
fn xml_decoded_utf8(raw: &[u8], state: &mut State) -> Result<Vec<u8>, i32> {
    let text = xml_unescaped(raw)?;
    if std::str::from_utf8(&text).is_err() {
        state.local_error = Some(ListLocalError::InvalidUtf8);
        return Err(ListingError::InvalidXml.code());
    }
    Ok(text)
}
fn check_body(body: &[u8], state: &mut State) -> Result<(), i32> {
    let error = match std::str::from_utf8(body) {
        Err(_) => ListLocalError::InvalidUtf8,
        Ok(text) if !is_xml_text(text) => ListLocalError::InvalidXmlText,
        Ok(_) => return Ok(()),
    };
    state.local_error = Some(error);
    Err(ListingError::InvalidXml.code())
}
fn is_xml_text(text: &str) -> bool {
    if !text.chars().all(is_xml_char) {
        return false;
    }
    let mut rest = text.as_bytes();
    while let Some((start, markup)) = next_markup(rest) {
        if !xml_references_valid(&rest[..start]) {
            return false;
        }
        let body_start = start + markup.open().len();
        let Some(close) = find(&rest[body_start..], markup.close()) else {
            return true;
        };
        rest = &rest[body_start + close + markup.close().len()..];
    }
    xml_references_valid(rest)
}
fn xml_references_valid(text: &[u8]) -> bool {
    (0..text.len())
        .filter(|&start| text[start] == b'&')
        .all(|start| is_xml_reference(&text[start + 1..]))
}
fn is_xml_reference(text: &[u8]) -> bool {
    let Some(number) = text.strip_prefix(b"#") else {
        return is_predefined_entity(text);
    };
    let (digits, radix) = match number.strip_prefix(b"x") {
        Some(digits) => (digits, 16),
        None => (number, 10),
    };
    let Some(end) = digits
        .iter()
        .position(|byte| !char::from(*byte).is_digit(radix))
    else {
        return false;
    };
    digits[end] == b';'
        && reference_value(&digits[..end], radix)
            .and_then(char::from_u32)
            .is_some_and(is_xml_char)
}
fn reference_value(digits: &[u8], radix: u32) -> Option<u32> {
    if digits.is_empty() {
        return None;
    }
    digits.iter().try_fold(0_u32, |value, byte| {
        value
            .checked_mul(radix)?
            .checked_add(char::from(*byte).to_digit(radix)?)
    })
}
fn is_predefined_entity(text: &[u8]) -> bool {
    [b"lt;".as_slice(), b"gt;", b"amp;", b"apos;", b"quot;"]
        .iter()
        .any(|entity| text.starts_with(entity))
}
fn is_xml_char(c: char) -> bool {
    matches!(
        c,
        '\t' | '\n' | '\r' | '\u{20}'..='\u{fffd}' | '\u{10000}'..='\u{10ffff}'
    )
}
fn emit(
    entry: ListEntry,
    state: &mut State,
    sink: &mut dyn FnMut(ListEntry) -> i32,
) -> Result<(), i32> {
    let start = Instant::now();
    let rc = sink(entry);
    state.on_entry_ns += super::elapsed(start);
    state.entries_emitted += 1;
    if rc == 0 {
        Ok(())
    } else {
        state.callback_error = rc;
        Err(CANCELED_ERROR_CODE)
    }
}
fn parse_size(text: &[u8]) -> Option<u64> {
    let (negative, digits) = match text.split_first() {
        Some((b'+', rest)) => (false, rest),
        Some((b'-', rest)) => (true, rest),
        _ => (false, text),
    };
    if digits.is_empty() || digits.first() == Some(&b'_') || digits.last() == Some(&b'_') {
        return None;
    }
    let mut value: u64 = 0;
    for &byte in digits.iter().filter(|byte| **byte != b'_') {
        if !byte.is_ascii_digit() {
            return None;
        }
        value = value.checked_mul(10)?.checked_add(u64::from(byte - b'0'))?;
    }
    (!negative || value == 0).then_some(value)
}
pub(super) fn url_decoded(encoded: &[u8]) -> Vec<u8> {
    let mut result = Vec::with_capacity(encoded.len());
    let mut index = 0;
    while index < encoded.len() {
        let byte = encoded[index];
        if byte == b'+' {
            result.push(b' ');
            index += 1;
        } else if let (b'%', Some(&high), Some(&low)) =
            (byte, encoded.get(index + 1), encoded.get(index + 2))
            && let (Some(high), Some(low)) = (hex(high), hex(low))
        {
            result.push(high << 4 | low);
            index += 3;
        } else {
            result.push(byte);
            index += 1;
        }
    }
    match String::from_utf8_lossy(&result) {
        std::borrow::Cow::Borrowed(_) => result,
        std::borrow::Cow::Owned(replaced) => replaced.into_bytes(),
    }
}
fn hex(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}
fn xml_unescaped(raw: &[u8]) -> Result<Vec<u8>, i32> {
    if !raw.contains(&b'&') && !raw.contains(&b'<') {
        return Ok(raw.to_vec());
    }
    xml_text(raw)
}
pub(in crate::s3) fn xml_text(raw: &[u8]) -> Result<Vec<u8>, i32> {
    let mut decoded = Vec::with_capacity(raw.len());
    let mut rest = raw;
    while let Some((start, markup)) = next_markup(rest) {
        let body_start = start + markup.open().len();
        let close = find(&rest[body_start..], markup.close())
            .ok_or_else(|| ListingError::InvalidXml.code())?
            + body_start;
        let end = close + markup.close().len();
        append_unescaped(&rest[..start], &mut decoded)?;
        if markup == Markup::Cdata {
            decoded.extend_from_slice(&rest[body_start..close]);
        }
        rest = &rest[end..];
    }
    append_unescaped(rest, &mut decoded)?;
    Ok(decoded)
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Markup {
    Cdata,
    Comment,
    ProcessingInstruction,
}
impl Markup {
    const ALL: [Self; 3] = [Self::Cdata, Self::Comment, Self::ProcessingInstruction];
    fn open(self) -> &'static [u8] {
        match self {
            Self::Cdata => b"<![CDATA[",
            Self::Comment => b"<!--",
            Self::ProcessingInstruction => b"<?",
        }
    }
    fn close(self) -> &'static [u8] {
        match self {
            Self::Cdata => b"]]>",
            Self::Comment => b"-->",
            Self::ProcessingInstruction => b"?>",
        }
    }
}
fn next_markup(text: &[u8]) -> Option<(usize, Markup)> {
    text.iter()
        .enumerate()
        .filter(|(_, byte)| **byte == b'<')
        .find_map(|(start, _)| {
            Markup::ALL
                .into_iter()
                .find(|markup| text[start..].starts_with(markup.open()))
                .map(|markup| (start, markup))
        })
}
fn append_unescaped(text: &[u8], out: &mut Vec<u8>) -> Result<(), i32> {
    let start = out.len();
    out.resize(start + text.len(), 0);
    let mut len = 0;
    // SAFETY: the shim writes at most `text.len()` bytes into the resized tail
    // and reads `text` only during this call.
    check(unsafe {
        c::zaws_xml_unescape(
            ffi::AwsByteCursor::from_bytes(text),
            out[start..].as_mut_ptr(),
            &mut len,
        )
    })?;
    out.truncate(start + len);
    Ok(())
}
fn find(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}
fn local_name(qualified: &[u8]) -> &[u8] {
    qualified
        .iter()
        .rposition(|byte| *byte == b':')
        .map_or(qualified, |colon| &qualified[colon + 1..])
}
pub(in crate::s3) struct Node<'p>(*mut c::XmlNode, PhantomData<&'p c::XmlNode>);
impl Node<'_> {
    pub(in crate::s3) fn name(&self) -> Vec<u8> {
        // SAFETY: this opaque node is live throughout its enclosing parser callback.
        copy(unsafe { c::aws_xml_node_get_name(self.0) })
    }
    fn name_is(&self, expected: &[u8]) -> bool {
        local_name(&self.name()).eq_ignore_ascii_case(expected)
    }
    pub(in crate::s3) fn body(&self) -> Result<Vec<u8>, i32> {
        let mut body = ffi::AwsByteCursor::from_bytes(&[]);
        // SAFETY: output borrows the live node and is copied before returning.
        check(unsafe { c::aws_xml_node_as_body(self.0, &mut body) })?;
        Ok(copy(body))
    }
    fn text(&self, state: &mut State) -> Result<Vec<u8>, i32> {
        xml_decoded_utf8(&self.body()?, state)
    }
    pub(in crate::s3) fn children(
        &self,
        callback: &mut dyn for<'p> FnMut(Node<'p>) -> Result<(), i32>,
    ) -> Result<(), i32> {
        let mut handler = Handler {
            callback,
            error: None,
        };
        // SAFETY: the node, callback and stack handler remain live throughout
        // this synchronous traversal.
        let traversed = check(unsafe {
            c::aws_xml_node_traverse(
                self.0,
                Some(visit),
                (&mut handler as *mut Handler<'_>).cast(),
            )
        });
        traversed.map_err(|code| handler.error.unwrap_or(code))
    }
}
fn copy(cursor: ffi::AwsByteCursor) -> Vec<u8> {
    if cursor.len == 0 {
        return Vec::new();
    }
    // SAFETY: only called with a cursor from a live XML node.
    unsafe { std::slice::from_raw_parts(cursor.ptr, cursor.len).to_vec() }
}
struct Handler<'a> {
    callback: &'a mut dyn for<'p> FnMut(Node<'p>) -> Result<(), i32>,
    error: Option<i32>,
}
unsafe extern "C" fn visit(node: *mut c::XmlNode, data: *mut c_void) -> i32 {
    // SAFETY: traversal retains the exclusive stack handler until every callback returns.
    let handler = unsafe { &mut *data.cast::<Handler<'_>>() };
    match (handler.callback)(Node(node, PhantomData)) {
        Ok(()) => 0,
        Err(code) => {
            handler.error = Some(code);
            // SAFETY: this modifies only the current thread's CRT error state.
            unsafe { ffi::aws_raise_error(code) }
        }
    }
}
