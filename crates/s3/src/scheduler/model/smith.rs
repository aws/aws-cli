use super::super::*;
use crate::testing::Choices;
use cli_core::interrupt;
mod runtime;
use runtime::{FakeRuntime, Output, SubmitShape};

const REQUEST_COUNT_MAX: usize = 8;
const STEP_COUNT: usize = 4 * REQUEST_COUNT_MAX;
const FAILURE_CODE: i32 = 91;
const _: () = {
    assert!(REQUEST_COUNT_MAX > 0 && REQUEST_COUNT_MAX <= u32::MAX as usize);
    assert!(STEP_COUNT >= 3 * REQUEST_COUNT_MAX);
    assert!(FAILURE_CODE != 0 && FAILURE_CODE != crt::s3::CANCELED_ERROR_CODE);
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Rejected,
    InFlight,
    Finished,
    ShutDown,
}
#[derive(Debug)]
struct RequestModel {
    phase: Phase,
    canceled: bool,
    finish_code: i32,
}
impl RequestModel {
    fn canceled_by_interrupt(&self) -> bool {
        self.canceled && self.finish_code == crt::s3::CANCELED_ERROR_CODE
    }
    fn is_finished(&self) -> bool {
        matches!(self.phase, Phase::Finished | Phase::ShutDown)
    }
}
#[derive(Clone, Copy, Debug)]
enum Op {
    Submit,
    Finish,
    Shutdown,
    Interrupt,
}
impl Op {
    const ALL: [Self; 4] = [Self::Submit, Self::Finish, Self::Shutdown, Self::Interrupt];
}
#[derive(Clone, Copy, Debug)]
enum FinishOutcome {
    Success,
    Failure,
    Canceled,
}
impl FinishOutcome {
    const ALL: [Self; 3] = [Self::Success, Self::Failure, Self::Canceled];
    fn result(self) -> TransferResult {
        let (error_code, response_status) = match self {
            Self::Success => (0, 200),
            Self::Failure => (FAILURE_CODE, 503),
            Self::Canceled => (crt::s3::CANCELED_ERROR_CODE, 0),
        };
        TransferResult {
            error_code,
            response_status,
            ..Default::default()
        }
    }
}
fn pick<T: Copy, const N: usize>(input: &mut Choices<'_>, choices: [T; N]) -> T {
    choices[input.index(N)]
}

/// Replays submission rejection, finish-before-adoption, cancellation, and callback ownership.
pub fn ownership(bytes: &[u8]) {
    replay(&mut Choices::new(bytes));
}
fn replay(input: &mut Choices<'_>) -> ExpectedCounts {
    let quiet = input.flag();
    let interrupt = Arc::new(interrupt::State::new());
    let fake = Arc::new(FakeRuntime {
        interrupt: Arc::clone(&interrupt),
        ..FakeRuntime::default()
    });
    let output = Arc::new(Output::default());
    let scheduler = Scheduler::new(
        download_request(quiet),
        "/".into(),
        fake.clone(),
        output.clone(),
    );
    let _registration = interrupt.register(scheduler.clone());
    let mut round = Round {
        scheduler,
        fake,
        output,
        interrupt: &interrupt,
        models: Vec::new(),
        input,
        quiet,
        interrupted: false,
    };
    round.run()
}
fn download_request(quiet: bool) -> TransferRequest {
    TransferRequest {
        direction: transfer::Direction::Download,
        bucket: "bucket".into(),
        prefix: Vec::new(),
        local_root: "downloads/".into(),
        runtime: Default::default(),
        quiet,
        dryrun: false,
        no_overwrite: false,
        glacier: crate::transfer::GlacierPolicy::Warn,
        content_types: None,
        refusal: None,
        page_size: 0,
        max_in_flight: REQUEST_COUNT_MAX as u32,
        collect_stats: true,
        prefetch: true,
        sizing: Default::default(),
        download: None,
        object: None,
        filter: Default::default(),
        headers: Default::default(),
        checksums: Default::default(),
        delete: Default::default(),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: Default::default(),
    }
}

struct Round<'a, 'b> {
    scheduler: Arc<Scheduler>,
    fake: Arc<FakeRuntime>,
    output: Arc<Output>,
    interrupt: &'a interrupt::State,
    models: Vec<RequestModel>,
    input: &'a mut Choices<'b>,
    quiet: bool,
    interrupted: bool,
}
impl Round<'_, '_> {
    fn run(&mut self) -> ExpectedCounts {
        for _ in 0..STEP_COUNT {
            self.step();
            self.expect_consistent();
        }
        self.settle();
        self.scheduler.drain();
        self.expect_consistent();
        let state = lock(&self.scheduler.state);
        assert_eq!(state.in_flight, 0);
        assert!(state.requests.is_empty());
        assert_eq!(state.stats.submitted, state.destroyed);
        ExpectedCounts::from_models(&self.models)
    }
    fn step(&mut self) {
        match pick(self.input, Op::ALL) {
            Op::Submit => self.submit(),
            Op::Finish => {
                let index = self.input.index(REQUEST_COUNT_MAX);
                self.finish(index);
            }
            Op::Shutdown => {
                let index = self.input.index(REQUEST_COUNT_MAX);
                self.shutdown(index);
            }
            Op::Interrupt => self.deliver_interrupt(),
        }
    }
    fn submit(&mut self) {
        let index = self.models.len();
        if index == REQUEST_COUNT_MAX {
            return;
        }
        let shape = self.submit_shape();
        *lock(&self.fake.shape) = shape;
        let dropped = self.interrupted;
        let named = self.scheduler.handle_download_entry(
            &format!("object-{index}"),
            index as u64 + 1,
            None,
        );
        *lock(&self.fake.shape) = SubmitShape::default();
        assert!(named.is_ok());
        let submitted = lock(&self.fake.observed).len();
        if dropped {
            assert_eq!(submitted, index);
            return;
        }
        assert_eq!(submitted, index + 1);
        if shape.race_interrupt {
            self.record_interrupt();
        }
        self.record_submission(shape);
    }
    fn submit_shape(&mut self) -> SubmitShape {
        let rejected = self.input.flag();
        SubmitShape {
            rejected,
            early_finish: !rejected && self.input.flag(),
            race_interrupt: !self.interrupted && self.input.flag(),
        }
    }
    fn record_submission(&mut self, shape: SubmitShape) {
        let phase = if shape.rejected {
            Phase::Rejected
        } else if shape.early_finish {
            Phase::Finished
        } else {
            Phase::InFlight
        };
        self.models.push(RequestModel {
            phase,
            canceled: phase == Phase::InFlight && self.interrupted,
            finish_code: 0,
        });
    }
    fn finish(&mut self, index: usize) {
        let Some(model) = self
            .models
            .get_mut(index)
            .filter(|model| model.phase == Phase::InFlight)
        else {
            return;
        };
        let result = pick(self.input, FinishOutcome::ALL).result();
        model.finish_code = result.error_code;
        let callback = lock(&self.fake.observed)[index].callback.clone();
        assert!(callback.is_some());
        if let Some(callback) = callback {
            callback.finish(result);
        }
        model.phase = Phase::Finished;
    }
    fn shutdown(&mut self, index: usize) {
        let Some(model) = self
            .models
            .get_mut(index)
            .filter(|model| model.phase == Phase::Finished)
        else {
            return;
        };
        let callback = lock(&self.fake.observed)[index].callback.take();
        assert!(callback.is_some());
        if let Some(callback) = callback {
            callback.shutdown();
        }
        model.phase = Phase::ShutDown;
    }
    fn deliver_interrupt(&mut self) {
        if self.interrupted {
            return;
        }
        self.interrupt.request();
        self.record_interrupt();
    }
    fn record_interrupt(&mut self) {
        self.interrupted = true;
        for model in self
            .models
            .iter_mut()
            .filter(|model| model.phase == Phase::InFlight)
        {
            model.canceled = true;
        }
    }
    fn settle(&mut self) {
        for index in 0..REQUEST_COUNT_MAX {
            self.finish(index);
        }
        for index in 0..REQUEST_COUNT_MAX {
            self.shutdown(index);
        }
    }

    fn expect_consistent(&self) {
        let counts = ExpectedCounts::from_models(&self.models);
        self.expect_scheduler_counts(&counts);
        self.expect_request_ownership();
        self.expect_output(&counts);
    }
    fn expect_scheduler_counts(&self, counts: &ExpectedCounts) {
        let state = lock(&self.scheduler.state);
        assert_eq!(state.stats.submitted, self.models.len() as u64);
        assert_eq!(
            (state.stats.succeeded, state.stats.failed, state.canceled),
            (counts.succeeded, counts.failed, counts.canceled)
        );
        assert_eq!(state.warned + state.stats.skipped, 0);
        assert_eq!(state.destroyed, counts.destroyed);
        assert_eq!(state.in_flight, counts.in_flight);
        assert!(state.fatal.is_none());
    }
    fn expect_request_ownership(&self) {
        let state = lock(&self.scheduler.state);
        let observed = lock(&self.fake.observed);
        assert_eq!(observed.len(), self.models.len());
        assert!(
            state
                .requests
                .keys()
                .all(|&id| id < self.models.len() as u64)
        );
        for (index, (model, actual)) in self.models.iter().zip(observed.iter()).enumerate() {
            assert_eq!(actual.key, format!("object-{index}").into_bytes());
            assert_eq!(
                actual.releases.load(Ordering::Relaxed),
                usize::from(model.is_finished())
            );
            assert_eq!(
                actual.cancels.load(Ordering::Relaxed),
                usize::from(model.canceled)
            );
            assert_eq!(
                state.requests.contains_key(&(index as u64)),
                model.phase == Phase::InFlight
            );
        }
    }
    fn expect_output(&self, counts: &ExpectedCounts) {
        assert_eq!(self.fake.commits.load(Ordering::Relaxed), counts.succeeded);
        assert_eq!(self.fake.discards.load(Ordering::Relaxed), counts.deleted);
        let lines = self.output.counts();
        if self.quiet {
            assert_eq!(lines, runtime::Lines::default());
        } else {
            assert_eq!(
                lines,
                runtime::Lines {
                    success: counts.succeeded,
                    failure: counts.failed,
                    canceled: counts.canceled,
                    other: 0,
                }
            );
        }
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
struct ExpectedCounts {
    succeeded: u64,
    failed: u64,
    canceled: u64,
    destroyed: u64,
    deleted: u64,
    in_flight: usize,
}
impl ExpectedCounts {
    fn from_models(models: &[RequestModel]) -> Self {
        let mut counts = Self::default();
        for model in models {
            counts.record(model);
        }
        counts
    }
    fn record(&mut self, model: &RequestModel) {
        match model.phase {
            Phase::Rejected => {
                self.failed += 1;
                self.destroyed += 1;
                self.deleted += 1;
            }
            Phase::InFlight => self.in_flight += 1,
            Phase::Finished | Phase::ShutDown => self.record_finished(model),
        }
    }
    fn record_finished(&mut self, model: &RequestModel) {
        if model.phase == Phase::ShutDown {
            self.destroyed += 1;
        } else {
            self.in_flight += 1;
        }
        if model.finish_code == 0 {
            self.succeeded += 1;
        } else if model.canceled_by_interrupt() {
            self.deleted += 1;
            self.canceled += 1;
        } else {
            self.deleted += 1;
            self.failed += 1;
        }
    }
}

#[cfg(test)]
mod tests;
