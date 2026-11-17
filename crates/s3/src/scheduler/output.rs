use super::*;
use crate::download::{CloseError, SharedWriterService, WriteError};

pub(super) fn finalize(job: &Job, result: &TransferResult) -> Finalize {
    let output = lock(&job.output).prepared.take();
    let Some(output) = output else {
        release_slot(job);
        if let Some(failure) = job.output_failure_result(result) {
            delete_temp(job);
            return failure;
        }
        if result.error_code != 0 {
            delete_temp(job);
            return Finalize::Transfer(Box::new(result.clone()));
        }
        return commit(job);
    };
    let concluded = output.finish(result.error_code == 0);
    let closed = output.close_file();
    release_slot(job);
    let failure = match (concluded, closed) {
        (Err(error), _) => Finalize::Write(crate::cp::write_error_name(&error)),
        _ if result.error_code != 0 => Finalize::Transfer(Box::new(result.clone())),
        (Ok(_), Err(error)) => Finalize::Write(close_error_name(error)),
        (Ok(_), Ok(())) => return commit(job),
    };
    delete_temp(job);
    failure
}
fn close_error_name(error: CloseError) -> String {
    crate::cp::write_error_name(&WriteError::Close(error))
}
fn commit(job: &Job) -> Finalize {
    let Some(temp) = &job.temp_path else {
        return Finalize::Success;
    };
    if let Err(failure) = transfer::complete_downloaded_temp_file(temp, &job.local_path) {
        return Finalize::Commit(failure);
    }
    if let Some(seconds) = job.modified
        && let Err(name) = transfer::set_destination_mtime(&job.local_path, seconds)
    {
        return Finalize::Mtime(name.into());
    }
    Finalize::Success
}
pub(super) fn abandon(job: &Job) {
    let output = lock(&job.output).prepared.take();
    if let Some(output) = output {
        output.discard();
        let _ = output.close_file();
    }
    release_slot(job);
    delete_temp(job);
}
fn delete_temp(job: &Job) {
    if let Some(temp) = &job.temp_path {
        transfer::delete_file_best_effort(temp);
    }
}
pub(super) fn retire(
    job: &Job,
    result: &TransferResult,
    await_shutdown: &dyn Fn(),
) -> Option<String> {
    let output = lock(&job.output).prepared.take();
    let concluded = output
        .as_ref()
        .map(|output| output.finish(result.error_code == 0));
    await_shutdown();
    let closed = output.map(SharedOutput::close_file);
    if job.size_changed.load(Ordering::Acquire) {
        release_slot(job);
    }
    delete_temp(job);
    if let Some(Err(error)) = concluded {
        return Some(crate::cp::write_error_name(&error));
    }
    closed?.err().map(close_error_name)
}
fn release_slot(job: &Job) {
    let mut held = lock(&job.output);
    assert!(held.prepared.is_none(), "the slot outlives its output");
    let slot = held.slot.take();
    drop(held);
    drop(slot);
}
#[derive(Debug)]
pub(super) enum Output<'a> {
    RecvFile(&'a Path),
    Native(SharedOutput),
}
pub(super) fn prepare<'a>(
    job: &'a Job,
    service: Option<&SharedWriterService>,
    size: u64,
) -> Result<Output<'a>, String> {
    {
        let mut held = lock(&job.output);
        assert!(held.prepared.is_none(), "an attempt prepares one output");
        held.failure = None;
    }
    job.custom_writer.store(false, Ordering::Release);
    let path = output_path(job)?;
    let size_changed = job.size_changed.load(Ordering::Acquire);
    let Some(service) =
        service.filter(|service| !size_changed && service.should_use_custom_writer(size))
    else {
        return Ok(Output::RecvFile(path));
    };
    let held = lock(&job.output).slot.take();
    let slot = match held {
        Some(slot) => slot,
        None => service
            .acquire_output_slot(size)
            .map_err(|e| crate::cp::write_error_name(&e))?,
    };
    let prepared = service.prepare_path(&slot, path, size);
    let mut held = lock(&job.output);
    held.slot = Some(slot);
    let output = prepared.map_err(|e| crate::cp::write_error_name(&e))?;
    held.prepared = Some(output.clone());
    drop(held);
    job.custom_writer.store(true, Ordering::Release);
    Ok(Output::Native(output))
}
/// The temp path a download's output opens, or why it has none: a
/// destination outside its root gets no temp path, and the CRT would cut one
/// holding a NUL at the NUL and replace the file its prefix names. Neither
/// writer sees such a path.
fn output_path(job: &Job) -> Result<&Path, String> {
    let path = job
        .temp_path
        .as_deref()
        .ok_or_else(|| "DownloadDestinationOutsideRoot".to_owned())?;
    if transfer::path_holds_nul(path) {
        return Err("DownloadDestinationEmbeddedNull".into());
    }
    Ok(path)
}
pub(super) fn record_failure(job: &Job, failure: Option<OutputFailure>) {
    lock(&job.output).failure = failure;
}

#[cfg(test)]
mod tests;
