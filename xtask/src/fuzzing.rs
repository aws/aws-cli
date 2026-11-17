//! Coverage-guided model campaigns on the pinned analysis toolchain.
//!
//! `cargo xtask fuzz [--target NAME] [--runs N] [--time SECONDS] [--seed N]`
//! runs one campaign per target, each starting from its campaign corpus under
//! `target/fuzz-campaign/corpus/` and its curated inputs under
//! `fuzz/corpus/`. libFuzzer writes new inputs only to the campaign corpus,
//! which persists across runs. `cargo xtask fuzz --merge [--target NAME]`
//! minimizes each campaign corpus instead.

use crate::{TaskError, deps, process};
use std::fs;
use std::hash::{BuildHasher, RandomState};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

const TARGETS: [&str; 11] = [
    "pool_reservations",
    "pool_ownership",
    "pool_operations",
    "writer_ranges",
    "writer_pages",
    "writer_retries",
    "writer_output",
    "scheduler_orderings",
    "scheduler_phases",
    "path_containment",
    "error_body",
];
const RUNNER_VERSION: &str = "cargo-fuzz 0.13.2";
/// The longest input any campaign mutates. Each model bounds its own loops,
/// and a choice reads one or two bytes, so the deepest trace, about 1,600
/// choices of `writer_retries`, fits.
const LENGTH_MAX: usize = 4096;
/// The executions of a campaign given no budget: the CI budget.
const RUNS_DEFAULT: u32 = 1000;
/// AddressSanitizer's quarantine for campaigns, in megabytes. The
/// quarantine counts the bytes a freed allocation asked for, not the chunk it
/// holds, and the direct writer's bounce buffers are page-aligned
/// allocations of a few dozen bytes. Under the default of 256 MB,
/// `writer_retries` passes libFuzzer's 2 GB RSS limit within about 40,000
/// executions while its live heap stays near 25 MB. Under 16 MB its RSS levels
/// off near 1.3 GB, and the quarantine still holds the frees of many
/// executions.
const ASAN_QUARANTINE_MB: u32 = 16;

#[derive(Debug, Default, Eq, PartialEq)]
struct Options<'a> {
    /// libFuzzer's `-runs`, which counts the corpus load's executions too.
    runs: Option<u32>,
    /// libFuzzer's `-max_total_time`, in seconds.
    time: Option<u32>,
    /// libFuzzer's `-seed`; a random one when absent.
    seed: Option<u32>,
    /// Minimize each campaign corpus instead of running a campaign.
    merge: bool,
    target: Option<&'a str>,
}

pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    deps::native_host()?;
    let options = options(args)?;
    let version = process::output(Command::new("cargo").args(["fuzz", "--version"]))?;
    if String::from_utf8_lossy(&version.stdout).trim() != RUNNER_VERSION {
        return Err(deps::error(format!(
            "install the pinned runner: cargo install cargo-fuzz --version 0.13.2 --locked; \
             expected {RUNNER_VERSION}"
        )));
    }
    let nightly = analysis_toolchain(root)?;
    let link = link_flags(root)?;
    for target in TARGETS {
        if options.target.is_some_and(|selected| selected != target) {
            continue;
        }
        let mut command = Command::new("cargo");
        command
            .current_dir(root)
            .arg(format!("+{nightly}"))
            .args(["fuzz", "run", target]);
        if let Some(flags) = &link {
            // cargo-fuzz appends these to the flags it sets.
            command.env("RUSTFLAGS", flags);
        }
        // cargo-fuzz appends its own option to these.
        let inherited = std::env::var("ASAN_OPTIONS").ok();
        command.env("ASAN_OPTIONS", sanitizer_options(inherited.as_deref()));
        if options.merge {
            merge(root, target, command)?;
        } else {
            campaign(root, target, &options, command)?;
        }
    }
    Ok(())
}

/// Runs one campaign over the target's campaign corpus, which it creates
/// when absent and never clears, and its curated inputs, which libFuzzer
/// reads but never writes.
fn campaign(
    root: &Path,
    target: &str,
    options: &Options<'_>,
    mut command: Command,
) -> Result<(), TaskError> {
    let corpus = campaign_corpus(root, target);
    fs::create_dir_all(&corpus)?;
    let seed = options.seed.unwrap_or_else(random_seed);
    writeln!(
        io::stdout(),
        "fuzz: {target}, {}, seed {seed}",
        budget_text(options)
    )?;
    command.arg(&corpus);
    let curated = root.join("fuzz/corpus").join(target);
    if curated.is_dir() {
        command.arg(curated);
    }
    command
        .arg("--")
        .args(budget_flags(options))
        .arg(format!("-seed={seed}"))
        .arg(format!("-max_len={LENGTH_MAX}"));
    process::run(&mut command)
}

/// Minimizes the target's campaign corpus with libFuzzer's `-merge=1` into a
/// fresh directory, which then replaces it.
fn merge(root: &Path, target: &str, mut command: Command) -> Result<(), TaskError> {
    let corpus = campaign_corpus(root, target);
    if !corpus.is_dir() {
        writeln!(
            io::stdout(),
            "fuzz: {target} has no campaign corpus to merge"
        )?;
        return Ok(());
    }
    let merged = root.join("target/fuzz-campaign/merged").join(target);
    if merged.exists() {
        fs::remove_dir_all(&merged)?;
    }
    fs::create_dir_all(&merged)?;
    writeln!(io::stdout(), "fuzz: merging the {target} campaign corpus")?;
    command
        .arg(&merged)
        .arg(&corpus)
        .args(["--", "-merge=1", &format!("-max_len={LENGTH_MAX}")]);
    process::run(&mut command)?;
    fs::remove_dir_all(&corpus)?;
    fs::rename(&merged, &corpus)?;
    Ok(())
}

/// The AddressSanitizer options a campaign runs with: `inherited`, plus the
/// campaign quarantine unless `inherited` sets one.
fn sanitizer_options(inherited: Option<&str>) -> String {
    let inherited = inherited.unwrap_or_default();
    if inherited.contains("quarantine_size_mb") {
        return inherited.to_owned();
    }
    let quarantine = format!("quarantine_size_mb={ASAN_QUARANTINE_MB}");
    if inherited.is_empty() {
        quarantine
    } else {
        format!("{inherited}:{quarantine}")
    }
}

/// Where a target's campaigns keep the inputs libFuzzer finds.
fn campaign_corpus(root: &Path, target: &str) -> PathBuf {
    root.join("target/fuzz-campaign/corpus").join(target)
}

/// libFuzzer's budget flags: the runs and time given, or the default runs.
fn budget_flags(options: &Options<'_>) -> Vec<String> {
    let mut flags = Vec::new();
    if let Some(runs) = options.runs {
        flags.push(format!("-runs={runs}"));
    }
    if let Some(time) = options.time {
        flags.push(format!("-max_total_time={time}"));
    }
    if flags.is_empty() {
        flags.push(format!("-runs={RUNS_DEFAULT}"));
    }
    flags
}

/// The budget as the campaign line prints it; a campaign stops at whichever
/// limit it meets first.
fn budget_text(options: &Options<'_>) -> String {
    match (options.runs, options.time) {
        (Some(runs), Some(time)) => format!("{runs} runs or {time} seconds"),
        (None, Some(time)) => format!("{time} seconds"),
        (runs, None) => format!("{} runs", runs.unwrap_or(RUNS_DEFAULT)),
    }
}

/// A seed from the standard library's per-process random hash keys. libFuzzer
/// reads a seed of 0 as a request to choose one itself, which it would not
/// print here, so the seed is at least 1.
fn random_seed() -> u32 {
    let word = RandomState::new().hash_one(std::process::id());
    u32::try_from(word % u64::from(u32::MAX)).unwrap_or(0) + 1
}

/// The rustc flags that link a Linux campaign through the pinned LLVM's
/// clang and lld, the linker of the release build, rather than the analysis
/// nightly's default: its bundled rust-lld on x86-64, the host's GNU ld on
/// aarch64. A campaign builds for the host's glibc target, since
/// AddressSanitizer rejects a statically linked libc, so it cannot link
/// through the release build's musl driver. None elsewhere: a macOS
/// campaign links with Apple's linker, as the release build does.
fn link_flags(root: &Path) -> Result<Option<String>, TaskError> {
    if !cfg!(target_os = "linux") {
        return Ok(None);
    }
    let tools = deps::toolchain(root, &deps::Pins::load(root)?)?;
    let mut flags = Vec::new();
    for (flag, path) in [
        ("-Clinker=", &tools.clang),
        ("-Clink-arg=--ld-path=", &tools.ld_lld),
    ] {
        // Cargo splits RUSTFLAGS at whitespace, and cargo-fuzz reads only it.
        let path = path
            .to_str()
            .filter(|path| !path.contains(char::is_whitespace))
            .ok_or_else(|| {
                deps::error(format!(
                    "RUSTFLAGS cannot carry the pinned LLVM path {}",
                    path.display()
                ))
            })?;
        flags.push(format!("{flag}{path}"));
    }
    Ok(Some(flags.join(" ")))
}

fn options(args: &[String]) -> Result<Options<'_>, TaskError> {
    let mut result = Options::default();
    let mut args = args.iter();
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--merge" => result.merge = true,
            "--runs" => result.runs = Some(positive(flag, args.next())?),
            "--time" => result.time = Some(positive(flag, args.next())?),
            "--seed" => result.seed = Some(positive(flag, args.next())?),
            "--target" => match args.next() {
                Some(value) if TARGETS.contains(&value.as_str()) => result.target = Some(value),
                value => {
                    return Err(deps::error(format!(
                        "unknown fuzz target: {}",
                        value.map_or("(none)", String::as_str)
                    )));
                }
            },
            _ => return Err(deps::error(format!("unknown fuzz option: {flag}"))),
        }
    }
    let budget = result.runs.is_some() || result.time.is_some() || result.seed.is_some();
    if result.merge && budget {
        return Err(deps::error("--merge takes only --target"));
    }
    Ok(result)
}

/// The positive u32 that follows `flag`.
fn positive(flag: &str, value: Option<&String>) -> Result<u32, TaskError> {
    value
        .and_then(|value| value.parse::<u32>().ok())
        .filter(|value| *value > 0)
        .ok_or_else(|| deps::error(format!("{flag} requires a positive u32")))
}

fn analysis_toolchain(root: &Path) -> Result<String, TaskError> {
    let value: toml::Value = toml::from_str(&fs::read_to_string(
        root.join("rust-analysis-toolchain.toml"),
    )?)
    .map_err(|error| deps::error(error.to_string()))?;
    value
        .get("toolchain")
        .and_then(|value| value.get("channel"))
        .and_then(toml::Value::as_str)
        .filter(|name| name.starts_with("nightly-"))
        .map(str::to_owned)
        .ok_or_else(|| deps::error("analysis toolchain must name a dated nightly"))
}

#[cfg(test)]
mod tests;
