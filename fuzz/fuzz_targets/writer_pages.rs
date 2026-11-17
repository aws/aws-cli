#![no_main]
libfuzzer_sys::fuzz_target!(|data: &[u8]| s3::download::testing::page_completion(data));
