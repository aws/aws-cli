use super::*;
#[derive(Clone, Copy, Debug, Default)]
pub(super) struct SubmitShape {
    pub rejected: bool,
    pub early_finish: bool,
    pub race_interrupt: bool,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) struct Lines {
    pub success: u64,
    pub failure: u64,
    pub canceled: u64,
    pub other: u64,
}
#[derive(Debug, Default)]
pub(super) struct Output(Mutex<Lines>);
impl Output {
    pub fn counts(&self) -> Lines {
        *lock(&self.0)
    }
}
impl Sink for Output {
    fn emit(&self, event: Event) -> Result<(), String> {
        let mut lines = lock(&self.0);
        let line = match event.stream {
            Stream::Stdout if event.text.starts_with(b"download: ") => &mut lines.success,
            Stream::Stderr if event.text.starts_with(b"download failed: ") => &mut lines.failure,
            Stream::Stderr if event.text == b"cancelled: ctrl-c received\n" => &mut lines.canceled,
            _ => &mut lines.other,
        };
        *line += 1;
        Ok(())
    }
}
#[derive(Debug)]
pub(super) struct Observed {
    pub key: Vec<u8>,
    pub callback: Option<Arc<dyn Completion>>,
    pub cancels: Arc<AtomicUsize>,
    pub releases: Arc<AtomicUsize>,
}
#[derive(Debug, Default)]
pub(super) struct FakeRuntime {
    pub shape: Mutex<SubmitShape>,
    pub interrupt: Arc<interrupt::State>,
    pub observed: Mutex<Vec<Observed>>,
    pub commits: AtomicU64,
    pub discards: AtomicU64,
}
#[derive(Debug)]
struct Handle {
    cancels: Arc<AtomicUsize>,
    releases: Arc<AtomicUsize>,
}
impl OwnedRequest for Handle {
    fn cancel(&self) {
        self.cancels.fetch_add(1, Ordering::Relaxed);
    }
}
impl Drop for Handle {
    fn drop(&mut self) {
        self.releases.fetch_add(1, Ordering::Relaxed);
    }
}
impl Operations for FakeRuntime {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, _: &Path) -> crate::transfer::SourceInspection {
        crate::transfer::SourceInspection::Size(0)
    }
    fn temp_path(&self, path: &Path) -> Result<PathBuf, TempPathError> {
        let mut temp = path.as_os_str().to_owned();
        temp.push(".fake-temp");
        Ok(temp.into())
    }
    fn submit(
        &self,
        job: Arc<Job>,
        callback: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        let shape = *lock(&self.shape);
        let cancels = Arc::new(AtomicUsize::new(0));
        let releases = Arc::new(AtomicUsize::new(0));
        lock(&self.observed).push(Observed {
            key: job.raw_key.clone(),
            callback: (!shape.rejected).then(|| callback.clone()),
            cancels: cancels.clone(),
            releases: releases.clone(),
        });
        if shape.race_interrupt {
            self.interrupt.request();
        }
        if shape.rejected {
            return Err(SubmitError::Transfer(Box::new(TransferResult {
                error_code: FAILURE_CODE,
                ..Default::default()
            })));
        }
        if shape.early_finish {
            callback.finish(TransferResult {
                response_status: 200,
                ..Default::default()
            });
        }
        Ok(Box::new(Handle { cancels, releases }))
    }
    fn finalize(&self, _: &Job, _: &TransferResult) -> Finalize {
        self.commits.fetch_add(1, Ordering::Relaxed);
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {
        self.discards.fetch_add(1, Ordering::Relaxed);
    }
}
