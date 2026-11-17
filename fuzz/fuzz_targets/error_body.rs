#![no_main]
libfuzzer_sys::fuzz_target!(|data: &[u8]| crt::s3::error_body::fuzz_read(data));
