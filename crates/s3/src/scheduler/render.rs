use super::*;
use crate::request_failure::{Reason, RequestUrl};
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stream {
    Stdout,
    Stderr,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Event {
    pub stream: Stream,
    pub text: Vec<u8>,
}
pub trait Sink: Send + Sync + fmt::Debug {
    fn emit(&self, event: Event) -> Result<(), String>;
    fn publish(&self, event: crate::results::Event, quiet: bool) -> Result<(), String> {
        if quiet {
            return Ok(());
        }
        let mut out = Vec::new();
        let mut err = Vec::new();
        let mut printer = crate::results::Printer::new(crate::results::PrinterConfig {
            mode: crate::results::Mode::NoProgress,
            ..Default::default()
        });
        printer.handle(
            &crate::results::Recorder::default(),
            &event,
            0,
            &mut out,
            &mut err,
        );
        for (stream, bytes) in [(Stream::Stdout, out), (Stream::Stderr, err)] {
            if !bytes.is_empty() {
                self.emit(Event {
                    stream,
                    text: bytes,
                })?;
            }
        }
        Ok(())
    }
    fn progress(&self, _bytes: u64) {}
    /// Whether the sink's processor draws byte progress: only then are requests
    /// sent with a CRT progress hook (`Scheduler::wants_progress_hook`).
    fn wants_progress(&self) -> bool {
        false
    }
}
impl Scheduler {
    fn remote_path(&self, key: &[u8]) -> Vec<u8> {
        match self.request.object.as_ref().and_then(|o| o.remote.as_ref()) {
            Some(remote) => remote.as_encoded_bytes().to_vec(),
            None => [
                b"s3://".as_slice(),
                self.request.bucket.as_bytes(),
                b"/",
                key,
            ]
            .concat(),
        }
    }
    pub(super) fn line(&self, job: &Job) -> crate::results::Line {
        self.entry_line(job.direction, &job.raw_key, &job.local_path)
    }
    pub(super) fn entry_line(
        &self,
        direction: transfer::Direction,
        key: &[u8],
        local_path: &Path,
    ) -> crate::results::Line {
        let remote = self.remote_path(key);
        let local = || {
            transfer::display_local_path(&self.cwd, local_path)
                .as_os_str()
                .as_encoded_bytes()
                .to_vec()
        };
        let (source, destination) = match direction {
            transfer::Direction::Download => (remote, Some(local())),
            transfer::Direction::Upload => (local(), Some(remote)),
            transfer::Direction::Delete => (remote, None),
        };
        let transfer_type = match (direction, &self.request.sources) {
            (transfer::Direction::Delete, _) | (_, transfer::SourceDisposition::Keep) => {
                direction.into()
            }
            (_, transfer::SourceDisposition::Delete { .. }) => crate::results::TransferType::Move,
        };
        crate::results::Line {
            transfer_type,
            source,
            destination,
        }
    }
    pub(super) fn local_delete_line(&self, local_path: &Path) -> crate::results::Line {
        crate::results::Line {
            transfer_type: crate::results::TransferType::Delete,
            source: transfer::display_local_path(&self.cwd, local_path)
                .into_os_string()
                .into_encoded_bytes(),
            destination: None,
        }
    }
    pub(super) fn local_failure(&self, _job: &Job, error: &str) -> Failure {
        Failure {
            exception: error.as_bytes().to_vec(),
            text: None,
        }
    }
    pub(super) fn transfer_failure(&self, job: &Job, result: &TransferResult) -> Failure {
        let reason = Reason {
            result,
            missing_key: None,
            url: RequestUrl::Object {
                endpoint_url: &self.request.runtime.endpoint_url,
                request_key: &job.request_key,
            },
        };
        Failure {
            exception: crate::request_failure::transfer_sentence_bytes(reason),
            text: None,
        }
    }
    pub(super) fn source_delete_failure(&self, job: &Job, error: &SourceDeleteError) -> Failure {
        let exception = match error {
            SourceDeleteError::Local(error) => {
                transfer::source_removal_failure(&self.cwd, &job.local_path, error)
            }
            SourceDeleteError::Request(result) => {
                let reason = Reason {
                    result,
                    missing_key: None,
                    url: RequestUrl::Object {
                        endpoint_url: &self.request.runtime.endpoint_url,
                        request_key: &job.request_key,
                    },
                };
                crate::request_failure::client_sentence_bytes(
                    reason,
                    &self.request.runtime.credentials,
                )
            }
        };
        Failure {
            exception,
            text: None,
        }
    }
    pub(super) fn mtime_warning(&self, job: &Job, error: &str) -> Vec<u8> {
        let path = crate::local_path::absolute_path(&self.cwd, &job.local_path);
        transfer::mtime_warning(&path, error)
    }
    pub(super) fn commit_failure(&self, job: &Job, failure: transfer::CommitFailure) -> Failure {
        let Some(temp) = &job.temp_path else {
            let text = [
                b"error: unable to write downloaded file ".as_slice(),
                job.local_path.as_os_str().as_encoded_bytes(),
                b": ",
                failure.error.as_bytes(),
            ]
            .concat();
            return Failure {
                exception: failure.error.as_bytes().to_vec(),
                text: Some(text),
            };
        };
        Failure {
            exception: transfer::rename_error_text(&self.cwd, failure, temp, &job.local_path),
            text: None,
        }
    }
}
#[derive(Debug)]
pub(super) struct Failure {
    pub exception: Vec<u8>,
    pub text: Option<Vec<u8>>,
}
