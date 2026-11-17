//! The object settings `s3 cp` sends with the requests of each object.
//!
//! Upstream copies each setting the command line gives onto the request
//! parameters of the operations it applies to, skipping any whose value is
//! empty (`RequestParamsMapper`). An upload's PutObject, or the
//! CreateMultipartUpload of a multipart upload, takes them all. The CRT builds
//! each UploadPart and CompleteMultipartUpload from that PUT and keeps only the
//! headers those operations take (aws-c-s3 s3_request_messages.c), so every
//! request of an upload starts from the same headers. A download's HeadObject
//! and every GetObject take the customer key, and every request of a transfer
//! the request payer.
//!
//! The checksum settings build no header here: upstream hands an upload's
//! algorithm and a download's checksum mode to the CRT, which computes or
//! checks the checksum and sends the headers that takes
//! (s3transfer's `S3ClientArgsCreator`).
//!
//! Each `--grants` pair sends its grantee, as given, in the header of its
//! permission ([`Grant`]), and a later pair of the same permission replaces
//! an earlier one, as each overwrites its request parameter
//! (`RequestParamsMapper._set_grant_params`). Upstream tests the list for truth
//! rather than each grantee, so an empty grantee is still sent.
//!
//! botocore sends each setting as its header, as given, except three. It
//! reads `--expires` as a timestamp and sends an HTTP date ([`HttpDate`]).
//! It collapses metadata names that differ only in case into one header, as
//! its case-insensitive `HeadersDict` stores them. And it sends the customer
//! key base64-encoded beside the base64 of its MD5 (botocore's `_sse_md5`).
//!
//! # Examples
//!
//! ```
//! use s3::object_settings::{CustomerAlgorithm, CustomerKey, ObjectSettings};
//! let settings = ObjectSettings {
//!     cache_control: Some("max-age=60"),
//!     customer_algorithm: Some(CustomerAlgorithm::Aes256),
//!     customer_key: Some(CustomerKey::new(b"0123456789abcdef0123456789abcdef")),
//!     ..ObjectSettings::default()
//! };
//! assert_eq!(settings.customer_key_refusal(), None);
//! let headers = settings.upload_headers();
//! assert_eq!(headers[0].name, b"Cache-Control");
//! assert_eq!(headers[0].value, b"max-age=60");
//! // A download sends the customer key alone: its algorithm, the key, and
//! // the key's MD5.
//! assert_eq!(settings.download_headers().len(), 3);
//! ```
use crate::AdmissionReason;
use crate::cp_args::Args;
use crate::transfer::{Direction, RequestPayer};
use crt::s3::Header;
use std::collections::HashMap;
use std::collections::hash_map::Entry;
use std::fmt;

mod http_date;
mod md5;

#[doc(inline)]
pub use http_date::{HttpDate, UnconvertedTimestamp};

macro_rules! choice {
    (
        $(#[$meta:meta])*
        $name:ident { $($(#[$variant_meta:meta])* $variant:ident => $value:literal),+ $(,)? }
    ) => {
        $(#[$meta])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
        pub enum $name {
            $($(#[$variant_meta])* $variant),+
        }
        impl $name {
            /// The header value, as the argparse choice spells it.
            pub const fn header_value(self) -> &'static str {
                match self {
                    $(Self::$variant => $value),+
                }
            }
        }
        impl TryFrom<&str> for $name {
            type Error = UnknownChoice;
            /// The choice `value` names, as argparse stores it.
            fn try_from(value: &str) -> Result<Self, UnknownChoice> {
                match value {
                    $($value => Ok(Self::$variant),)+
                    _ => Err(UnknownChoice),
                }
            }
        }
    };
}

choice! {
    /// A canned ACL, `--acl`.
    CannedAcl {
        Private => "private",
        PublicRead => "public-read",
        PublicReadWrite => "public-read-write",
        AuthenticatedRead => "authenticated-read",
        AwsExecRead => "aws-exec-read",
        BucketOwnerRead => "bucket-owner-read",
        BucketOwnerFullControl => "bucket-owner-full-control",
        LogDeliveryWrite => "log-delivery-write",
    }
}
choice! {
    /// The storage class an upload creates its object in, `--storage-class`.
    StorageClass {
        Standard => "STANDARD",
        ReducedRedundancy => "REDUCED_REDUNDANCY",
        StandardIa => "STANDARD_IA",
        OnezoneIa => "ONEZONE_IA",
        IntelligentTiering => "INTELLIGENT_TIERING",
        Glacier => "GLACIER",
        DeepArchive => "DEEP_ARCHIVE",
        GlacierIr => "GLACIER_IR",
    }
}
choice! {
    /// The server-side encryption S3 applies, `--sse`, whose bare flag is
    /// AES256.
    ServerSideEncryption {
        Aes256 => "AES256",
        AwsKms => "aws:kms",
    }
}
choice! {
    /// The algorithm of an SSE-C customer key, `--sse-c`, whose bare flag
    /// is AES256.
    CustomerAlgorithm {
        Aes256 => "AES256",
    }
}
choice! {
    /// The algorithm of the checksum an upload sends, `--checksum-algorithm`.
    ChecksumAlgorithm {
        Crc64Nvme => "CRC64NVME",
        Crc32 => "CRC32",
        Sha256 => "SHA256",
        Sha1 => "SHA1",
        Crc32c => "CRC32C",
        Sha512 => "SHA512",
        Xxhash64 => "XXHASH64",
        Xxhash3 => "XXHASH3",
        Xxhash128 => "XXHASH128",
    }
}
impl ChecksumAlgorithm {
    /// The CRT algorithm of the same name, which awscrt's
    /// `S3ChecksumAlgorithm` names as the choice does.
    pub const fn crt(self) -> crt::s3::ChecksumAlgorithm {
        use crt::s3::ChecksumAlgorithm as Crt;
        match self {
            Self::Crc64Nvme => Crt::Crc64Nvme,
            Self::Crc32 => Crt::Crc32,
            Self::Sha256 => Crt::Sha256,
            Self::Sha1 => Crt::Sha1,
            Self::Crc32c => Crt::Crc32c,
            Self::Sha512 => Crt::Sha512,
            Self::Xxhash64 => Crt::Xxhash64,
            Self::Xxhash3 => Crt::Xxhash3,
            Self::Xxhash128 => Crt::Xxhash128,
        }
    }
}
choice! {
    /// A download's checksum mode, `--checksum-mode`, whose one choice has
    /// it check the object's checksum.
    ChecksumMode {
        Enabled => "ENABLED",
    }
}

/// The permission a `--grants` pair grants, upstream's
/// `_permission_to_param`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GrantPermission {
    /// `read`, GrantRead.
    Read,
    /// `full`, GrantFullControl.
    FullControl,
    /// `readacl`, GrantReadACP.
    ReadAcp,
    /// `writeacl`, GrantWriteACP.
    WriteAcp,
}
impl GrantPermission {
    /// The header botocore sends the grantee in.
    pub const fn header_name(self) -> &'static str {
        match self {
            Self::Read => "x-amz-grant-read",
            Self::FullControl => "x-amz-grant-full-control",
            Self::ReadAcp => "x-amz-grant-read-acp",
            Self::WriteAcp => "x-amz-grant-write-acp",
        }
    }
}
impl TryFrom<&str> for GrantPermission {
    type Error = UnknownChoice;
    /// The permission `value` names, which upstream matches exactly.
    fn try_from(value: &str) -> Result<Self, UnknownChoice> {
        match value {
            "read" => Ok(Self::Read),
            "full" => Ok(Self::FullControl),
            "readacl" => Ok(Self::ReadAcp),
            "writeacl" => Ok(Self::WriteAcp),
            _ => Err(UnknownChoice),
        }
    }
}

/// One `--grants` pair: the permission before its first `=`, and the
/// grantee after it, as given.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Grant<'a> {
    pub permission: GrantPermission,
    pub grantee: &'a str,
}
impl<'a> Grant<'a> {
    /// The grant `pair` spells, or None for one upstream refuses with a
    /// ParamValidationError: a pair with no `=`, or a permission other
    /// than `read`, `full`, `readacl` and `writeacl` (`_set_grant_params`).
    pub fn parse(pair: &'a str) -> Option<Self> {
        let (permission, grantee) = pair.split_once('=')?;
        Some(Self {
            permission: GrantPermission::try_from(permission).ok()?,
            grantee,
        })
    }
}

/// A setting value outside the choices argparse accepts.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UnknownChoice;
impl fmt::Display for UnknownChoice {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("setting value is not one of its choices")
    }
}
impl std::error::Error for UnknownChoice {}

/// A setting value native does not convert as upstream does.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[non_exhaustive]
pub enum UnsupportedSetting {
    /// A closed setting's value outside its choices, which argparse's
    /// choices rule out.
    UnknownChoice,
    /// An `--expires` outside the timestamp forms [`HttpDate`] reads.
    Expires,
}
impl fmt::Display for UnsupportedSetting {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnknownChoice => UnknownChoice.fmt(f),
            Self::Expires => UnconvertedTimestamp.fmt(f),
        }
    }
}
impl std::error::Error for UnsupportedSetting {}
impl From<UnknownChoice> for UnsupportedSetting {
    fn from(_: UnknownChoice) -> Self {
        Self::UnknownChoice
    }
}
impl From<UnconvertedTimestamp> for UnsupportedSetting {
    fn from(_: UnconvertedTimestamp) -> Self {
        Self::Expires
    }
}

/// An SSE-C customer key as the command line gave it, whose bytes `Debug`
/// hides.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct CustomerKey<'a>(&'a [u8]);
impl<'a> CustomerKey<'a> {
    /// The key whose bytes are `key`: a string's UTF-8, or a file's bytes.
    pub const fn new(key: &'a [u8]) -> Self {
        Self(key)
    }
    /// The key's bytes.
    pub const fn as_bytes(&self) -> &'a [u8] {
        self.0
    }
}
impl fmt::Debug for CustomerKey<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("CustomerKey(<redacted>)")
    }
}

/// Why upstream refuses the customer key settings before any request.
///
/// Each is one of `_validate_sse_c_arg`'s ParamValidationErrors, which test the
/// values' truth, so an empty key counts as none.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CustomerKeyRefusal {
    /// `--sse-c` without a nonempty `--sse-c-key`.
    MissingKey,
    /// A nonempty `--sse-c-key` without `--sse-c`.
    MissingAlgorithm,
}
impl CustomerKeyRefusal {
    /// The ParamValidationError's message.
    pub const fn message(self) -> &'static str {
        match self {
            Self::MissingKey => "If --sse-c is specified, --sse-c-key must be specified as well.",
            Self::MissingAlgorithm => {
                "If --sse-c-key is specified, --sse-c must be specified as well."
            }
        }
    }
}
impl fmt::Display for CustomerKeyRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.message())
    }
}
impl std::error::Error for CustomerKeyRefusal {}

/// Why upstream refuses a checksum setting before any request: the setting
/// belongs to the other direction.
///
/// Each is `_raise_if_paths_type_incorrect_for_param`'s
/// ParamValidationError.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChecksumRefusal {
    /// `--checksum-algorithm` on a download.
    AlgorithmOnDownload,
    /// `--checksum-mode` on an upload.
    ModeOnUpload,
}
impl ChecksumRefusal {
    /// The ParamValidationError's message.
    pub const fn message(self) -> &'static str {
        match self {
            Self::AlgorithmOnDownload => {
                "Expected checksum-algorithm parameter to be used with one of following path \
                 formats: <LocalPath> <S3Uri>, <S3Uri> <S3Uri>. Instead, received <S3Uri> \
                 <LocalPath>."
            }
            Self::ModeOnUpload => {
                "Expected checksum-mode parameter to be used with one of following path \
                 formats: <S3Uri> <LocalPath>. Instead, received <LocalPath> <S3Uri>."
            }
        }
    }
}
impl fmt::Display for ChecksumRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.message())
    }
}
impl std::error::Error for ChecksumRefusal {}

/// The object settings a copy names, each as upstream reads it.
///
/// A string setting is None when its value is empty, as upstream skips a
/// value that is not truthy.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub struct ObjectSettings<'a> {
    /// `--content-type`, which also stops upstream guessing an upload's
    /// type from its source's name (`_should_inject_content_type`).
    pub content_type: Option<&'a str>,
    pub cache_control: Option<&'a str>,
    pub content_disposition: Option<&'a str>,
    pub content_encoding: Option<&'a str>,
    pub content_language: Option<&'a str>,
    /// `--expires`, which botocore's merged S3 model types as a timestamp.
    pub expires: Option<HttpDate>,
    pub website_redirect: Option<&'a str>,
    /// `--metadata`: each key and value, in the order the map gave them.
    pub metadata: &'a [(String, String)],
    /// `--grants`: each pair, in the order given, as [`Grant::parse`]
    /// reads it.
    pub grants: &'a [String],
    pub acl: Option<CannedAcl>,
    pub storage_class: Option<StorageClass>,
    pub encryption: Option<ServerSideEncryption>,
    pub kms_key_id: Option<&'a str>,
    pub customer_algorithm: Option<CustomerAlgorithm>,
    /// `--sse-c-key`, when nonempty.
    pub customer_key: Option<CustomerKey<'a>>,
    pub request_payer: Option<RequestPayer>,
    /// `--checksum-algorithm`, which only an upload takes.
    pub checksum_algorithm: Option<ChecksumAlgorithm>,
    /// `--checksum-mode`, which only a download takes.
    pub checksum_mode: Option<ChecksumMode>,
}
impl<'a> ObjectSettings<'a> {
    /// The settings `args` names.
    ///
    /// # Errors
    /// Returns [`UnsupportedSetting`] when a setting with closed choices
    /// holds a value native does not know, which argparse's choices rule
    /// out, or `--expires` a timestamp [`HttpDate`] does not read, which
    /// only botocore converts or refuses.
    pub fn from_args(args: &'a Args) -> Result<Self, UnsupportedSetting> {
        let text = |value: &'a Option<String>| value.as_deref().filter(|value| !value.is_empty());
        Ok(Self {
            content_type: text(&args.content_type),
            cache_control: text(&args.cache_control),
            content_disposition: text(&args.content_disposition),
            content_encoding: text(&args.content_encoding),
            content_language: text(&args.content_language),
            expires: text(&args.expires)
                .map(str::parse::<HttpDate>)
                .transpose()?,
            website_redirect: text(&args.website_redirect),
            metadata: &args.metadata.0,
            grants: &args.grants,
            acl: choice(&args.acl)?,
            storage_class: choice(&args.storage_class)?,
            encryption: choice(&args.sse)?,
            kms_key_id: text(&args.sse_kms_key_id),
            customer_algorithm: choice(&args.sse_c)?,
            customer_key: args
                .sse_c_key
                .as_deref()
                .filter(|key| !key.is_empty())
                .map(CustomerKey::new),
            request_payer: args
                .request_payer
                .as_deref()
                .map(RequestPayer::try_from)
                .transpose()
                .map_err(|_| UnknownChoice)?,
            checksum_algorithm: choice(&args.checksum_algorithm)?,
            checksum_mode: choice(&args.checksum_mode)?,
        })
    }
    /// Why upstream refuses a checksum setting of a transfer in `direction`,
    /// which it checks before the paths exist; None when it takes them.
    pub fn checksum_refusal(&self, direction: Direction) -> Option<ChecksumRefusal> {
        match direction {
            Direction::Download if self.checksum_algorithm.is_some() => {
                Some(ChecksumRefusal::AlgorithmOnDownload)
            }
            Direction::Upload if self.checksum_mode.is_some() => {
                Some(ChecksumRefusal::ModeOnUpload)
            }
            Direction::Upload | Direction::Download | Direction::Delete => None,
        }
    }
    /// Why upstream refuses the customer key settings, which it checks for
    /// every transfer before any request; None when it takes them.
    pub fn customer_key_refusal(&self) -> Option<CustomerKeyRefusal> {
        match (self.customer_algorithm, self.customer_key) {
            (Some(_), None) => Some(CustomerKeyRefusal::MissingKey),
            (None, Some(_)) => Some(CustomerKeyRefusal::MissingAlgorithm),
            _ => None,
        }
    }
    /// The headers each request of an upload sends, in the order upstream
    /// maps them (`RequestParamsMapper.map_put_object_params`): the object's
    /// own, its grants, its metadata, then its encryption.
    pub fn upload_headers(&self) -> Vec<Header> {
        let expires = self.expires.map(|date| date.to_string());
        let object = [
            ("x-amz-acl", self.acl.map(CannedAcl::header_value)),
            (
                "x-amz-storage-class",
                self.storage_class.map(StorageClass::header_value),
            ),
            ("x-amz-website-redirect-location", self.website_redirect),
            ("Content-Type", self.content_type),
            ("Cache-Control", self.cache_control),
            ("Content-Disposition", self.content_disposition),
            ("Content-Encoding", self.content_encoding),
            ("Content-Language", self.content_language),
            ("Expires", expires.as_deref()),
        ];
        let encryption = [
            (
                "x-amz-server-side-encryption",
                self.encryption.map(ServerSideEncryption::header_value),
            ),
            (
                "x-amz-server-side-encryption-aws-kms-key-id",
                self.kms_key_id,
            ),
        ];
        let metadata = sent_metadata(self.metadata)
            .into_iter()
            .map(|(key, value)| Header::new([METADATA_PREFIX, key.as_bytes()].concat(), value));
        let grants = sent_grants(self.grants)
            .into_iter()
            .map(|grant| Header::new(grant.permission.header_name(), grant.grantee));
        let mut headers: Vec<Header> = given(object)
            .chain(grants)
            .chain(metadata)
            .chain(given(encryption))
            .collect();
        self.extend_customer_key(&mut headers);
        headers
    }
    /// The headers each object request of a download sends: the customer
    /// key's, if any.
    pub fn download_headers(&self) -> Vec<Header> {
        let mut headers = Vec::new();
        self.extend_customer_key(&mut headers);
        headers
    }
    /// botocore's `_sse_md5`: the algorithm, the key base64-encoded, and
    /// the base64 of the key's MD5, when both settings are given.
    fn extend_customer_key(&self, headers: &mut Vec<Header>) {
        let (Some(algorithm), Some(key)) = (self.customer_algorithm, self.customer_key) else {
            return;
        };
        headers.extend([
            Header::new(
                "x-amz-server-side-encryption-customer-algorithm",
                algorithm.header_value(),
            ),
            Header::new(
                "x-amz-server-side-encryption-customer-key",
                base64(key.as_bytes()),
            ),
            Header::new(
                "x-amz-server-side-encryption-customer-key-MD5",
                base64(&md5::digest(key.as_bytes())),
            ),
        ]);
    }
    /// Why an upload with these settings stays with Python: a value the
    /// upload could not send, which fails it with an error only the
    /// fallback renders. None admits it.
    ///
    /// The CRT's HTTP encoder refuses a header value holding a control
    /// character other than a tab (aws-c-http h1_encoder.c). botocore
    /// refuses metadata that is not ASCII (`validate_ascii_metadata`), and the
    /// fallback reports an invalid header name for a metadata key that is not
    /// an HTTP token. A grant [`Grant::parse`] refuses stays too: upstream
    /// raises its error as it maps the request parameters of each file it
    /// submits, after the file's skip warnings and even in a dry run
    /// (`BaseTransferRequestSubmitter._do_submit`), so it fails only an upload
    /// that reaches a file.
    pub fn admit_upload(&self) -> Option<AdmissionReason> {
        let values = [
            self.content_type,
            self.cache_control,
            self.content_disposition,
            self.content_encoding,
            self.content_language,
            self.website_redirect,
            self.kms_key_id,
        ];
        let sendable = values
            .into_iter()
            .flatten()
            .all(|value| is_field_value(value.as_bytes()))
            && self.grants.iter().all(|pair| {
                Grant::parse(pair).is_some_and(|grant| is_field_value(grant.grantee.as_bytes()))
            })
            && self.metadata.iter().all(|(key, value)| {
                key.bytes().all(is_token_byte)
                    && value.is_ascii()
                    && is_field_value(value.as_bytes())
            });
        (!sendable).then_some(AdmissionReason::UnsupportedValue)
    }
}

const METADATA_PREFIX: &[u8] = b"x-amz-meta-";

/// The metadata botocore sends: the first spelling of each name, at its
/// place, with the last value given any name equal to it but for case.
///
/// `HeadersDict` folds names with `str.lower`, which an admitted upload's
/// token names fold as ASCII does.
fn sent_metadata(metadata: &[(String, String)]) -> Vec<(&str, &str)> {
    let mut sent: Vec<(&str, &str)> = Vec::with_capacity(metadata.len());
    let mut places: HashMap<String, usize> = HashMap::with_capacity(metadata.len());
    for (key, value) in metadata {
        match places.entry(key.to_ascii_lowercase()) {
            Entry::Occupied(place) => sent[*place.get()].1 = value,
            Entry::Vacant(place) => {
                place.insert(sent.len());
                sent.push((key, value));
            }
        }
    }
    sent
}

fn sent_grants(pairs: &[String]) -> Vec<Grant<'_>> {
    let mut sent: Vec<Grant<'_>> = Vec::with_capacity(pairs.len());
    for grant in pairs.iter().filter_map(|pair| Grant::parse(pair)) {
        match sent
            .iter_mut()
            .find(|earlier| earlier.permission == grant.permission)
        {
            Some(earlier) => earlier.grantee = grant.grantee,
            None => sent.push(grant),
        }
    }
    sent
}

fn given<'a, const N: usize>(
    settings: [(&'static str, Option<&'a str>); N],
) -> impl Iterator<Item = Header> + 'a {
    settings
        .into_iter()
        .filter_map(|(name, value)| Some(Header::new(name, value?)))
}

fn choice<'a, T: TryFrom<&'a str, Error = UnknownChoice>>(
    value: &'a Option<String>,
) -> Result<Option<T>, UnknownChoice> {
    value.as_deref().map(T::try_from).transpose()
}

/// Whether aws-c-http sends `value` as a header value: visible ASCII,
/// space, tab, and any byte above ASCII (`aws_strutil_is_http_field_value`,
/// which the encoder applies once it trims the value's whitespace).
fn is_field_value(value: &[u8]) -> bool {
    value
        .iter()
        .all(|&byte| byte == b'\t' || (b' '..=b'~').contains(&byte) || byte >= 0x80)
}

/// Whether `byte` may appear in an HTTP token, a header's name (RFC 9110
/// `tchar`).
fn is_token_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || b"!#$%&'*+-.^_`|~".contains(&byte)
}

fn base64(bytes: &[u8]) -> Vec<u8> {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut text = Vec::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let group = u32::from(chunk[0]) << 16
            | u32::from(chunk.get(1).copied().unwrap_or(0)) << 8
            | u32::from(chunk.get(2).copied().unwrap_or(0));
        for index in 0..4 {
            text.push(if index <= chunk.len() {
                ALPHABET[((group >> (18 - 6 * index)) & 63) as usize]
            } else {
                b'='
            });
        }
    }
    text
}

#[cfg(test)]
mod tests;
