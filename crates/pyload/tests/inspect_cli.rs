use fearless_simd as _;
use pyload as _;
use ruzstd as _;

#[cfg(unix)]
#[path = "inspect_cli/tests.rs"]
mod tests;
