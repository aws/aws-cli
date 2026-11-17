#![no_main]
libfuzzer_sys::fuzz_target!(|data: &[u8]| s3::testing::path_containment(data));
