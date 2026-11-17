//! Local and hosted CI share the same dependency and guarded product phases.
//! `runtime` and `checks` partition the product sequence onto independent
//! runners; `product` runs them all in one local sequence. Build options
//! after a product phase are validated once and forwarded to the children
//! that accept them.
use crate::product::options::{self as build_options, DEFAULT_PROFILE, LinkMode, PythonPayload};
use crate::{TaskError, deps, process, sanitizers};
use std::fmt;
use std::io::{self, Write};
use std::path::Path;
use std::process::Command;
use std::time::Instant;

#[derive(Clone, Copy, Eq, PartialEq)]
enum Host {
    Linux,
    Macos,
    Windows,
}

impl Host {
    fn current() -> Self {
        if cfg!(target_os = "linux") {
            Self::Linux
        } else if cfg!(windows) {
            Self::Windows
        } else {
            // The public entrypoint already rejected unsupported native hosts.
            Self::Macos
        }
    }
}

/// One of the independent runner partitions of the product sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Lane {
    /// The default-profile product, its blackbox runs, and integration collection.
    Runtime,
    /// Source checks, development and default-profile unit, sanitizer,
    /// harness, parser, and fuzz checks.
    Checks,
}

/// One product command and the lane that runs it on an isolated runner.
struct ProductCommand {
    lane: Lane,
    arguments: Vec<String>,
}

/// Build options given after a product phase, validated once by the
/// `cargo xtask build` option parser, and what each command kind receives.
#[derive(Debug, PartialEq, Eq)]
struct Forwarded {
    /// The options as given, which every `xtask build` child receives.
    build: Vec<String>,
    /// The target triple whose directory holds the built artifacts.
    target: String,
    /// The options that tell `xtask blackbox` which build it tests.
    blackbox: Vec<String>,
}

impl Forwarded {
    /// Validate `args` as `cargo xtask build` does, including the host check
    /// of the selected link mode. `--profile` and `--sanitize-c` are refused
    /// because the sequence sets them per child.
    fn parse(args: &[String]) -> Result<Self, TaskError> {
        reject_sequence_options(args)?;
        let options = build_options::parse(args)?;
        Ok(Self {
            build: args.to_vec(),
            blackbox: blackbox_options(&options),
            target: options.target,
        })
    }

    /// Append the options a command kind accepts. `build` takes them all
    /// and `blackbox` the description of the build it tests; `test` has no
    /// product options and tests the default static configuration, and the
    /// remaining commands build nothing the options select. Every harness
    /// consumes the artifact under the forwarded target.
    fn apply(&self, mut arguments: Vec<String>) -> Vec<String> {
        let options = match arguments.as_slice() {
            [xtask, kind, ..] if xtask == "xtask" && kind == "build" => &self.build,
            [xtask, kind, ..] if xtask == "xtask" && kind == "blackbox" => &self.blackbox,
            _ => return arguments,
        };
        arguments.extend(options.iter().cloned());
        arguments
    }
}

/// The `xtask blackbox` options that describe a system build, whose
/// executable and payload tests check its own linkage; a static build
/// needs none.
fn blackbox_options(options: &build_options::Options) -> Vec<String> {
    if options.link_mode != LinkMode::System {
        return Vec::new();
    }
    let mut blackbox = owned(&["--link-mode", "system"]);
    if options.crt_static_prefix.is_some() {
        blackbox.extend(owned(&["--crt-link", "static"]));
    }
    if options.python_payload == PythonPayload::System {
        blackbox.extend(owned(&["--python-payload", "system"]));
    }
    blackbox.push("--python-exe".to_owned());
    blackbox.push(options.python_exe.display().to_string());
    blackbox
}

/// Walk `args` as the build option parser does, refusing a stray word and
/// the options the sequence sets itself.
fn reject_sequence_options(args: &[String]) -> Result<(), TaskError> {
    let mut tokens = args.iter();
    while let Some(token) = tokens.next() {
        if token == "--download-writer-debug" {
            continue;
        }
        let flag = match token.split_once('=') {
            Some((flag, _)) => flag,
            None => {
                tokens.next();
                token.as_str()
            }
        };
        if !flag.starts_with("--") {
            return Err(deps::error(format!("unexpected CI argument: {token}")));
        }
        if matches!(flag, "--profile" | "--sanitize-c") {
            return Err(deps::error(format!("{flag} is set by each CI command")));
        }
    }
    Ok(())
}

const USAGE: &str = "usage: cargo xtask ci deps | \
                     cargo xtask ci product|runtime|checks [BUILD OPTION...]";

/// The phase comes first, then its options, so the host check can follow
/// them. `deps` prepares the static dependency stages and keeps the static
/// host list. A product phase takes the check of its forwarded link mode,
/// which `Forwarded::parse` applies through the `cargo xtask build` option
/// parser: the static host list, or for system mode a native Linux/glibc
/// host of an architecture `build_support::SYSTEM_ARCHITECTURES` lists. The
/// children that build or run the static configuration whatever the options
/// (`xtask test`, `check-argparse`, `fuzz-argparse`, `fuzz`, and
/// `harness-test`) still take the static host list, so on a glibc host
/// outside it a system sequence stops at the first of them.
pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    let Some((phase, options)) = args.split_first() else {
        return Err(deps::error(USAGE));
    };
    if phase == "deps" && options.is_empty() {
        deps::native_host()?;
        return dependencies(root);
    }
    let phase = Phase::parse(phase).ok_or_else(|| deps::error(USAGE))?;
    let forwarded =
        Forwarded::parse(options).map_err(|error| deps::error(format!("{error}\n{USAGE}")))?;
    let commands = phase_commands_for(Host::current(), phase, &forwarded);
    sequence(root, &commands)
}

/// A product phase: the whole sequence, or one runner lane's partition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Product,
    Lane(Lane),
}

impl Phase {
    fn parse(name: &str) -> Option<Self> {
        match name {
            "product" => Some(Self::Product),
            "runtime" => Some(Self::Lane(Lane::Runtime)),
            "checks" => Some(Self::Lane(Lane::Checks)),
            _ => None,
        }
    }
}

/// `product` runs every command in local order; a lane runs its partition.
fn phase_commands_for(host: Host, phase: Phase, forwarded: &Forwarded) -> Vec<Vec<String>> {
    match phase {
        Phase::Product => product_commands_for(host, forwarded),
        Phase::Lane(lane) => partition_for(host, lane, forwarded),
    }
}

/// Prepare every dependency the lanes use and record their roots in
/// `deps::ROOTS_FILE`, from which CI compacts the snapshot it saves.
fn dependencies(root: &Path) -> Result<(), TaskError> {
    let mut roots = deps::dependency_roots(root, &["all".into()])?;
    if Host::current() == Host::Linux {
        let runtime = sanitizers::prepare(root)?;
        writeln!(io::stdout(), "UBSan runtime: {}", runtime.display())?;
        roots.insert("ubsan-minimal", sanitizers::runtime_prefix(&runtime)?);
    }
    roots.write(&mut io::stdout().lock())?;
    roots.save(&root.join(deps::ROOTS_FILE))?;
    process::run(
        Command::new("cargo")
            .current_dir(root)
            .args(["fetch", "--locked"]),
    )?;
    process::run(Command::new("cargo").current_dir(root).args([
        "fetch",
        "--locked",
        "--manifest-path",
        "fuzz/Cargo.toml",
    ]))?;
    install_fuzzer(root)?;
    Ok(())
}

fn install_fuzzer(root: &Path) -> Result<(), TaskError> {
    let installed = process::output(Command::new("cargo").args(["fuzz", "--version"]))
        .is_ok_and(|output| String::from_utf8_lossy(&output.stdout).trim() == "cargo-fuzz 0.13.2");
    if !installed {
        deps::guard("cargo-fuzz")?;
        process::run(Command::new("cargo").current_dir(root).args([
            "install",
            "cargo-fuzz",
            "--version",
            "0.13.2",
            "--locked",
            "--force",
        ]))?;
    }
    Ok(())
}

/// Run the commands in order; the first failure stops the sequence.
fn sequence(root: &Path, commands: &[Vec<String>]) -> Result<(), TaskError> {
    for arguments in commands {
        run_child(root, arguments)?;
    }
    Ok(())
}

/// Report each child's command and elapsed time, including a failed child's.
/// A child that cannot start reports no elapsed time.
fn run_child(root: &Path, arguments: &[String]) -> Result<(), TaskError> {
    let label = label(arguments);
    writeln!(io::stderr(), "ci command: {label}")?;
    let start = Instant::now();
    let mut child = process::spawn(&mut product_command(root, arguments))
        .map_err(|error| deps::error(format!("unable to spawn cargo: {error}")))?;
    let status = child
        .wait()
        .map_err(|error| deps::error(format!("unable to wait for cargo: {error}")))?;
    writeln!(
        io::stderr(),
        "ci elapsed: {}ms: {label}",
        start.elapsed().as_millis()
    )?;
    if status.success() {
        Ok(())
    } else {
        Err(failure(&label, &status))
    }
}

fn label(arguments: &[String]) -> String {
    format!("cargo {}", arguments.join(" "))
}

/// A failed child's error names its whole command line, not the program
/// alone.
fn failure(label: &str, status: &dyn fmt::Display) -> TaskError {
    deps::error(format!("ci command failed: {label}: {status}"))
}

fn product_command(root: &Path, arguments: &[String]) -> Command {
    let mut command = Command::new("cargo");
    command
        .current_dir(root)
        .args(arguments)
        .env("AWSCLI_FORBID_EXPENSIVE_BUILDS", "1");
    command
}

fn artifact(target: &str, profile: &str) -> String {
    let executable = if cfg!(windows) { "aws.exe" } else { "aws" };
    format!("target/{target}/{profile}/{executable}")
}

fn product_commands_for(host: Host, forwarded: &Forwarded) -> Vec<Vec<String>> {
    lane_inventory_for(host, forwarded)
        .into_iter()
        .map(|command| command.arguments)
        .collect()
}

/// The commands a lane owns, in product order; the lanes partition `product`.
fn partition_for(host: Host, lane: Lane, forwarded: &Forwarded) -> Vec<Vec<String>> {
    lane_inventory_for(host, forwarded)
        .into_iter()
        .filter(|command| command.lane == lane)
        .map(|command| command.arguments)
        .collect()
}

const RELEASE_BUILD: [&str; 4] = ["xtask", "build", "--profile", DEFAULT_PROFILE];

fn owned(arguments: &[&str]) -> Vec<String> {
    arguments.iter().copied().map(str::to_owned).collect()
}

/// The product sequence in local order, each command in its lane, with the
/// forwarded build options.
fn lane_inventory_for(host: Host, forwarded: &Forwarded) -> Vec<ProductCommand> {
    let release = artifact(&forwarded.target, DEFAULT_PROFILE);
    let mut commands = Vec::new();
    let mut add = |lane, arguments: &[&str]| {
        commands.push(ProductCommand {
            lane,
            arguments: forwarded.apply(owned(arguments)),
        });
    };
    // `xtask lint` runs the repository source checks, rustfmt, and Clippy
    // over the configuration the tests build.
    add(Lane::Checks, &["xtask", "lint"]);
    add(Lane::Checks, &["xtask", "test"]);
    add(
        Lane::Checks,
        &["xtask", "test", "--profile", DEFAULT_PROFILE],
    );
    add(Lane::Checks, &["xtask", "harness-test"]);
    // Every command runs on every host unless the platform cannot run it.
    // The sanitized test links the pinned musl UBSan runtime, which exists
    // only for the Linux musl toolchain.
    if host == Host::Linux {
        add(Lane::Checks, &SANITIZED_TEST);
    }
    add(Lane::Runtime, &RELEASE_BUILD);
    blackbox(&mut add, &release);
    add(Lane::Checks, &["xtask", "check-argparse"]);
    add(Lane::Checks, &["xtask", "fuzz-argparse"]);
    // The model fuzz campaigns run on the checks runner. The Windows fuzz
    // targets link the MSVC AddressSanitizer runtime DLL, which the runner
    // does not put on PATH, so they cannot start there yet.
    if host != Host::Windows {
        add(Lane::Checks, &["xtask", "fuzz", "--runs", "1000"]);
    }
    // Collection drives the default-profile product like the other
    // binary harnesses on the runtime runner.
    add(
        Lane::Runtime,
        &[
            "xtask",
            "integ",
            "--aws-binary",
            &release,
            "--",
            "--collect-only",
        ],
    );
    commands
}

/// The blackbox runs of the release product `release`: its default
/// configuration, then the oracle for the repository's tests, the same
/// binary on the Python route, which runs the in-tree AWS CLI and passes them
/// all but the launcher differences and upstream issues its ledger lists.
fn blackbox(add: &mut impl FnMut(Lane, &[&str]), release: &str) {
    add(
        Lane::Runtime,
        &["xtask", "blackbox", "--aws-binary", release],
    );
    add(
        Lane::Runtime,
        &[
            "xtask",
            "blackbox",
            "--aws-binary",
            release,
            "--suite",
            "repo",
            "--env",
            "AWS_CLI_NATIVE_ROUTER=python",
        ],
    );
}

const SANITIZED_TEST: [&str; 6] = [
    "xtask",
    "test",
    "--sanitize-c",
    "full",
    "--profile",
    DEFAULT_PROFILE,
];

#[cfg(test)]
mod tests;
