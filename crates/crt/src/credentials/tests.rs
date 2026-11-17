use super::*;
use std::sync::Mutex;

/// Where a test's query leaves its answer: the access key, or `None` for a
/// failure, once per answer.
fn recorder() -> (Arc<Mutex<Vec<Option<String>>>>, Query) {
    let answers = Arc::new(Mutex::new(Vec::new()));
    let sink = Arc::clone(&answers);
    let query = Query::new(move |view| {
        crate::signal::lock(&sink).push(view.map(|view| view.access_key_id.to_owned()));
    });
    (answers, query)
}

const VIEW: View<'static> = View {
    access_key_id: "AKIDDELEGATE",
    secret_access_key: "delegate-secret",
    session_token: Some("delegate-token"),
    account_id: None,
    expiration: None,
};

#[test]
fn a_query_is_answered_exactly_once() {
    let (answers, query) = recorder();
    query.complete(VIEW);
    assert_eq!(
        *crate::signal::lock(&answers),
        [Some("AKIDDELEGATE".into())]
    );
    let (answers, query) = recorder();
    query.fail();
    assert_eq!(*crate::signal::lock(&answers), [None]);
}

#[test]
fn a_dropped_query_reports_a_failure() {
    let (answers, query) = recorder();
    drop(query);
    assert_eq!(*crate::signal::lock(&answers), [None]);
}

#[test]
fn debug_output_never_shows_the_secret_or_the_token() {
    let debug = format!("{VIEW:?}");
    assert!(debug.contains("AKIDDELEGATE"));
    assert!(!debug.contains("delegate-secret") && !debug.contains("delegate-token"));
}

mod loopback;
