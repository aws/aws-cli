#![allow(
    clippy::expect_used,
    reason = "the fixtures push only while the pool is open"
)]
use super::*;

#[test]
fn every_job_completes_before_join() -> io::Result<()> {
    let values = Arc::new(Mutex::new(Vec::new()));
    let output = Arc::clone(&values);
    let mut pool = WritePool::new(2, 4, move |value| lock(&output).push(value));
    pool.start()?;
    for value in 1..=6 {
        pool.push(value).expect("open pool");
    }
    pool.close();
    pool.join();
    let mut values = lock(&values);
    values.sort();
    assert_eq!(*values, [1, 2, 3, 4, 5, 6]);
    assert_eq!(pool.stats().executed, 6);
    assert!(pool.stats().queue_hwm >= 1);
    Ok(())
}

#[test]
fn close_drains_backlog_queued_before_start() -> io::Result<()> {
    let values = Arc::new(Mutex::new(Vec::new()));
    let output = Arc::clone(&values);
    let mut pool = WritePool::new(1, 4, move |value| lock(&output).push(value));
    for value in [7, 8, 9, 10] {
        pool.push(value).expect("open pool");
    }
    pool.close();
    pool.start()?;
    pool.join();
    let mut values = lock(&values);
    values.sort_unstable();
    assert_eq!(*values, [7, 8, 9, 10]);
    Ok(())
}

#[test]
fn push_after_close_fails() -> io::Result<()> {
    let mut pool = WritePool::new(1, 2, |_: usize| {});
    pool.start()?;
    pool.close();
    pool.join();
    assert_eq!(pool.push(1), Err(Closed));
    Ok(())
}

#[test]
fn concurrent_producers_and_workers_complete_every_job_once() -> io::Result<()> {
    let count = if cfg!(miri) { 8 } else { 2_000 };
    let values = Arc::new(Mutex::new(Vec::new()));
    let output = Arc::clone(&values);
    let mut pool = WritePool::new(3, 4, move |value| lock(&output).push(value));
    pool.start()?;
    thread::scope(|scope| {
        for producer in 0..4 {
            let pool = &pool;
            scope.spawn(move || {
                for index in 0..count {
                    pool.push(producer * count + index).expect("open pool");
                }
            });
        }
    });
    pool.close();
    pool.join();
    let mut values = lock(&values);
    values.sort_unstable();
    assert_eq!(*values, (0..4 * count).collect::<Vec<_>>());
    assert_eq!(pool.stats().executed, 4 * count);
    Ok(())
}
#[test]
fn a_ring_that_cannot_be_reserved_is_out_of_memory() {
    let mut pool = WritePool::new(1, usize::MAX, |_: u64| {});
    let error = pool.start().expect_err("unreservable ring");
    assert_eq!(error.kind(), io::ErrorKind::OutOfMemory);
    assert!(pool.threads.is_empty());
}
