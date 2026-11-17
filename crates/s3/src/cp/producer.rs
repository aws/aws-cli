use super::recursive::{ProducerOutcome, SingleObject, TransferRequest};
use crate::scheduler::{Entry, ObjectCondition, Scheduler};
use crate::sync::comparator::{self, Comparator, Destination, Modified, Pairing};
use crate::transfer::{self, SourceInspection, SourceSkip, UploadWalkStep};
use cli_core::interrupt;
use crt::s3::{HeadObjectResult, TransferResult};
use std::ffi::OsString;
use std::fs::{self, ReadDir};
use std::io;
use std::ops::ControlFlow;
use std::path::{Path, PathBuf};
use std::sync::Arc;

#[derive(Debug)]
#[cfg_attr(
    windows,
    expect(
        clippy::large_enum_variant,
        reason = "Windows' ReadDir holds its find data inline; a walk opens one root"
    )
)]
pub(crate) enum LocalRoot {
    Directory(ReadDir),
    Skipped(SourceSkip),
    Unfollowed,
}

pub(crate) fn open_local_root(request: &TransferRequest) -> io::Result<Option<LocalRoot>> {
    if request.direction != transfer::Direction::Upload || request.object.is_some() {
        return Ok(None);
    }
    open_walk_root(request).map(Some)
}
fn open_walk_root(request: &TransferRequest) -> io::Result<LocalRoot> {
    // Upstream's file generator checks for a link before anything else
    // (`FileGenerator.should_ignore_file`).
    if request.links.drops_root() {
        return Ok(LocalRoot::Unfollowed);
    }
    let root = &request.local_root;
    let skip = match fs::read_dir(root) {
        Ok(source) => return Ok(LocalRoot::Directory(source)),
        Err(error) => match error.kind() {
            io::ErrorKind::NotADirectory | io::ErrorKind::NotFound => SourceSkip::Missing,
            io::ErrorKind::PermissionDenied => denied_root_skip(root),
            _ => return Err(error),
        },
    };
    Ok(LocalRoot::Skipped(skip))
}
fn denied_root_skip(local_root: &Path) -> SourceSkip {
    match fs::metadata(local_root) {
        Ok(_) => SourceSkip::UnreadableDirectory,
        Err(_) => SourceSkip::Missing,
    }
}

pub(crate) fn produce_walk(
    request: &TransferRequest,
    scheduler: &Arc<Scheduler>,
    source: LocalRoot,
    state: &interrupt::State,
) -> ProducerOutcome {
    let source = match source {
        LocalRoot::Directory(source) => source,
        LocalRoot::Skipped(skip) => {
            return match scheduler.skip_upload_source(&request.local_root, skip) {
                Ok(()) => ProducerOutcome::WalkCompleted,
                Err(error) => ProducerOutcome::SubmitFailed(error.to_string()),
            };
        }
        LocalRoot::Unfollowed => return ProducerOutcome::WalkCompleted,
    };
    let walk = Walk {
        request,
        scheduler,
        state,
        list: |path: &Path| fs::read_dir(path),
    };
    match walk.run(source) {
        Ok(()) => ProducerOutcome::WalkCompleted,
        Err(error) => ProducerOutcome::WalkFailed(error),
    }
}

struct Walk<'a, L> {
    request: &'a TransferRequest,
    scheduler: &'a Arc<Scheduler>,
    state: &'a interrupt::State,
    list: L,
}

struct Listed {
    name: OsString,
    directory: bool,
}
impl Listed {
    fn listed_name(&self) -> transfer::ListedName<'_> {
        transfer::ListedName {
            name: self.name.as_encoded_bytes(),
            directory: self.directory,
        }
    }
}

struct Frame {
    relative: PathBuf,
    entries: Vec<Listed>,
    next: usize,
}

impl<L: Fn(&Path) -> io::Result<ReadDir>> Walk<'_, L> {
    fn run(&self, source: ReadDir) -> Result<(), String> {
        let mut frames = vec![self.list_directory(PathBuf::new(), source)?];
        while let Some(file) = self.next_file(&mut frames)? {
            self.scheduler
                .handle_upload_entry(&file.relative, Some(file.size))
                .map_err(|error| error.to_string())?;
        }
        Ok(())
    }

    fn run_sync<D: Destination<Name = Vec<u8>>>(
        &self,
        source: ReadDir,
        comparator: &mut Comparator<D>,
    ) -> Result<(), SyncWalkError<D::Error>> {
        let mut frames = vec![
            self.list_directory(PathBuf::new(), source)
                .map_err(SyncWalkError::Walk)?,
        ];
        while let Some(file) = self.next_file(&mut frames).map_err(SyncWalkError::Walk)? {
            if !self
                .scheduler
                .includes_source(file.relative.as_os_str().as_encoded_bytes())
            {
                continue;
            }
            let entry = comparator::Entry {
                name: &*comparator::local_name(&file.relative),
                size: file.size,
                modified: file.modified,
            };
            let mut remover = ObjectRemover::new(self.request, self.scheduler);
            let pairing = comparator
                .pair(&entry, &mut remover)
                .map_err(SyncWalkError::Destination)?;
            remover.result().map_err(SyncWalkError::Walk)?;
            if matches!(pairing, Pairing::Both(true) | Pairing::SourceOnly) {
                self.scheduler
                    .submit_walked_upload(&file.relative, Some(file.size))
                    .map_err(|error| SyncWalkError::Walk(error.to_string()))?;
            }
        }
        Ok(())
    }

    fn next_file(&self, frames: &mut Vec<Frame>) -> Result<Option<WalkedFile>, String> {
        while !frames.is_empty() {
            if self.state.is_requested() {
                break;
            }
            if let Some(file) = self.step_entry(frames)? {
                return Ok(Some(file));
            }
        }
        Ok(None)
    }

    fn step_entry(&self, frames: &mut Vec<Frame>) -> Result<Option<WalkedFile>, String> {
        let Some(frame) = frames.last_mut() else {
            return Ok(None);
        };
        let Some(listed) = frame.entries.get(frame.next) else {
            frames.pop();
            return Ok(None);
        };
        frame.next += 1;
        let relative = frame.relative.join(&listed.name);
        // Upstream joins a listed directory's name with its separator, so
        // the stat fails once anything but a directory is there, or when the
        // separator takes the path past the OS's limit.
        let mut local_path =
            transfer::build_recursive_source_path(&self.request.local_root, &relative)
                .into_os_string();
        if listed.directory {
            local_path.push(std::path::MAIN_SEPARATOR_STR);
        }
        let local_path = PathBuf::from(local_path);
        let Ok(metadata) = fs::metadata(&local_path) else {
            return self.skip(&local_path, SourceSkip::Missing).map(|()| None);
        };
        if metadata.is_dir() {
            if let Some(frame) = self.enter_directory(relative, &local_path)? {
                frames.push(frame);
            }
            return Ok(None);
        }
        let modified = match Modified::from_metadata(&metadata) {
            Some(modified) => modified,
            None => {
                self.scheduler
                    .warn_invalid_timestamp()
                    .map_err(|error| error.to_string())?;
                Modified::EPOCH
            }
        };
        Ok(Some(WalkedFile {
            relative,
            size: metadata.len(),
            modified,
        }))
    }

    fn enter_directory(
        &self,
        relative: PathBuf,
        local_path: &Path,
    ) -> Result<Option<Frame>, String> {
        let path = transfer::build_recursive_source_path(&self.request.local_root, &relative);
        if self.request.links.drops(&path) {
            return Ok(None);
        }
        let skip = match (self.list)(&path) {
            Ok(reader) => return self.list_directory(relative, reader).map(Some),
            Err(error) => match error.kind() {
                io::ErrorKind::PermissionDenied => SourceSkip::UnreadableSubdirectory,
                io::ErrorKind::NotFound | io::ErrorKind::NotADirectory => SourceSkip::Missing,
                _ => return Err(super::io_error_name(&error).to_owned()),
            },
        };
        self.skip(local_path, skip).map(|()| None)
    }

    fn list_directory(&self, relative: PathBuf, reader: ReadDir) -> Result<Frame, String> {
        let mut entries = Vec::new();
        for entry in reader {
            if self.state.is_requested() {
                break;
            }
            let entry = entry.map_err(|error| super::io_error_name(&error).to_owned())?;
            let name = entry.file_name();
            if let Some(directory) = self.list_entry(&relative.join(&name))? {
                entries.push(Listed { name, directory });
            }
        }
        entries.sort_by(|a, b| transfer::listing_order(a.listed_name(), b.listed_name()));
        Ok(Frame {
            relative,
            entries,
            next: 0,
        })
    }

    fn list_entry(&self, relative: &Path) -> Result<Option<bool>, String> {
        let path = transfer::build_recursive_source_path(&self.request.local_root, relative);
        if self.request.links.drops(&path) {
            return Ok(None);
        }
        match transfer::recursive_upload_walk_step(&path).unwrap_or(UploadWalkStep::Inspect) {
            UploadWalkStep::Descend => match fs::read_dir(&path) {
                Ok(_) => Ok(Some(true)),
                Err(error) if error.kind() == io::ErrorKind::PermissionDenied => self
                    .skip(&path, SourceSkip::UnreadableSubdirectory)
                    .map(|()| None),
                Err(error) => Err(super::io_error_name(&error).to_owned()),
            },
            UploadWalkStep::SkipDirectory => match fs::read_dir(&path) {
                Err(error) if error.kind() == io::ErrorKind::PermissionDenied => self
                    .skip(&path, SourceSkip::UnreadableSubdirectory)
                    .map(|()| None),
                _ => Ok(Some(true)),
            },
            UploadWalkStep::Inspect => match self.scheduler.inspect_local_path(&path) {
                SourceInspection::Skipped(skip) => self.skip(&path, skip).map(|()| None),
                SourceInspection::Size(_) | SourceInspection::InvalidTimestamp(_) => {
                    Ok(Some(false))
                }
            },
        }
    }

    fn skip(&self, path: &Path, skip: SourceSkip) -> Result<(), String> {
        self.scheduler
            .skip_local_path(path, skip)
            .map_err(|error| error.to_string())
    }
}

#[derive(Debug)]
struct WalkedFile {
    relative: PathBuf,
    size: u64,
    modified: Modified,
}

#[derive(Debug)]
enum SyncWalkError<E> {
    Walk(String),
    Destination(E),
}

struct ObjectRemover<'a> {
    request: &'a TransferRequest,
    scheduler: &'a Arc<Scheduler>,
    failure: Option<String>,
}
impl<'a> ObjectRemover<'a> {
    fn new(request: &'a TransferRequest, scheduler: &'a Arc<Scheduler>) -> Self {
        Self {
            request,
            scheduler,
            failure: None,
        }
    }
    fn result(self) -> Result<(), String> {
        self.failure.map_or(Ok(()), Err)
    }
}
impl comparator::Remover<Vec<u8>> for ObjectRemover<'_> {
    fn remove(&mut self, entry: comparator::Entry<Vec<u8>>) -> ControlFlow<()> {
        let key = [self.request.prefix.as_slice(), &entry.name].concat();
        match self.scheduler.submit_destination_delete(key, entry.size) {
            Ok(()) => ControlFlow::Continue(()),
            Err(error) => {
                self.failure = Some(error.to_string());
                ControlFlow::Break(())
            }
        }
    }
}

pub(crate) fn produce_sync_walk<D: Destination<Name = Vec<u8>>>(
    request: &TransferRequest,
    scheduler: &Arc<Scheduler>,
    source: LocalRoot,
    state: &interrupt::State,
    comparator: &mut Comparator<D>,
) -> Result<ProducerOutcome, D::Error> {
    let walked = match source {
        LocalRoot::Directory(source) => {
            let walk = Walk {
                request,
                scheduler,
                state,
                list: |path: &Path| fs::read_dir(path),
            };
            walk.run_sync(source, comparator)
        }
        LocalRoot::Skipped(skip) => scheduler
            .skip_upload_source(&request.local_root, skip)
            .map_err(|error| SyncWalkError::Walk(error.to_string())),
        LocalRoot::Unfollowed => Ok(()),
    };
    match walked {
        Ok(()) if !state.is_requested() => {
            let mut remover = ObjectRemover::new(request, scheduler);
            let stopped = comparator.finish(&mut remover)?.is_break();
            Ok(match remover.result() {
                Err(error) => ProducerOutcome::WalkFailed(error),
                Ok(()) => {
                    debug_assert!(!stopped, "only a failure stops the remover");
                    ProducerOutcome::WalkCompleted
                }
            })
        }
        Ok(()) => Ok(ProducerOutcome::WalkCompleted),
        Err(SyncWalkError::Walk(error)) => Ok(ProducerOutcome::WalkFailed(error)),
        Err(SyncWalkError::Destination(error)) => Err(error),
    }
}

pub(crate) struct LocalDestination<'a> {
    walk: Walk<'a, fn(&Path) -> io::Result<ReadDir>>,
    frames: Option<Vec<Frame>>,
}
impl std::fmt::Debug for LocalDestination<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LocalDestination")
            .field("root", &self.walk.request.local_root)
            .field("opened", &self.frames.is_some())
            .finish()
    }
}
impl<'a> LocalDestination<'a> {
    pub(crate) fn new(
        request: &'a TransferRequest,
        scheduler: &'a Arc<Scheduler>,
        state: &'a interrupt::State,
    ) -> Self {
        Self {
            walk: Walk {
                request,
                scheduler,
                state,
                list: |path: &Path| fs::read_dir(path),
            },
            frames: None,
        }
    }
    fn open(&self) -> Result<Vec<Frame>, String> {
        let request = self.walk.request;
        match open_walk_root(request) {
            Ok(LocalRoot::Directory(reader)) => {
                Ok(vec![self.walk.list_directory(PathBuf::new(), reader)?])
            }
            Ok(LocalRoot::Skipped(skip)) => self
                .walk
                .skip(&request.local_root, skip)
                .map(|()| Vec::new()),
            Ok(LocalRoot::Unfollowed) => Ok(Vec::new()),
            Err(error) => Err(super::io_error_name(&error).to_owned()),
        }
    }
}
impl Destination for LocalDestination<'_> {
    type Name = comparator::LocalName;
    type Error = String;
    fn next_entry(&mut self) -> Result<Option<comparator::Entry<comparator::LocalName>>, String> {
        if self.frames.is_none() {
            let (frames, opened) = match self.open() {
                Ok(frames) => (frames, Ok(())),
                Err(error) => (Vec::new(), Err(error)),
            };
            self.frames = Some(frames);
            opened?;
        }
        let Some(frames) = self.frames.as_mut() else {
            return Ok(None);
        };
        // A file `--include` and `--exclude` leave out is no entry at all,
        // as upstream filters the destination before its comparator.
        let filter = self
            .walk
            .request
            .sync
            .as_ref()
            .map(|sync| &sync.destination_filter);
        while let Some(file) = self.walk.next_file(frames)? {
            let name = file.relative.as_os_str().as_encoded_bytes();
            if filter.is_some_and(|filter| !filter.includes(name)) {
                continue;
            }
            return Ok(Some(comparator::Entry {
                size: file.size,
                modified: file.modified,
                name: comparator::LocalName::from_relative_path(file.relative),
            }));
        }
        Ok(None)
    }
}

pub(crate) fn produce_object(scheduler: &Arc<Scheduler>, object: &SingleObject) -> ProducerOutcome {
    if scheduler.drops_upload_operand() {
        return ProducerOutcome::ObjectCompleted;
    }
    let produced = if scheduler.includes_source(object.local_path.as_os_str().as_encoded_bytes()) {
        scheduler.submit_entry(Entry {
            key: object.key.clone(),
            local_path: object.local_path.clone(),
            ..Entry::default()
        })
    } else {
        scheduler.exclude_upload_source(&object.local_path)
    };
    match produced {
        Ok(()) => ProducerOutcome::ObjectCompleted,
        Err(error) => ProducerOutcome::SubmitFailed(error.to_string()),
    }
}

pub(crate) fn produce_delete_object(
    scheduler: &Arc<Scheduler>,
    object: &SingleObject,
) -> ProducerOutcome {
    if !scheduler.includes_source(&object.key) {
        return ProducerOutcome::ObjectCompleted;
    }
    match scheduler.submit_entry(Entry {
        key: object.key.clone(),
        ..Entry::default()
    }) {
        Ok(()) => ProducerOutcome::ObjectCompleted,
        Err(error) => ProducerOutcome::SubmitFailed(error.to_string()),
    }
}

pub(crate) fn produce_download_object(
    scheduler: &Arc<Scheduler>,
    object: &SingleObject,
    head: impl FnOnce() -> Result<HeadObjectResult, Box<TransferResult>>,
) -> ProducerOutcome {
    let head = match head() {
        Ok(head) => head,
        Err(result) if result.canceled_by_interrupt => return ProducerOutcome::HeadCanceled,
        Err(result) => return ProducerOutcome::HeadFailed(result),
    };
    if head.transfer.canceled_by_interrupt {
        return ProducerOutcome::HeadCanceled;
    }
    if head.transfer.error_code != 0 {
        return ProducerOutcome::HeadFailed(Box::new(head.transfer));
    }
    // Upstream reads ContentLength and then LastModified; the engine fails a
    // missing length itself.
    if head.content_length.is_some() && head.last_modified_epoch_seconds.is_none() {
        return ProducerOutcome::HeadMissingLastModified;
    }
    if head.content_length.is_some() && !scheduler.includes_source(&object.key) {
        return ProducerOutcome::ObjectCompleted;
    }
    let etag = (head.etag.is_present() && !head.etag.is_truncated())
        .then(|| head.etag.as_bytes().to_vec());
    let condition = ObjectCondition {
        etag,
        full_object_checksum: head.full_object_checksum,
    };
    let entry = Entry {
        key: object.key.clone(),
        local_path: object.local_path.clone(),
        local: object.local.clone(),
        size: head.content_length,
        size_listed: false,
        modified: head.last_modified_epoch_seconds,
        archive: head.archive,
        condition,
        case_name: None,
    };
    match scheduler.submit_entry(entry) {
        Ok(()) => ProducerOutcome::ObjectCompleted,
        Err(error) => ProducerOutcome::SubmitFailed(error.to_string()),
    }
}

#[cfg(test)]
mod tests;
