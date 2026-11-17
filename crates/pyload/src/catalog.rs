//! Byte-oriented payload catalog operations.
#![forbid(unsafe_code)]

pub fn prefix_upper_bound<'a>(buffer: &'a mut [u8], prefix: &[u8]) -> Option<&'a [u8]> {
    if prefix.len() > buffer.len() {
        return None;
    }
    let index = prefix.iter().rposition(|&byte| byte != 0xff)?;
    buffer[..index].copy_from_slice(&prefix[..index]);
    buffer[index] = prefix[index] + 1;
    Some(&buffer[..=index])
}
pub fn immediate_child<'a>(prefix: &[u8], name: &'a [u8]) -> Option<&'a [u8]> {
    let suffix = name.strip_prefix(prefix)?;
    let end = suffix
        .iter()
        .position(|&byte| byte == b'/')
        .unwrap_or(suffix.len());
    (end > 0).then_some(&suffix[..end])
}
pub fn is_model_file(file_name: &[u8], type_name: &[u8]) -> bool {
    file_name.strip_prefix(type_name) == Some(b".json")
}

#[cfg(test)]
mod tests;
