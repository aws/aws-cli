use super::PreferredEncoding;

pub(super) fn preferred() -> PreferredEncoding {
    #[cfg(windows)]
    {
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn GetACP() -> u32;
        }
        // SAFETY: GetACP takes no pointers and returns the process ANSI code page.
        PreferredEncoding::AnsiCodePage(unsafe { GetACP() })
    }
    #[cfg(not(windows))]
    PreferredEncoding::Locale
}
