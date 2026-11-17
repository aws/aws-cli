//! Unpredictable ids for download temp names.
//!
//! A download writes to `<destination>.<id>` and renames it into place, and
//! that open follows symlinks. If another local user could predict the name
//! in a directory they can write to, they could plant a symlink there and
//! have the download overwrite its target, so every id is drawn from the
//! operating system's random source. Each thread keeps its own batch of
//! random bytes, so drawing an id takes no lock and costs one system call
//! per 512 ids.
use std::cell::RefCell;
use std::io;

const ID_BYTES: usize = std::mem::size_of::<u64>();
pub(super) const BATCH_BYTES: usize = 4096;
#[cfg(test)]
pub(super) const IDS_PER_BATCH: usize = BATCH_BYTES / ID_BYTES;

pub(super) type Source = fn() -> io::Result<[u8; BATCH_BYTES]>;

/// One thread's unread random bytes. Bytes are zeroed once handed out.
#[derive(Debug)]
pub(super) struct Batch {
    bytes: [u8; BATCH_BYTES],
    offset: usize,
}
impl Batch {
    /// An empty batch, which its first draw refills.
    pub(super) const fn empty() -> Self {
        Self {
            bytes: [0; BATCH_BYTES],
            offset: BATCH_BYTES,
        }
    }
    /// The next id, refilling the batch from `source` once it is spent.
    pub(super) fn draw(&mut self, source: Source) -> io::Result<u64> {
        if self.offset == BATCH_BYTES {
            self.bytes = source()?;
            self.offset = 0;
        }
        let range = self.offset..self.offset + ID_BYTES;
        let mut id = [0; ID_BYTES];
        id.copy_from_slice(&self.bytes[range.clone()]);
        self.bytes[range].fill(0);
        self.offset += ID_BYTES;
        Ok(u64::from_ne_bytes(id))
    }
}

thread_local! {
    static BATCH: RefCell<Batch> = const { RefCell::new(Batch::empty()) };
}

/// The next id from this thread's batch, which `source` refills.
pub(super) fn draw(source: Source) -> io::Result<u64> {
    BATCH.with_borrow_mut(|batch| batch.draw(source))
}
