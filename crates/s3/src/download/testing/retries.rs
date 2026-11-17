use super::super::{
    WriteError,
    io::{self, DirectAlignment, IoStats, PositionalWriter},
};
use crate::testing::Choices;
use std::{fs::File, ops::Range, sync::Mutex};

#[repr(align(64))]
struct Source([u8; 256]);
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Fault {
    Unaligned,
    Zero,
    NoSpace,
}
/// The faulting disk: a write's outcome is the input's choice.
#[derive(Debug)]
struct Disk<'s, 'a> {
    source: &'s [u8],
    alignment: DirectAlignment,
    image: Vec<u8>,
    input: &'s mut Choices<'a>,
    retries: usize,
    terminal: Option<Fault>,
    calls: u64,
    interrupted: u64,
    short: u64,
    accepted: usize,
}
impl PositionalWriter for Mutex<Disk<'_, '_>> {
    fn write_at(&self, _: &File, bytes: &[u8], offset: u64) -> std::io::Result<usize> {
        self.lock().unwrap().write(bytes, offset)
    }
}
impl Disk<'_, '_> {
    fn write(&mut self, bytes: &[u8], offset: u64) -> std::io::Result<usize> {
        self.calls += 1;
        let start = offset as usize;
        assert!(!bytes.is_empty());
        assert!(start.is_multiple_of(self.alignment.offset));
        assert!(bytes.len().is_multiple_of(self.alignment.offset));
        assert!((bytes.as_ptr() as usize).is_multiple_of(self.alignment.memory));
        assert!(start + bytes.len() <= self.image.len());
        for (index, &byte) in bytes.iter().enumerate() {
            assert_eq!(byte, self.source.get(start + index).copied().unwrap_or(0));
        }
        let length = self.write_length(bytes.len())?;
        self.image[start..start + length].copy_from_slice(&bytes[..length]);
        self.accepted += length;
        Ok(length)
    }
    fn write_length(&mut self, length: usize) -> std::io::Result<usize> {
        let step = self.alignment.memory.max(self.alignment.offset);
        if let Some(fault) = self.terminal
            && (fault != Fault::Unaligned || (step > 1 && length > 1))
            && self.input.flag()
        {
            self.terminal = None;
            return match fault {
                Fault::Zero => Ok(0),
                Fault::NoSpace => Err(std::io::ErrorKind::StorageFull.into()),
                Fault::Unaligned => {
                    let remainder = self.input.range(1, step.min(length) - 1);
                    Ok(step * self.input.range(0, (length - 1 - remainder) / step) + remainder)
                }
            };
        }
        if self.retries == 0 || !self.input.flag() {
            return Ok(length);
        }
        self.retries -= 1;
        if length >= 2 * step && self.input.flag() {
            self.short += 1;
            Ok(step * self.input.range(1, length / step - 1))
        } else {
            self.interrupted += 1;
            Err(std::io::ErrorKind::Interrupted.into())
        }
    }
}

/// Checks positional and direct writes with bounded faults against an independent disk image.
pub fn write_retries(bytes: &[u8]) {
    write_retries_from(&mut Choices::new(bytes));
}
pub(super) fn write_retries_from(input: &mut Choices<'_>) {
    let direct = input.flag();
    let alignment = if direct {
        DirectAlignment {
            offset: 1 << input.range(0, 6),
            memory: 1 << input.range(0, 6),
        }
    } else {
        DirectAlignment {
            offset: 1,
            memory: 1,
        }
    };
    let size = input.range(1, 256);
    let retries = input.range(0, 8);
    let terminal = input
        .flag()
        .then(|| [Fault::Unaligned, Fault::Zero, Fault::NoSpace][input.index(3)]);
    let mut chunks = split(size, alignment.offset, input);
    let source = Source(std::array::from_fn(|index| {
        (index as u8).wrapping_mul(7).wrapping_add(3)
    }));
    let disk = Mutex::new(Disk {
        source: &source.0[..size],
        alignment,
        image: vec![0; size.div_ceil(alignment.offset) * alignment.offset],
        input,
        retries,
        terminal,
        calls: 0,
        interrupted: 0,
        short: 0,
        accepted: 0,
    });
    let file = File::open(std::env::current_exe().unwrap()).unwrap();
    while !chunks.is_empty() {
        if direct && disk.lock().unwrap().input.flag() {
            reject_illegal(&disk, &file);
        }
        let pick = disk.lock().unwrap().input.index(chunks.len());
        if !write_chunk(&disk, &file, chunks.swap_remove(pick), direct) {
            return;
        }
    }
    let disk = disk.lock().unwrap();
    assert_eq!(&disk.image[..size], disk.source);
    assert!(disk.image[size..].iter().all(|&byte| byte == 0));
}

fn split(size: usize, block: usize, input: &mut Choices<'_>) -> Vec<Range<usize>> {
    let mut chunks = Vec::new();
    let mut start = 0;
    while start < size {
        let blocks = input.range(1, (size - start).div_ceil(block));
        let end = (start + blocks * block).min(size);
        chunks.push(start..end);
        start = end;
    }
    chunks
}

fn write_chunk(disk: &Mutex<Disk<'_, '_>>, file: &File, chunk: Range<usize>, direct: bool) -> bool {
    let (source, alignment, armed) = {
        let mut disk = disk.lock().unwrap();
        disk.calls = 0;
        disk.interrupted = 0;
        disk.short = 0;
        disk.accepted = 0;
        (disk.source, disk.alignment, disk.terminal)
    };
    let bytes = &source[chunk.clone()];
    let result = if direct {
        io::write_direct(
            disk,
            file,
            bytes,
            chunk.start as u64,
            source.len() as u64,
            alignment,
        )
    } else {
        io::write_all(disk, file, bytes, chunk.start as u64, None)
    };
    let disk = disk.lock().unwrap();
    if let Some(armed) = armed.filter(|_| disk.terminal.is_none()) {
        match armed {
            Fault::Unaligned => assert_eq!(result, Err(WriteError::DirectShortWriteUnaligned)),
            Fault::Zero => assert_eq!(result, Err(WriteError::WriteZero)),
            Fault::NoSpace => assert!(matches!(
                result,
                Err(WriteError::Io {
                    kind: std::io::ErrorKind::StorageFull,
                    ..
                })
            )),
        }
        return false;
    }
    let stats = result.unwrap();
    let padded = bytes.len().div_ceil(alignment.offset) * alignment.offset;
    assert_eq!(disk.accepted, padded);
    assert_eq!(disk.calls, 1 + disk.interrupted + disk.short);
    verify_stats(&disk, bytes, direct, stats);
    true
}

fn verify_stats(disk: &Disk<'_, '_>, bytes: &[u8], direct: bool, stats: IoStats) {
    if !cfg!(feature = "download-writer-debug") {
        return;
    }
    let padding = bytes.len().div_ceil(disk.alignment.offset) * disk.alignment.offset - bytes.len();
    let bounce = direct
        && (padding != 0 || !(bytes.as_ptr() as usize).is_multiple_of(disk.alignment.memory));
    assert_eq!(stats.calls, disk.calls);
    assert_eq!(stats.interrupted, disk.interrupted);
    assert_eq!(stats.short_writes, disk.short);
    assert_eq!(
        stats.bounce_bytes,
        if bounce { bytes.len() as u64 } else { 0 }
    );
    assert_eq!(stats.padded_bytes, padding as u64);
}

fn reject_illegal(disk: &Mutex<Disk<'_, '_>>, file: &File) {
    let (source, alignment, calls, accepted, pick, end) = {
        let mut disk = disk.lock().unwrap();
        (
            disk.source,
            disk.alignment,
            disk.calls,
            disk.accepted,
            disk.input.index(4),
            disk.image.len(),
        )
    };
    let write =
        |bytes, offset| io::write_direct(disk, file, bytes, offset, source.len() as u64, alignment);
    match pick {
        0 => assert_eq!(
            write(&source[..1], end as u64),
            Err(WriteError::OutOfBounds)
        ),
        1 if alignment.offset > 1 && source.len() >= 2 => {
            assert_eq!(
                write(&source[1..2], 1),
                Err(WriteError::DirectOffsetUnaligned)
            );
        }
        2 if alignment.offset > 1 && source.len() >= 2 => {
            assert_eq!(
                write(&source[..1], 0),
                Err(WriteError::DirectNonFinalLengthUnaligned)
            );
        }
        3 => {
            assert!(write(&source[..0], 0).is_ok());
        }
        _ => {}
    }
    let disk = disk.lock().unwrap();
    assert_eq!((disk.calls, disk.accepted), (calls, accepted));
}
