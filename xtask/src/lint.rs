//! Repository checks that complement rustfmt and Clippy.

use crate::{TaskError, deps, process};
use std::collections::BTreeSet;
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

mod modules;

/// Directories holding project-owned Rust sources, relative to the repository
/// root; absent directories are optional. The fuzz package sits outside the
/// Cargo workspace but is a project source all the same.
const SOURCE_DIRECTORIES: [&str; 4] = ["crates", "xtask/src", "fuzz/src", "fuzz/fuzz_targets"];

/// Project-owned C sources under the same roots: the crate shims. They have
/// no formatter or module tree, so only the naming ban and fix markers apply
/// to them.
const C_EXTENSIONS: [&str; 2] = ["c", "h"];

/// The awscli-config crate's sources, which keep their own ratchet.
const CONFIG_SOURCE_DIRECTORY: [&str; 3] = ["crates", "awscli-config", "src"];

/// The fuzz package is excluded from the workspace, so it has its own manifest.
const FUZZ_MANIFEST: &str = "fuzz/Cargo.toml";

/// Build output, downloaded dependencies, and third-party source are not inventoried.
const EXCLUDED_DIRECTORIES: [&str; 6] = [
    "vendor",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
];

/// Cargo's build output, excluded only beside a `Cargo.toml`: `target` is also
/// an ordinary module directory (`crates/cli-router/src/tests/target`).
const CARGO_TARGET_DIRECTORY: &str = "target";

/// The inventory has about 630 Rust and C files; the largest is about 68 KiB. These
/// bounds allow about four times that size without unbounded directory or
/// source reads.
const FILE_COUNT_MAX: usize = 2560;
const SOURCE_BYTES_MAX: usize = 256 * 1024;
/// Source trees are fewer than 8 levels deep; fixtures and new crates have
/// room to grow. Module nesting follows directory nesting, so the same bound
/// limits module traversal.
const DIRECTORY_DEPTH_MAX: usize = 32;
/// The roots hold about 1,150 entries, two per Rust file; include non-Rust
/// fixtures while bounding enumeration independently of source count.
const DIRECTORY_ENTRY_MAX: usize = FILE_COUNT_MAX * 2;
/// Rust modules have no per-module import context, so each reached file is
/// parsed once and the visit bound is the file bound.
const VISIT_COUNT_MAX: usize = FILE_COUNT_MAX;
/// The current inventory reports no violations; cap diagnostic storage.
const DIAGNOSTIC_COUNT_MAX: usize = FILE_COUNT_MAX * 64;
/// The guideline's column budget, counted in Unicode code points after rustfmt.
const LINE_COLUMNS_MAX: usize = 100;
/// Inclusive declaration-to-closing-brace span, including comments and blank lines.
/// The guideline's screen-sized function ceiling.
const FUNCTION_LINES_MAX: usize = 70;

/// The contract a diagnostic failed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Rule {
    LineColumns,
    FunctionLines,
    Fixme,
    BannedIdentifier,
    TestPlacement,
    TestSuffix,
    MissingModule,
    UnreachableSource,
    GlobReexport,
    UnboundedLoop,
    ErasedError,
}

impl Rule {
    fn name(self) -> &'static str {
        match self {
            Self::LineColumns => "line_columns",
            Self::FunctionLines => "function_lines",
            Self::Fixme => "fixme",
            Self::BannedIdentifier => "banned_identifier",
            Self::TestPlacement => "test_placement",
            Self::TestSuffix => "test_suffix",
            Self::MissingModule => "missing_module",
            Self::UnreachableSource => "unreachable_source",
            Self::GlobReexport => "glob_reexport",
            Self::UnboundedLoop => "unbounded_loop",
            Self::ErasedError => "erased_error",
        }
    }
}

/// Diagnostics are data so negative fixtures need not parse failure text.
#[derive(Debug, Clone, PartialEq, Eq)]
struct Diagnostic {
    /// Source path associated with the failure.
    path: PathBuf,
    /// One-based line, or zero for a file-level failure.
    line: usize,
    /// The failed contract.
    rule: Rule,
    /// Rule detail such as `columns=101 max=100`, or empty.
    detail: String,
}

impl Diagnostic {
    /// `{path}:{line}: {rule} {detail}`, with `path` relative to `root`.
    fn render(&self, root: &Path) -> String {
        let path = self.path.strip_prefix(root).unwrap_or(&self.path);
        let mut text = format!("{}:{}: {}", path.display(), self.line, self.rule.name());
        if !self.detail.is_empty() {
            text.push(' ');
            text.push_str(&self.detail);
        }
        text
    }
}

/// Every diagnostic found so far, bounded by `DIAGNOSTIC_COUNT_MAX`.
#[derive(Debug, Default)]
struct Report {
    diagnostics: Vec<Diagnostic>,
}

impl Report {
    fn add(
        &mut self,
        path: &Path,
        line: usize,
        rule: Rule,
        detail: String,
    ) -> Result<(), TaskError> {
        if self.diagnostics.len() == DIAGNOSTIC_COUNT_MAX {
            return Err(limit(
                "source check report",
                "DIAGNOSTIC_COUNT_MAX",
                DIAGNOSTIC_COUNT_MAX,
            ));
        }
        self.diagnostics.push(Diagnostic {
            path: path.to_path_buf(),
            line,
            rule,
            detail,
        });
        Ok(())
    }
}

/// The bounded walk shared by every inventory root.
#[derive(Debug, Default)]
struct Inventory {
    /// Rust and C sources found so far.
    files: Vec<PathBuf>,
    /// Directory entries enumerated so far, Rust or not.
    entries: usize,
}

/// The failure for an exceeded inventory or traversal bound, naming the bound.
fn limit(subject: &str, name: &str, value: usize) -> TaskError {
    TaskError::Message(format!("lint: {subject} exceeds {name}={value}"))
}

pub fn run(root: &Path) -> Result<(), TaskError> {
    check_sources(root)?;
    process::run(
        Command::new("cargo")
            .current_dir(root)
            .args(["fmt", "--all", "--check"]),
    )?;
    process::run(Command::new("cargo").current_dir(root).args([
        "fmt",
        "--manifest-path",
        FUZZ_MANIFEST,
        "--check",
    ]))?;
    let environment = deps::native_environment(root, !cfg!(windows))?;
    let mut workspace = workspace_clippy(root);
    environment.apply(&mut workspace);
    process::run(&mut workspace)?;
    process::run(&mut fuzz_clippy(root))
}

/// Clippy over the workspace as `cargo xtask test` builds it: for the
/// product's target, under the dependency environment the caller applies.
fn workspace_clippy(root: &Path) -> Command {
    let mut command = Command::new("cargo");
    command.current_dir(root).args([
        "clippy",
        "--workspace",
        "--all-targets",
        "--locked",
        "--target",
        deps::TARGET,
    ]);
    command.args(["--", "-D", "warnings"]);
    command
}

/// Clippy over the fuzz package as cargo-fuzz builds it, with `fuzzing` set,
/// so its build scripts compile no C, as they compile none for a campaign.
fn fuzz_clippy(root: &Path) -> Command {
    let mut command = Command::new("cargo");
    command
        .current_dir(root)
        .args(["clippy", "--manifest-path", FUZZ_MANIFEST])
        .args(["--all-targets", "--locked", "--", "-D", "warnings"])
        .env("RUSTFLAGS", "--cfg fuzzing");
    command
}

/// The repository source checks alone, which `cargo xtask test` also runs.
pub(crate) fn check_sources(root: &Path) -> Result<(), TaskError> {
    let sources = inventory(root)?;
    let diagnostics = check_inventory(&sources, &target_roots(root)?)?;
    report(root, &diagnostics, &mut io::stderr().lock())
}

/// Writes every diagnostic, one per line, then fails with their count.
fn report(
    root: &Path,
    diagnostics: &[Diagnostic],
    output: &mut impl Write,
) -> Result<(), TaskError> {
    for diagnostic in diagnostics {
        writeln!(output, "{}", diagnostic.render(root))?;
    }
    if diagnostics.is_empty() {
        return Ok(());
    }
    Err(TaskError::Message(format!(
        "{} source check violations",
        diagnostics.len()
    )))
}

/// Checks every source and its reachability from `roots`, returning all
/// diagnostics sorted by path and line, file-level ones (line zero) first.
fn check_inventory(sources: &[PathBuf], roots: &[PathBuf]) -> Result<Vec<Diagnostic>, TaskError> {
    if sources.len() > FILE_COUNT_MAX {
        return Err(limit("source inventory", "FILE_COUNT_MAX", FILE_COUNT_MAX));
    }
    let mut report = Report::default();
    for path in sources {
        let source = read_source(path)?;
        if is_c_source(path) {
            check_c_text(path, &source, &mut report)?;
        } else {
            check_text(path, &source, &mut report)?;
        }
    }
    let mut reached = BTreeSet::new();
    for path in roots {
        visit_module(path, true, 0, &mut reached, &mut report)?;
    }
    for path in sources.iter().filter(|path| is_rust_source(path)) {
        if !reached.contains(&fs::canonicalize(path)?) {
            report.add(
                path,
                0,
                Rule::UnreachableSource,
                "no build root reaches it".into(),
            )?;
        }
    }
    let mut diagnostics = report.diagnostics;
    diagnostics.sort_by(|left, right| (&left.path, left.line).cmp(&(&right.path, right.line)));
    Ok(diagnostics)
}

/// Every Rust and C source under `SOURCE_DIRECTORIES`, sorted by path.
fn inventory(root: &Path) -> Result<Vec<PathBuf>, TaskError> {
    let mut inventory = Inventory::default();
    for directory in SOURCE_DIRECTORIES {
        let directory = root.join(directory);
        if directory.is_dir() {
            collect_sources(&directory, 0, &mut inventory)?;
        }
    }
    inventory.files.sort();
    Ok(inventory.files)
}

fn collect_sources(
    directory: &Path,
    depth: usize,
    inventory: &mut Inventory,
) -> Result<(), TaskError> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        inventory.entries += 1;
        if inventory.entries > DIRECTORY_ENTRY_MAX {
            return Err(limit(
                "source directory walk",
                "DIRECTORY_ENTRY_MAX",
                DIRECTORY_ENTRY_MAX,
            ));
        }
        let path = entry.path();
        if entry.file_type()?.is_dir() {
            if excluded_directory(&path) {
                continue;
            }
            if depth == DIRECTORY_DEPTH_MAX {
                let subject = format!("directory {}", path.display());
                return Err(limit(&subject, "DIRECTORY_DEPTH_MAX", DIRECTORY_DEPTH_MAX));
            }
            collect_sources(&path, depth + 1, inventory)?;
        } else if is_rust_source(&path) || is_c_source(&path) {
            if inventory.files.len() == FILE_COUNT_MAX {
                return Err(limit("source inventory", "FILE_COUNT_MAX", FILE_COUNT_MAX));
            }
            inventory.files.push(path);
        }
    }
    Ok(())
}

fn is_rust_source(path: &Path) -> bool {
    path.extension().is_some_and(|extension| extension == "rs")
}

fn is_c_source(path: &Path) -> bool {
    path.extension()
        .is_some_and(|extension| C_EXTENSIONS.iter().any(|name| extension == *name))
}

/// Build output, caches, and third-party source are not inventoried.
fn excluded_directory(path: &Path) -> bool {
    let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
        return false;
    };
    EXCLUDED_DIRECTORIES.contains(&name)
        || (name == CARGO_TARGET_DIRECTORY && path.with_file_name("Cargo.toml").is_file())
}

/// Reads a source, failing with the byte bound instead of reading past it.
fn read_source(path: &Path) -> Result<String, TaskError> {
    let mut bytes = Vec::new();
    File::open(path)?
        .take((SOURCE_BYTES_MAX + 1) as u64)
        .read_to_end(&mut bytes)?;
    if bytes.len() > SOURCE_BYTES_MAX {
        let subject = path.display().to_string();
        return Err(limit(&subject, "SOURCE_BYTES_MAX", SOURCE_BYTES_MAX));
    }
    String::from_utf8(bytes)
        .map_err(|error| TaskError::Io(io::Error::new(io::ErrorKind::InvalidData, error)))
}

/// Crate roots of every Cargo target and the fuzz package's.
fn target_roots(root: &Path) -> Result<Vec<PathBuf>, TaskError> {
    let mut roots = manifest_roots(root, "Cargo.toml")?;
    roots.extend(manifest_roots(root, FUZZ_MANIFEST)?);
    Ok(roots)
}

fn manifest_roots(root: &Path, manifest: &str) -> Result<Vec<PathBuf>, TaskError> {
    let output = process::output(Command::new("cargo").current_dir(root).args([
        "metadata",
        "--no-deps",
        "--format-version",
        "1",
        "--locked",
        "--manifest-path",
        manifest,
    ]))?;
    let metadata: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|error| TaskError::Message(error.to_string()))?;
    let packages = metadata["packages"]
        .as_array()
        .ok_or_else(|| TaskError::Message("Cargo metadata did not contain packages".into()))?;
    let mut roots = Vec::new();
    for package in packages {
        if let Some(targets) = package["targets"].as_array() {
            for target in targets {
                if let Some(path) = target["src_path"].as_str() {
                    roots.push(PathBuf::from(path));
                }
            }
        }
    }
    Ok(roots)
}

/// Visits `path` and every module it declares, resolving children as rustc
/// does: crate roots of any name, `mod.rs` files and `#[path]` files own
/// their directory, and every other file owns `parent/stem`. A `#[path]`
/// value is relative to the declaring file's directory.
fn visit_module(
    path: &Path,
    owns_directory: bool,
    depth: usize,
    reached: &mut BTreeSet<PathBuf>,
    report: &mut Report,
) -> Result<(), TaskError> {
    if depth > DIRECTORY_DEPTH_MAX {
        let subject = format!("module {}", path.display());
        return Err(limit(&subject, "DIRECTORY_DEPTH_MAX", DIRECTORY_DEPTH_MAX));
    }
    let canonical = fs::canonicalize(path)?;
    if reached.contains(&canonical) {
        return Ok(());
    }
    if reached.len() == VISIT_COUNT_MAX {
        return Err(limit(
            "module traversal",
            "VISIT_COUNT_MAX",
            VISIT_COUNT_MAX,
        ));
    }
    reached.insert(canonical);
    let source = read_source(path)?;
    let parent = path
        .parent()
        .ok_or_else(|| TaskError::Message("missing parent".into()))?;
    let directory = match path.file_stem() {
        Some(stem) if !owns_directory && stem != "mod" => parent.join(stem),
        _ => parent.to_path_buf(),
    };
    for declaration in modules::declarations(&source)? {
        let name = declaration.name;
        // rustc treats every `#[path]` file as a `mod.rs` file.
        let aliased = declaration.path.is_some();
        let child = if let Some(explicit) = declaration.path {
            parent.join(explicit)
        } else {
            let flat = directory.join(format!("{name}.rs"));
            let nested = directory.join(name).join("mod.rs");
            if flat.is_file() { flat } else { nested }
        };
        if child.is_file() {
            visit_module(&child, aliased, depth + 1, reached, report)?;
        } else {
            report.add(path, 0, Rule::MissingModule, name.to_owned())?;
        }
    }
    Ok(())
}

fn check_text(path: &Path, source: &str, report: &mut Report) -> Result<(), TaskError> {
    check_columns(path, source, report)?;
    check_markers(path, source, report)?;
    let tokens = tokens(source);
    check_function_lines(path, source, &tokens, report)?;
    check_banned(path, source, &tokens, report)?;
    check_glob_reexports(path, source, &tokens, report)?;
    if in_config_crate(path) {
        check_config(path, source, &tokens, report)?;
    }
    check_test_placement(path, source, &tokens, report)?;
    if path
        .file_stem()
        .is_some_and(|name| name.to_string_lossy().ends_with("_test"))
    {
        report.add(path, 0, Rule::TestSuffix, "name the file tests.rs".into())?;
    }
    Ok(())
}

/// C sources have no formatter or module tree: only the naming ban and fix
/// markers apply. The tokenizer's comment and literal rules hold for C.
fn check_c_text(path: &Path, source: &str, report: &mut Report) -> Result<(), TaskError> {
    check_markers(path, source, report)?;
    check_banned(path, source, &tokens(source), report)
}

fn check_columns(path: &Path, source: &str, report: &mut Report) -> Result<(), TaskError> {
    for (index, line) in source.lines().enumerate() {
        let columns = line.chars().count();
        if columns > LINE_COLUMNS_MAX {
            let detail = format!("columns={columns} max={LINE_COLUMNS_MAX}");
            report.add(path, index + 1, Rule::LineColumns, detail)?;
        }
    }
    Ok(())
}

/// Leftover markers hide in comments, so every line is checked.
fn check_markers(path: &Path, source: &str, report: &mut Report) -> Result<(), TaskError> {
    let marker = ["FIX", "ME"].concat();
    for (index, line) in source.lines().enumerate() {
        if line.contains(&marker) {
            let detail = "TODO, or resolve it before merging".into();
            report.add(path, index + 1, Rule::Fixme, detail)?;
        }
    }
    Ok(())
}

/// The span rule, which clippy's `too_many_lines` (it skips blank and
/// comment lines) does not replace: a function with a body measures from its
/// first token (visibility and qualifiers, not attributes or doc comments)
/// through its closing brace. Prototypes, `#[test]` functions and `tests.rs`
/// files are exempt.
fn check_function_lines(
    path: &Path,
    source: &str,
    tokens: &[&str],
    report: &mut Report,
) -> Result<(), TaskError> {
    if path.file_name().is_some_and(|name| name == "tests.rs") {
        return Ok(());
    }
    for (index, _) in tokens
        .iter()
        .enumerate()
        .filter(|(_, token)| **token == "fn")
    {
        // A function pointer type such as `fn(u8) -> u8` has no name.
        let Some(name) = tokens.get(index + 1).filter(|name| is_identifier(name)) else {
            continue;
        };
        let Some(close) = body_close(&tokens[index..]) else {
            continue;
        };
        let first = item_start(&tokens[..index]);
        if test_function(&tokens[..first]) {
            continue;
        }
        let span = &source[token_offset(source, tokens[first])..token_offset(source, close)];
        let lines = 1 + span.bytes().filter(|byte| *byte == b'\n').count();
        if lines > FUNCTION_LINES_MAX {
            let detail = format!("function={name} lines={lines} max={FUNCTION_LINES_MAX}");
            let line = token_line(source, tokens[first]);
            report.add(path, line, Rule::FunctionLines, detail)?;
        }
    }
    Ok(())
}

fn is_identifier(token: &str) -> bool {
    token
        .bytes()
        .next()
        .is_some_and(|byte| byte.is_ascii_alphabetic() || byte == b'_')
}

/// The closing brace of the body that follows `fn name`, or `None` for a
/// prototype: a `;` outside the parameter list and array types comes first.
fn body_close<'a>(item: &[&'a str]) -> Option<&'a str> {
    let mut nesting = 0usize;
    let open = item.iter().position(|token| {
        match *token {
            "(" | "[" => nesting += 1,
            ")" | "]" => nesting = nesting.saturating_sub(1),
            _ => {}
        }
        nesting == 0 && (*token == "{" || *token == ";")
    })?;
    if item[open] == ";" {
        return None;
    }
    let mut depth = 0usize;
    for token in &item[open..] {
        match *token {
            "{" => depth += 1,
            "}" => depth -= 1,
            _ => continue,
        }
        if depth == 0 {
            return Some(token);
        }
    }
    None
}

/// The index of the item's first token: the qualifiers and visibility before
/// `fn`. String literals such as an `extern "C"` ABI are not tokens here.
fn item_start(before: &[&str]) -> usize {
    let mut start = before.len();
    while let Some(token) = start.checked_sub(1).map(|last| before[last]) {
        match token {
            "pub" | "const" | "async" | "unsafe" | "extern" | "default" | "safe" => start -= 1,
            // `pub(crate)`, `pub(super)` and `pub(in path)`.
            ")" => match before[..start].iter().rposition(|token| *token == "(") {
                Some(open) if open > 0 && before[open - 1] == "pub" => start = open - 1,
                _ => break,
            },
            _ => break,
        }
    }
    start
}

/// Whether the attributes that end `before` include `#[test]` or a
/// `path::test` attribute such as `#[tokio::test]`.
fn test_function(before: &[&str]) -> bool {
    let mut end = before.len();
    while end > 0 && before[end - 1] == "]" {
        let Some(open) = attribute_open(&before[..end]) else {
            return false;
        };
        let content = &before[open + 1..end - 1];
        if content.last() == Some(&"test")
            && (content.len() == 1 || content[content.len() - 2] == ":")
        {
            return true;
        }
        if open == 0 || before[open - 1] != "#" {
            return false;
        }
        end = open - 1;
    }
    false
}

/// The `[` that opens the attribute whose `]` ends `tokens`.
fn attribute_open(tokens: &[&str]) -> Option<usize> {
    let mut depth = 0usize;
    for (index, token) in tokens.iter().enumerate().rev() {
        match *token {
            "]" => depth += 1,
            "[" => depth -= 1,
            _ => continue,
        }
        if depth == 0 {
            return Some(index);
        }
    }
    None
}

/// The project bans the word from project-owned names in every spelling.
fn check_banned(
    path: &Path,
    source: &str,
    tokens: &[&str],
    report: &mut Report,
) -> Result<(), TaskError> {
    let banned = ["pro", "duction"].concat();
    for token in tokens
        .iter()
        .filter(|token| token.to_ascii_lowercase().contains(&banned))
    {
        let line = token_line(source, token);
        report.add(path, line, Rule::BannedIdentifier, (*token).to_owned())?;
    }
    Ok(())
}

/// A public glob `use` hides the names a module exports, so they are listed
/// instead. Private globs such as a test file's `use super::*;` stay allowed.
fn check_glob_reexports(
    path: &Path,
    source: &str,
    tokens: &[&str],
    report: &mut Report,
) -> Result<(), TaskError> {
    for (index, _) in tokens
        .iter()
        .enumerate()
        .filter(|(_, token)| **token == "use")
    {
        if !public_use(&tokens[..index]) {
            continue;
        }
        let statement = &tokens[index..];
        let end = statement
            .iter()
            .position(|token| *token == ";")
            .unwrap_or(statement.len());
        for glob in statement[..end].iter().filter(|token| **token == "*") {
            let detail = "use explicit re-exports".into();
            report.add(path, token_line(source, glob), Rule::GlobReexport, detail)?;
        }
    }
    Ok(())
}

/// Whether the tokens before a `use` end in `pub`, `pub(crate)`,
/// `pub(super)` or `pub(in path)`.
fn public_use(before: &[&str]) -> bool {
    let visibility = match before {
        [rest @ .., ")"] => rest
            .iter()
            .rposition(|token| *token == "(")
            .map(|open| &rest[..open]),
        _ => Some(before),
    };
    visibility.is_some_and(|tokens| tokens.last() == Some(&"pub"))
}

/// Whether `path` lies in the awscli-config crate's sources.
fn in_config_crate(path: &Path) -> bool {
    let names: Vec<_> = path
        .components()
        .map(|component| component.as_os_str().to_str().unwrap_or_default())
        .collect();
    names
        .windows(CONFIG_SOURCE_DIRECTORY.len())
        .any(|window| window == CONFIG_SOURCE_DIRECTORY)
}

/// The crates/awscli-config/src ratchet, which covers that module's tests
/// too: it reports `loop` and `dyn Error` trait objects. Each report names
/// the replacement.
fn check_config(
    path: &Path,
    source: &str,
    tokens: &[&str],
    report: &mut Report,
) -> Result<(), TaskError> {
    for (index, token) in tokens.iter().enumerate() {
        let (rule, detail) = match *token {
            "loop" => (Rule::UnboundedLoop, "bounded iteration"),
            "dyn" if erased_error(&tokens[index + 1..]) => {
                (Rule::ErasedError, "a composed error type")
            }
            _ => continue,
        };
        report.add(path, token_line(source, token), rule, detail.into())?;
    }
    Ok(())
}

/// Whether the trait path after `dyn` ends in `Error`, as in `dyn Error` or
/// `dyn std::error::Error + Send`.
fn erased_error(after: &[&str]) -> bool {
    let path = after.iter().take_while(|token| {
        **token == ":"
            || token
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
    });
    path.last() == Some(&"Error")
}

fn check_test_placement(
    path: &Path,
    source: &str,
    tokens: &[&str],
    report: &mut Report,
) -> Result<(), TaskError> {
    if path.file_name().is_some_and(|name| name == "tests.rs") {
        return Ok(());
    }
    let attributes = tokens
        .windows(4)
        .filter(|window| *window == ["#", "[", "test", "]"])
        .filter_map(|window| window.first());
    for attribute in attributes {
        let detail = "move unit tests into a sibling tests.rs".into();
        report.add(
            path,
            token_line(source, attribute),
            Rule::TestPlacement,
            detail,
        )?;
    }
    Ok(())
}

/// The one-based line of `token`, which `tokens` sliced out of `source`.
fn token_line(source: &str, token: &str) -> usize {
    let prefix = source
        .as_bytes()
        .get(..token_offset(source, token))
        .unwrap_or_default();
    prefix.iter().filter(|byte| **byte == b'\n').count() + 1
}

/// The byte offset of `token`, which `tokens` sliced out of `source`.
fn token_offset(source: &str, token: &str) -> usize {
    token.as_ptr().addr().saturating_sub(source.as_ptr().addr())
}

/// Tokenizes identifiers and punctuation, excluding comments and string contents.
fn tokens(source: &str) -> Vec<&str> {
    lexical_tokens(source)
        .into_iter()
        .filter(|token| skip_literal(token.as_bytes(), 0).is_none())
        .collect()
}

/// Preserves whole literals for attributes without interpreting their contents as code.
fn lexical_tokens(source: &str) -> Vec<&str> {
    let bytes = source.as_bytes();
    let mut result = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index..].starts_with(b"//") {
            index += bytes[index..]
                .iter()
                .position(|byte| *byte == b'\n')
                .unwrap_or(bytes.len() - index);
        } else if bytes[index..].starts_with(b"/*") {
            index = skip_comment(bytes, index);
        } else if let Some(end) = skip_literal(bytes, index) {
            result.push(&source[index..end]);
            index = end;
        } else if bytes[index].is_ascii_alphanumeric() || bytes[index] == b'_' {
            let start = index;
            while index < bytes.len()
                && (bytes[index].is_ascii_alphanumeric() || bytes[index] == b'_')
            {
                index += 1;
            }
            result.push(&source[start..index]);
        } else {
            let start = index;
            let Some(character) = source[index..].chars().next() else {
                break;
            };
            index += character.len_utf8();
            if !character.is_whitespace() {
                result.push(&source[start..index]);
            }
        }
    }
    result
}

fn skip_literal(bytes: &[u8], start: usize) -> Option<usize> {
    let mut index = start;
    if matches!(bytes.get(index), Some(b'b' | b'c')) {
        index += 1;
    }
    match bytes.get(index)? {
        b'"' => Some(skip_string(bytes, index)),
        b'\'' => skip_character(bytes, index),
        b'r' => skip_raw_string(bytes, index + 1),
        _ => None,
    }
}

fn skip_raw_string(bytes: &[u8], mut index: usize) -> Option<usize> {
    let start = index;
    while bytes.get(index) == Some(&b'#') {
        index += 1;
    }
    let hashes = index - start;
    if bytes.get(index) != Some(&b'"') {
        return None;
    }
    index += 1;
    while index < bytes.len() {
        if bytes[index] == b'"'
            && bytes
                .get(index + 1..index + 1 + hashes)
                .is_some_and(|suffix| suffix.iter().all(|byte| *byte == b'#'))
        {
            return Some(index + 1 + hashes);
        }
        index += 1;
    }
    Some(bytes.len())
}

fn skip_character(bytes: &[u8], start: usize) -> Option<usize> {
    let first = *bytes.get(start + 1)?;
    let end = if first == b'\\' {
        let offset = bytes
            .get(start + 3..)?
            .iter()
            .position(|byte| *byte == b'\'')?;
        start + 3 + offset
    } else {
        let width = match first {
            0..=127 => 1,
            192..=223 => 2,
            224..=239 => 3,
            240..=247 => 4,
            _ => return None,
        };
        start + 1 + width
    };
    (bytes.get(end) == Some(&b'\'')).then_some(end + 1)
}

fn skip_string(bytes: &[u8], start: usize) -> usize {
    let mut index = start + 1;
    while index < bytes.len() {
        match bytes[index] {
            b'\\' => index = (index + 2).min(bytes.len()),
            b'"' => return index + 1,
            _ => index += 1,
        }
    }
    index
}

fn skip_comment(bytes: &[u8], start: usize) -> usize {
    let mut index = start + 2;
    let mut depth = 1;
    while index + 1 < bytes.len() {
        if bytes[index..].starts_with(b"/*") {
            depth += 1;
            index += 2;
        } else if bytes[index..].starts_with(b"*/") {
            depth -= 1;
            index += 2;
            if depth == 0 {
                return index;
            }
        } else {
            index += 1;
        }
    }
    bytes.len()
}

#[cfg(test)]
mod tests;
