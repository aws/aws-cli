/// The part of `path` `guess_type` takes an extension from: what follows
/// the last slash.
pub(super) fn file_name(path: &[u8]) -> &[u8] {
    path.rsplit(|byte| *byte == b'/').next().unwrap_or_default()
}

/// `posixpath.dirname(path)`: what precedes the last slash, less the
/// slashes that end it unless only slashes do.
pub(super) fn dir_name(path: &[u8]) -> &[u8] {
    let head = &path[..path
        .iter()
        .rposition(|&byte| byte == b'/')
        .map_or(0, |i| i + 1)];
    match head.iter().rposition(|&byte| byte != b'/') {
        Some(last) => &head[..=last],
        None => head,
    }
}

/// `posixpath.abspath(path)` with `cwd` as the working directory: `path`
/// joined to `cwd` unless it starts with a slash, then normalized. Empty and
/// `.` components drop, `..` drops the component before it, and two leading
/// slashes stay while three or more become one.
pub(super) fn absolute_path(cwd: &[u8], path: &[u8]) -> Vec<u8> {
    let joined = if path.starts_with(b"/") {
        path.to_vec()
    } else {
        let separator: &[u8] = if cwd.ends_with(b"/") { b"" } else { b"/" };
        [cwd, separator, path].concat()
    };
    let double_root = joined.starts_with(b"//") && !joined.starts_with(b"///");
    let mut components = Vec::new();
    for component in joined.split(|byte| *byte == b'/') {
        match component {
            b"" | b"." => {}
            b".." => {
                components.pop();
            }
            _ => components.push(component),
        }
    }
    let mut normal = if double_root {
        b"//".to_vec()
    } else {
        b"/".to_vec()
    };
    normal.extend_from_slice(&components.join(&b'/'));
    normal
}

#[cfg(test)]
mod tests;
