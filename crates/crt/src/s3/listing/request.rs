#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum Operation {
    ListObjectsV2,
    ListBuckets,
}
impl Operation {
    pub(super) fn name(self) -> &'static [u8] {
        match self {
            Self::ListObjectsV2 => b"ListObjectsV2",
            Self::ListBuckets => b"ListBuckets",
        }
    }
    /// The error codes the operation's model names (s3 service-2.json),
    /// which botocore's retries leave to the model.
    pub(super) fn modeled_errors(self) -> &'static [&'static [u8]] {
        match self {
            Self::ListObjectsV2 => &[b"NoSuchBucket"],
            Self::ListBuckets => &[],
        }
    }
}
#[derive(Debug, Clone, Copy)]
pub(super) struct Query<'a> {
    pub operation: Operation,
    pub prefix: &'a [u8],
    pub delimiter: &'a [u8],
    pub region: &'a [u8],
    pub page_size: u32,
}
impl Query<'_> {
    pub(super) fn build_path(self, base: &[u8], token: Option<&[u8]>) -> Vec<u8> {
        let mut path = if base.is_empty() {
            b"/".to_vec()
        } else {
            base.to_vec()
        };
        let mut query = false;
        let mut param = |name: &[u8], value: &[u8], required: bool| {
            if value.is_empty() && !required {
                return;
            }
            path.push(if query { b'&' } else { b'?' });
            query = true;
            path.extend_from_slice(name);
            path.push(b'=');
            append_encoded(&mut path, value);
        };
        if self.operation == Operation::ListObjectsV2 {
            param(b"list-type", b"2", true);
            param(b"prefix", self.prefix, true);
            param(b"delimiter", self.delimiter, false);
        } else {
            param(b"prefix", self.prefix, false);
            param(b"bucket-region", self.region, false);
        }
        if self.page_size != 0 {
            let name = if self.operation == Operation::ListObjectsV2 {
                b"max-keys".as_slice()
            } else {
                b"max-buckets"
            };
            param(name, self.page_size.to_string().as_bytes(), true);
        }
        param(b"continuation-token", token.unwrap_or_default(), false);
        if self.operation == Operation::ListObjectsV2 {
            param(b"encoding-type", b"url", true);
        }
        path
    }
}
fn append_encoded(out: &mut Vec<u8>, bytes: &[u8]) {
    const HEX: &[u8] = b"0123456789ABCDEF";
    for &byte in bytes {
        if byte.is_ascii_alphanumeric() || b"-_.~".contains(&byte) {
            out.push(byte);
        } else {
            out.extend_from_slice(&[b'%', HEX[(byte >> 4) as usize], HEX[(byte & 15) as usize]]);
        }
    }
}
