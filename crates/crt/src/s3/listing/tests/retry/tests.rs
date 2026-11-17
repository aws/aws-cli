use super::*;
use crate::s3::botocore_retry::{ErrorKind, Quota};
use crate::s3::{INVALID_RESPONSE_STATUS_ERROR_CODE, ListLocalError, ListResult};
use driver::run_with_quota;
use std::sync::LazyLock;

#[derive(Clone, Copy)]
struct Response {
    body: &'static [u8],
    error_code: i32,
    status: i32,
    error_body: &'static [u8],
}
const fn page(body: &'static [u8]) -> Response {
    Response {
        body,
        error_code: 0,
        status: 200,
        error_body: b"",
    }
}
const fn failure(status: i32) -> Response {
    Response {
        body: b"",
        error_code: 1,
        status,
        error_body: b"",
    }
}
const fn error_document(status: i32, error_body: &'static [u8]) -> Response {
    Response {
        error_body,
        ..failure(status)
    }
}
const fn throttled(error_body: &'static [u8]) -> Response {
    Response {
        body: b"",
        error_code: INVALID_RESPONSE_STATUS_ERROR_CODE,
        status: 429,
        error_body,
    }
}
#[derive(Default)]
struct Recorder {
    responses: Vec<Response>,
    refused: Vec<usize>,
    redirect_enabled: bool,
    interrupted: bool,
    paths: Vec<Vec<u8>>,
    redirects: usize,
    backoffs: Vec<u64>,
    kinds: Vec<ErrorKind>,
    canceled: usize,
    released: usize,
}
impl PageOps for Recorder {
    type Handle = Arc<Page>;
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        let index = self.paths.len();
        self.paths.push(path.to_vec());
        if self.refused.contains(&index) {
            return Ok(Submit::Failed(crate::s3::UNKNOWN_ERROR_CODE));
        }
        let response = self.responses.get(index).copied().unwrap_or(page_end());
        let (head, tail) = response.body.split_at(response.body.len() / 2);
        for chunk in [head, tail] {
            assert_eq!(page.append_chunk(chunk), Ok(()));
        }
        if response.error_body.is_empty() {
            page.finish(TransferResult {
                error_code: response.error_code,
                response_status: response.status,
                ..TransferResult::default()
            });
        } else {
            page.finish_response(
                response.error_code,
                response.status,
                response.error_body,
                b"ListObjectsV2",
            );
        }
        Ok(Submit::Submitted(Arc::clone(page)))
    }
    fn recover_region(&mut self, _: &ListResult) -> bool {
        self.redirects += 1;
        self.redirect_enabled
    }
    fn cancel(&mut self, _: &Self::Handle) {
        self.canceled += 1;
    }
    fn release(&mut self, page: Self::Handle) {
        self.released += 1;
        page.shutdown();
    }
    fn backoff(&mut self, attempt: u64, kind: ErrorKind) -> Result<(), Canceled> {
        self.backoffs.push(attempt);
        self.kinds.push(kind);
        if self.interrupted {
            Err(Canceled)
        } else {
            Ok(())
        }
    }
}
const fn page_end() -> Response {
    failure(599)
}
const FIRST: &[u8] = b"<ListBucketResult><Contents><Key>a</Key><Size>1</Size></Contents>\
    <IsTruncated>true</IsTruncated>\
    <NextContinuationToken>token-1</NextContinuationToken></ListBucketResult>";
const SECOND: &[u8] = b"<ListBucketResult><Contents><Key>b</Key><Size>2</Size></Contents>\
    <IsTruncated>true</IsTruncated>\
    <NextContinuationToken>token-2</NextContinuationToken></ListBucketResult>";
const FINAL: &[u8] = b"<ListBucketResult><Contents><Key>c</Key><Size>3</Size></Contents>\
    <IsTruncated>false</IsTruncated></ListBucketResult>";
const TRUNCATED: &[u8] = b"<ListBucketResult><Contents><Key>b</Key>";
const REJECTED_WITH_TOKEN: &[u8] = b"<ListBucketResult><IsTruncated>true</IsTruncated>\
    <NextContinuationToken>token-1</NextContinuationToken>\
    <Contents><Key>a\x01</Key><Size>1</Size></Contents></ListBucketResult>";
fn objects() -> Query<'static> {
    Query {
        operation: Operation::ListObjectsV2,
        prefix: b"",
        delimiter: b"",
        region: b"",
        page_size: 0,
    }
}
fn options(prefetch: bool) -> Options<'static> {
    let mut options = Options::new(b"/bucket", objects(), prefetch);
    options.page_attempts = 3;
    options
}
fn page_path(token: Option<&[u8]>) -> Vec<u8> {
    objects().build_path(b"/bucket", token)
}
struct Run {
    result: ListResult,
    names: Vec<u8>,
}
fn run(options: Options<'_>, ops: &mut Recorder, quota: &mut Quota) -> Run {
    let _library = Library::acquire();
    let mut names = Vec::new();
    let result = run_with_quota(
        options,
        ops,
        None,
        &mut |entry| {
            names.extend_from_slice(&entry.name);
            names.push(b'\n');
            0
        },
        quota,
    );
    Run { result, names }
}
fn recorder(responses: &[Response]) -> Recorder {
    Recorder {
        responses: responses.to_vec(),
        ..Recorder::default()
    }
}

#[test]
fn a_page_botocores_parser_rejects_is_requested_again_from_its_token() {
    let _library = Library::acquire();
    let mut ops = recorder(&[page(FIRST), page(TRUNCATED), page(FINAL)]);
    let mut stats = ListStats::default();
    let mut names = Vec::new();
    let result = run_with_quota(
        options(true),
        &mut ops,
        Some(&mut stats),
        &mut |entry| {
            names.push(entry.name);
            0
        },
        &mut Quota::default(),
    );
    assert_eq!(result.transfer.response_status, 200);
    assert_eq!(result.transfer.retries_exhausted, None);
    assert_eq!(names, [b"a", b"c"]);
    let token_1 = page_path(Some(b"token-1"));
    assert_eq!(ops.paths, [page_path(None), token_1.clone(), token_1]);
    assert_eq!(ops.backoffs, [1]);
    assert_eq!(ops.kinds, [ErrorKind::Transient]);
    assert_eq!((ops.canceled, ops.released), (0, 3));
    assert_eq!(stats.pages, 3);
}
#[test]
fn a_rejected_page_cancels_the_prefetch_made_from_its_body() {
    let mut ops = recorder(&[page(REJECTED_WITH_TOKEN), page(SECOND), page(FINAL)]);
    let run = run(options(true), &mut ops, &mut Quota::default());
    assert_eq!(run.result.transfer.response_status, 200);
    assert_eq!(run.names, b"c\n");
    let expected = [
        page_path(None),
        page_path(Some(b"token-1")),
        page_path(None),
    ];
    assert_eq!(ops.paths, expected);
    assert_eq!((ops.canceled, ops.backoffs.len(), ops.released), (1, 1, 3));
}
#[test]
fn a_rejected_page_drops_a_probe_token_whose_prefetch_was_refused() {
    let responses = [
        page(REJECTED_WITH_TOKEN),
        page(b""),
        page(FIRST),
        page(FINAL),
    ];
    let mut ops = Recorder {
        refused: vec![1],
        ..recorder(&responses)
    };
    let run = run(options(true), &mut ops, &mut Quota::default());
    assert_eq!(run.result.transfer.response_status, 200);
    assert_eq!(run.names, b"a\nc\n");
    let token_1 = page_path(Some(b"token-1"));
    let expected = [page_path(None), token_1.clone(), page_path(None), token_1];
    assert_eq!(ops.paths, expected);
    assert_eq!((ops.canceled, ops.backoffs.len(), ops.released), (0, 1, 3));
}
#[test]
fn ctrl_c_in_a_retrys_backoff_ends_the_run_without_the_retry() {
    let mut ops = Recorder {
        interrupted: true,
        ..recorder(&[page(FIRST), page(TRUNCATED), page(FINAL)])
    };
    let run = run(options(true), &mut ops, &mut Quota::default());
    assert_eq!(run.result.local_error, Some(ListLocalError::Canceled));
    assert_eq!(run.names, b"a\n");
    assert_eq!(
        (ops.paths.len(), ops.backoffs.len(), ops.released),
        (2, 1, 2)
    );
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows every attempt of the rejected page"
)]
fn a_page_rejected_on_every_attempt_fails_the_run_as_botocores_500() {
    let responses = [
        page(FIRST),
        page(TRUNCATED),
        page(b"<html>oops"),
        page(b"\xff"),
    ];
    let mut ops = recorder(&responses);
    let run = run(options(true), &mut ops, &mut Quota::default());
    let transfer = &run.result.transfer;
    assert_eq!((transfer.error_code, transfer.response_status), (0, 500));
    assert_eq!(transfer.retries_exhausted, Some(2));
    assert_eq!(run.result.callback_error, 0);
    assert_eq!(run.result.local_error, None);
    assert_eq!(
        transfer.service_error.operation.as_bytes(),
        b"ListObjectsV2"
    );
    assert!(transfer.service_error.code.is_empty());
    assert_eq!(run.result.request_path, page_path(Some(b"token-1")));
    assert_eq!(run.names, b"a\n");
    assert_eq!(ops.paths.len(), 4);
    assert_eq!(ops.backoffs, [1, 2]);
    assert_eq!(ops.released, 4);
}
#[test]
fn the_attempts_are_the_configured_count_and_one_makes_no_retry() {
    for attempts in [1, 2, 5] {
        let query = Query {
            operation: Operation::ListBuckets,
            ..objects()
        };
        let mut options = Options::new(b"", query, false);
        options.page_attempts = attempts;
        let mut ops = recorder(&[page(b"<html>oops"); 5]);
        let run = run(options, &mut ops, &mut Quota::default());
        let transfer = &run.result.transfer;
        assert_eq!(transfer.response_status, 500);
        assert_eq!(transfer.retries_exhausted, Some(attempts - 1));
        assert_eq!(transfer.service_error.operation.as_bytes(), b"ListBuckets");
        assert_eq!(ops.paths.len() as u64, attempts);
        assert_eq!(ops.backoffs.len() as u64, attempts - 1);
    }
}
#[test]
fn a_retry_the_quota_cannot_cover_is_not_made_and_names_no_retries() {
    let mut ops = recorder(&[page(TRUNCATED); 3]);
    let mut quota = Quota { available: 20 };
    let run = run(options(true), &mut ops, &mut quota);
    assert_eq!(run.result.transfer.response_status, 500);
    assert_eq!(run.result.transfer.retries_exhausted, None);
    assert_eq!((ops.paths.len(), ops.backoffs.len()), (2, 1));
    assert_eq!(quota.available, 6);
}
#[test]
fn an_error_at_a_pages_last_attempt_names_the_retries() {
    let rejected = page(TRUNCATED);
    let denied = failure(403);
    let cases: [(&[Response], Option<u64>); 3] = [
        (&[rejected, rejected, denied], Some(2)),
        (&[rejected, denied], None),
        (&[denied], None),
    ];
    for (responses, retries) in cases {
        let mut ops = recorder(responses);
        let run = run(options(false), &mut ops, &mut Quota::default());
        assert_eq!(run.result.transfer.response_status, 403);
        assert_eq!(run.result.transfer.retries_exhausted, retries);
        assert_eq!(ops.paths.len(), responses.len());
    }
}
#[test]
fn a_page_that_parses_gives_its_retries_quota_back() {
    let responses = [page(FIRST), page(TRUNCATED), page(TRUNCATED), page(FINAL)];
    let mut ops = recorder(&responses);
    let mut quota = Quota { available: 40 };
    let run = run(options(false), &mut ops, &mut quota);
    assert_eq!(run.names, b"a\nc\n");
    assert_eq!(quota.available, 40 + 1 - 2 * 14 + 14);
}
#[test]
fn the_redirects_resend_is_one_of_the_pages_attempts() {
    for prefetch in [false, true] {
        let responses = [failure(301), page(TRUNCATED), page(TRUNCATED), page(FINAL)];
        let mut ops = Recorder {
            redirect_enabled: true,
            ..recorder(&responses)
        };
        let run = run(options(prefetch), &mut ops, &mut Quota::default());
        assert_eq!(run.result.transfer.response_status, 500);
        assert_eq!(run.result.transfer.retries_exhausted, Some(2));
        assert_eq!(run.names, b"");
        assert_eq!((ops.paths.len(), ops.redirects), (3, 1));
        assert_eq!(ops.backoffs, [2]);
    }
}
#[test]
fn a_page_is_redirected_once_and_after_its_retries_as_well() {
    let (redirect, rejected) = (failure(301), page(TRUNCATED));
    let cases: [(&[Response], i32, usize, &[u64]); 2] = [
        (
            &[rejected, rejected, redirect, rejected, page(FINAL)],
            500,
            4,
            &[1, 2],
        ),
        (&[redirect, rejected, redirect, page(FINAL)], 301, 3, &[2]),
    ];
    for (responses, status, submits, backoffs) in cases {
        let mut ops = Recorder {
            redirect_enabled: true,
            ..recorder(responses)
        };
        let run = run(options(false), &mut ops, &mut Quota::default());
        assert_eq!(run.result.transfer.response_status, status);
        assert_eq!(run.names, b"");
        assert_eq!((ops.paths.len(), ops.redirects), (submits, 1));
        assert_eq!(ops.backoffs, backoffs);
    }
}
#[test]
fn an_error_after_the_redirect_names_the_retries_the_resend_took() {
    let (redirect, rejected, denied) = (failure(301), page(TRUNCATED), failure(403));
    let cases: [(&[Response], Option<u64>); 3] = [
        (&[rejected, rejected, redirect, denied], Some(3)),
        (&[redirect, rejected, denied], Some(2)),
        (&[redirect, denied], None),
    ];
    for (responses, retries) in cases {
        let mut ops = Recorder {
            redirect_enabled: true,
            ..recorder(responses)
        };
        let run = run(options(false), &mut ops, &mut Quota::default());
        assert_eq!(run.result.transfer.response_status, 403);
        assert_eq!(run.result.transfer.retries_exhausted, retries);
        assert_eq!((ops.paths.len(), ops.redirects), (responses.len(), 1));
    }
}
#[test]
fn a_redirected_page_that_parses_gives_back_what_no_retry_took() {
    let mut ops = Recorder {
        redirect_enabled: true,
        ..recorder(&[failure(301), page(FINAL)])
    };
    let mut quota = Quota { available: 20 };
    let run = run(options(false), &mut ops, &mut quota);
    assert_eq!(run.names, b"c\n");
    assert!(ops.backoffs.is_empty());
    assert_eq!(quota.available, 20 + 1);
}
static LONG_MESSAGE: LazyLock<String> =
    LazyLock::new(|| format!("{}\u{e9} tail", "a".repeat(1023)));
static DENIED_WITH_LONG_MESSAGE: LazyLock<Vec<u8>> = LazyLock::new(|| {
    let message = LONG_MESSAGE.as_str();
    format!("<Error><Code>AccessDenied</Code><Message>{message}</Message></Error>").into_bytes()
});
static MOVED_WITH_LONG_MESSAGE: LazyLock<Vec<u8>> = LazyLock::new(|| {
    let message = LONG_MESSAGE.as_str();
    format!("<Error><Code>PermanentRedirect</Code><Message>moved {message}</Message></Error>")
        .into_bytes()
});
#[test]
fn a_failed_pages_message_reaches_the_result_whole() {
    let denied = error_document(403, &DENIED_WITH_LONG_MESSAGE);
    let responses = [
        page(REJECTED_WITH_TOKEN),
        denied,
        error_document(301, &MOVED_WITH_LONG_MESSAGE),
        denied,
    ];
    let mut ops = Recorder {
        redirect_enabled: true,
        ..recorder(&responses)
    };
    let run = run(options(true), &mut ops, &mut Quota::default());
    let transfer = &run.result.transfer;
    assert_eq!(transfer.response_status, 403);
    assert_eq!(transfer.service_error.code.as_bytes(), b"AccessDenied");
    assert_eq!(transfer.service_error.message, LONG_MESSAGE.as_bytes());
    assert_eq!((ops.paths.len(), ops.canceled, ops.redirects), (4, 1, 1));
}
#[test]
fn a_page_whose_429_the_crt_gave_up_on_is_requested_again_from_its_token() {
    let error = b"<Error><Code>TooManyRequests</Code></Error>";
    for response in [throttled(b""), throttled(error)] {
        let mut ops = recorder(&[page(FIRST), response, page(FINAL)]);
        let mut quota = Quota::default();
        let run = run(options(true), &mut ops, &mut quota);
        assert_eq!(run.result.transfer.response_status, 200);
        assert_eq!(run.names, b"a\nc\n");
        let token_1 = page_path(Some(b"token-1"));
        assert_eq!(ops.paths, [page_path(None), token_1.clone(), token_1]);
        assert_eq!(
            (ops.backoffs, ops.kinds),
            (vec![1], vec![ErrorKind::Throttling])
        );
        assert_eq!(quota.available, Quota::CAPACITY_MAX);
    }
}
#[test]
fn a_429_with_a_modeled_code_is_not_retried() {
    let mut ops = recorder(&[throttled(b"<Error><Code>NoSuchBucket</Code></Error>")]);
    let run = run(options(false), &mut ops, &mut Quota::default());
    let transfer = &run.result.transfer;
    assert_eq!(transfer.response_status, 429);
    assert_eq!(transfer.service_error.code.as_bytes(), b"NoSuchBucket");
    assert_eq!(transfer.retries_exhausted, None);
    assert_eq!((ops.paths.len(), ops.backoffs.len()), (1, 0));
}
#[test]
fn a_page_throttled_on_every_attempt_names_the_retries() {
    for (available, attempts, retries) in [(500, 3, Some(2)), (9, 2, None)] {
        let mut ops = recorder(&[throttled(b""); 3]);
        let mut quota = Quota { available };
        let run = run(options(false), &mut ops, &mut quota);
        assert_eq!(run.result.transfer.response_status, 429);
        assert_eq!(run.result.transfer.retries_exhausted, retries);
        assert_eq!(ops.paths.len(), attempts);
        assert_eq!(ops.backoffs, (1..attempts as u64).collect::<Vec<_>>());
        assert!(ops.kinds.iter().all(|kind| *kind == ErrorKind::Throttling));
    }
}
#[test]
fn a_429_after_the_redirect_is_retried_as_the_next_attempt() {
    let mut ops = Recorder {
        redirect_enabled: true,
        ..recorder(&[failure(301), throttled(b""), throttled(b""), page(FINAL)])
    };
    let run = run(options(false), &mut ops, &mut Quota::default());
    assert_eq!(run.result.transfer.response_status, 429);
    assert_eq!(run.result.transfer.retries_exhausted, Some(2));
    assert_eq!((ops.paths.len(), ops.redirects), (3, 1));
    assert_eq!(ops.backoffs, [2]);
}
