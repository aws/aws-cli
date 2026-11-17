use std::collections::BTreeSet;
use std::io;

/// Linker assertions that fail the static musl link unless the C allocation
/// entry points are mimalloc's. crt-sys's `shim/mimalloc.c` defines each as an
/// alias of a `mimalloc_libc_` function no other object defines, so one
/// address proves the binding even after stripping. musl's own definitions
/// would give the libc entry points another address.
pub const ALLOCATOR_ASSERTIONS: &str = "\
ASSERT(malloc == mimalloc_libc_malloc, \"malloc must resolve to mimalloc\");
ASSERT(calloc == mimalloc_libc_calloc, \"calloc must resolve to mimalloc\");
ASSERT(realloc == mimalloc_libc_realloc, \"realloc must resolve to mimalloc\");
ASSERT(free == mimalloc_libc_free, \"free must resolve to mimalloc\");
ASSERT(!DEFINED(reallocarray) || reallocarray == mimalloc_libc_reallocarray,
       \"reallocarray must resolve to mimalloc\");
ASSERT(!DEFINED(aligned_alloc) || aligned_alloc == mimalloc_libc_aligned_alloc,
       \"aligned_alloc must resolve to mimalloc\");
ASSERT(!DEFINED(posix_memalign) || posix_memalign == mimalloc_libc_posix_memalign,
       \"posix_memalign must resolve to mimalloc\");
ASSERT(!DEFINED(memalign) || memalign == mimalloc_libc_memalign,
       \"memalign must resolve to mimalloc\");
ASSERT(!DEFINED(valloc) || valloc == mimalloc_libc_valloc,
       \"valloc must resolve to mimalloc\");
ASSERT(!DEFINED(malloc_usable_size) || malloc_usable_size == mimalloc_libc_malloc_usable_size,
       \"malloc_usable_size must resolve to mimalloc\");
ASSERT(!DEFINED(__libc_malloc) || __libc_malloc == mimalloc_libc_malloc,
       \"__libc_malloc must resolve to mimalloc\");
ASSERT(!DEFINED(__libc_calloc) || __libc_calloc == mimalloc_libc_calloc,
       \"__libc_calloc must resolve to mimalloc\");
ASSERT(!DEFINED(__libc_realloc) || __libc_realloc == mimalloc_libc_realloc,
       \"__libc_realloc must resolve to mimalloc\");
ASSERT(!DEFINED(__libc_free) || __libc_free == mimalloc_libc_free,
       \"__libc_free must resolve to mimalloc\");
";

/// The `rust-objcopy` arguments, before the input and output archives, that
/// localize CPython's bundled mimalloc: every `mi_` and `_mi_` symbol.
/// python-fallback's build script passes the same arguments for the Linux
/// archive.
pub const MIMALLOC_LOCALIZE_ARGUMENTS: [&str; 3] = [
    "--wildcard",
    "--localize-symbol=mi_*",
    "--localize-symbol=_mi_*",
];

/// Check an `llvm-nm -A -P` listing of the localized CPython archive.
///
/// Localization binds references only within the object that defines them.
/// A member that still refers to a mimalloc symbol would bind to the CLI's
/// allocator at link time and free CPython-heap blocks with the wrong heap,
/// so every mimalloc symbol must be defined, local, and in one member.
///
/// # Errors
/// Reports an undefined or global mimalloc symbol, or definitions in more
/// than one archive member.
pub fn check_private_mimalloc(listing: &str) -> io::Result<()> {
    let mut members = BTreeSet::new();
    for line in listing.lines() {
        // Each line is `archive[member]: name type [value size]`.
        let Some((member, symbol)) = line.split_once("]: ") else {
            continue;
        };
        let mut fields = symbol.split_whitespace();
        let (Some(name), Some(kind)) = (fields.next(), fields.next()) else {
            continue;
        };
        if !name.starts_with("mi_") && !name.starts_with("_mi_") {
            continue;
        }
        if matches!(kind, "U" | "w" | "v") {
            return Err(io::Error::other(format!(
                "{member}] refers to {name} without defining it; it would bind to the CLI \
                 allocator"
            )));
        }
        if kind.chars().all(|letter| letter.is_ascii_uppercase()) {
            return Err(io::Error::other(format!(
                "{member}] still exports {name} after localization"
            )));
        }
        members.insert(member);
    }
    if members.len() > 1 {
        return Err(io::Error::other(format!(
            "CPython's mimalloc is defined in {} archive members; localization keeps \
             references private only within one",
            members.len()
        )));
    }
    Ok(())
}

/// Check an `llvm-readobj --section-groups` listing of the localized archive.
///
/// Linkers deduplicate COMDAT groups by signature name whatever the
/// signature symbol's binding, so a group signed by a now-local mimalloc
/// symbol could still be discarded in favor of the CLI allocator's copy.
/// The pinned `rust-objcopy` clears `GRP_COMDAT` on such groups (the tests
/// link a fixture to show it); this check refuses an archive whose objcopy
/// did not. The CPython archive is C and currently has no section groups at
/// all.
///
/// # Errors
/// Reports a COMDAT group whose signature is a mimalloc symbol.
pub fn check_private_mimalloc_groups(listing: &str) -> io::Result<()> {
    let mut comdat = false;
    for line in listing.lines().map(str::trim) {
        if line == "Group {" {
            comdat = false;
        } else if line.starts_with("Type: COMDAT") {
            comdat = true;
        } else if let Some(signature) = line.strip_prefix("Signature: ")
            && comdat
            && (signature.starts_with("mi_") || signature.starts_with("_mi_"))
        {
            return Err(io::Error::other(format!(
                "CPython's archive has a COMDAT group signed by {signature}; the link could \
                 discard its private copy in favor of the CLI allocator's"
            )));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
