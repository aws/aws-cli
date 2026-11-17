//! Bounded independent models of the download writer's range, page and write loops.
#![expect(clippy::unwrap_used, reason = "bounded test model invariants")]
mod composition;
pub(crate) mod fakes;
mod ranges;
mod retries;
#[cfg(test)]
mod tests;

#[doc(inline)]
pub use super::service::testing::shared_writer_reentry;
#[doc(inline)]
pub use composition::output_composition;
#[doc(inline)]
pub use ranges::{callback_ranges, page_completion};
#[doc(inline)]
pub use retries::write_retries;
