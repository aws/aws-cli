use super::*;
use crate::testing::{Script, sweep};

/// Bodies of 8, 3 and 5 bytes, A's outcome, the queue's capacity and the
/// salt 17.
fn round(terminal: Terminal, capacity: usize) -> Script {
    Script::new()
        .range(1, 64, 8)
        .range(1, 64, 3)
        .range(1, 64, 5)
        .index(2, usize::from(terminal == Terminal::WriteFailure))
        .range(1, 3, capacity)
        .range(0, 255, 17)
}

#[test]
fn fuzz_shared_writer_ticket_reentry() {
    for terminal in [Terminal::Active, Terminal::WriteFailure] {
        for capacity in 1..=3 {
            round(terminal, capacity).replay(shared_writer_reentry_from);
        }
    }
    sweep(8, shared_writer_reentry);
}
