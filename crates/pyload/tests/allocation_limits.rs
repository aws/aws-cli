use fearless_simd as _;
use ruzstd as _;

#[path = "allocation_limits/counting.rs"]
mod counting;
#[path = "allocation_limits/tests.rs"]
mod tests;

use counting::{Counts, counted};
