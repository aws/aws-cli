#![expect(clippy::unwrap_used, reason = "test assertions")]
use super::*;
use crate::download::{
    service::ThreadSpawner,
    stream_copy::{self, CopyMode},
    testing::fakes::{self, FakePlatform},
};
use std::{
    ops::Range,
    sync::{Barrier, atomic::Ordering, mpsc},
    time::Duration,
};

const PAGE: usize = 4096;

fn mapped(
    mapping: Arc<dyn MappedFile>,
    batch_bytes: usize,
    prefaulter: Option<Prefaulter>,
) -> Output {
    let size = mapping.len();
    Output {
        writer: WriterMode::Mmap,
        target: RwLock::new(Some(Target {
            mode: Mode::Mmap {
                tracker: Box::new(Mutex::new(PageCompletionTracker::new(
                    size,
                    PAGE,
                    batch_bytes,
                ))),
                mapping,
                prefaulter: Mutex::new(prefaulter),
                copy: CopyMode::Memcpy,
            },
            file: fakes::file(),
        })),
        size: size as u64,
        platform: Arc::new(FakePlatform::default()),
        state: Mutex::new(State::default()),
        wake: Condvar::new(),
    }
}
fn prefault_completed(output: &Output, page: usize) -> bool {
    let target = output.target();
    let prefaulter = match target.as_ref() {
        Some(Target {
            mode: Mode::Mmap { prefaulter, .. },
            ..
        }) => Some(prefaulter),
        _ => None,
    };
    lock(prefaulter.unwrap())
        .as_ref()
        .unwrap()
        .page_completed(page)
}

#[test]
fn a_mapped_write_marks_every_page_it_touches_copied() {
    let platform = Arc::new(FakePlatform::default());
    let mapping = platform.mmap_file(&fakes::file(), 12_000).unwrap();
    let prefaulter = Prefaulter::start_with(
        Arc::clone(&mapping),
        LocalityContext::default(),
        platform,
        &ThreadSpawner,
    )
    .unwrap();
    let output = mapped(mapping, EVICTION_BYTES, Some(prefaulter));
    output.write_now(0, &[1; 6_000]).unwrap();
    assert!(prefault_completed(&output, 0));
    assert!(prefault_completed(&output, 1));
    assert!(!prefault_completed(&output, 2));
    output.write_now(6_000, &[2; 6_000]).unwrap();
    assert!(prefault_completed(&output, 2));
    assert_eq!(output.conclude(true).unwrap().written_bytes, 12_000);
    output.close_file().unwrap();
}

#[derive(Debug)]
struct HeldEviction {
    bytes: Mutex<Vec<u8>>,
    hold: Mutex<Option<Arc<Barrier>>>,
}
impl MappedFile for HeldEviction {
    fn len(&self) -> usize {
        lock(&self.bytes).len()
    }
    unsafe fn copy_unique(&self, offset: usize, bytes: &[u8], mode: CopyMode) -> CopyPath {
        stream_copy::copy(
            mode,
            &mut lock(&self.bytes)[offset..offset + bytes.len()],
            bytes,
        )
    }
    fn advise(&self, _: Range<usize>, advice: Advice) -> std::io::Result<()> {
        if advice == Advice::Evict {
            let hold = lock(&self.hold).take();
            if let Some(hold) = hold {
                hold.wait();
                hold.wait();
            }
        }
        Ok(())
    }
}

#[test]
fn eviction_advice_runs_outside_the_page_accounting_lock() {
    let hold = Arc::new(Barrier::new(2));
    let mapping = Arc::new(HeldEviction {
        bytes: Mutex::new(vec![0; 2 * PAGE]),
        hold: Mutex::new(Some(Arc::clone(&hold))),
    });
    let output = Arc::new(mapped(mapping.clone(), PAGE, None));
    let first = {
        let output = Arc::clone(&output);
        std::thread::spawn(move || output.write_now(0, &[1; PAGE]))
    };
    hold.wait();
    let (done, finished) = mpsc::channel();
    let second = {
        let output = Arc::clone(&output);
        std::thread::spawn(move || {
            let result = output.write_now(PAGE as u64, &[2; PAGE]);
            let _ = done.send(());
            result
        })
    };
    let concurrent = finished.recv_timeout(Duration::from_secs(5)).is_ok();
    hold.wait();
    first.join().unwrap().unwrap();
    second.join().unwrap().unwrap();
    assert!(
        concurrent,
        "the second write waited for the first's eviction"
    );
    assert_eq!(
        output.conclude(true).unwrap().written_bytes,
        2 * PAGE as u64
    );
    assert_eq!(lock(&mapping.bytes)[PAGE - 1..PAGE + 1], [1, 2]);
    output.close_file().unwrap();
}

#[test]
fn direct_bounce_buffers_use_the_bounce_alignment() {
    let platform = Arc::new(FakePlatform::default());
    *lock(&platform.alignment) = Some(DirectAlignment {
        memory: 512,
        offset: 512,
    });
    let config = fakes::config(WriterMode::Direct);
    let policy = Policy {
        config: &config,
        prefault: PrefaultSource::Disabled,
        spawner: &ThreadSpawner,
    };
    let output = Output::prepare(
        fakes::file(),
        1_000,
        policy,
        Arc::clone(&platform) as Arc<dyn Platform>,
        &LocalityContext::default(),
        &mut ObjectPhases::default(),
    )
    .unwrap();
    assert_eq!(output.mode(), WriterMode::Direct);
    output.write_now(0, &[7; 1_000]).unwrap();
    assert_eq!(output.conclude(true).unwrap().written_bytes, 1_000);
    output.close_file().unwrap();
    assert_eq!(
        *lock(&platform.bounce_alignments),
        [io::BOUNCE_ALIGNMENT; 2]
    );
    assert_eq!(lock(&platform.disk)[..], [7; 1_000]);
}

fn writer_config(mode: WriterMode, requirement: Requirement) -> WriterConfig {
    WriterConfig {
        requirement,
        ..fakes::config(mode)
    }
}
fn prepared(
    file: File,
    size: u64,
    config: &WriterConfig,
    prefault: PrefaultSource,
    platform: Arc<dyn Platform>,
) -> Result<Arc<Output>, WriteError> {
    Output::prepare(
        file,
        size,
        Policy {
            config,
            prefault,
            spawner: &ThreadSpawner,
        },
        platform,
        &LocalityContext::default(),
        &mut ObjectPhases::default(),
    )
}
fn prefault_threads(output: &Output) -> Option<usize> {
    match output.target().as_ref() {
        Some(Target {
            mode: Mode::Mmap { prefaulter, .. },
            ..
        }) => lock(prefaulter).as_ref().map(Prefaulter::thread_count),
        _ => None,
    }
}
#[cfg(unix)]
fn contents(mut file: &File) -> Vec<u8> {
    use std::io::{Read, Seek};
    let mut bytes = Vec::new();
    file.rewind().unwrap();
    file.read_to_end(&mut bytes).unwrap();
    bytes
}
fn write_xyz(output: &Output, platform: &FakePlatform) {
    output.write_now(0, b"xyz").unwrap();
    assert_eq!(output.conclude(true).unwrap().written_bytes, 3);
    output.close_file().unwrap();
    assert_eq!(*lock(&platform.disk), b"xyz");
}
fn errno(code: i32) -> WriteError {
    WriteError::from(std::io::Error::from_raw_os_error(code))
}

#[test]
fn first_error_survives_competing_writer_reports() {
    let config = writer_config(WriterMode::Pwrite, Requirement::Required);
    let platform = Arc::new(FakePlatform::default());
    let output = prepared(
        fakes::file(),
        4,
        &config,
        PrefaultSource::Disabled,
        platform,
    )
    .unwrap();
    output.fail(errno(libc::ENOSPC));
    let start = Arc::new(Barrier::new(3));
    let competitors: Vec<_> = [libc::EIO, libc::EACCES]
        .into_iter()
        .map(|code| {
            let (output, start) = (Arc::clone(&output), Arc::clone(&start));
            std::thread::spawn(move || {
                start.wait();
                output.fail(errno(code));
            })
        })
        .collect();
    start.wait();
    for competitor in competitors {
        competitor.join().unwrap();
    }
    assert_eq!(output.error(), Some(errno(libc::ENOSPC)));
    assert_eq!(output.write_now(0, b"late"), Err(errno(libc::ENOSPC)));
    output.close_file().unwrap();
}

#[test]
fn mmap_output_honors_prefault_mode() {
    let config = writer_config(WriterMode::Mmap, Requirement::Required);
    for (prefault, threads) in [
        (PrefaultSource::Disabled, None),
        (PrefaultSource::Private, Some(PREFAULT_THREADS_PER_SHARD)),
    ] {
        let platform = Arc::new(FakePlatform::default());
        let output = prepared(fakes::file(), 8 * PAGE as u64, &config, prefault, platform).unwrap();
        assert_eq!(output.mode(), WriterMode::Mmap);
        assert_eq!(prefault_threads(&output), threads);
        output.close_file().unwrap();
    }
}

#[test]
fn a_preferred_direct_writer_falls_back_where_direct_io_is_refused() {
    let platform = Arc::new(FakePlatform::default());
    platform.direct_refused.store(true, Ordering::Relaxed);
    platform
        .unsupported_preallocation
        .store(true, Ordering::Relaxed);
    let disabled = PrefaultSource::Disabled;
    let required = writer_config(WriterMode::Direct, Requirement::Required);
    let error = prepared(fakes::file(), 3, &required, disabled, platform.clone()).unwrap_err();
    assert_eq!(error, WriteError::DirectUnavailable);
    let preferred = writer_config(WriterMode::Direct, Requirement::Preferred);
    let disabled = PrefaultSource::Disabled;
    let output = prepared(fakes::file(), 3, &preferred, disabled, platform.clone()).unwrap();
    assert_eq!(output.mode(), WriterMode::Pwrite);
    write_xyz(&output, &platform);
    assert_eq!(platform.direct_disables.load(Ordering::Relaxed), 0);
}

#[test]
fn a_preferred_direct_writer_the_file_rejects_turns_direct_io_off_again() {
    let platform = Arc::new(FakePlatform::default());
    *lock(&platform.alignment) = Some(DirectAlignment {
        memory: 3,
        offset: 3,
    });
    platform
        .unsupported_preallocation
        .store(true, Ordering::Relaxed);
    let disabled = PrefaultSource::Disabled;
    let required = writer_config(WriterMode::Direct, Requirement::Required);
    let error = prepared(fakes::file(), 3, &required, disabled, platform.clone()).unwrap_err();
    assert_eq!(error, WriteError::DirectInvalidAlignment);
    assert_eq!(platform.direct_disables.load(Ordering::Relaxed), 0);
    let sized = platform.set_lengths.load(Ordering::Relaxed);
    let preferred = writer_config(WriterMode::Direct, Requirement::Preferred);
    let disabled = PrefaultSource::Disabled;
    let output = prepared(fakes::file(), 3, &preferred, disabled, platform.clone()).unwrap();
    assert_eq!(output.mode(), WriterMode::Pwrite);
    assert_eq!(platform.direct_enables.load(Ordering::Relaxed), 2);
    assert_eq!(platform.direct_disables.load(Ordering::Relaxed), 1);
    assert!(!platform.direct_enabled.load(Ordering::Relaxed));
    assert_eq!(platform.set_lengths.load(Ordering::Relaxed) - sized, 2);
    assert_eq!(lock(&platform.disk).len(), 3);
    write_xyz(&output, &platform);
}

#[cfg(unix)]
#[test]
fn direct_probe_and_body_writes_share_injected_writer_state() {
    use std::os::unix::fs::FileExt;
    let platform = Arc::new(FakePlatform::default());
    *lock(&platform.alignment) = Some(DirectAlignment {
        memory: 8,
        offset: 8,
    });
    let file = fakes::file();
    file.write_all_at(b"abc", 0).unwrap();
    let reader = file.try_clone().unwrap();
    let preferred = writer_config(WriterMode::Direct, Requirement::Preferred);
    let disabled = PrefaultSource::Disabled;
    let output = prepared(file, 3, &preferred, disabled, platform.clone()).unwrap();
    assert_eq!(output.mode(), WriterMode::Direct);
    assert_eq!(*lock(&platform.write_sizes), [8]);
    assert_eq!(*lock(&platform.disk), [0; 3]);
    output.write_now(0, b"xyz").unwrap();
    assert_eq!(*lock(&platform.write_sizes), [8, 8]);
    assert_eq!(*lock(&platform.disk), *b"xyz\0\0\0\0\0");
    assert_eq!(output.conclude(true).unwrap().written_bytes, 3);
    output.close_file().unwrap();
    assert_eq!(*lock(&platform.disk), b"xyz");
    assert_eq!(contents(&reader), b"abc");
}

#[test]
fn direct_probe_allocation_failure_leaves_the_output_untouched() {
    let platform = Arc::new(FakePlatform::default());
    platform.bounce_failure.store(true, Ordering::Relaxed);
    lock(&platform.disk).extend_from_slice(b"abc");
    let required = writer_config(WriterMode::Direct, Requirement::Required);
    let disabled = PrefaultSource::Disabled;
    let error = prepared(fakes::file(), 3, &required, disabled, platform.clone()).unwrap_err();
    assert!(
        matches!(
            error,
            WriteError::Io {
                kind: std::io::ErrorKind::OutOfMemory,
                ..
            }
        ),
        "{error:?}"
    );
    assert!(lock(&platform.write_sizes).is_empty());
    assert_eq!(*lock(&platform.disk), b"abc");
    assert_eq!(platform.set_lengths.load(Ordering::Relaxed), 1);
    assert_eq!(platform.closes.load(Ordering::Relaxed), 1);
}

#[test]
fn a_mapped_writer_that_cannot_be_set_up_falls_back_without_its_mapping() {
    let platform = Arc::new(FakePlatform::default());
    platform.evict_error.store(true, Ordering::Relaxed);
    let preferred = writer_config(WriterMode::Mmap, Requirement::Preferred);
    let private = PrefaultSource::Private;
    let output = prepared(
        fakes::file(),
        8 * PAGE as u64,
        &preferred,
        private,
        platform.clone(),
    );
    let output = output.unwrap();
    assert_eq!(output.mode(), WriterMode::Pwrite);
    let mapping = lock(&platform.mapping).take().unwrap();
    assert_eq!(Arc::strong_count(&mapping), 1);
    output.write_now(0, b"written without a mapping").unwrap();
    assert_eq!(&lock(&platform.disk)[..25], b"written without a mapping");
    output.close_file().unwrap();
}

#[cfg(target_os = "linux")]
fn native_output(mode: WriterMode, size: u64) -> Result<(Arc<Output>, File), WriteError> {
    let file = fakes::file();
    let reader = file.try_clone().unwrap();
    let config = writer_config(mode, Requirement::Required);
    let platform = Arc::new(platform::NativePlatform);
    let output = prepared(file, size, &config, PrefaultSource::Disabled, platform)?;
    assert_eq!(output.mode(), mode);
    Ok((output, reader))
}

#[cfg(target_os = "linux")]
#[cfg_attr(miri, ignore = "real O_DIRECT writes are covered natively")]
#[test]
fn direct_writer_persists_aligned_data_and_an_unaligned_eof_tail() {
    let platform = platform::NativePlatform;
    let file = fakes::file();
    if platform.enable_direct_io(&file).is_err() {
        return;
    }
    let block = platform.direct_io_alignment(&file).unwrap().offset;
    if block <= 3 {
        return;
    }
    let size = block as u64 + 3;
    let (output, reader) = match native_output(WriterMode::Direct, size) {
        Err(WriteError::Io {
            name: "DownloadPositionalWriteRejected",
            ..
        }) => return,
        result => result.unwrap(),
    };
    let mut first = platform::AlignedBuffer::new(block, io::BOUNCE_ALIGNMENT).unwrap();
    first.as_mut_slice().fill(b'a');
    output.write_now(0, first.as_slice()).unwrap();
    output.write_now(block as u64, b"xyz").unwrap();
    let stats = output.conclude(true).unwrap();
    if cfg!(feature = "download-writer-debug") {
        assert_eq!(stats.direct_padded_bytes, block as u64 - 3);
    }
    output.close_file().unwrap();
    platform.disable_direct_io(&reader).unwrap();
    let bytes = contents(&reader);
    assert_eq!(bytes.len() as u64, size);
    assert!(bytes[..block].iter().all(|&byte| byte == b'a'));
    assert_eq!(&bytes[block..], b"xyz");
}

#[cfg(target_os = "linux")]
#[cfg_attr(miri, ignore = "real file mappings are covered natively")]
#[test]
fn mmap_and_pwrite_agree_for_misaligned_page_boundary_chunks() {
    let page = platform::NativePlatform.page_size();
    let size = page * 2 + 37;
    let expected: Vec<u8> = (0..size)
        .map(|index| index.wrapping_mul(31).wrapping_add(7) as u8)
        .collect();
    let chunks = [
        0..page - 3,
        page - 3..page + 5,
        page + 5..page * 2,
        page * 2..size,
    ];
    for mode in [WriterMode::Pwrite, WriterMode::Mmap] {
        let (output, reader) = match native_output(mode, size as u64) {
            Err(WriteError::MmapUnavailable) if mode == WriterMode::Mmap => return,
            result => result.unwrap(),
        };
        for chunk in chunks.clone() {
            output
                .write_now(chunk.start as u64, &expected[chunk])
                .unwrap();
        }
        assert_eq!(output.conclude(true).unwrap().written_bytes, size as u64);
        output.close_file().unwrap();
        assert_eq!(contents(&reader), expected, "{mode:?}");
    }
}
