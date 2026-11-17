use crate::{
    Diagnostic, Entries, Entry, Kind, Nested, OrderedMap, Origin, Sections, Syntax, Value,
    text::{self, is_space, strip},
};

#[derive(Debug)]
struct Pending {
    parts: Vec<String>,
    origin: Origin,
}
type Options = OrderedMap<Pending>;
#[derive(Debug, Default)]
struct Parser<'a> {
    source: &'a str,
    sections: OrderedMap<Options>,
    defaults: Options,
    section: Option<String>,
    has_section: bool,
    option: Option<String>,
    indent: usize,
    diagnostic: Option<Diagnostic>,
}
#[expect(
    clippy::expect_used,
    reason = "the parser selects only inserted section and option keys"
)]
impl Parser<'_> {
    fn options(&mut self) -> &mut Options {
        if let Some(name) = &self.section {
            self.sections
                .get_mut(name)
                .expect("selected section exists")
        } else {
            &mut self.defaults
        }
    }
    fn fail(&mut self, line: usize, syntax: Syntax) {
        self.diagnostic = Some(Diagnostic {
            source: self.source.to_owned(),
            line: Some(line),
            syntax,
        });
    }
    fn parse_line(&mut self, raw: &str, line: usize) -> bool {
        let value = strip(raw);
        if value.is_empty() {
            if let Some(key) = self.option.clone() {
                self.options()
                    .get_mut(&key)
                    .expect("selected option exists")
                    .parts
                    .push(String::new());
            }
            return true;
        }
        if value.starts_with(['#', ';']) {
            return true;
        }
        let indent = raw.chars().take_while(|c| is_space(*c)).count();
        if let Some(key) = self.option.clone()
            && indent > self.indent
        {
            self.options()
                .get_mut(&key)
                .expect("selected option exists")
                .parts
                .push(value.to_owned());
            return true;
        }
        self.indent = indent;
        self.parse_line_declaration(value, line)
    }
    fn parse_line_declaration(&mut self, value: &str, line: usize) -> bool {
        if value.starts_with('[')
            && let Some(end) = value.rfind(']')
            && end > 1
        {
            return self.parse_line_header(&value[1..end], line);
        }
        if !self.has_section {
            self.fail(line, Syntax::MissingSection);
            return false;
        }
        self.parse_line_option(value, line)
    }
    fn parse_line_header(&mut self, name: &str, line: usize) -> bool {
        self.has_section = true;
        self.option = None;
        if name == "DEFAULT" {
            self.section = None;
        } else {
            if self.sections.contains_key(name) {
                self.fail(line, Syntax::DuplicateSection);
                return false;
            }
            self.sections.insert(name.to_owned(), Options::default());
            self.section = Some(name.to_owned());
        }
        true
    }
    fn parse_line_option(&mut self, value: &str, line: usize) -> bool {
        let Some(delimiter) = value.find(['=', ':']) else {
            if self.diagnostic.is_none() {
                self.fail(line, Syntax::InvalidOption);
            }
            return true;
        };
        let key = text::lower(strip(&value[..delimiter]));
        if key.is_empty() {
            if self.diagnostic.is_none() {
                self.fail(line, Syntax::InvalidOption);
            }
            self.option = None;
            return true;
        }
        if self.options().contains_key(&key) {
            self.fail(line, Syntax::DuplicateOption);
            return false;
        }
        let origin = Origin {
            source: self.source.to_owned(),
            section: self.section.clone().unwrap_or_else(|| "DEFAULT".to_owned()),
            key: key.clone(),
            line,
        };
        self.options().insert(
            key.clone(),
            Pending {
                parts: vec![strip(&value[delimiter + 1..]).to_owned()],
                origin,
            },
        );
        self.option = Some(key);
        true
    }
}

pub(crate) fn parse(text: &str, source: &str, kind: Kind) -> Result<Sections, Diagnostic> {
    let mut parser = Parser {
        source,
        ..Parser::default()
    };
    let mut remaining = text;
    let mut line = 1;
    while !remaining.is_empty() {
        let end = remaining.find(['\r', '\n']).unwrap_or(remaining.len());
        if !parser.parse_line(&remaining[..end], line) {
            break;
        }
        remaining = &remaining[end..];
        remaining = remaining.strip_prefix('\r').unwrap_or(remaining);
        remaining = remaining.strip_prefix('\n').unwrap_or(remaining);
        line += 1;
    }
    if let Some(diagnostic) = parser.diagnostic.take() {
        return Err(diagnostic);
    }
    parse_sections(&parser, kind)
}
fn parse_sections(parser: &Parser<'_>, kind: Kind) -> Result<Sections, Diagnostic> {
    let mut result = Sections::default();
    for (name, options) in parser.sections.iter() {
        let mut entries = Entries::default();
        for (key, pending) in options.iter().chain(parser.defaults.iter()) {
            if !entries.contains_key(key) {
                entries.insert(key.to_owned(), parse_sections_entry(pending, kind)?);
            }
        }
        result.insert(name.to_owned(), entries);
    }
    Ok(result)
}
fn parse_sections_entry(pending: &Pending, kind: Kind) -> Result<Entry, Diagnostic> {
    let joined = pending.parts.join("\n");
    // RawConfigParser rstrips the joined value, but keeps its initial newline.
    let value = joined.trim_end_matches(is_space);
    let value = if kind == Kind::Aliases || !value.starts_with('\n') {
        Value::String(value.to_owned())
    } else {
        let mut nested = Nested::default();
        for raw in value.split(|c| {
            matches!(
                c,
                '\n' | '\r' | '\u{b}' | '\u{c}' | '\u{1c}'
                    ..='\u{1e}' | '\u{85}' | '\u{2028}' | '\u{2029}'
            )
        }) {
            if !parse_sections_entry_nested_line(&mut nested, raw) {
                return Err(Diagnostic {
                    source: pending.origin.source.clone(),
                    line: Some(pending.origin.line),
                    syntax: Syntax::InvalidNested,
                });
            }
        }
        Value::Nested(nested)
    };
    Ok(Entry {
        value,
        origin: pending.origin.clone(),
    })
}
fn parse_sections_entry_nested_line(nested: &mut Nested, raw: &str) -> bool {
    let line = strip(raw);
    if line.is_empty() {
        return true;
    }
    let Some((key, value)) = line.split_once('=') else {
        return false;
    };
    nested.insert(strip(key).to_owned(), strip(value).to_owned());
    true
}
