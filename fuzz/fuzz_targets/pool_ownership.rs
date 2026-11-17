#![no_main]
libfuzzer_sys::fuzz_target!(|data: &[u8]| crt::source_pool::model::ownership(data));
