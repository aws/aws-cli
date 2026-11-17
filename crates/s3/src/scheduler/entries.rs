use super::*;
use crate::transfer::{SourceInspection, SourceSkip};

/// What a producer hands the engine for one object. Producers resolve names
/// and report what they found; the engine decides and moves bytes.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Entry {
    /// The object key, as result lines spell it.
    pub key: Vec<u8>,
    /// The local path results name: the upload source or the download
    /// destination. A destination the producer ruled out is named by the
    /// root it would have been resolved under, so a failure ahead of that
    /// rule can still report it.
    pub local_path: PathBuf,
    /// What the producer found at a download's destination.
    pub local: EntryLocal,
    /// The listed size or HEAD Content-Length, or the size a recursive
    /// upload's walk found. None for an upload whose source the engine
    /// inspects, and for a HEAD that carried no length.
    pub size: Option<u64>,
    /// Whether `size` is a listing's. A listing can be older than the object
    /// its GET fetches, so the file that GET completes is committed whatever
    /// its length, as upstream's CRT handler commits it; a HEAD's is checked.
    pub size_listed: bool,
    /// LastModified from the listing or HEAD; None for uploads.
    pub modified: Option<i64>,
    /// What the Glacier rule reads from the listing or HEAD.
    pub archive: Archive,
    /// What the HeadObject or listing entry that found a download's object
    /// conditions its GETs on.
    pub condition: ObjectCondition,
    /// The case-folded name a sync download under `--case-conflict` took
    /// for this object, which its job holds until it ends.
    pub case_name: Option<String>,
}
/// What a download's GETs are conditioned on, from the HeadObject or the
/// listing entry that found its object; the default conditions nothing, as
/// an upload's or a delete's.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ObjectCondition {
    /// The ETag the response reported; None leaves the CRT to condition the
    /// GETs on its own discovery request.
    pub etag: Option<Vec<u8>>,
    /// What the response said of the object's full-object checksum.
    pub full_object_checksum: crt::s3::FullObjectChecksum,
}
impl ObjectCondition {
    /// The condition the CRT sends, when there is an ETag to send.
    pub fn download_condition(&self) -> Option<crt::s3::DownloadCondition<'_>> {
        self.etag.as_deref().map(|etag| crt::s3::DownloadCondition {
            etag,
            full_object_checksum: &self.full_object_checksum,
        })
    }
}
pub type Archive = crt::s3::ArchiveState;
/// What a producer found at a download's destination.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub enum EntryLocal {
    /// `local_path` is the file to read or write.
    #[default]
    Resolved,
    /// A download whose name resolves above its destination: the relative
    /// key the warning names.
    ParentEscape(String),
    /// A download whose name normalizes to its destination root's parent,
    /// which upstream does not flag. `local_path` is the path the name maps
    /// to; the engine sends the GET but creates nothing on the way to it, so
    /// the download writes nothing outside its root.
    RootParent,
}
#[derive(Debug)]
enum Unrequested {
    MissingContentLength,
    ParentDirectory(&'static str),
    TempPath(TempPathError),
}
enum Prepared {
    Ready(PathBuf),
    ParentFailure(&'static str),
    TempPathFailure(TempPathError),
}
impl Scheduler {
    /// Runs the engine's side of the lifecycle for one object, in the
    /// command's direction, blocking for a slot while the window is full.
    /// The rules apply in upstream's order, and each either ends the entry or
    /// passes it on. An entry the rules end before its request is skipped,
    /// with or without a warning, queued and failed in place of its request,
    /// or, under `--dryrun`, reported in place of its transfer. An output
    /// failure, including a queued result that could not be published,
    /// returns without a request; the producer stops on it.
    pub fn submit_entry(self: &Arc<Self>, entry: Entry) -> Result<(), Error> {
        if self.stopped() {
            return Ok(());
        }
        match self.request.direction {
            transfer::Direction::Download => self.submit_download_entry(entry),
            transfer::Direction::Upload => self.submit_upload_entry(entry),
            transfer::Direction::Delete => self.submit_delete_entry(entry),
        }
    }
    /// Upstream's `triggers_warning` for an upload source: why it is
    /// skipped, or the size it is queued with and whether upstream reads
    /// its mtime.
    pub fn inspect_upload_source(&self, local_path: &Path) -> SourceInspection {
        assert_eq!(self.request.direction, transfer::Direction::Upload);
        self.inspect_local_path(local_path)
    }
    /// Upstream's `triggers_warning` for a path a local walk lists.
    ///
    /// The walk is an upload's source, or a sync download's destination,
    /// which upstream's file generator walks the same way.
    pub fn inspect_local_path(&self, local_path: &Path) -> SourceInspection {
        self.operations.inspect_source(local_path)
    }
    /// Warns about an upload source upstream's file generator skips: it
    /// queues nothing, and the warning, counted even under `--quiet`, makes
    /// the command exit 2.
    pub fn skip_upload_source(&self, local_path: &Path, skip: SourceSkip) -> Result<(), Error> {
        assert_eq!(self.request.direction, transfer::Direction::Upload);
        self.skip_local_path(local_path, skip)
    }
    /// Warns about a path a local walk skips, as for an upload source.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take the warning.
    pub fn skip_local_path(&self, local_path: &Path, skip: SourceSkip) -> Result<(), Error> {
        self.publish_skip_warning(transfer::source_skip_warning(&self.cwd, local_path, skip))
    }
    /// Warns that upstream cannot read the mtime of a file a local walk or
    /// a single upload lists, which it compares as the epoch: the file is
    /// still listed, and the warning, counted even under `--quiet`, makes
    /// the command exit 2.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take the warning.
    pub fn warn_invalid_timestamp(&self) -> Result<(), Error> {
        self.publish_warning(transfer::INVALID_TIMESTAMP_WARNING.to_vec())
    }
    fn publish_skip_warning(&self, warning: Vec<u8>) -> Result<(), Error> {
        lock(&self.state).stats.skipped += 1;
        self.publish_warning(warning)
    }
    fn publish_warning(&self, warning: Vec<u8>) -> Result<(), Error> {
        lock(&self.state).warned += 1;
        if self.request.quiet {
            return Ok(());
        }
        self.sink
            .publish(crate::results::Event::Warning(warning), self.request.quiet)
            .map_err(Error::Output)
    }
    /// Prints `text` on stderr as upstream's `uni_print` does outside its
    /// results: it counts as nothing, and prints under `--quiet` too.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take it.
    pub fn print_diagnostic(&self, text: Vec<u8>) -> Result<(), Error> {
        self.sink
            .publish(crate::results::Event::Diagnostic(text), false)
            .map_err(Error::Output)
    }
    fn publish_dry_run(&self, direction: transfer::Direction, entry: &Entry) -> Result<(), Error> {
        self.publish_dry_run_line(self.entry_line(direction, &entry.key, &entry.local_path))
    }
    fn publish_dry_run_line(&self, line: crate::results::Line) -> Result<(), Error> {
        if self.request.quiet {
            return Ok(());
        }
        self.sink
            .publish(crate::results::Event::DryRun(line), self.request.quiet)
            .map_err(Error::Output)
    }
    /// The synchronous path: filters and maps one listed object on the
    /// caller's thread, as the submitter maps a queued one.
    pub fn handle_download_entry(
        self: &Arc<Self>,
        key: &str,
        size: u64,
        modified: Option<i64>,
    ) -> Result<(), Error> {
        if !self.listed_entry_passes_filters(key.as_bytes(), size) {
            return Ok(());
        }
        self.handle_download_entry_with_archive(key, size, modified, Archive::default())
    }
    /// Whether a listed object passes the filters checked before queueing.
    pub fn listed_entry_passes_filters(&self, key: &[u8], size: u64) -> bool {
        let folder_marker = size == 0 && key.ends_with(b"/");
        let selected = match self.request.direction {
            transfer::Direction::Delete => {
                folder_marker || !self.request.delete.folder_markers_only
            }
            transfer::Direction::Download | transfer::Direction::Upload => !folder_marker,
        };
        selected && key.starts_with(&self.request.prefix) && self.includes_source(key)
    }
    pub(super) fn handle_listed_entry(
        self: &Arc<Self>,
        key: &str,
        size: u64,
        modified: Option<i64>,
        archive: Archive,
        case_name: Option<String>,
        condition: ObjectCondition,
    ) -> Result<(), Error> {
        if self.request.direction != transfer::Direction::Delete {
            return self.map_download_entry(key, size, modified, archive, case_name, condition);
        }
        self.submit_entry(Entry {
            key: key.as_bytes().to_vec(),
            size: Some(size),
            size_listed: true,
            ..Entry::default()
        })
    }
    /// Whether `--no-follow-symlinks` drops the source a single upload names,
    /// a link, which upstream's file generator drops before it inspects or
    /// filters it (`FileGenerator.list_files`, `should_ignore_file`).
    pub fn drops_upload_operand(&self) -> bool {
        self.request.links.drops_operand()
    }
    /// Whether `--include` and `--exclude` leave in the source named `name`.
    ///
    /// A producer names a walked file by its path relative to the walk's
    /// root, an object by its key, and a single upload by its source path.
    pub fn includes_source(&self, name: &[u8]) -> bool {
        self.request.filter.includes(name)
    }
    /// Drops a single upload's source the filters leave out.
    ///
    /// Upstream's file generator inspects the source before its filter sees
    /// it, so a source it skips, or whose mtime it cannot read, is still
    /// warned about, as the engine warns about one it takes.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take that warning.
    pub fn exclude_upload_source(&self, local_path: &Path) -> Result<(), Error> {
        if self.stopped() {
            return Ok(());
        }
        match self.inspect_upload_source(local_path) {
            SourceInspection::Skipped(skip) => self.skip_upload_source(local_path, skip),
            SourceInspection::InvalidTimestamp(_) => self.warn_invalid_timestamp(),
            SourceInspection::Size(_) => Ok(()),
        }
    }
    /// The listing mapper: names a listed object's destination under the local
    /// root, or the parent reference that rules it out, and hands it to
    /// `submit_entry`. The object passed `download_entry_passes_filters`.
    pub fn handle_download_entry_with_archive(
        self: &Arc<Self>,
        key: &str,
        size: u64,
        modified: Option<i64>,
        archive: Archive,
    ) -> Result<(), Error> {
        self.map_download_entry(
            key,
            size,
            modified,
            archive,
            None,
            ObjectCondition::default(),
        )
    }
    fn map_download_entry(
        self: &Arc<Self>,
        key: &str,
        size: u64,
        modified: Option<i64>,
        archive: Archive,
        case_name: Option<String>,
        condition: ObjectCondition,
    ) -> Result<(), Error> {
        let relative = key
            .as_bytes()
            .starts_with(&self.request.prefix)
            .then(|| key.get(self.request.prefix.len()..))
            .flatten();
        debug_assert!(
            relative.is_some(),
            "the filters pass only keys in the prefix"
        );
        let Some(relative) = relative else {
            return Ok(());
        };
        let root = transfer::normalize_local_directory_root(&self.request.local_root);
        let (local_path, local) = if uri::relative_key_escapes_root(relative) {
            (root, EntryLocal::ParentEscape(relative.to_owned()))
        } else if uri::relative_key_names_root_parent(relative) {
            (
                transfer::build_recursive_destination_path(&root, relative),
                EntryLocal::RootParent,
            )
        } else {
            (
                transfer::build_recursive_destination_path(&root, relative),
                EntryLocal::Resolved,
            )
        };
        self.submit_entry(Entry {
            key: key.as_bytes().to_vec(),
            local_path,
            local,
            size: Some(size),
            size_listed: true,
            modified,
            archive,
            condition,
            case_name,
        })
    }
    /// The walk mapper: names one walked file, relative to the local root,
    /// and hands it to `submit_entry` with the `size` its sorted pass found,
    /// or None to let the engine's inspection find it, unless `--include`
    /// and `--exclude` leave it out. The walk warned about every file it
    /// skips before this, as upstream's file generator does before its
    /// filter.
    pub fn handle_upload_entry(
        self: &Arc<Self>,
        relative: &Path,
        size: Option<u64>,
    ) -> Result<(), Error> {
        if !self.includes_source(relative.as_os_str().as_encoded_bytes()) {
            return Ok(());
        }
        self.submit_walked_upload(relative, size)
    }
    /// Names one walked file, `relative` to the local root, to `submit_entry`.
    ///
    /// The caller decided it is uploaded: `--include` and `--exclude` left
    /// it in, and a sync paired it for transfer.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take its result.
    pub fn submit_walked_upload(
        self: &Arc<Self>,
        relative: &Path,
        size: Option<u64>,
    ) -> Result<(), Error> {
        self.submit_entry(Entry {
            key: transfer::build_recursive_upload_key(&self.request.prefix, relative),
            local_path: self.request.local_root.join(relative),
            size,
            ..Entry::default()
        })
    }
    fn submit_download_entry(self: &Arc<Self>, entry: Entry) -> Result<(), Error> {
        let Some(size) = entry.size else {
            return self.submit_unrequested(entry, Unrequested::MissingContentLength);
        };
        if self.ends_download_entry(&entry)? {
            return Ok(());
        }
        if self.request.dryrun {
            return self.publish_dry_run(transfer::Direction::Download, &entry);
        }
        if self.request.collect_stats {
            lock(&self.state).stats.record_size(size);
        }
        let temp = if entry.local == EntryLocal::RootParent {
            None
        } else {
            match self.prepare_download(&entry.local_path) {
                Prepared::Ready(temp) => Some(temp),
                Prepared::ParentFailure(error) => {
                    return self.submit_unrequested(entry, Unrequested::ParentDirectory(error));
                }
                Prepared::TempPathFailure(error) => {
                    return self.submit_unrequested(entry, Unrequested::TempPath(error));
                }
            }
        };
        let request_key = uri::encode_s3_request_path_key_bytes(&entry.key);
        self.submit(Job {
            direction: transfer::Direction::Download,
            raw_key: entry.key,
            request_key,
            local_path: entry.local_path,
            temp_path: temp,
            size: Some(size),
            size_listed: entry.size_listed,
            size_changed: AtomicBool::new(false),
            modified: entry.modified,
            condition: entry.condition,
            case_name: entry.case_name,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        })
    }
    fn ends_download_entry(&self, entry: &Entry) -> Result<bool, Error> {
        let warning = if !entry.archive.readable()
            && self.request.glacier != transfer::GlacierPolicy::Transfer
        {
            if self.request.glacier == transfer::GlacierPolicy::Skip {
                lock(&self.state).stats.skipped += 1;
                return Ok(true);
            }
            let source = [
                format!("s3://{}/", self.request.bucket).as_bytes(),
                &entry.key,
            ]
            .concat();
            transfer::glacier_warning(&source)
        } else if let EntryLocal::ParentEscape(relative) = &entry.local {
            transfer::parent_escape_warning(relative).into_bytes()
        } else {
            let skipped = self.request.links.skips_download(&entry.local_path)
                || (self.request.no_overwrite && self.operations.exists(&entry.local_path));
            if skipped {
                lock(&self.state).stats.skipped += 1;
            }
            return Ok(skipped);
        };
        self.publish_skip_warning(warning)?;
        Ok(true)
    }
    fn prepare_download(&self, local_path: &Path) -> Prepared {
        if let Err(error) = lock(&self.parents).ensure(self.operations.as_ref(), local_path) {
            return Prepared::ParentFailure(error);
        }
        match self.operations.temp_path(local_path) {
            Ok(temp) => Prepared::Ready(temp),
            Err(error) => Prepared::TempPathFailure(error),
        }
    }
    fn submit_upload_entry(self: &Arc<Self>, entry: Entry) -> Result<(), Error> {
        let inspection = match entry.size {
            Some(size) => SourceInspection::Size(size),
            None => self.inspect_upload_source(&entry.local_path),
        };
        let size = match inspection {
            SourceInspection::Size(size) => size,
            SourceInspection::InvalidTimestamp(size) => {
                self.warn_invalid_timestamp()?;
                size
            }
            SourceInspection::Skipped(skip) => {
                return self.skip_upload_source(&entry.local_path, skip);
            }
        };
        if size > transfer::MAX_UPLOAD_SIZE {
            let display = transfer::display_local_path(&self.cwd, &entry.local_path);
            self.publish_warning(transfer::upload_size_warning(&display))?;
        }
        if self.request.dryrun {
            return self.publish_dry_run(transfer::Direction::Upload, &entry);
        }
        let request_key = uri::encode_s3_request_path_key_bytes(&entry.key);
        self.submit(Job {
            direction: transfer::Direction::Upload,
            raw_key: entry.key,
            request_key,
            local_path: entry.local_path,
            temp_path: None,
            size: Some(size),
            size_listed: false,
            size_changed: AtomicBool::new(false),
            modified: None,
            condition: ObjectCondition::default(),
            case_name: None,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        })
    }
    fn submit_delete_entry(self: &Arc<Self>, entry: Entry) -> Result<(), Error> {
        if self.request.dryrun {
            return self.publish_dry_run(transfer::Direction::Delete, &entry);
        }
        let request_key = uri::encode_s3_request_path_key_bytes(&entry.key);
        self.submit(Job {
            direction: transfer::Direction::Delete,
            raw_key: entry.key,
            request_key,
            local_path: PathBuf::new(),
            temp_path: None,
            size: entry.size,
            size_listed: entry.size_listed,
            size_changed: AtomicBool::new(false),
            modified: None,
            condition: ObjectCondition::default(),
            case_name: None,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        })
    }
    fn submit_unrequested(&self, entry: Entry, failure: Unrequested) -> Result<(), Error> {
        assert_eq!(self.request.direction, transfer::Direction::Download);
        let job = Job {
            direction: transfer::Direction::Download,
            request_key: uri::encode_s3_request_path_key_bytes(&entry.key),
            raw_key: entry.key,
            local_path: entry.local_path,
            temp_path: None,
            size: None,
            size_listed: false,
            size_changed: AtomicBool::new(false),
            modified: None,
            condition: ObjectCondition::default(),
            case_name: entry.case_name,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        };
        let Some(id) = self.queue_job(&job, 0)? else {
            return Ok(());
        };
        self.operations.discard(&job);
        lock(&self.state).stats.failed += 1;
        let (exception, text) = match failure {
            Unrequested::MissingContentLength => ("DownloadMissingContentLength", None),
            Unrequested::ParentDirectory(name) => (
                name,
                Some(path_error(transfer::PARENT_DIRECTORY_FAILURE, &job, name)),
            ),
            Unrequested::TempPath(error) => {
                let name = error.name();
                (
                    name,
                    Some(path_error(transfer::TEMP_PATH_FAILURE, &job, name)),
                )
            }
        };
        let reported = self.sink.publish(
            crate::results::Event::Failure {
                key: id,
                line: self.line(&job),
                exception: exception.as_bytes().to_vec(),
                transferred: Some(0),
                text,
            },
            self.request.quiet,
        );
        self.retire(&job, 0);
        reported.map_err(|error| {
            self.record_fatal(&error);
            Error::Output(error)
        })
    }
    /// Deletes the object `key` of the listed `size` only a sync upload's
    /// destination holds, under `--delete`, or reports it under a dry run.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take its queued result.
    pub fn submit_destination_delete(
        self: &Arc<Self>,
        key: Vec<u8>,
        size: u64,
    ) -> Result<(), Error> {
        if self.stopped() {
            return Ok(());
        }
        self.submit_delete_entry(Entry {
            key,
            size: Some(size),
            size_listed: true,
            ..Entry::default()
        })
    }
    /// Removes the file at `local_path` only a sync download's destination
    /// holds, under `--delete`, or reports it under a dry run.
    ///
    /// # Errors
    ///
    /// [`Error::Output`] when the result sink cannot take a result.
    pub fn delete_local_file(&self, local_path: &Path) -> Result<(), Error> {
        if self.stopped() {
            return Ok(());
        }
        let line = self.local_delete_line(local_path);
        if self.request.dryrun {
            return self.publish_dry_run_line(line);
        }
        let job = Job {
            direction: transfer::Direction::Delete,
            raw_key: Vec::new(),
            request_key: String::new(),
            local_path: local_path.to_path_buf(),
            temp_path: None,
            size: Some(0),
            size_listed: false,
            size_changed: AtomicBool::new(false),
            modified: None,
            condition: ObjectCondition::default(),
            case_name: None,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        };
        let Some(id) = self.queue_job(&job, 0)? else {
            return Ok(());
        };
        let event = match std::fs::remove_file(local_path) {
            Ok(()) => {
                lock(&self.state).stats.succeeded += 1;
                crate::results::Event::Success { key: id, line }
            }
            Err(error) => {
                lock(&self.state).stats.failed += 1;
                crate::results::Event::Failure {
                    key: id,
                    line,
                    exception: transfer::source_removal_failure(&self.cwd, local_path, &error),
                    transferred: Some(0),
                    text: None,
                }
            }
        };
        let reported = self.sink.publish(event, self.request.quiet);
        self.retire(&job, 0);
        reported.map_err(|error| {
            self.record_fatal(&error);
            Error::Output(error)
        })
    }
}

fn path_error(prefix: &str, job: &Job, error: &str) -> Vec<u8> {
    [
        prefix.as_bytes(),
        b" ",
        job.local_path.as_os_str().as_encoded_bytes(),
        b": ",
        error.as_bytes(),
    ]
    .concat()
}

pub(super) fn temp_path(path: &Path, id: u64) -> Result<PathBuf, TempPathError> {
    transfer::make_download_temp_path(path, id).map_err(|_| TempPathError::OutOfMemory)
}
