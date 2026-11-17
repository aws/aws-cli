#![expect(
    clippy::unwrap_used,
    reason = "tests assert channel completion and fixture setup"
)]
#![expect(
    clippy::expect_used,
    reason = "every scripted submission requires a canned response"
)]
#![expect(
    clippy::panic,
    reason = "unexpected fake transport events fail the test"
)]
use super::super::*;
use super::super::{
    driver::{Options, PageOps, Submit},
    page::Page,
    request::{Operation, Query},
};
use crate::s3::{
    CANCELED_ERROR_CODE, INVALID_ARGUMENT_ERROR_CODE, ListLocalError, TransferResult,
    UNKNOWN_ERROR_CODE,
};
use crate::signal::lock;
use cli_core::interrupt::Canceled;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
fn objects() -> Query<'static> {
    Query {
        operation: Operation::ListObjectsV2,
        prefix: b"",
        delimiter: b"",
        region: b"",
        page_size: 0,
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Outcome {
    Answered,
    Refused,
    Unbuilt,
}
#[derive(Clone)]
struct Reply {
    body: &'static [u8],
    outcome: Outcome,
}
impl Reply {
    fn ok(body: &'static [u8]) -> Self {
        Self {
            body,
            outcome: Outcome::Answered,
        }
    }
    fn failed(outcome: Outcome) -> Self {
        Self {
            body: FINAL,
            outcome,
        }
    }
}
struct FakeOps {
    replies: VecDeque<Reply>,
    events: Arc<Mutex<Vec<String>>>,
    next: usize,
}
impl PageOps for FakeOps {
    type Handle = (usize, Arc<Page>);
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        let id = self.next;
        self.next += 1;
        lock(&self.events).push(format!("submit {id} {}", String::from_utf8_lossy(path)));
        let reply = self
            .replies
            .pop_front()
            .expect("a response for every submission");
        match reply.outcome {
            Outcome::Answered => {}
            Outcome::Refused => return Ok(Submit::Failed(UNKNOWN_ERROR_CODE)),
            Outcome::Unbuilt => {
                return Err(Box::new(TransferResult::from_crt_error(
                    INVALID_ARGUMENT_ERROR_CODE,
                )));
            }
        }
        let _ = page.append_chunk(reply.body);
        page.finish(TransferResult {
            response_status: 200,
            ..TransferResult::default()
        });
        Ok(Submit::Submitted((id, Arc::clone(page))))
    }
    fn cancel(&mut self, handle: &Self::Handle) {
        lock(&self.events).push(format!("cancel {}", handle.0));
    }
    fn release(&mut self, handle: Self::Handle) {
        lock(&self.events).push(format!("release {}", handle.0));
        handle.1.shutdown();
        lock(&self.events).push(format!("shutdown {}", handle.0));
    }
    fn backoff(
        &mut self,
        attempt: u64,
        _: crate::s3::botocore_retry::ErrorKind,
    ) -> Result<(), Canceled> {
        lock(&self.events).push(format!("backoff {attempt}"));
        Ok(())
    }
}
fn fake(replies: Vec<Reply>) -> FakeOps {
    FakeOps {
        replies: replies.into(),
        events: Arc::new(Mutex::new(Vec::new())),
        next: 0,
    }
}
const FIRST: &[u8] = b"<ListBucketResult><IsTruncated>true</IsTruncated><NextContinuatio\
    nToken>next</NextContinuationToken><Contents><Key>a</Key></Conten\
    ts></ListBucketResult>";
const SECOND: &[u8] = b"<ListBucketResult><IsTruncated>true</IsTruncated><NextContinuati\
    onToken>later</NextContinuationToken><Contents><Key>a</Key></Cont\
    ents></ListBucketResult>";
const FINAL: &[u8] = b"<ListBucketResult><IsTruncated>false</IsTruncated><Contents><Key>\
    b</Key></Contents></ListBucketResult>";
#[test]
fn prefetch_precedes_emit_and_shutdown_is_counted_once() {
    let mut ops = fake(vec![Reply::ok(FIRST), Reply::ok(FINAL)]);
    let events = Arc::clone(&ops.events);
    let mut stats = ListStats::default();
    let result = driver::run(
        Options::new(b"/bucket", objects(), true),
        &mut ops,
        Some(&mut stats),
        &mut |entry| {
            lock(&events).push(format!("emit {}", String::from_utf8_lossy(&entry.name)));
            0
        },
    );
    assert_eq!(result.transfer.error_code, 0);
    let events = lock(&events);
    let submit = events
        .iter()
        .position(|v| v.starts_with("submit 1"))
        .unwrap();
    let emit = events.iter().position(|v| v == "emit a").unwrap();
    assert!(submit < emit);
    assert_eq!(stats.pages, 2);
    assert_eq!(stats.entries, 2);
    assert_eq!(stats.shutdown_wait.count, 2);
    assert_eq!(stats.token_pages, 1);
    assert_eq!(stats.final_pages, 1);
}
#[test]
fn sink_stop_cancels_prefetch_and_drains_every_shutdown() {
    let mut ops = fake(vec![Reply::ok(FIRST), Reply::ok(FINAL)]);
    let result = driver::run(
        Options::new(b"", objects(), true),
        &mut ops,
        None,
        &mut |_| 12,
    );
    assert_eq!(result.callback_error, 12);
    assert_eq!(result.transfer.error_code, CANCELED_ERROR_CODE);
    let events = lock(&ops.events);
    assert!(events.iter().any(|v| v == "cancel 1"));
    assert!(events.iter().any(|v| v == "shutdown 0"));
    assert!(events.iter().any(|v| v == "shutdown 1"));
}
#[test]
fn rejected_prefetch_retries_the_authoritative_token_serially() {
    let _library = crate::runtime::Library::acquire();
    for outcome in [Outcome::Refused, Outcome::Unbuilt] {
        let mut ops = fake(vec![
            Reply::ok(FIRST),
            Reply::failed(outcome),
            Reply::ok(FINAL),
        ]);
        let result = driver::run(
            Options::new(b"", objects(), true),
            &mut ops,
            None,
            &mut |_| 0,
        );
        assert_eq!(result.transfer.error_code, 0, "{outcome:?}");
        assert_eq!(result.local_error, None, "{outcome:?}");
        assert_eq!(ops.next, 3, "{outcome:?}");
    }
}
#[test]
fn buckets_submit_the_next_page_after_emission() {
    let first = b"<ListAllMyBucketsResult><Buckets><Bucket><Name>a</Name></Bucket><\
        /Buckets><ContinuationToken>next</ContinuationToken></ListAllMyBu\
        cketsResult>";
    let mut ops = fake(vec![
        Reply::ok(first),
        Reply::ok(b"<ListAllMyBucketsResult/>"),
    ]);
    let events = Arc::clone(&ops.events);
    let query = Query {
        operation: Operation::ListBuckets,
        ..objects()
    };
    driver::run(Options::new(b"", query, false), &mut ops, None, &mut |_| {
        lock(&events).push("emit".into());
        0
    });
    let events = lock(&events);
    let emit = events.iter().position(|v| v == "emit").unwrap();
    let submit = events
        .iter()
        .position(|v| v.starts_with("submit 1"))
        .unwrap();
    assert!(emit < submit);
}
#[test]
fn page_budget_bounds_capacity_and_preserves_first_append_failure() {
    let page = Page::new(9);
    assert!(page.append_chunk(b"12345").is_ok());
    assert!(page.append_chunk(b"6789").is_ok());
    assert_eq!(lock(&page.inner).body.capacity(), 9);
    assert!(page.append_chunk(b"0").is_err());
    assert_eq!(lock(&page.inner).body, b"123456789");
    assert!(page.append_chunk(b"more").is_err());
}
#[test]
fn histogram_and_retry_status_preserve_the_published_schema() {
    let mut stats = ListPhaseStats::default();
    for value in [0, 999_999, 1_000_000, 2_000_000, 3_000_000, 4_000_000] {
        stats.add(value);
    }
    assert_eq!(&stats.histogram[..4], &[2, 1, 2, 1]);
    assert_eq!(stats.ns_min, 0);
    assert_eq!(stats.ns_max, 4_000_000);
    let mut saturated = ListPhaseStats::default();
    saturated.add(u64::MAX);
    assert_eq!(saturated.histogram[15], 1);
    for (crt_name, attempt_status, status) in [
        (&b"AWS_ERROR_S3_SLOW_DOWN"[..], 503, 503),
        (b"AWS_IO_SOCKET_CONNECTION_REFUSED", 0, 0),
        (b"AWS_ERROR_HTTP_CONNECTION_CLOSED", 500, 0),
    ] {
        let page = Page::new(100);
        lock(&page.inner).attempt_status = attempt_status;
        let mut result = TransferResult::default();
        result.crt_name.set(crt_name);
        page.finish(result);
        assert_eq!(
            lock(&page.inner).result.as_ref().unwrap().response_status,
            status,
            "{}",
            String::from_utf8_lossy(crt_name)
        );
    }
}
use std::sync::mpsc;
use std::time::Duration;
enum Event {
    Submit(usize),
    Release(usize, Arc<Page>),
}
struct DelayedOps {
    next: usize,
    events: mpsc::Sender<Event>,
}
impl PageOps for DelayedOps {
    type Handle = (usize, Arc<Page>);
    fn submit(
        &mut self,
        page: &Arc<Page>,
        _: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        let id = self.next;
        self.next += 1;
        self.events.send(Event::Submit(id)).unwrap();
        page.append_chunk([FIRST, SECOND, FINAL][id.min(2)])
            .unwrap();
        page.finish(TransferResult {
            response_status: 200,
            ..TransferResult::default()
        });
        Ok(Submit::Submitted((id, Arc::clone(page))))
    }
    fn cancel(&mut self, _: &Self::Handle) {
        panic!("all pages should complete normally");
    }
    fn release(&mut self, handle: Self::Handle) {
        self.events
            .send(Event::Release(handle.0, handle.1))
            .unwrap();
    }
    fn backoff(&mut self, _: u64, _: crate::s3::botocore_retry::ErrorKind) -> Result<(), Canceled> {
        Ok(())
    }
}
#[test]
fn delayed_shutdown_is_awaited_before_reuse_and_return() {
    let (send, receive) = mpsc::channel();
    let (done_send, done_receive) = mpsc::channel();
    let worker = std::thread::spawn(move || {
        let mut ops = DelayedOps {
            next: 0,
            events: send,
        };
        let mut stats = ListStats::default();
        let result = driver::run(
            Options::new(b"", objects(), true),
            &mut ops,
            Some(&mut stats),
            &mut |_| 0,
        );
        done_send.send((result, stats)).unwrap();
    });
    let timeout = Duration::from_secs(10);
    submitted(&receive, 0);
    let first = released(&receive, 0);
    submitted(&receive, 1);
    let second = released(&receive, 1);
    assert!(matches!(receive.try_recv(), Err(mpsc::TryRecvError::Empty)));
    first.shutdown();
    submitted(&receive, 2);
    let third = released(&receive, 2);
    assert!(matches!(
        done_receive.try_recv(),
        Err(mpsc::TryRecvError::Empty)
    ));
    second.shutdown();
    third.shutdown();
    let (result, stats) = done_receive.recv_timeout(timeout).unwrap();
    worker.join().unwrap();
    assert_eq!(result.transfer.error_code, 0);
    assert_eq!(stats.pages, 3);
    assert_eq!(stats.shutdown_wait.count, 3);
}

fn submitted(receive: &mpsc::Receiver<Event>, expected: usize) {
    let event = receive.recv_timeout(Duration::from_secs(10)).unwrap();
    assert!(matches!(event, Event::Submit(id) if id == expected));
}
fn released(receive: &mpsc::Receiver<Event>, expected: usize) -> Arc<Page> {
    match receive.recv_timeout(Duration::from_secs(10)).unwrap() {
        Event::Release(id, page) if id == expected => page,
        _ => panic!("expected page release"),
    }
}

#[test]
fn serial_object_pages_submit_after_emission() {
    let mut ops = fake(vec![Reply::ok(FIRST), Reply::ok(FINAL)]);
    let events = Arc::clone(&ops.events);
    let result = driver::run(
        Options::new(b"", objects(), false),
        &mut ops,
        None,
        &mut |_| {
            lock(&events).push("emit".into());
            0
        },
    );
    assert_eq!(result.transfer.error_code, 0);
    let events = lock(&events);
    assert!(
        events.iter().position(|event| event == "emit").unwrap()
            < events
                .iter()
                .position(|event| event.starts_with("submit 1"))
                .unwrap()
    );
}

fn failed_submissions(outcome: Outcome) -> Vec<(crate::s3::ListResult, Vec<Vec<u8>>, usize)> {
    let _library = crate::runtime::Library::acquire();
    [
        vec![Reply::failed(outcome)],
        vec![
            Reply::ok(FIRST),
            Reply::failed(outcome),
            Reply::failed(outcome),
        ],
    ]
    .into_iter()
    .map(|replies| {
        let attempts = replies.len();
        let mut ops = fake(replies);
        let mut names = Vec::new();
        let result = driver::run(
            Options::new(b"/bucket", objects(), true),
            &mut ops,
            None,
            &mut |entry| {
                names.push(entry.name);
                0
            },
        );
        assert_eq!(ops.next, attempts);
        let events = lock(&ops.events);
        assert!(!events.iter().any(|event| event.starts_with("cancel")));
        let shutdowns = events
            .iter()
            .filter(|event| event.starts_with("shutdown"))
            .count();
        (result, names, shutdowns)
    })
    .collect()
}
#[test]
fn a_refused_submission_ends_the_run_with_its_code() {
    let runs = failed_submissions(Outcome::Refused);
    let expected: [&[&[u8]]; 2] = [&[], &[b"a"]];
    for ((result, names, shutdowns), (emitted, collected)) in
        runs.into_iter().zip(expected.into_iter().zip([0, 1]))
    {
        assert_eq!(result.local_error, None);
        assert_eq!(result.transfer.error_code, UNKNOWN_ERROR_CODE);
        assert_eq!(result.transfer.crt_name.as_bytes(), b"AWS_ERROR_UNKNOWN");
        assert_eq!(result.transfer.response_status, 0);
        assert!(result.request_path.is_empty());
        assert_eq!(names, emitted);
        assert_eq!(shutdowns, collected);
    }
}
#[test]
fn a_message_failure_is_a_local_error_with_its_request_path() {
    let runs = failed_submissions(Outcome::Unbuilt);
    let expected: [&[&[u8]]; 2] = [&[], &[b"a"]];
    for ((result, names, shutdowns), (emitted, collected)) in
        runs.into_iter().zip(expected.into_iter().zip([0, 1]))
    {
        assert_eq!(result.local_error, Some(ListLocalError::CrtFailure));
        assert_eq!(result.transfer.error_code, INVALID_ARGUMENT_ERROR_CODE);
        assert!(result.request_path.starts_with(b"/bucket?list-type=2"));
        assert_eq!(names, emitted);
        assert_eq!(shutdowns, collected);
    }
}

#[test]
fn a_page_with_no_body_chunk_records_a_zero_transfer_phase() {
    let _library = crate::runtime::Library::acquire();
    let mut ops = fake(vec![Reply::ok(b"")]);
    let mut stats = ListStats::default();
    let result = driver::run(
        Options::new(b"", objects(), true),
        &mut ops,
        Some(&mut stats),
        &mut |_| 0,
    );
    assert_eq!(result.transfer.error_code, 0);
    assert_eq!(stats.pages, 1);
    assert_eq!(stats.chunks, 0);
    assert_eq!(stats.transfer.count, 1);
    assert_eq!(stats.transfer.ns_max, 0);
}

#[test]
fn parse_failure_cancels_prefetch_and_collects_current_page_stats() {
    let _library = crate::runtime::Library::acquire();
    let mut ops = fake(vec![
        Reply::ok(b"<Wrong><NextContinuationToken>next</NextContinuationToken></Wrong>"),
        Reply::ok(FINAL),
    ]);
    let mut stats = ListStats::default();
    let result = driver::run(
        Options::new(b"", objects(), true),
        &mut ops,
        Some(&mut stats),
        &mut |_| 0,
    );
    assert_ne!(result.transfer.error_code, 0);
    assert_eq!(
        result.local_error,
        Some(crate::s3::ListLocalError::UnexpectedRoot)
    );
    assert_eq!(stats.pages, 1);
    let events = lock(&ops.events);
    assert!(!events.iter().any(|event| event.starts_with("backoff")));
    assert!(events.iter().any(|event| event == "cancel 1"));
    assert_eq!(
        events
            .iter()
            .filter(|event| event.starts_with("shutdown"))
            .count(),
        2
    );
}

#[test]
fn exact_page_budget_accepts_final_page_and_oversized_prefetch_drains() {
    let _library = crate::runtime::Library::acquire();
    let mut ops = fake(vec![Reply::ok(FIRST), Reply::ok(FINAL)]);
    let mut options = Options::new(b"", objects(), true);
    options.page_count_max = 2;
    assert_eq!(
        driver::run(options, &mut ops, None, &mut |_| 0)
            .transfer
            .error_code,
        0
    );
    assert_eq!(ops.next, 2);
    let mut ops = fake(vec![Reply::ok(FIRST), Reply::ok(&[b'x'; 1024])]);
    let mut options = Options::new(b"", objects(), true);
    options.page_body_bytes_max = FIRST.len();
    assert_ne!(
        driver::run(options, &mut ops, None, &mut |_| 0)
            .transfer
            .error_code,
        0
    );
    assert_eq!(ops.next, 2);
    assert_eq!(
        lock(&ops.events)
            .iter()
            .filter(|event| event.starts_with("shutdown"))
            .count(),
        2
    );
}
