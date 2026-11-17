//! Repeatable native verification and analysis-toolchain selection.
use crate::{TaskError, coverage, deps, lint, process, sanitizers};

mod options;
use options::{Mode, Options, options};
use std::fs;
use std::io::{self, Write};
use std::path::Path;
use std::process::Command;

/// S3 tests inside its Miri filters that Miri cannot finish.
const S3_MIRI_EXCLUSIONS: [&str; 3] = [
    // Binds a page with mbind, a syscall Miri does not emulate.
    "download::platform::tests::a_memory_probe_leaves_no_policy_on_the_page_it_bound",
    // Expects one pwrite to write both bytes, which Miri's short writes break.
    "download::platform::tests::positional_write_preserves_file_position_and_exact_length",
    // Fills and writes a 2 MiB body, which Miri takes over three minutes to do.
    "download::io::tests::large_misaligned_body_reuses_one_bounded_bounce_and_zeroes_only_its_tail",
];
/// The packages `-p` may name; each runs whole unless `MIRI_FILTERS` limits it.
const MIRI_PACKAGES: [&str; 9] = [
    "awscli-config",
    "awscli-argparse",
    "pyload",
    "numa",
    "cli-core",
    "crt",
    "s3",
    "cli-router",
    "python-fallback",
];
/// The packages Miri tests when none is named: those whose unit tests reach
/// their own unsafe code, or, in pyload, a dependency's. Miri finds undefined
/// behavior only in code built on unsafe. The others forbid it or keep it
/// behind Windows, the linker or CPython, and Miri spent over an hour
/// interpreting their safe parsers.
const MIRI_DEFAULT_PACKAGES: [&str; 5] = ["pyload", "numa", "cli-core", "crt", "s3"];
/// Packages whose Miri runs are limited to the tests matching fixed filters:
/// the tests that reach the package's unsafe code and that Miri can run.
/// Libtest filters match substrings, so a test's full name selects that test
/// and a module path selects every test under it.
const MIRI_FILTERS: [(&str, &[&str]); 4] = [
    // The tests that drive the third-party SIMD and zstd unsafe code:
    // fearless_simd's group matches and the small frames ruzstd decodes.
    (
        "pyload",
        &[
            "swiss_group::",
            "decompress::tests::decodes_concatenated_frames_and_checks_total_output",
            "decompress::tests::validates_trailing_frames_even_after_excess_output",
            "decompress::tests::accepts_skippable_frames_and_empty_input",
            "decompress::tests::rejects_a_frame_content_size_the_blocks_do_not_produce",
            "decompress::tests::rejects_a_block_larger_than_a_small_window",
            "decompress::tests::steps_over_a_content_checksum_to_the_next_frame",
        ],
    ),
    // The descriptor checks and the `uname` host facts. The other unsafe code
    // reaches signals, `getpwuid_r`, `O_PATH` opens or FIFOs, which Miri does
    // not emulate.
    (
        "cli-core",
        &[
            "startup::tests::only_a_closed_descriptor_reads_as_closed",
            "startup::tests::stdout_started_open_without_a_record",
            "client_config::tests::user_agent::tests::native_uname_supplies_nonempty_host_facts",
        ],
    ),
    // The source pool, the CRT callbacks its tests call without the CRT, and
    // the anonymous page mappings. The other crt tests call the CRT, which
    // Miri cannot run, and some name the source pool too.
    (
        "crt",
        &[
            "source_pool::",
            "runtime::native::tests::shutdown_callback_retains_signal_after_waiter_releases_owner",
            concat!(
                "s3::native::tests::body::tests::",
                "progress_forwarding_preserves_each_parts_bytes_without_finishing"
            ),
            "page_mapping::",
        ],
    ),
    // The download writers: aligned buffers, positional and direct writes,
    // and the outputs that choose between them over the native platform; the
    // fuzz models' replay tests, which run each script and eight sweep cases
    // through the writer's range, page and write loops, the shared writer
    // service's threads and the scheduler; and the `getrandom` loop that
    // names a download's temporary file.
    (
        "s3",
        &[
            "download::platform::tests::",
            "download::io::tests::",
            "download::output::tests::",
            "download::testing::tests::",
            "download::service::testing::tests::",
            "scheduler::model::",
            "transfer::tests::temp_name_ids_come_from_the_os_and_name_the_temp_file",
        ],
    ),
];
/// The packages TSan instruments. TSan needs glibc on Linux, so it builds
/// for the host's glibc target there, for which the C libraries crt and s3
/// link are not built; elsewhere the host's target is the product's, so
/// those packages link the prepared C libraries.
const THREAD_SANITIZER_PACKAGES: &[&str] = if cfg!(target_os = "linux") {
    &["cli-core"]
} else {
    &["cli-core", "crt", "s3"]
};
/// Packages whose TSan runs are limited to the tests matching a fixed filter.
const THREAD_SANITIZER_FILTERS: [(&str, &[&str]); 2] = [
    ("crt", &["source_pool::"]),
    ("cli-core", &["interrupt::concurrency"]),
];
pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    deps::native_host()?;
    let options = options(args)?;
    let filter = options.filter.as_deref();
    match options.mode {
        Mode::Workspace => workspace(root, &options),
        Mode::Miri => miri(root, &options.packages, filter),
        Mode::ThreadSanitizer => thread_sanitizer(root, &options.packages, filter),
        Mode::Coverage => coverage::run(root, &options.packages, filter),
        Mode::C(mode) => sanitizers::c(root, mode, &options.profile, filter),
    }
}

/// The default mode runs the repository source checks before `cargo test`.
/// A filtered run selects tests by name, so it skips the source checks.
fn workspace(root: &Path, options: &Options) -> Result<(), TaskError> {
    if options.filter.is_none() {
        lint::check_sources(root)?;
    }
    let environment = deps::native_environment(root, !cfg!(windows))?;
    let mut command = workspace_command(root, options);
    environment.apply(&mut command);
    environment.apply_test_tools(&mut command);
    environment.apply_link(&mut command);
    process::run(&mut command)
}

/// The tests of the product configuration: the target the product ships
/// for, under the dependency environment the caller applies.
fn workspace_command(root: &Path, options: &Options) -> Command {
    let mut command = Command::new("cargo");
    command.current_dir(root).args([
        "test",
        "--locked",
        "--profile",
        &options.profile,
        "--target",
        deps::TARGET,
    ]);
    if options.packages.is_empty() {
        command.arg("--workspace");
    } else {
        for package in &options.packages {
            command.args(["-p", package]);
        }
    }
    forward_filter(&mut command, options.filter.as_deref());
    command
}

/// Pass the libtest filter to a cargo test command after the test-binary
/// arguments it already has, opening them with `--` if it has none.
fn forward_filter(command: &mut Command, filter: Option<&str>) {
    let Some(filter) = filter else {
        return;
    };
    if !command.get_args().any(|argument| argument == "--") {
        command.arg("--");
    }
    command.arg(filter);
}

/// Apply the libtest filter to one analysis package. A package listed in
/// `fixed` runs only the tests matching its fixed filters. Libtest filters
/// match substrings and combine as alternatives, so a user filter honors
/// that limit only when it contains one of the fixed filters.
fn package_filter(
    command: &mut Command,
    harness: &str,
    package: &str,
    fixed: &[(&str, &[&str])],
    filter: Option<&str>,
) -> Result<(), TaskError> {
    let Some((_, fixed)) = fixed.iter().find(|(name, _)| *name == package) else {
        forward_filter(command, filter);
        return Ok(());
    };
    match filter {
        None => {
            for fixed in *fixed {
                forward_filter(command, Some(fixed));
            }
        }
        Some(filter) if fixed.iter().any(|fixed| filter.contains(fixed)) => {
            forward_filter(command, Some(filter));
        }
        Some(filter) => {
            let fixed = fixed.join(" or ");
            return Err(error(format!(
                "{harness} runs only the {package} tests matching {fixed}; --filter {filter} \
                must contain {fixed}, or select other packages with -p"
            )));
        }
    }
    Ok(())
}

fn analysis_toolchain(root: &Path) -> Result<String, TaskError> {
    let value: toml::Value = toml::from_str(&fs::read_to_string(
        root.join("rust-analysis-toolchain.toml"),
    )?)
    .map_err(|e| error(e.to_string()))?;
    value
        .get("toolchain")
        .and_then(|v| v.get("channel"))
        .and_then(toml::Value::as_str)
        .filter(|name| name.starts_with("nightly-"))
        .map(str::to_owned)
        .ok_or_else(|| error("analysis toolchain must name a dated nightly"))
}
fn analysis_command(root: &Path) -> Result<Command, TaskError> {
    let mut command = Command::new("cargo");
    command
        .arg(format!("+{}", analysis_toolchain(root)?))
        .current_dir(root);
    Ok(command)
}
fn packages<'a>(
    requested: &'a [String],
    allowed: &'a [&'a str],
) -> Result<Vec<&'a str>, TaskError> {
    if requested.is_empty() {
        return Ok(allowed.to_vec());
    }
    requested
        .iter()
        .map(|name| {
            if allowed.contains(&name.as_str()) {
                Ok(name.as_str())
            } else {
                Err(error(format!("{name} is outside this analysis harness")))
            }
        })
        .collect()
}
/// Miri builds no C, but python-fallback's build script still copies the
/// prepared payload's generated sources, so every Miri run gets the
/// dependency environment.
fn miri(root: &Path, requested: &[String], filter: Option<&str>) -> Result<(), TaskError> {
    let commands = miri_commands(root, requested, filter)?;
    let environment = deps::native_environment(root, !cfg!(windows))?;
    for mut command in commands {
        environment.apply(&mut command);
        process::run(&mut command)?;
    }
    writeln!(
        io::stdout(),
        "Miri: by default checks only the unit tests that reach unsafe code it can run; \
        name other packages with -p. Tests of the CRT, CPython, signals and syscalls \
        Miri does not emulate, and a 2 MiB S3 write, remain covered by native tests; \
        concurrency stress runs under TSan."
    )?;
    Ok(())
}
fn miri_commands(
    root: &Path,
    requested: &[String],
    filter: Option<&str>,
) -> Result<Vec<Command>, TaskError> {
    let selected = if requested.is_empty() {
        MIRI_DEFAULT_PACKAGES.to_vec()
    } else {
        packages(requested, &MIRI_PACKAGES)?
    };
    let mut commands = Vec::new();
    for package in selected {
        let mut command = analysis_command(root)?;
        command.args(["miri", "test", "--locked", "--lib", "-p", package]);
        command.env("MIRIFLAGS", "-Zmiri-disable-isolation");
        if package == "s3" {
            command.arg("--");
            for name in S3_MIRI_EXCLUSIONS {
                command.args(["--skip", name]);
            }
        }
        package_filter(&mut command, "Miri", package, &MIRI_FILTERS, filter)?;
        commands.push(command);
    }
    Ok(commands)
}
fn thread_sanitizer(
    root: &Path,
    requested: &[String],
    filter: Option<&str>,
) -> Result<(), TaskError> {
    let target = host_target(root)?;
    let commands = thread_sanitizer_commands(root, requested, &target, filter)?;
    let environment = if target == deps::TARGET {
        Some(deps::native_environment(root, !cfg!(windows))?)
    } else {
        None
    };
    for mut command in commands {
        if let Some(environment) = &environment {
            environment.apply(&mut command);
        }
        process::run(&mut command)?;
    }
    writeln!(
        io::stdout(),
        "TSan: instrumented the standard library and the library tests of the selected \
        workspace packages, as their fixed filters limit them; excludes C CRT and native \
        signal/syscall adapters."
    )?;
    Ok(())
}

fn thread_sanitizer_commands(
    root: &Path,
    requested: &[String],
    target: &str,
    filter: Option<&str>,
) -> Result<Vec<Command>, TaskError> {
    let mut commands = Vec::new();
    for package in packages(requested, THREAD_SANITIZER_PACKAGES)? {
        let mut command = thread_sanitizer_command(root, target)?;
        command.args(["--lib", "-p", package]);
        package_filter(
            &mut command,
            "TSan",
            package,
            &THREAD_SANITIZER_FILTERS,
            filter,
        )?;
        commands.push(command);
    }
    Ok(commands)
}

fn thread_sanitizer_command(root: &Path, target: &str) -> Result<Command, TaskError> {
    let mut command = analysis_command(root)?;
    command.args(["test", "--locked", "-Zbuild-std", "--target", target]);
    command.env("RUSTFLAGS", "-Zsanitizer=thread");
    command.env("TSAN_OPTIONS", "halt_on_error=1");
    command.env("CARGO_TARGET_DIR", root.join("target/analysis/tsan"));
    Ok(command)
}
fn host_target(root: &Path) -> Result<String, TaskError> {
    let output = process::output(Command::new("rustc").current_dir(root).arg("-vV"))?;
    String::from_utf8_lossy(&output.stdout)
        .lines()
        .find_map(|line| line.strip_prefix("host: ").map(str::to_owned))
        .ok_or_else(|| error("rustc host missing"))
}
fn error(message: impl Into<String>) -> TaskError {
    TaskError::Message(message.into())
}

#[cfg(test)]
mod tests;
