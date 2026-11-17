//! Loads the lexicographically latest service endpoint model from a payload.
use pyload::View;
#[derive(Debug)]
#[non_exhaustive]
pub enum RulesError {
    InvalidServiceName,
    MissingEndpointRules,
    InvalidEndpointRules,
    /// `DecodeFailed` or `OutputLengthMismatch`: a compressed resource is corrupt or does not
    /// decode to exactly its declared length.
    Decode(pyload::decompress::Error),
    /// A resource's bytes or its decoder scratch could not be reserved.
    OutOfMemory,
    Payload(pyload::Error),
    Resolve(crt::endpoints::ResolveError),
}
impl std::fmt::Display for RulesError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidServiceName => f.write_str("invalid service name"),
            Self::MissingEndpointRules => f.write_str("missing endpoint rules"),
            Self::InvalidEndpointRules => f.write_str("invalid endpoint rules"),
            Self::Decode(error) => error.fmt(f),
            Self::OutOfMemory => f.write_str("out of memory"),
            Self::Payload(error) => write!(f, "invalid endpoint payload: {error}"),
            Self::Resolve(error) => error.fmt(f),
        }
    }
}
impl std::error::Error for RulesError {}
impl From<pyload::Error> for RulesError {
    fn from(error: pyload::Error) -> Self {
        Self::Payload(error)
    }
}
/// Selects the greatest complete model name within a validated service prefix.
pub fn versioned_resource_name<'a>(
    view: View<'a>,
    service: &str,
    basename: &str,
) -> Result<&'a [u8], RulesError> {
    if service.is_empty()
        || !service
            .bytes()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == b'-')
    {
        return Err(RulesError::InvalidServiceName);
    }
    let prefix = format!("awscli/botocore/data/{service}/");
    let suffix = format!("/{basename}.json");
    let mut best = None;
    let mut index = view.first_name_at_least(prefix.as_bytes())?;
    while index < view.entry_count() {
        let name = view.entry_name_at(index)?;
        if !name.starts_with(prefix.as_bytes()) {
            break;
        }
        if name.ends_with(suffix.as_bytes()) && best.is_none_or(|old| old < name) {
            best = Some(name);
        }
        index += 1;
    }
    best.ok_or(RulesError::MissingEndpointRules)
}
/// Copies or decompresses an embedded resource using its declared exact length.
///
/// It reserves the output and then the decoder scratch fallibly, so an exhausted heap returns
/// `OutOfMemory` instead of aborting. A frame that does not decode to exactly the declared length
/// returns the decoder's own error; `InvalidEndpointRules` is only a declared length this target
/// cannot address.
pub fn load_resource(view: View<'_>, name: &[u8]) -> Result<Vec<u8>, RulesError> {
    let entry = view
        .find(name)?
        .ok_or(RulesError::MissingEndpointRules)?
        .entry;
    let stored = view.stored_bytes(entry)?;
    if !entry.is_compressed() {
        let mut bytes = reserve(stored.len())?;
        bytes.extend_from_slice(stored);
        return Ok(bytes);
    }
    let len =
        usize::try_from(entry.uncompressed_len).map_err(|_| RulesError::InvalidEndpointRules)?;
    let mut bytes = reserve(len)?;
    bytes.resize(len, 0);
    let mut scratch = reserve(pyload::decompress::ZSTD_BUFFER_LEN)?;
    pyload::decompress::decode_zstd(stored, &mut bytes, scratch.spare_capacity_mut())
        .map_err(RulesError::Decode)?;
    Ok(bytes)
}
fn reserve(len: usize) -> Result<Vec<u8>, RulesError> {
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(len)
        .map_err(|_| RulesError::OutOfMemory)?;
    Ok(bytes)
}
/// A service's decompressed rule set and the partitions it reads, shared by
/// every evaluation for a command.
#[derive(Clone, PartialEq, Eq)]
pub struct Rules {
    pub rules: std::sync::Arc<[u8]>,
    pub partitions: std::sync::Arc<[u8]>,
}
impl std::fmt::Debug for Rules {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Rules")
            .field("rules", &self.rules.len())
            .field("partitions", &self.partitions.len())
            .finish()
    }
}
impl Rules {
    /// Loads the service's latest rule set and the partitions from a payload.
    pub fn load(view: View<'_>, service: &str) -> Result<Self, RulesError> {
        let rules_name = versioned_resource_name(view, service, "endpoint-rule-set-1")?;
        let rules = load_resource(view, rules_name)?;
        let partitions = load_resource(view, b"awscli/botocore/data/partitions.json")?;
        Ok(Self {
            rules: rules.into(),
            partitions: partitions.into(),
        })
    }
    pub fn resolve(
        &self,
        parameters: crt::endpoints::Parameters<'_>,
    ) -> Result<crt::endpoints::Resolved, RulesError> {
        let documents = crt::endpoints::Documents {
            rules_json: &self.rules,
            partitions_json: &self.partitions,
        };
        crt::endpoints::resolve(documents, parameters).map_err(RulesError::Resolve)
    }
}
pub fn resolve(
    view: View<'_>,
    service: &str,
    parameters: crt::endpoints::Parameters<'_>,
) -> Result<crt::endpoints::Resolved, RulesError> {
    Rules::load(view, service)?.resolve(parameters)
}
#[cfg(test)]
mod tests;
