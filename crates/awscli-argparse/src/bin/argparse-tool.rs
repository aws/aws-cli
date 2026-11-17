#![forbid(unsafe_code)]
use awscli_argparse::{
    Options,
    chain::{self, FORMATTER_WIDTH_DEFAULT, Outcome},
    tables, tool, unpack,
};
use std::io::{Read, Write};
const BATCH_RECORD_COUNT_MAX: usize = 1 << 16;
const BATCH_RECORD_BYTES_TYPICAL: usize = 4096;
const BATCH_BYTES_MAX: usize = BATCH_RECORD_COUNT_MAX * BATCH_RECORD_BYTES_TYPICAL;
const FORMATTER_MARGIN: usize = 2;
const STDOUT_BUFFER_BYTES: usize = 4096;
const _: () = {
    assert!(BATCH_BYTES_MAX == 256 * 1024 * 1024);
    assert!(BATCH_RECORD_COUNT_MAX < awscli_argparse::ARG_COUNT_MAX);
    assert!(FORMATTER_WIDTH_DEFAULT + FORMATTER_MARGIN == 80);
};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().collect();
    let mut output =
        std::io::BufWriter::with_capacity(STDOUT_BUFFER_BYTES, std::io::stdout().lock());
    if args.len() == 2 && args[1] == "dump-tables" {
        tool::dump_tables().write_json(&mut output)?;
        writeln!(output)?;
    } else if args.len() == 3 && args[1] == "parse" {
        parse_batch(std::path::Path::new(&args[2]), &mut output)?;
    } else {
        return Err("expected dump-tables or parse <jsonl>".into());
    }
    output.flush()?;
    Ok(())
}
fn parse_batch(
    path: &std::path::Path,
    output: &mut impl Write,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut input = String::new();
    std::fs::File::open(path)?
        .take(BATCH_BYTES_MAX as u64 + 1)
        .read_to_string(&mut input)?;
    if input.len() > BATCH_BYTES_MAX {
        return Err("request too large".into());
    }
    let variables = unpack::process_variables();
    let directory = unpack::current_directory()?;
    let files = unpack::FsParamfiles;
    let environment = unpack::Environment {
        directory: &directory,
        variables: &variables,
        files: &files,
        preferred_encoding: unpack::host_preferred_encoding(),
    };
    let width = formatter_width(variables.get("COLUMNS").and_then(|value| value.to_str()));
    for (index, line) in input.lines().filter(|l| !l.is_empty()).enumerate() {
        if index >= BATCH_RECORD_COUNT_MAX {
            return Err("too many records".into());
        }
        let request = decode_request(line, index)?;
        let mut parsed = chain::parse(
            &request.argv,
            &Options {
                formatter_width: width,
                ..Options::default()
            },
            &tables::TABLES_DEFAULT,
        );
        let unsupported = if parsed.outcome == Outcome::Parsed {
            chain::complete(&mut parsed, &environment)
        } else {
            false
        };
        tool::result_json(&parsed, unsupported, request.color).write_json(&mut *output)?;
        writeln!(output)?;
    }
    Ok(())
}
#[derive(Debug, PartialEq, Eq)]
struct Request {
    argv: Vec<String>,
    color: bool,
}
fn decode_request(line: &str, index: usize) -> Result<Request, String> {
    let record = awscli_argparse::json::parse_with_limit(line.as_bytes(), BATCH_BYTES_MAX)
        .map_err(|e| e.describe(line))?;
    let argv = record["argv"]
        .as_array()
        .ok_or("argv must be a list")?
        .iter()
        .map(|v| {
            v.as_str()
                .map(str::to_owned)
                .ok_or("argument must be a string")
        })
        .collect::<Result<Vec<_>, _>>()?;
    let color = match record.get("color") {
        None => false,
        Some(color) => color.as_bool().ok_or("color must be a boolean")?,
    };
    if argv.len() > awscli_argparse::ARG_COUNT_MAX
        || argv.iter().any(|a| a.len() > awscli_argparse::ARG_LEN_MAX)
    {
        return Err(format!("request exceeds host argv limits record={index}"));
    }
    Ok(Request { argv, color })
}

fn formatter_width(raw: Option<&str>) -> usize {
    raw.and_then(|text| {
        let text = text.trim_matches([' ', '\t', '\r', '\n']);
        let digits = text.strip_prefix('+').unwrap_or(text).as_bytes();
        if !digits.first().is_some_and(u8::is_ascii_digit)
            || !digits.last().is_some_and(u8::is_ascii_digit)
        {
            return None;
        }
        text.replace('_', "").parse::<usize>().ok()
    })
    .filter(|columns| *columns > 0)
    .map_or(FORMATTER_WIDTH_DEFAULT, |columns| {
        columns.saturating_sub(FORMATTER_MARGIN)
    })
}
#[cfg(test)]
#[path = "argparse-tool/tests.rs"]
mod tests;
