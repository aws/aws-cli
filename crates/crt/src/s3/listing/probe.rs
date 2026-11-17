const OPEN: &[u8] = b"<NextContinuationToken>";
const CLOSE: &[u8] = b"</NextContinuationToken>";
const FINAL: &[u8] = b"<IsTruncated>false</IsTruncated>";
const NEEDLE_MAX: usize = FINAL.len();
const _: () = assert!(NEEDLE_MAX >= OPEN.len() && NEEDLE_MAX >= CLOSE.len());

/// Where the scan stands.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum ProbeState {
    /// Nothing decisive seen yet.
    #[default]
    Scanning,
    /// A non-empty token without entity escapes was found.
    Token,
    /// The final-page marker was found before any token tag.
    FinalPage,
    /// The body ended first, or the token needs the full parse.
    Unresolved,
}
impl ProbeState {
    /// Whether the scan found the token or the final-page marker.
    pub fn is_resolved(self) -> bool {
        matches!(self, Self::Token | Self::FinalPage)
    }
}
#[derive(Debug, Default)]
pub struct TokenProbe {
    state: ProbeState,
    open_tag_found: bool,
    scan_pos: usize,
    match_offset: usize,
    value_start: usize,
    value_len: usize,
    body_len: usize,
}
impl TokenProbe {
    /// Advances the scan over the accumulated body: the previous bytes plus
    /// the newly appended chunk. Returns the resulting state.
    pub fn scan(&mut self, body: &[u8]) -> ProbeState {
        if body.len() < self.body_len {
            self.finish();
            return self.state;
        }
        self.body_len = body.len();
        if self.state != ProbeState::Scanning {
            return self.state;
        }
        if !self.open_tag_found && !self.scan_for_open_tag(body) {
            return self.state;
        }
        self.scan_for_close_tag(body);
        self.state
    }
    fn scan_for_open_tag(&mut self, body: &[u8]) -> bool {
        let base = self.scan_pos.min(body.len());
        let open = find(&body[base..], OPEN);
        let final_page = find(&body[base..], FINAL);
        if let Some(offset) = final_page
            && open.is_none_or(|position| offset < position)
        {
            self.match_offset = base + offset;
            self.state = ProbeState::FinalPage;
            return false;
        }
        let Some(offset) = open else {
            self.scan_pos = resume_pos(body.len(), base);
            return false;
        };
        self.open_tag_found = true;
        self.match_offset = base + offset;
        self.value_start = self.match_offset + OPEN.len();
        self.scan_pos = self.value_start;
        true
    }
    fn scan_for_close_tag(&mut self, body: &[u8]) {
        let base = self.scan_pos.min(body.len());
        let Some(offset) = find(&body[base..], CLOSE) else {
            self.scan_pos = resume_pos(body.len(), self.value_start);
            return;
        };
        self.value_len = base + offset - self.value_start;
        let token = &body[self.value_range()];
        let encoded = token.iter().any(|byte| matches!(byte, b'&' | b'<'));
        self.state = if token.is_empty() || encoded {
            ProbeState::Unresolved
        } else {
            ProbeState::Token
        };
    }
    /// Marks end of body: a probe still scanning becomes unresolved.
    pub fn finish(&mut self) {
        if self.state == ProbeState::Scanning {
            self.state = ProbeState::Unresolved;
        }
    }
    pub fn state(&self) -> ProbeState {
        self.state
    }
    pub fn match_offset(&self) -> usize {
        self.match_offset
    }
    pub fn value_range(&self) -> std::ops::Range<usize> {
        self.value_start..self.value_start + self.value_len
    }
    /// The token value in `body`, in the [`ProbeState::Token`] state.
    pub fn token<'b>(&self, body: &'b [u8]) -> &'b [u8] {
        debug_assert_eq!(self.state, ProbeState::Token);
        &body[self.value_range()]
    }
}
fn resume_pos(body_len: usize, floor: usize) -> usize {
    body_len.saturating_sub(NEEDLE_MAX - 1).max(floor)
}
fn find(body: &[u8], needle: &[u8]) -> Option<usize> {
    body.windows(needle.len())
        .position(|window| window == needle)
}
