/// Python `str.isspace()`, including the separators U+001C to U+001F that
/// Unicode's White_Space property omits; `str.strip()` and `str.split()`
/// remove exactly these characters.
pub fn is_space(c: char) -> bool {
    matches!(c,
        '\u{9}'..='\u{d}' | '\u{1c}'..='\u{20}' | '\u{85}' | '\u{a0}' | '\u{1680}'
        | '\u{2000}'..='\u{200a}' | '\u{2028}' | '\u{2029}' | '\u{202f}' | '\u{205f}' | '\u{3000}'
    )
}

pub(crate) fn strip(text: &str) -> &str {
    text.trim_matches(is_space)
}

pub(crate) fn lower(text: &str) -> String {
    text.to_lowercase()
}
