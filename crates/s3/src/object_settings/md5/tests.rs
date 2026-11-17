use super::*;

fn hex(digest: [u8; 16]) -> String {
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[test]
fn digests_the_rfc_1321_test_suite() {
    for (input, expected) in [
        (b"".as_slice(), "d41d8cd98f00b204e9800998ecf8427e"),
        (b"a".as_slice(), "0cc175b9c0f1b6a831c399e269772661"),
        (b"abc".as_slice(), "900150983cd24fb0d6963f7d28e17f72"),
        (
            b"message digest".as_slice(),
            "f96b697d7cb7938d525a2f31aaf161d0",
        ),
        (
            b"abcdefghijklmnopqrstuvwxyz".as_slice(),
            "c3fcd3d76192e4007dfb496cca67e13b",
        ),
        (
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789".as_slice(),
            "d174ab98d277d9f5a5611c2c9f419d9f",
        ),
        (
            b"12345678901234567890123456789012345678901234567890123456789012345678901234567890"
                .as_slice(),
            "57edf4a22be3c955ac49da2e2107b67a",
        ),
    ] {
        assert_eq!(hex(digest(input)), expected, "{input:?}");
    }
}

#[test]
fn digests_every_padding_boundary() {
    for (len, expected) in [
        (55, "6912ee65fff2d9f9ce2508cddf8bcda0"),
        (56, "51fdd1acda72405dfdfa03fcb85896d7"),
        (57, "5320ef4c17ef34a0cf2db763338d25eb"),
        (63, "48a6295221902e8e0938f773a7185e72"),
        (64, "b2d3f56bc197fd985d5965079b5e7148"),
        (65, "8bd7053801c768420faf816fadba971c"),
        (119, "1c772251899a7ff007400b888d6b2042"),
        (120, "b7ba1efc6022e9ed272f00b8831e26e6"),
        (128, "37eff01866ba3f538421b30b7cbefcac"),
        (1000, "a24f1e3ef66950e1327f210e3997ba2c"),
    ] {
        let input: Vec<u8> = (0..len).map(|index| (index % 251) as u8).collect();
        assert_eq!(hex(digest(&input)), expected, "{len}");
    }
}
