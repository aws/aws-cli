use std::{
    env, fs,
    io::{self, Write},
    process::Command,
};
fn main() -> io::Result<()> {
    let mut output = io::stdout().lock();
    let path = "../../deps/pins.toml";
    let text = fs::read_to_string(path)?;
    let crt = text
        .lines()
        .find_map(|line| line.strip_prefix("awscrt_version = "))
        .ok_or_else(|| io::Error::other(format!("{path} has no awscrt_version")))?
        .trim_matches(['\'', '"']);
    writeln!(output, "cargo:rerun-if-changed={path}")?;
    writeln!(output, "cargo:rustc-env=AWSCRT_VERSION={crt}")?;
    writeln!(output, "cargo:rerun-if-env-changed=RUSTC")?;
    writeln!(output, "cargo:rustc-env=RUST_VERSION={}", rustc_version()?)?;
    writeln!(output, "cargo:rustc-check-cfg=cfg(aws_optimized)")?;
    if env::var("OPT_LEVEL").is_ok_and(|level| level != "0") {
        writeln!(output, "cargo:rustc-cfg=aws_optimized")?;
    }
    Ok(())
}
fn rustc_version() -> io::Result<String> {
    let rustc = env::var_os("RUSTC").unwrap_or_else(|| "rustc".into());
    let reply = Command::new(&rustc).arg("--version").output()?;
    let text = String::from_utf8_lossy(&reply.stdout);
    let mut words = text.split_whitespace();
    match (reply.status.success(), words.next(), words.next()) {
        (true, Some("rustc"), Some(version)) if is_release(version) => Ok(version.to_owned()),
        _ => Err(io::Error::other(format!(
            "{} --version replied {:?}, not `rustc <release> ...`",
            rustc.to_string_lossy(),
            text.trim()
        ))),
    }
}
fn is_release(version: &str) -> bool {
    let (release, suffix) = match version.split_once('-') {
        Some((release, suffix)) if !suffix.is_empty() => (release, suffix),
        Some(_) => return false,
        None => (version, ""),
    };
    let numeric = |part: &str| !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_digit());
    release.split('.').count() == 3
        && release.split('.').all(numeric)
        && suffix
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'.')
}
