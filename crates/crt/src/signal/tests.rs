use super::*;
use std::sync::{Arc, mpsc};
use std::time::Duration;

const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(10);

#[test]
fn completion_before_repeated_waits() {
    let signal = ShutdownSignal::new();
    signal.complete();
    signal.wait();
    signal.wait();
    assert!(signal.is_complete());
}
#[test]
fn completion_wakes_waiter() -> Result<(), Box<dyn std::error::Error>> {
    let signal = Arc::new(ShutdownSignal::new());
    let (started_sender, started) = mpsc::channel();
    let (finished_sender, finished) = mpsc::channel();
    let waiter = std::thread::spawn({
        let signal = Arc::clone(&signal);
        move || {
            signal.wait_notifying(|| {
                let _ = started_sender.send(());
            });
            let _ = finished_sender.send(());
        }
    });
    started.recv_timeout(HANDSHAKE_TIMEOUT)?;
    signal.complete();
    finished.recv_timeout(HANDSHAKE_TIMEOUT)?;
    assert!(waiter.join().is_ok());
    signal.wait();
    assert!(signal.is_complete());
    Ok(())
}
