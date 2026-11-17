use super::{Event, Key};
use std::collections::HashMap;
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Recorder {
    pub bytes_transferred: u64,
    pub bytes_failed_to_transfer: u64,
    pub files_transferred: u64,
    pub files_failed: u64,
    pub files_warned: u64,
    pub files_skipped: u64,
    pub errors: u64,
    pub expected_bytes_transferred: u64,
    pub expected_files_transferred: u64,
    pub final_expected_files_transferred: Option<u64>,
    pub start_time_ns: Option<u64>,
    pub bytes_transfer_speed: f64,
    ongoing: HashMap<Key, Ongoing>,
}
#[derive(Debug, Clone, Default, PartialEq, Eq)]
struct Ongoing {
    progress: u64,
    size: Option<u64>,
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CommandResult {
    pub num_tasks_failed: u64,
    pub num_tasks_warned: u64,
}
impl Recorder {
    pub fn record(&mut self, event: &Event, now_ns: u64) {
        match event {
            Event::Queued { key, size } => self.record_queued(*key, *size, now_ns),
            Event::Progress {
                key,
                bytes,
                total_size,
                timestamp_ns,
            } => self.record_progress(*key, *bytes, *total_size, *timestamp_ns),
            Event::Success { key, .. } => {
                self.ongoing.remove(key);
                self.files_transferred += 1;
            }
            Event::Failure {
                key, transferred, ..
            } => self.record_failure(*key, *transferred),
            Event::Skip { key } => {
                self.ongoing.remove(key);
                self.files_skipped += 1;
            }
            Event::Warning(_) => self.files_warned += 1,
            Event::Fatal(_) | Event::CtrlC => self.errors += 1,
            Event::FinalTotal(total) => self.final_expected_files_transferred = Some(*total),
            Event::Diagnostic(_) | Event::DryRun(_) => {}
        }
    }
    fn record_queued(&mut self, key: Key, size: Option<u64>, now_ns: u64) {
        self.ongoing.insert(key, Ongoing { progress: 0, size });
        self.start_time_ns.get_or_insert(now_ns);
        self.expected_bytes_transferred += size.unwrap_or(0);
        self.expected_files_transferred += 1;
    }
    fn record_progress(
        &mut self,
        key: Option<Key>,
        bytes: u64,
        total_size: Option<u64>,
        timestamp_ns: u64,
    ) {
        if let Some(ongoing) = key.and_then(|key| self.ongoing.get_mut(&key)) {
            self.expected_bytes_transferred += learn_unknown_size(ongoing, bytes, total_size);
            ongoing.progress += bytes;
        }
        self.bytes_transferred += bytes;
        if let Some(start) = self.start_time_ns
            && timestamp_ns > start
        {
            let elapsed_s = (timestamp_ns - start) as f64 / 1e9;
            self.bytes_transfer_speed = self.bytes_transferred as f64 / elapsed_s;
        }
    }
    fn failure_remainder(&self, key: Key, transferred: Option<u64>) -> u64 {
        self.ongoing.get(&key).map_or(0, |ongoing| {
            ongoing
                .size
                .unwrap_or(0)
                .saturating_sub(transferred.unwrap_or(ongoing.progress))
        })
    }
    fn record_failure(&mut self, key: Key, transferred: Option<u64>) {
        self.bytes_failed_to_transfer += self.failure_remainder(key, transferred);
        self.ongoing.remove(&key);
        self.files_transferred += 1;
        self.files_failed += 1;
    }
    pub fn expected_totals_are_final(&self) -> bool {
        self.final_expected_files_transferred == Some(self.expected_files_transferred)
    }
    pub fn has_remaining_progress(&self) -> bool {
        !self.expected_totals_are_final()
            || self.files_transferred + self.files_skipped != self.expected_files_transferred
    }
    pub fn command_result(&self) -> CommandResult {
        CommandResult {
            num_tasks_failed: self.files_failed + self.errors,
            num_tasks_warned: self.files_warned,
        }
    }
}
fn learn_unknown_size(ongoing: &mut Ongoing, bytes: u64, total_size: Option<u64>) -> u64 {
    if ongoing.size.is_some() {
        return 0;
    }
    ongoing.size = total_size;
    total_size.map_or(bytes, |size| size.saturating_sub(ongoing.progress))
}
