use crate::Sections;
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Organized {
    pub profiles: Sections,
    pub sso_sessions: Sections,
    pub services: Sections,
    pub ordinary: Sections,
}
pub(crate) fn organize(sections: &Sections) -> Organized {
    let mut result = Organized::default();
    for (header, entries) in sections.iter() {
        let destination = if header.starts_with("profile") {
            Some(&mut result.profiles)
        } else if header.starts_with("sso-session") {
            Some(&mut result.sso_sessions)
        } else if header.starts_with("services") {
            Some(&mut result.services)
        } else {
            None
        };
        if let Some(map) = destination {
            if let Some(name) = organize_split_name(header) {
                map.insert(name, entries.clone());
            }
        } else if header == "default" {
            result.profiles.insert(header.to_owned(), entries.clone());
        } else if header != "sso_sessions" {
            result.ordinary.insert(header.to_owned(), entries.clone());
        }
    }
    result
}
#[derive(Debug, Default)]
struct QuoteState {
    delimiter: Option<char>,
    escaped: bool,
}
fn organize_split_name(header: &str) -> Option<String> {
    let mut name = String::new();
    let mut quote = QuoteState::default();
    let mut active = false;
    let mut count = 0;
    // shlex.split uses ASCII whitespace, disables comments, and concatenates quoted fragments.
    for c in header.chars() {
        if organize_split_name_quoted(&mut name, &mut quote, c) {
            continue;
        } else if matches!(c, ' ' | '\t' | '\r' | '\n') {
            if active {
                count += 1;
                if count > 2 {
                    return None;
                }
                if count == 1 {
                    name.clear();
                }
                active = false;
            }
        } else {
            active = true;
            match c {
                '\'' | '"' => quote.delimiter = Some(c),
                '\\' => quote.escaped = true,
                _ => name.push(c),
            }
        }
    }
    organize_split_name_complete(&quote, count, active).then_some(name)
}
fn organize_split_name_quoted(name: &mut String, quote: &mut QuoteState, c: char) -> bool {
    if quote.escaped {
        // Inside double quotes, a backslash escapes only the quote and itself.
        if quote.delimiter.is_some() && !matches!(c, '"' | '\\') {
            name.push('\\');
        }
        name.push(c);
        quote.escaped = false;
        return true;
    }
    let Some(delimiter) = quote.delimiter else {
        return false;
    };
    if c == delimiter {
        quote.delimiter = None;
    } else if c == '\\' && delimiter == '"' {
        quote.escaped = true;
    } else {
        name.push(c);
    }
    true
}
fn organize_split_name_complete(quote: &QuoteState, count: usize, active: bool) -> bool {
    debug_assert!(count <= 2);
    quote.delimiter.is_none() && !quote.escaped && count + usize::from(active) == 2
}
