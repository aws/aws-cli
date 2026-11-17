#![cfg_attr(
    unix,
    expect(
        clippy::unwrap_used,
        reason = "test assertions require successful local setup"
    )
)]
use super::*;

#[cfg(unix)]
fn sigpipe_action() -> libc::sigaction {
    // SAFETY: all-zero initialization provides valid storage for the query output.
    let mut action: libc::sigaction = unsafe { std::mem::zeroed() };
    // SAFETY: action is a writable sigaction; a null new action requests a query.
    let result = unsafe { libc::sigaction(libc::SIGPIPE, std::ptr::null(), &mut action) };
    assert_eq!(result, 0);
    action
}

#[cfg(unix)]
#[test]
fn sigpipe_handler_replaces_the_ignored_disposition() {
    let before = sigpipe_action();
    install_sigpipe_handler().unwrap();
    let installed = sigpipe_action();
    // SAFETY: before was filled by sigaction; restoring it keeps the test
    // process's disposition as the harness set it.
    unsafe {
        libc::sigaction(libc::SIGPIPE, &before, std::ptr::null_mut());
    }
    assert_eq!(installed.sa_sigaction, on_sigpipe as *const () as usize);
    assert_ne!(installed.sa_sigaction, libc::SIG_IGN);
    assert_ne!(installed.sa_sigaction, libc::SIG_DFL);
    assert_eq!(installed.sa_flags & libc::SA_RESTART, libc::SA_RESTART);
}

#[cfg(unix)]
#[test]
fn only_a_closed_descriptor_reads_as_closed() {
    let mut fds = [0; 2];
    // SAFETY: fds is writable storage for the two pipe descriptors.
    assert_eq!(unsafe { libc::pipe(fds.as_mut_ptr()) }, 0);
    let open = fds.map(descriptor_closed);
    // SAFETY: both descriptors were opened above and are closed once.
    unsafe {
        libc::close(fds[0]);
        libc::close(fds[1]);
    }
    assert_eq!(open, [false, false]);
    assert!(descriptor_closed(libc::c_int::MAX));
}

#[test]
fn stdout_started_open_without_a_record() {
    assert!(!stdout_closed_at_start());
    assert!(matches!(CommandStdout::unlocked(), CommandStdout::Open(_)));
}

#[cfg(unix)]
#[test]
fn closed_stdout_fails_every_write_with_ebadf() {
    let mut stdout = CommandStdout::Closed;
    let failures = [
        stdout.write(b"entry\n").unwrap_err(),
        stdout
            .write_vectored(&[io::IoSlice::new(b"entry\n")])
            .unwrap_err(),
        stdout.write_all(b"entry\n").unwrap_err(),
        writeln!(stdout, "entry").unwrap_err(),
    ];
    for failure in failures {
        assert_eq!(failure.raw_os_error(), Some(libc::EBADF));
    }
    stdout.write_all(b"").unwrap();
    stdout.flush().unwrap();
}

#[cfg(target_os = "linux")]
const STACK_HEADER_BYTES: u64 = 16 * 1024 * 1024;

#[cfg(target_os = "linux")]
fn header(p_type: u32, p_memsz: u64) -> ProgramHeader {
    ProgramHeader {
        p_type,
        p_flags: libc::PF_R | libc::PF_W,
        p_offset: 0,
        p_vaddr: 0,
        p_paddr: 0,
        p_filesz: 0,
        p_memsz,
        p_align: 16,
    }
}

#[cfg(target_os = "linux")]
fn stack_headers(p_memsz: u64) -> [ProgramHeader; 2] {
    [
        header(libc::PT_LOAD, 4096),
        header(libc::PT_GNU_STACK, p_memsz),
    ]
}

#[cfg(target_os = "linux")]
#[derive(Debug)]
struct FakeStackLimit {
    limit: Option<(libc::rlim_t, libc::rlim_t)>,
    set_fails: bool,
    gets: usize,
    sets: Vec<(libc::rlim_t, libc::rlim_t)>,
}

#[cfg(target_os = "linux")]
impl FakeStackLimit {
    fn new(cur: libc::rlim_t, max: libc::rlim_t) -> Self {
        Self {
            limit: Some((cur, max)),
            set_fails: false,
            gets: 0,
            sets: Vec::new(),
        }
    }
}

#[cfg(target_os = "linux")]
impl StackLimit for FakeStackLimit {
    fn get(&mut self) -> io::Result<libc::rlimit> {
        self.gets += 1;
        let (rlim_cur, rlim_max) = self
            .limit
            .ok_or_else(|| io::Error::from_raw_os_error(libc::EPERM))?;
        Ok(libc::rlimit { rlim_cur, rlim_max })
    }
    fn set(&mut self, limit: &libc::rlimit) -> io::Result<()> {
        self.sets.push((limit.rlim_cur, limit.rlim_max));
        if self.set_fails {
            return Err(io::Error::from_raw_os_error(libc::EPERM));
        }
        self.limit = Some((limit.rlim_cur, limit.rlim_max));
        Ok(())
    }
}

#[cfg(target_os = "linux")]
#[test]
fn a_zero_stack_header_leaves_the_limit_unread() {
    let mut limit = FakeStackLimit::new(128 * 1024, libc::RLIM_INFINITY);
    expand_stack_size_from(&stack_headers(0), &mut limit);
    assert_eq!((limit.gets, limit.sets), (0, Vec::new()));
}

#[cfg(target_os = "linux")]
#[test]
fn no_stack_header_leaves_the_limit_unread() {
    let mut limit = FakeStackLimit::new(128 * 1024, libc::RLIM_INFINITY);
    expand_stack_size_from(&[header(libc::PT_LOAD, STACK_HEADER_BYTES)], &mut limit);
    assert_eq!((limit.gets, limit.sets), (0, Vec::new()));
}

#[cfg(target_os = "linux")]
#[test]
fn a_large_enough_soft_limit_is_kept() {
    for cur in [STACK_HEADER_BYTES, 32 * 1024 * 1024] {
        let mut limit = FakeStackLimit::new(cur, libc::RLIM_INFINITY);
        expand_stack_size_from(&stack_headers(STACK_HEADER_BYTES), &mut limit);
        assert_eq!((limit.gets, limit.sets), (1, Vec::new()));
    }
}

#[cfg(target_os = "linux")]
#[test]
fn the_raised_soft_limit_is_clamped_to_the_hard_limit() {
    let hard = 10 * 1024 * 1024;
    let mut limit = FakeStackLimit::new(128 * 1024, hard);
    expand_stack_size_from(&stack_headers(STACK_HEADER_BYTES), &mut limit);
    assert_eq!(limit.sets, [(hard, hard)]);
}

#[cfg(target_os = "linux")]
#[test]
fn an_unlimited_hard_limit_raises_the_soft_limit_to_the_header_size() {
    let mut limit = FakeStackLimit::new(8 * 1024 * 1024, libc::RLIM_INFINITY);
    expand_stack_size_from(&stack_headers(STACK_HEADER_BYTES), &mut limit);
    assert_eq!(limit.sets, [(STACK_HEADER_BYTES, libc::RLIM_INFINITY)]);
}

#[cfg(target_os = "linux")]
#[test]
fn a_failed_setrlimit_is_ignored() {
    let mut limit = FakeStackLimit {
        set_fails: true,
        ..FakeStackLimit::new(128 * 1024, libc::RLIM_INFINITY)
    };
    expand_stack_size_from(&stack_headers(STACK_HEADER_BYTES), &mut limit);
    assert_eq!(limit.sets, [(STACK_HEADER_BYTES, libc::RLIM_INFINITY)]);
    assert_eq!(limit.limit, Some((128 * 1024, libc::RLIM_INFINITY)));
}

#[cfg(target_os = "linux")]
#[test]
fn a_failed_getrlimit_leaves_the_limit_alone() {
    let mut limit = FakeStackLimit {
        limit: None,
        ..FakeStackLimit::new(0, 0)
    };
    expand_stack_size_from(&stack_headers(STACK_HEADER_BYTES), &mut limit);
    assert_eq!((limit.gets, limit.sets), (1, Vec::new()));
}

#[cfg(target_os = "linux")]
#[test]
fn the_auxiliary_vector_names_the_executable_program_headers() {
    let headers = program_headers();
    assert!(headers.iter().any(|header| header.p_type == libc::PT_LOAD));
}
