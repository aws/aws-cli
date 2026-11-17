#![expect(
    clippy::unwrap_used,
    reason = "bounded actor model setup and invariants"
)]
use super::*;
use crate::testing::Choices as Reader;
use std::{collections::BTreeMap, sync::OnceLock};
mod controls;
mod leaves;
mod model;
#[cfg(test)]
mod tests;
use controls::{Cleanup, Gate};
use leaves::{ActorPlatform, file_key, output_file};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Terminal {
    Active,
    WriteFailure,
}
#[derive(Clone, Copy, Debug)]
struct Choices {
    sizes: [usize; 3],
    terminal: Terminal,
    queue_capacity: usize,
    salt: u8,
}
impl Choices {
    fn decode(input: &mut Reader<'_>) -> Self {
        Self {
            sizes: [input.range(1, 64), input.range(1, 64), input.range(1, 64)],
            terminal: [Terminal::Active, Terminal::WriteFailure][input.range(0, 1)],
            queue_capacity: input.range(1, 3),
            salt: input.range(0, 255) as u8,
        }
    }
}

/// Runs one round whose six choices are all made before the actors start.
pub fn shared_writer_reentry(bytes: &[u8]) {
    shared_writer_reentry_from(&mut Reader::new(bytes));
}
fn shared_writer_reentry_from(input: &mut Reader<'_>) {
    let round = Round::new(Choices::decode(input));
    let _cleanup = Cleanup(Arc::clone(&round));
    round.run();
    round.verify();
}

#[derive(Debug)]
struct Entry {
    expected: Vec<u8>,
    image: Vec<u8>,
    writes: usize,
    releases: usize,
    accepted: bool,
}
#[derive(Debug)]
struct Ledger {
    files: BTreeMap<usize, usize>,
    entries: [Entry; 3],
}
#[derive(Debug)]
struct State {
    service: Arc<SharedWriterService>,
    outputs: Mutex<Option<[SharedOutput; 3]>>,
    slots: Mutex<Option<[OutputSlot; 3]>>,
}
#[derive(Debug)]
struct Round {
    choices: Choices,
    ledger: Mutex<Ledger>,
    state: OnceLock<State>,
    writing: [Gate; 3],
    allowed: [Gate; 3],
    released: [Gate; 3],
    producer_done: Gate,
}
impl Round {
    fn new(choices: Choices) -> Arc<Self> {
        let round = Arc::new(Self {
            choices,
            ledger: Mutex::new(Ledger {
                files: BTreeMap::new(),
                entries: std::array::from_fn(|index| entry(choices, index)),
            }),
            state: OnceLock::new(),
            writing: std::array::from_fn(|_| Gate::default()),
            allowed: std::array::from_fn(|_| Gate::default()),
            released: std::array::from_fn(|_| Gate::default()),
            producer_done: Gate::default(),
        });
        round.initialize();
        round
    }
    fn initialize(self: &Arc<Self>) {
        let platform = Arc::new(ActorPlatform(Arc::downgrade(self)));
        let mut service = self.service(platform);
        let slots: [OutputSlot; 3] = std::array::from_fn(|index| {
            service
                .acquire_output_slot(self.choices.sizes[index] as u64)
                .unwrap()
        });
        let outputs = std::array::from_fn(|index| {
            let file = output_file();
            lock(&self.ledger).files.insert(file_key(&file), index);
            service
                .prepare(&slots[index], file, self.choices.sizes[index] as u64)
                .unwrap()
        });
        service.spawn(3, &ThreadSpawner).unwrap();
        self.state
            .set(State {
                service: Arc::new(service),
                outputs: Mutex::new(Some(outputs)),
                slots: Mutex::new(Some(slots)),
            })
            .unwrap();
    }
    fn service(&self, platform: Arc<dyn Platform>) -> SharedWriterService {
        let queues = Queues::new(1, self.choices.queue_capacity).unwrap();
        SharedWriterService {
            shared: Arc::new(Shared {
                config: SharedConfig {
                    writer: WriterConfig {
                        mode: WriterMode::Pwrite,
                        requirement: Requirement::Required,
                        workers: Some(3),
                        prefault: PrefaultMode::Disabled,
                        numa: NumaConfig {
                            mode: NumaMode::Disabled,
                            ..NumaConfig::default()
                        },
                        ..WriterConfig::default()
                    },
                    custom_writer_required: true,
                    in_flight_max: 3,
                    queue_jobs_per_shard: self.choices.queue_capacity,
                },
                platform,
                spawner: Arc::new(ThreadSpawner),
                locality: LocalityContext::default(),
                queues,
                slots: Mutex::new(OutputSlots::default()),
                available: Condvar::new(),
                max_outputs: 3,
                max_large_outputs: 3,
                pending_jobs_hwm: AtomicUsize::new(0),
                jobs_enqueued: AtomicU64::new(0),
                jobs_written: AtomicU64::new(0),
            }),
            workers: Mutex::new(Vec::new()),
            prefault_pool: None,
        }
    }
    fn state(&self) -> &State {
        self.state.get().unwrap()
    }
    fn output(&self, index: usize) -> SharedOutput {
        lock(&self.state().outputs).as_ref().unwrap()[index].clone()
    }
}
fn entry(choices: Choices, index: usize) -> Entry {
    let length = choices.sizes[index];
    Entry {
        expected: (0..length)
            .map(|offset| choices.salt.wrapping_add((index * 64 + offset) as u8))
            .collect(),
        image: vec![0; length],
        writes: 0,
        releases: 0,
        accepted: false,
    }
}
