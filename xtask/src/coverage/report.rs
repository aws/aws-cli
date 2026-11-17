//! Product-source line coverage projected onto the application baseline.
//!
//! The lcov export of the `aws` object alone is the baseline: its executable
//! product lines are the application denominator. The export of every test
//! executable and `aws` together supplies the hits. A baseline line is
//! covered when the union hit the same file and line. Union lines outside the
//! baseline are test-only and are reported apart, so they never enlarge the
//! application denominator.

use crate::{TaskError, deps};
use std::collections::BTreeMap;
use std::fmt::Write;
use std::path::{Component, Path, PathBuf};

/// Source line numbers above this cannot describe project source files.
const LINE_NUMBER_MAX: u32 = 100_000_000;

/// Each product file's executable lines and whether any run hit each one.
type Files = BTreeMap<PathBuf, BTreeMap<u32, bool>>;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct Totals {
    /// Executable lines that were hit.
    covered: usize,
    /// Executable lines.
    counted: usize,
}

impl Totals {
    fn add(&mut self, hit: bool) {
        self.counted += 1;
        self.covered += usize::from(hit);
    }
}

/// What the projection learns about the union's lines.
#[derive(Debug, Default, Eq, PartialEq)]
struct Projection {
    /// Every union line.
    test: Totals,
    /// Union lines the application baseline does not contain.
    outside: Totals,
}

/// The coverage summary of an application baseline export and a union
/// export. A baseline without product lines is an error. The baseline's own
/// counts are ignored: the merged profile also carries test hits.
pub(super) fn summary(root: &Path, application: &[u8], union: &[u8]) -> Result<String, TaskError> {
    let mut baseline = parse_lcov(root, application)?;
    if totals(&baseline).counted == 0 {
        return Err(deps::error(
            "LLVM application baseline contains no product lines",
        ));
    }
    let projection = project(&mut baseline, &parse_lcov(root, union)?);
    render(&baseline, &projection)
}

/// The product files of an lcov export. Records of one file from several
/// objects merge, and a line is hit when any of its records counts a hit.
fn parse_lcov(root: &Path, bytes: &[u8]) -> Result<Files, TaskError> {
    let text =
        std::str::from_utf8(bytes).map_err(|_| deps::error("LLVM lcov export is not UTF-8"))?;
    let mut files = Files::new();
    let mut in_record = false;
    let mut current = None;
    for line in text.lines() {
        if let Some(path) = line.strip_prefix("SF:") {
            if in_record {
                return Err(deps::error("LLVM lcov source record lacks end_of_record"));
            }
            in_record = true;
            current = product_file(root, Path::new(path));
            if let Some(path) = &current {
                files.entry(path.clone()).or_default();
            }
        } else if line == "end_of_record" {
            if !in_record {
                return Err(deps::error(
                    "LLVM lcov end_of_record outside a source record",
                ));
            }
            in_record = false;
            current = None;
        } else if let Some(record) = line.strip_prefix("DA:") {
            if !in_record {
                return Err(deps::error("LLVM lcov line record outside a source record"));
            }
            let (number, hit) = line_record(record)?;
            if let Some(lines) = current.as_ref().and_then(|path| files.get_mut(path)) {
                *lines.entry(number).or_default() |= hit;
            }
        }
    }
    if in_record {
        return Err(deps::error("LLVM lcov export ends inside a source record"));
    }
    Ok(files)
}

/// A `DA:<line>,<count>[,<checksum>]` record's line and whether it was hit.
fn line_record(record: &str) -> Result<(u32, bool), TaskError> {
    let mut fields = record.split(',');
    let number = fields
        .next()
        .and_then(|value| value.parse::<u32>().ok())
        .filter(|number| (1..=LINE_NUMBER_MAX).contains(number));
    let count = fields.next().and_then(|value| value.parse::<u64>().ok());
    match (number, count) {
        (Some(number), Some(count)) => Ok((number, count != 0)),
        _ => Err(deps::error(format!(
            "malformed LLVM lcov line record: DA:{record}"
        ))),
    }
}

/// Marks each baseline line that the union hit, and counts the union lines
/// that fall outside the baseline instead.
fn project(baseline: &mut Files, union: &Files) -> Projection {
    let mut projection = Projection::default();
    for (path, lines) in union {
        let mut application = baseline.get_mut(path);
        for (number, hit) in lines {
            projection.test.add(*hit);
            match application
                .as_mut()
                .and_then(|application| application.get_mut(number))
            {
                Some(covered) => *covered |= *hit,
                None => projection.outside.add(*hit),
            }
        }
    }
    projection
}

fn totals(files: &Files) -> Totals {
    let mut result = Totals::default();
    for hit in files.values().flat_map(BTreeMap::values) {
        result.add(*hit);
    }
    result
}

fn product_file(root: &Path, path: &Path) -> Option<PathBuf> {
    let relative = path.strip_prefix(root).ok()?;
    let parts: Vec<_> = relative.components().collect();
    let component = |index| match parts.get(index) {
        Some(Component::Normal(value)) => value.to_str(),
        _ => None,
    };
    if component(0) != Some("crates") || component(2) != Some("src") {
        return None;
    }
    if matches!(component(1), Some("build-support" | "xtask" | "fuzz")) {
        return None;
    }
    let excluded = [
        "tests",
        "tests.rs",
        "testing",
        "testing.rs",
        "model",
        "model.rs",
        "fakes.rs",
    ];
    if parts.iter().any(|part| {
        part.as_os_str()
            .to_str()
            .is_some_and(|part| excluded.contains(&part))
    }) || path.extension().is_none_or(|extension| extension != "rs")
    {
        return None;
    }
    Some(relative.to_path_buf())
}

/// The diagnostic lines, the per-file table and the application total, in
/// that order.
fn render(files: &Files, projection: &Projection) -> Result<String, TaskError> {
    let (test, outside) = (projection.test, projection.outside);
    let mut result = String::new();
    writeln!(
        result,
        "Test-executable diagnostic: {}/{} lines (not application coverage)\n\
        Test lines outside application baseline: {}/{}\n\
        Product file\tCovered lines\tTotal lines\tCoverage",
        test.covered, test.counted, outside.covered, outside.counted
    )
    .map_err(format_error)?;
    let mut total = Totals::default();
    for (path, lines) in files {
        let mut file = Totals::default();
        for hit in lines.values() {
            file.add(*hit);
        }
        row(&mut result, &path.to_string_lossy(), file)?;
        total.covered += file.covered;
        total.counted += file.counted;
    }
    row(&mut result, "TOTAL", total)?;
    match percent(total) {
        Some(percent) => writeln!(
            result,
            "Application coverage: {}/{} ({percent:.2}%)",
            total.covered, total.counted
        ),
        None => writeln!(
            result,
            "Application coverage: {}/{} (unavailable)",
            total.covered, total.counted
        ),
    }
    .map_err(format_error)?;
    Ok(result)
}

/// One table row; a row without executable lines has no percentage.
fn row(output: &mut String, name: &str, lines: Totals) -> Result<(), TaskError> {
    let coverage = percent(lines).map_or_else(|| "n/a".to_owned(), |value| format!("{value:.2}%"));
    writeln!(
        output,
        "{name}\t{}\t{}\t{coverage}",
        lines.covered, lines.counted
    )
    .map_err(format_error)
}

fn percent(lines: Totals) -> Option<f64> {
    (lines.counted != 0).then(|| lines.covered as f64 * 100.0 / lines.counted as f64)
}

fn format_error(error: std::fmt::Error) -> TaskError {
    deps::error(error.to_string())
}

#[cfg(test)]
mod tests;
