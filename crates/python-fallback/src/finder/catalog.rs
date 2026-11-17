use super::object::{self, Owned, PyResult};
use crate::ffi::PyObject;
use pyload::{View, catalog};

pub(super) fn has_prefix(args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"O")?;
    let prefix = args[0].unicode()?;
    let view = object::view()?;
    let index = object::payload_result(view.first_name_at_least(prefix))?;
    let found = index < view.entry_count()
        && object::payload_result(view.entry_name_at(index))?.starts_with(prefix);
    object::boolean(found)
}

pub(super) fn list_prefix(args: *mut PyObject) -> PyResult<Owned> {
    list_names(args, false)
}

pub(super) fn list_dir(args: *mut PyObject) -> PyResult<Owned> {
    list_names(args, true)
}

fn list_names(args: *mut PyObject, children: bool) -> PyResult<Owned> {
    let args = object::args(args, c"O")?;
    let prefix = args[0].unicode()?;
    let view = object::view()?;
    let output = object::list()?;
    let first = object::payload_result(view.first_name_at_least(prefix))?;
    let mut previous: &[u8] = b"";
    for index in first..view.entry_count() {
        let name = object::payload_result(view.entry_name_at(index))?;
        if !name.starts_with(prefix) {
            break;
        }
        let Some(value) = listed_name(prefix, name, children) else {
            continue;
        };
        if children && value == previous {
            continue;
        }
        output.append(&object::string(value)?)?;
        previous = value;
    }
    Some(output)
}

fn listed_name<'a>(prefix: &[u8], name: &'a [u8], children: bool) -> Option<&'a [u8]> {
    if children {
        catalog::immediate_child(prefix, name)
    } else {
        Some(name)
    }
}

pub(super) fn list_services(args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"OO")?;
    let (prefix, type_name) = (args[0].unicode()?, args[1].unicode()?);
    list_groups(object::view()?, object::list()?, prefix, type_name, true)
}

pub(super) fn list_api_versions(args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"OOO")?;
    let (prefix, service, type_name) = (args[0].unicode()?, args[1].unicode()?, args[2].unicode()?);
    let view = object::view()?;
    let output = object::list()?;
    let prefix = lookup_parts(&[prefix, service, b"/"])?;
    list_groups(view, output, &prefix, type_name, false)
}

fn list_groups(
    view: View<'_>,
    output: Owned,
    prefix: &[u8],
    type_name: &[u8],
    services: bool,
) -> PyResult<Owned> {
    let mut index = object::payload_result(view.first_name_at_least(prefix))?;
    while index < view.entry_count() {
        let name = object::payload_result(view.entry_name_at(index))?;
        let Some(relative) = name.strip_prefix(prefix) else {
            break;
        };
        let Some(group) = group_name(relative) else {
            index += 1;
            continue;
        };
        let group_prefix = lookup_parts(&[prefix, group, b"/"])?;
        let limit = prefix_end(view, &group_prefix)?;
        if group_has_model(view, index..limit, &group_prefix, type_name, services)? {
            output.append(&object::string(group)?)?;
        }
        index = limit;
    }
    Some(output)
}

fn group_name(relative: &[u8]) -> Option<&[u8]> {
    let end = relative.iter().position(|byte| *byte == b'/')?;
    (end != 0).then_some(&relative[..end])
}

fn group_has_model(
    view: View<'_>,
    range: std::ops::Range<usize>,
    prefix: &[u8],
    type_name: &[u8],
    services: bool,
) -> PyResult<bool> {
    if range.end <= range.start {
        return object::runtime_error(c"zippy: invalid payload");
    }
    for index in range {
        let candidate = object::payload_result(view.entry_name_at(index))?;
        let relative = candidate
            .strip_prefix(prefix)
            .or_else(|| object::runtime_error(c"zippy: invalid payload"))?;
        let Some(file) = model_name(relative, services) else {
            continue;
        };
        if catalog::is_model_file(file, type_name) {
            return Some(true);
        }
    }
    Some(false)
}

fn model_name(relative: &[u8], services: bool) -> Option<&[u8]> {
    if !services {
        return Some(relative);
    }
    let version = group_name(relative)?;
    Some(&relative[version.len() + 1..])
}

fn prefix_end(view: View<'_>, prefix: &[u8]) -> PyResult<usize> {
    let mut buffer = [0; 4096];
    match catalog::prefix_upper_bound(&mut buffer, prefix) {
        Some(upper) => object::payload_result(view.first_name_at_least(upper)),
        None => Some(view.entry_count()),
    }
}

pub(super) fn lookup_parts(parts: &[&[u8]]) -> PyResult<Vec<u8>> {
    object::bounded::<4096>(parts, c"zippy: lookup name too long")
}
