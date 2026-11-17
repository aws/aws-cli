//! Windows environment names use NT's one-code-unit uppercase mapping.
use std::collections::BTreeMap;

pub(super) fn collect<V>(
    pairs: impl IntoIterator<Item = (String, V)>,
    equal: impl Fn(&str, &str) -> bool,
) -> BTreeMap<String, V> {
    let mut values: BTreeMap<String, V> = BTreeMap::new();
    for (name, value) in pairs {
        if let Some((_, existing)) = values.iter_mut().find(|(key, _)| equal(key, &name)) {
            *existing = value;
        } else {
            values.insert(name, value);
        }
    }
    values
}

pub(super) fn get<'a, V>(
    values: &'a BTreeMap<String, V>,
    name: &str,
    equal: impl Fn(&str, &str) -> bool,
) -> Option<&'a V> {
    values
        .iter()
        .find(|(key, _)| equal(key, name))
        .map(|(_, value)| value)
}

fn names_equal_with(left: &str, right: &str, upcase: impl Fn(u16) -> u16) -> bool {
    let mut right = right.chars();
    for left in left.chars() {
        let Some(right) = right.next() else {
            return false;
        };
        if left == right {
            continue;
        }
        match (u16::try_from(left as u32), u16::try_from(right as u32)) {
            (Ok(left), Ok(right)) if upcase(left) == upcase(right) => {}
            _ => return false,
        }
    }
    right.next().is_none()
}

#[cfg(windows)]
pub(super) fn names_equal(left: &str, right: &str) -> bool {
    #[link(name = "ntdll")]
    unsafe extern "system" {
        fn RtlUpcaseUnicodeChar(character: u16) -> u16;
    }
    names_equal_with(left, right, |character| {
        // SAFETY: this NT routine accepts one UTF-16 code unit and returns one.
        unsafe { RtlUpcaseUnicodeChar(character) }
    })
}

#[cfg(test)]
mod tests;
