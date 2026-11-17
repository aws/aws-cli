pub const HISTOGRAM_BUCKETS: usize = 16;

/// Running aggregate for one timing phase.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ListPhaseStats {
    /// Samples folded in.
    pub count: u64,
    /// Sum of every sample.
    pub sum_ns: u64,
    /// Smallest sample; meaningless while `count` is zero.
    pub ns_min: u64,
    /// Largest sample.
    pub ns_max: u64,
    /// Power-of-two millisecond histogram; see [`HISTOGRAM_BUCKETS`].
    pub histogram: [u64; HISTOGRAM_BUCKETS],
}
/// Per-run instrumentation.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ListStats {
    /// Pages folded in.
    pub pages: u64,
    /// Entries delivered to the sink.
    pub entries: u64,
    /// Run start to the end of the epilogue.
    pub total_ns: u64,
    /// Submit to first body chunk.
    pub ttfb: ListPhaseStats,
    /// First body chunk to finish.
    pub transfer: ListPhaseStats,
    /// Finish to meta-request shutdown.
    pub shutdown_wait: ListPhaseStats,
    /// Full XML parse including entry emission.
    pub parse_emit: ListPhaseStats,
    /// Cumulative sink time per page.
    pub on_entry: ListPhaseStats,
    /// Parse done to next page submit.
    pub gap: ListPhaseStats,
    /// Submit to probe resolution.
    pub token_latency: ListPhaseStats,
    /// Body bytes over every page.
    pub body_bytes: u64,
    /// Body chunks over every page.
    pub chunks: u64,
    /// First-chunk bytes over every page.
    pub first_chunk_bytes: u64,
    /// Pages where the probe extracted a token.
    pub token_pages: u64,
    /// Pages where the probe saw IsTruncated=false.
    pub final_pages: u64,
    /// Pages resolved within the first body chunk.
    pub resolved_chunk1: u64,
    /// Sum of open-tag byte offsets on token pages.
    pub token_offset_sum: u64,
    /// Pages the probe could not resolve by body end.
    pub token_unresolved: u64,
    /// Pages where the probe disagreed with the full parse.
    pub token_mismatch: u64,
    /// Cost of the probe scan itself.
    pub probe_ns: u64,
}

impl ListPhaseStats {
    /// Folds one sample in.
    pub fn add(&mut self, ns: u64) {
        self.count += 1;
        self.sum_ns += ns;
        self.ns_min = if self.count == 1 {
            ns
        } else {
            self.ns_min.min(ns)
        };
        self.ns_max = self.ns_max.max(ns);
        self.histogram[bucket_of(ns)] += 1;
    }
}
fn bucket_of(ns: u64) -> usize {
    let ms = ns / 1_000_000;
    ((u64::BITS - ms.leading_zeros()) as usize).min(HISTOGRAM_BUCKETS - 1)
}
