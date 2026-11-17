use fearless_simd as _;
use pyload::{container, inspect};
use ruzstd as _;
use std::ffi::OsString;
use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    let result = run(
        &std::env::args_os().collect::<Vec<_>>(),
        &mut io::stdout(),
        &mut io::stderr(),
    );
    match result {
        Ok(code) => ExitCode::from(code),
        Err(_) => {
            let _ = io::stderr().write_all(b"error: WriteFailed\n");
            ExitCode::FAILURE
        }
    }
}
fn run(args: &[OsString], out: &mut dyn Write, err: &mut dyn Write) -> io::Result<u8> {
    let Some(mode) = inspect::run_mode(args) else {
        inspect::usage(err)?;
        return Ok(2);
    };
    let path = args[1].as_encoded_bytes();
    let file = match std::fs::File::open(&args[1]) {
        Ok(file) => file,
        Err(error) => {
            let name = inspect::open_error_name(&error);
            err.write_all(&[b"failed to open ", path, b": ", name.as_bytes(), b"\n"].concat())?;
            return Ok(1);
        }
    };
    let location = match container::locate_file(&file) {
        Ok(location) => location,
        Err(error) => {
            err.write_all(&inspect::locate_error(path, &error))?;
            return Ok(1);
        }
    };
    run_inspect(mode, args, out, err, &file, location)
}

fn run_inspect(
    mode: inspect::Mode,
    args: &[OsString],
    out: &mut dyn Write,
    err: &mut dyn Write,
    file: &std::fs::File,
    location: container::Location,
) -> io::Result<u8> {
    let bytes = match container::read_payload(file, location) {
        Ok(bytes) => bytes,
        Err(error) => {
            err.write_all(inspect::section_read_error(location.name, &error).as_bytes())?;
            return Ok(1);
        }
    };
    let located = container::Located {
        container: location.container,
        name: location.name,
        offset: location.offset,
        bytes: &bytes,
    };
    let parsed = inspect::exact_payload_bytes(located).and_then(pyload::parse);
    let payload = match parsed {
        Ok(payload) => payload,
        Err(error) => {
            err.write_all(inspect::payload_error(located.name, error).as_bytes())?;
            return Ok(1);
        }
    };
    render(mode, args, out, err, located, &payload)
}

fn render(
    mode: inspect::Mode,
    args: &[OsString],
    out: &mut dyn Write,
    err: &mut dyn Write,
    located: container::Located<'_>,
    payload: &pyload::Payload<'_>,
) -> io::Result<u8> {
    match mode {
        inspect::Mode::Summary => inspect::summary(out, located, payload)?,
        inspect::Mode::List => inspect::list(out, payload)?,
        inspect::Mode::ExpectModelOnly => {
            if let Err(message) = inspect::expect_model_only(payload, &args[3..]) {
                err.write_all(&message)?;
                return Ok(1);
            }
        }
    }
    Ok(0)
}
