use super::*;

pub(super) fn fixture(wide: bool) -> Vec<u8> {
    let mut bytes = vec![0; 0x600];
    bytes[..2].copy_from_slice(b"MZ");
    put32(&mut bytes, 60, 0x80);
    bytes[0x80..0x84].copy_from_slice(b"PE\0\0");
    put16(&mut bytes, 0x84, if wide { 0x8664 } else { 0x14c });
    put16(&mut bytes, 0x86, 1);
    put16(&mut bytes, 0x94, 240);
    put16(&mut bytes, 0x98, if wide { 0x20b } else { 0x10b });
    let section = 0x188;
    bytes[section..section + 8].copy_from_slice(b".pyload\0");
    put32(&mut bytes, section + 8, 7);
    put32(&mut bytes, section + 16, 0x200);
    put32(&mut bytes, section + 20, 0x400);
    put32(&mut bytes, section + 36, 0x4000_0040);
    bytes[0x400..0x407].copy_from_slice(b"payload");
    bytes
}

mod tests;
