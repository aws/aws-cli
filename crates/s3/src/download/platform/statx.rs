//! Linux statx UAPI layout, independent of libc wrapper availability on musl.
pub(super) const STATX_DIOALIGN: u32 = 0x2000;
#[repr(C)]
pub(super) struct Statx {
    pub stx_mask: u32,
    block_size: u32,
    attributes: u64,
    links: u32,
    uid: u32,
    gid: u32,
    mode: u16,
    padding: u16,
    inode: u64,
    size: u64,
    blocks: u64,
    attributes_mask: u64,
    timestamps: [Timestamp; 4],
    rdev_major: u32,
    rdev_minor: u32,
    dev_major: u32,
    dev_minor: u32,
    mount_id: u64,
    pub stx_dio_mem_align: u32,
    pub stx_dio_offset_align: u32,
    spare: [u64; 12],
}
#[repr(C)]
struct Timestamp {
    seconds: i64,
    nanoseconds: u32,
    reserved: i32,
}
const _: () = {
    assert!(std::mem::size_of::<Statx>() == 256);
    assert!(std::mem::offset_of!(Statx, stx_dio_mem_align) == 152);
    assert!(std::mem::offset_of!(Statx, stx_dio_offset_align) == 156);
};
