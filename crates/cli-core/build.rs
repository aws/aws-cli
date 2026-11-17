//! Read the AWS CLI's version from the tracked upstream source.
use std::{
    fs,
    io::{self, Write},
};
fn main() -> io::Result<()> {
    let path = "../../aws-cli/awscli/__init__.py";
    let text = fs::read_to_string(path)?;
    let version = text
        .lines()
        .find_map(|line| line.strip_prefix("__version__ = "))
        .ok_or_else(|| io::Error::other(format!("{path} has no __version__")))?
        .trim_matches(['\'', '"']);
    let mut output = io::stdout().lock();
    writeln!(output, "cargo:rerun-if-changed={path}")?;
    writeln!(output, "cargo:rustc-env=AWS_CLI_UPSTREAM_VERSION={version}")
}
