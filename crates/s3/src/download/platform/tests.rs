use super::*;
use crate::download::testing::fakes;
use std::io::{Read, Seek, SeekFrom};

#[test]
fn positional_write_preserves_file_position_and_exact_length() -> io::Result<()> {
    let mut file = fakes::file();
    let platform = NativePlatform;
    platform.set_length(&file, 8)?;
    file.seek(SeekFrom::Start(1))?;
    assert_eq!(platform.write_at(&file, b"ab", 4)?, 2);
    assert_eq!(file.metadata()?.len(), 8);
    assert_eq!(file.stream_position()?, 1);
    file.rewind()?;
    let mut contents = [0; 8];
    file.read_exact(&mut contents)?;
    assert_eq!(contents, [0, 0, 0, 0, b'a', b'b', 0, 0]);
    Ok(())
}

#[test]
fn a_close_reports_the_delayed_failure_its_errno_names() {
    assert_eq!(NativePlatform.close_file(fakes::file()), Ok(()));
    for (errno, expected) in [
        (libc::EIO, CloseError::InputOutput),
        (libc::ENOSPC, CloseError::NoSpaceLeft),
        (libc::EDQUOT, CloseError::DiskQuota),
        (libc::EINTR, CloseError::Interrupted),
        (libc::EPERM, CloseError::Unexpected),
    ] {
        assert_eq!(native::close_error(Some(errno)), expected, "{errno}");
    }
    assert_eq!(native::close_error(None), CloseError::Unexpected);
}

#[test]
fn preallocation_handles_confirmed_unsupported_and_hard_failure_outcomes() {
    use crate::download::{lock, testing::fakes::FakePlatform};
    use std::sync::atomic::Ordering;
    let file = fakes::file();
    let not_needed = FakePlatform::default();
    assert_eq!(reserve(&not_needed, &file, 0), Ok(Preallocation::NotNeeded));
    assert_eq!(not_needed.preallocations.load(Ordering::Relaxed), 0);
    let confirmed = FakePlatform::default();
    lock(&confirmed.preallocation).push_back(io::ErrorKind::Interrupted);
    assert_eq!(
        reserve(&confirmed, &file, 1024),
        Ok(Preallocation::Confirmed)
    );
    assert_eq!(confirmed.preallocations.load(Ordering::Relaxed), 2);
    let unsupported = FakePlatform::default();
    unsupported
        .unsupported_preallocation
        .store(true, Ordering::Relaxed);
    assert_eq!(
        reserve(&unsupported, &file, 1024),
        Ok(Preallocation::Unsupported)
    );
    assert_eq!(unsupported.preallocations.load(Ordering::Relaxed), 1);
    let failed = FakePlatform::default();
    lock(&failed.preallocation).push_back(io::ErrorKind::StorageFull);
    assert_eq!(
        reserve(&failed, &file, 1024).map_err(|error| crate::cp::write_error_name(&error)),
        Err("No space left on device".into())
    );
    assert_eq!(failed.preallocations.load(Ordering::Relaxed), 1);
}

#[test]
fn a_size_past_off_t_is_too_big_to_reserve_or_set() {
    use crate::download::testing::fakes::FakePlatform;
    use std::sync::atomic::Ordering;
    let platform = FakePlatform::default();
    let file = fakes::file();
    let size = i64::MAX as u64 + 1;
    assert_eq!(reserve(&platform, &file, size), Err(WriteError::FileTooBig));
    assert_eq!(
        set_length(&platform, &file, size),
        Err(WriteError::FileTooBig)
    );
    assert_eq!(platform.preallocations.load(Ordering::Relaxed), 0);
    assert_eq!(platform.set_lengths.load(Ordering::Relaxed), 0);
}

#[cfg(target_os = "linux")]
#[cfg_attr(miri, ignore = "the fcntl and statx syscalls are covered natively")]
#[test]
fn direct_mode_sets_the_status_flag_and_obtains_valid_alignment_on_linux() -> io::Result<()> {
    use std::os::fd::AsRawFd;
    let file = fakes::file();
    let flags = || {
        // SAFETY: F_GETFL reads flags from a live descriptor.
        unsafe { libc::fcntl(file.as_raw_fd(), libc::F_GETFL) }
    };
    let before = flags();
    if NativePlatform.enable_direct_io(&file).is_err() {
        return Ok(());
    }
    assert_eq!(flags(), before | libc::O_DIRECT);
    NativePlatform.enable_direct_io(&file)?;
    assert_eq!(flags(), before | libc::O_DIRECT);
    assert_eq!(
        NativePlatform.direct_io_alignment(&file)?.validate(),
        Ok(())
    );
    NativePlatform.disable_direct_io(&file)?;
    NativePlatform.disable_direct_io(&file)?;
    assert_eq!(flags(), before & !libc::O_DIRECT);
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
fn a_memory_probe_leaves_no_policy_on_the_page_it_bound() -> Result<(), numa::NumaError> {
    let Ok(topology) = numa::discover() else {
        return Ok(());
    };
    let Some(node) = topology.first_node() else {
        return Ok(());
    };
    match NativePlatform.probe_numa_memory(node.id) {
        // The host reads its topology but refuses `mbind`, as a container
        // without CAP_SYS_NICE does, or lacks it.
        Err(numa::NumaError::Io(error))
            if matches!(error.raw_os_error(), Some(libc::EPERM | libc::ENOSYS)) =>
        {
            return Ok(());
        }
        result => result?,
    }
    let address = native::bind_probe_page(node.id)?;
    assert_ne!(memory_policy(address), Some(libc::MPOL_BIND));
    Ok(())
}
#[cfg(target_os = "linux")]
fn memory_policy(address: usize) -> Option<libc::c_int> {
    const MPOL_F_ADDR: libc::c_ulong = 1 << 1;
    let mut mode: libc::c_int = 0;
    // SAFETY: mode is live writable output storage, the null nodemask asks
    // for no node bits, and MPOL_F_ADDR only looks the address up.
    let result = unsafe {
        libc::syscall(
            libc::SYS_get_mempolicy,
            &mut mode as *mut libc::c_int,
            std::ptr::null_mut::<libc::c_ulong>(),
            0 as libc::c_ulong,
            address,
            MPOL_F_ADDR,
        )
    };
    (result == 0).then_some(mode)
}

#[test]
fn a_refused_probe_mapping_is_mapping_failed() {
    let unmappable = usize::MAX & !(NativePlatform.page_size() - 1);
    assert!(matches!(
        native::probe_mapping(unmappable),
        Err(numa::NumaError::MappingFailed)
    ));
}
