use super::EXPANDED_PATH_BYTES_MAX;
use std::collections::HashMap;
use std::ffi::OsString;

pub(super) fn expand(path: &str, variables: &HashMap<String, OsString>) -> Option<String> {
    let expanded = expand_vars(&expand_user(path, variables)?, variables)?;
    if reserved_device(&expanded) || device_namespace_or_pipe(&expanded) {
        None
    } else {
        Some(expanded)
    }
}

fn expand_user(path: &str, variables: &HashMap<String, OsString>) -> Option<String> {
    if path.len() > EXPANDED_PATH_BYTES_MAX {
        return None;
    }
    if !path.starts_with('~') {
        return Some(path.into());
    }
    let end = path.find(['/', '\\']).unwrap_or(path.len());
    if end != 1 {
        return None;
    }
    let home = value(variables, "USERPROFILE")?;
    if home.len() > EXPANDED_PATH_BYTES_MAX - (path.len() - end) {
        return None;
    }
    Some(format!("{home}{}", &path[end..]))
}

fn expand_vars(path: &str, variables: &HashMap<String, OsString>) -> Option<String> {
    if path.len() > EXPANDED_PATH_BYTES_MAX {
        return None;
    }
    let mut output = String::new();
    let mut rest = path;
    while !rest.is_empty() {
        let (literal, name, end) = piece(rest);
        let value = name
            .and_then(|name| value(variables, name))
            .unwrap_or(literal);
        if value.len() > EXPANDED_PATH_BYTES_MAX - output.len() {
            return None;
        }
        output.push_str(value);
        rest = &rest[end..];
    }
    Some(output)
}

fn value<'a>(variables: &'a HashMap<String, OsString>, name: &str) -> Option<&'a str> {
    variables
        .get(name)
        .and_then(|value| value.to_str())
        .or_else(|| {
            let upper = name.to_uppercase();
            variables
                .iter()
                .find_map(|(key, value)| (key.to_uppercase() == upper).then(|| value.to_str())?)
        })
}

fn piece(path: &str) -> (&str, Option<&str>, usize) {
    let tail = path.get(1..).unwrap_or("");
    match path.as_bytes()[0] {
        b'\'' => {
            let end = tail.find('\'').map_or(path.len(), |at| at + 2);
            (&path[..end], None, end)
        }
        b'%' | b'$' if tail.as_bytes().first() == path.as_bytes().first() => (&path[..1], None, 2),
        b'%' => delimited(path, 1, '%'),
        b'$' if tail.starts_with('{') => delimited(path, 2, '}'),
        b'$' => {
            let length = tail
                .bytes()
                .take_while(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
                .count();
            (&path[..length + 1], Some(&tail[..length]), length + 1)
        }
        _ => {
            let end = path.find(['\'', '%', '$']).unwrap_or(path.len());
            (&path[..end], None, end)
        }
    }
}

fn delimited(path: &str, start: usize, closing: char) -> (&str, Option<&str>, usize) {
    match path[start..].find(closing) {
        Some(length) => {
            let end = start + length + 1;
            (&path[..end], Some(&path[start..end - 1]), end)
        }
        None => (path, None, path.len()),
    }
}

fn reserved_device(path: &str) -> bool {
    let mut base = path.rsplit(['/', '\\']).next().unwrap_or(path);
    if base.len() >= 2 && base.as_bytes()[0].is_ascii_alphabetic() && base.as_bytes()[1] == b':' {
        base = &base[2..];
    }
    let stem = base
        .split(['.', ':'])
        .next()
        .unwrap_or(base)
        .trim_end_matches(' ');
    if ["CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"]
        .iter()
        .any(|name| stem.eq_ignore_ascii_case(name))
    {
        return true;
    }
    if let Some(prefix) = stem.get(..3)
        && (prefix.eq_ignore_ascii_case("COM") || prefix.eq_ignore_ascii_case("LPT"))
    {
        return matches!(
            &stem[3..],
            "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "¹" | "²" | "³"
        );
    }
    false
}

fn device_namespace_or_pipe(path: &str) -> bool {
    if path.len() < 2
        || !path.as_bytes()[..2]
            .iter()
            .all(|byte| matches!(byte, b'/' | b'\\'))
    {
        return false;
    }
    let rest = &path[2..];
    let Some(end) = rest.find(['/', '\\']) else {
        return false;
    };
    if matches!(&rest[..end], "." | "?") {
        return true;
    }
    rest[end + 1..]
        .split(['/', '\\'])
        .next()
        .is_some_and(|share| share.eq_ignore_ascii_case("pipe"))
}

pub(super) fn errno(error: &std::io::Error) -> Option<i32> {
    use std::io::ErrorKind;
    match error.kind() {
        ErrorKind::NotFound => Some(2),
        ErrorKind::PermissionDenied | ErrorKind::IsADirectory => Some(13),
        ErrorKind::NotADirectory => Some(20),
        ErrorKind::WouldBlock => Some(11),
        _ => None,
    }
}

#[cfg(test)]
mod tests;
