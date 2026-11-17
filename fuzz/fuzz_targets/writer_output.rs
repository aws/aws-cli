#![no_main]
libfuzzer_sys::fuzz_target!(|data: &[u8]| s3::download::testing::output_composition(data));
