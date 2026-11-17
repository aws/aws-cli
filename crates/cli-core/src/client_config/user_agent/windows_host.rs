#[cfg(windows)]
pub(super) fn host() -> super::Host {
    #[repr(C)]
    struct Version {
        size: u32,
        major: u32,
        minor: u32,
        build: u32,
        platform: u32,
        service_pack: [u16; 128],
        service_pack_major: u16,
        service_pack_minor: u16,
        suite_mask: u16,
        product_type: u8,
        reserved: u8,
    }
    #[link(name = "ntdll")]
    unsafe extern "system" {
        fn RtlGetVersion(version: *mut Version) -> i32;
    }
    const VER_NT_WORKSTATION: u8 = 1;
    let mut version = Version {
        size: std::mem::size_of::<Version>() as u32,
        major: 0,
        minor: 0,
        build: 0,
        platform: 0,
        service_pack: [0; 128],
        service_pack_major: 0,
        service_pack_minor: 0,
        suite_mask: 0,
        product_type: 0,
        reserved: 0,
    };
    // SAFETY: the structure has `OSVERSIONINFOEXW`'s documented ABI and
    // length and remains writable for the call.
    let status = unsafe { RtlGetVersion(&mut version) };
    super::Host {
        system: "Windows".into(),
        release: if status == 0 {
            let client = version.product_type == VER_NT_WORKSTATION;
            release_name(version.major, version.minor, version.build, client).into()
        } else {
            String::new()
        },
        machine: match std::env::consts::ARCH {
            "x86_64" => "AMD64",
            "aarch64" => "ARM64",
            arch => arch,
        }
        .into(),
    }
}
/// The release `platform.release()` names: CPython's `_WIN32_CLIENT_RELEASES`
/// for a client, else its `_WIN32_SERVER_RELEASES`, so Windows Server 2025
/// is "2025Server" rather than "11".
fn release_name(major: u32, minor: u32, build: u32, client: bool) -> &'static str {
    const CLIENT: &[((u32, u32, u32), &str)] = &[
        ((10, 1, 0), "post11"),
        ((10, 0, 22000), "11"),
        ((6, 4, 0), "10"),
        ((6, 3, 0), "8.1"),
        ((6, 2, 0), "8"),
        ((6, 1, 0), "7"),
    ];
    const SERVER: &[((u32, u32, u32), &str)] = &[
        ((10, 1, 0), "post2025Server"),
        ((10, 0, 26100), "2025Server"),
        ((10, 0, 20348), "2022Server"),
        ((10, 0, 17763), "2019Server"),
        ((6, 4, 0), "2016Server"),
        ((6, 3, 0), "2012ServerR2"),
        ((6, 2, 0), "2012Server"),
        ((6, 1, 0), "2008ServerR2"),
        ((6, 0, 0), "2008Server"),
        ((5, 2, 0), "2003Server"),
        ((5, 0, 0), "2000Server"),
    ];
    let releases = if client { CLIENT } else { SERVER };
    releases
        .iter()
        .find(|(version, _)| (major, minor, build) >= *version)
        .map_or("", |(_, name)| name)
}
#[cfg(test)]
mod tests;
