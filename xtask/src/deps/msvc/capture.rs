//! Bounded stdout and stderr capture for native tool discovery.
//!
//! Stdin is the null device, an overflow or read failure kills the child and
//! returns at once, and every failure names the program.

use std::io::{self, Read, Write};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::mpsc;

use crate::deps::{Result, error};
use crate::process;

/// Run `command` and return its stdout, each stream bounded by `limit` bytes.
///
/// A nonzero exit writes both captured streams to stderr before failing with
/// `{program} failed`.
pub(super) fn output(command: &mut Command, limit: usize) -> Result<String> {
    let program = command.get_program().to_string_lossy().into_owned();
    let (status, [stdout, stderr]) = run(command, limit, &program)?;
    if !status.success() {
        let mut report = io::stderr().lock();
        report.write_all(&stdout)?;
        report.write_all(&stderr)?;
        report.flush()?;
        return Err(error(format!("{program} failed")));
    }
    String::from_utf8(stdout)
        .map_err(|failure| error(format!("{program} did not emit UTF-8: {failure}")))
}

/// The stdout of a probe that exits zero, or `None` without reporting
/// anything, whatever the failure: the Perl probe skips any candidate whose
/// probe fails.
pub(super) fn probe(command: &mut Command, limit: usize) -> Option<String> {
    let program = command.get_program().to_string_lossy().into_owned();
    match run(command, limit, &program) {
        Ok((status, [stdout, _])) if status.success() => String::from_utf8(stdout).ok(),
        _ => None,
    }
}

/// Spawn with null stdin and piped output, then capture both streams.
fn run(command: &mut Command, limit: usize, program: &str) -> Result<(ExitStatus, [Vec<u8>; 2])> {
    command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = process::spawn(command).map_err(|failure| unable(program, &failure))?;
    let streams = streams(&mut child, limit).map_err(|failure| unable(program, &failure))?;
    let status = child.wait().map_err(|failure| unable(program, &failure))?;
    Ok((status, streams))
}

fn unable(program: &str, failure: &dyn std::fmt::Display) -> crate::TaskError {
    error(format!("unable to run {program}: {failure}"))
}

/// Read both streams on detached threads that own their pipes.
///
/// On the first overflow or read failure the child is killed and reaped,
/// and the error returns without waiting for the other reader, which a
/// grandchild holding its pipe open could keep blocked indefinitely.
fn streams(child: &mut Child, limit: usize) -> std::result::Result<[Vec<u8>; 2], String> {
    let stdout = child.stdout.take().ok_or("missing stdout pipe")?;
    let stderr = child.stderr.take().ok_or("missing stderr pipe")?;
    let (send, receive) = mpsc::channel();
    for (index, stream) in [
        (0, Box::new(stdout) as Box<dyn Read + Send>),
        (1, Box::new(stderr) as Box<dyn Read + Send>),
    ] {
        let send = send.clone();
        std::thread::spawn(move || {
            let mut bytes = Vec::new();
            let result = stream.take(limit as u64 + 1).read_to_end(&mut bytes);
            let _ = send.send((index, result.map(|_| bytes)));
        });
    }
    drop(send);
    let mut streams = [Vec::new(), Vec::new()];
    for (index, result) in receive {
        let failure = match result {
            Ok(bytes) if bytes.len() <= limit => {
                streams[index] = bytes;
                continue;
            }
            // An overflow is reported as StreamTooLong.
            Ok(_) => "StreamTooLong".to_owned(),
            Err(failure) => failure.to_string(),
        };
        let _ = child.kill();
        let _ = child.wait();
        return Err(failure);
    }
    Ok(streams)
}
