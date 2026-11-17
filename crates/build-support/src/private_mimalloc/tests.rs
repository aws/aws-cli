use super::*;

const LOCALIZED: &str = "\
a.a[libpython3.14-materialized.o]: _mi_heap_main d 0 40
a.a[libpython3.14-materialized.o]: mi_malloc t 10 20
a.a[libpython3.14-materialized.o]: PyMem_RawMalloc T 30 10
a.a[libpython3.14-materialized.o]: malloc U
a.a[_awscrt.o]: aws_py_get_allocator T 0 8
";

#[test]
fn one_member_with_local_definitions_passes() -> io::Result<()> {
    check_private_mimalloc(LOCALIZED)?;
    check_private_mimalloc("a.a[x.o]: PyMem_Malloc T 0 8\n")
}

#[test]
fn undefined_references_outside_the_definition_are_rejected() {
    for kind in ["U", "w", "v"] {
        let listing = format!("{LOCALIZED}a.a[_awscrt.o]: mi_free {kind}\n");
        assert!(check_private_mimalloc(&listing).is_err(), "{kind}");
    }
}

#[test]
fn global_definitions_left_by_localization_are_rejected() {
    let listing = LOCALIZED.replace("mi_malloc t", "mi_malloc T");
    assert!(check_private_mimalloc(&listing).is_err());
}

#[test]
fn definitions_in_two_members_are_rejected() {
    let listing = format!("{LOCALIZED}a.a[other.o]: _mi_page_empty r 0 8\n");
    assert!(check_private_mimalloc(&listing).is_err());
}

const GROUPS: &str = "\
File: a.a(libpython3.14-materialized.o)
Format: elf64-x86-64
Groups {
  Group {
    Name: .group (42)
    Type: COMDAT (0x1)
    Signature: PyObject_Inline
    Section(s) in group [
      .text.PyObject_Inline (5)
    ]
  }
}
";

#[test]
fn groups_without_mimalloc_signatures_pass() -> io::Result<()> {
    check_private_mimalloc_groups(GROUPS)?;
    check_private_mimalloc_groups("File: a.a(x.o)\nGroups {\n}\n")
}

#[test]
fn comdat_groups_signed_by_mimalloc_symbols_are_rejected() {
    for signature in ["mi_malloc", "_mi_heap_main"] {
        let listing = GROUPS.replace("PyObject_Inline", signature);
        assert!(
            check_private_mimalloc_groups(&listing).is_err(),
            "{signature}"
        );
    }
}

#[test]
fn non_comdat_groups_signed_by_mimalloc_symbols_pass() -> io::Result<()> {
    check_private_mimalloc_groups(
        &GROUPS
            .replace("COMDAT (0x1)", "(0x0)")
            .replace("PyObject_Inline", "mi_malloc"),
    )
}

const ENTRY_POINTS: [(&str, &str); 14] = [
    ("malloc", "mimalloc_libc_malloc"),
    ("calloc", "mimalloc_libc_calloc"),
    ("realloc", "mimalloc_libc_realloc"),
    ("free", "mimalloc_libc_free"),
    ("reallocarray", "mimalloc_libc_reallocarray"),
    ("aligned_alloc", "mimalloc_libc_aligned_alloc"),
    ("posix_memalign", "mimalloc_libc_posix_memalign"),
    ("memalign", "mimalloc_libc_memalign"),
    ("valloc", "mimalloc_libc_valloc"),
    ("malloc_usable_size", "mimalloc_libc_malloc_usable_size"),
    ("__libc_malloc", "mimalloc_libc_malloc"),
    ("__libc_calloc", "mimalloc_libc_calloc"),
    ("__libc_realloc", "mimalloc_libc_realloc"),
    ("__libc_free", "mimalloc_libc_free"),
];
const REQUIRED: usize = 4;

#[test]
fn assertions_check_every_entry_point_and_guard_the_optional_ones() {
    let statements: Vec<String> = ALLOCATOR_ASSERTIONS
        .split(';')
        .map(|statement| statement.split_whitespace().collect::<Vec<_>>().join(" "))
        .filter(|statement| !statement.is_empty())
        .collect();
    assert_eq!(statements.len(), ENTRY_POINTS.len());
    for (index, ((name, target), statement)) in ENTRY_POINTS.iter().zip(&statements).enumerate() {
        let check = format!("{name} == {target}, \"{name} must resolve to mimalloc\")");
        let expected = if index < REQUIRED {
            format!("ASSERT({check}")
        } else {
            format!("ASSERT(!DEFINED({name}) || {check}")
        };
        assert_eq!(statement, &expected);
    }
}

#[test]
fn assertions_cover_every_alias_the_shim_defines() {
    let shim = include_str!("../../../crt-sys/shim/mimalloc.c");
    let mut aliases = Vec::new();
    for statement in shim.split(';') {
        let Some((declaration, target)) = statement.rsplit_once(" LIBC_ALIAS(") else {
            continue;
        };
        let Some((head, _)) = declaration.trim_end().rsplit_once('(') else {
            continue;
        };
        let name = head.rsplit(|c: char| c == '*' || c.is_whitespace()).next();
        aliases.push((name.unwrap_or_default(), target.trim_end_matches(')')));
    }
    aliases.sort_unstable();
    let mut checked = ENTRY_POINTS;
    checked.sort_unstable();
    assert_eq!(aliases, checked);
}

#[cfg(target_os = "linux")]
mod link {
    use super::*;
    use std::env;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::process::{Command, Output};

    struct Tools {
        cc: PathBuf,
        ar: PathBuf,
        ld: PathBuf,
        llvm: PathBuf,
        scratch: PathBuf,
    }

    impl Tools {
        #[allow(
            clippy::print_stderr,
            reason = "a skipped link test says what it needs"
        )]
        fn new(test: &str) -> io::Result<Option<Self>> {
            let Some(cc) = env::var_os("AWS_NATIVE_TEST_CC").map(PathBuf::from) else {
                assert!(
                    env::var_os("AWS_NATIVE_CRT_PREFIX").is_none(),
                    "the native suite must supply AWS_NATIVE_TEST_CC"
                );
                eprintln!(
                    "skipping {test}: AWS_NATIVE_TEST_CC is unset; cargo xtask test \
                     links the fixtures with the managed compiler"
                );
                return Ok(None);
            };
            let clang = env::var_os("AWS_NATIVE_TEST_CLANG")
                .map(PathBuf::from)
                .ok_or_else(|| {
                    io::Error::other("the native suite must supply AWS_NATIVE_TEST_CLANG")
                })?;
            let scratch =
                env::temp_dir().join(format!("build-support-{test}-{}", std::process::id()));
            let _ = fs::remove_dir_all(&scratch);
            fs::create_dir_all(&scratch)?;
            Ok(Some(Self {
                ar: cc.with_file_name("ar"),
                cc,
                ld: clang.with_file_name("ld.lld"),
                llvm: rust_llvm_tools()?,
                scratch,
            }))
        }

        fn compile(&self, name: &str, source: &str, flags: &[&str]) -> io::Result<PathBuf> {
            let unit = self.scratch.join(format!("{name}.c"));
            let object = self.scratch.join(format!("{name}.o"));
            fs::write(&unit, source)?;
            let mut compile = Command::new(&self.cc);
            compile
                .args(flags)
                .arg("-c")
                .arg("-o")
                .arg(&object)
                .arg(&unit);
            succeed(&mut compile)?;
            Ok(object)
        }

        fn llvm(&self, tool: &str) -> Command {
            Command::new(self.llvm.join(tool))
        }

        fn list(&self, tool: &str, args: &[&str], archive: &Path) -> io::Result<String> {
            let output = succeed(self.llvm(tool).args(args).arg(archive))?;
            Ok(String::from_utf8_lossy(&output.stdout).into_owned())
        }
    }

    impl Drop for Tools {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.scratch);
        }
    }

    fn rust_llvm_tools() -> io::Result<PathBuf> {
        let cargo = env::var_os("CARGO").ok_or_else(|| io::Error::other("CARGO is unset"))?;
        let rustc = Path::new(&cargo).with_file_name("rustc");
        let print = |what: &str| -> io::Result<String> {
            let output = succeed(Command::new(&rustc).args(["--print", what]))?;
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
        };
        let tools = Path::new(&print("sysroot")?)
            .join("lib/rustlib")
            .join(print("host-tuple")?)
            .join("bin");
        Ok(tools)
    }

    fn succeed(command: &mut Command) -> io::Result<Output> {
        let output = command.output()?;
        if !output.status.success() {
            return Err(io::Error::other(format!(
                "{command:?} failed: {}",
                String::from_utf8_lossy(&output.stderr)
            )));
        }
        Ok(output)
    }

    fn allocator_fixture(names: &[(&str, &str)], separate: &str) -> String {
        let mut source = String::from("void _start(void) {}\n");
        let mut targets = BTreeSet::new();
        for (_, target) in ENTRY_POINTS {
            if targets.insert(target) {
                source.push_str(&format!("void {target}(void) {{}}\n"));
            }
        }
        for (name, target) in names {
            if *name == separate {
                source.push_str(&format!("void {name}(void) {{}}\n"));
            } else {
                source.push_str(&format!(
                    "void {name}(void) __attribute__((alias(\"{target}\")));\n"
                ));
            }
        }
        source
    }

    fn link(tools: &Tools, names: &[(&str, &str)], separate: &str) -> io::Result<Output> {
        let fixture = format!("allocator-{}-{separate}", names.len());
        let source = allocator_fixture(names, separate);
        let object = tools.compile(&fixture, &source, &["-ffreestanding"])?;
        let script = tools.scratch.join("allocator.ld");
        fs::write(&script, ALLOCATOR_ASSERTIONS)?;
        Command::new(&tools.ld)
            .args(["-static", "--gc-sections", "-o"])
            .arg(object.with_extension("out"))
            .arg(&object)
            .arg(&script)
            .output()
    }

    #[test]
    fn mimalloc_requires_every_present_name_to_alias_its_target() -> io::Result<()> {
        let Some(tools) = Tools::new("allocator-aliases")? else {
            return Ok(());
        };
        let aliased = link(&tools, &ENTRY_POINTS, "")?;
        assert!(
            aliased.status.success(),
            "{}",
            String::from_utf8_lossy(&aliased.stderr)
        );
        let required = link(&tools, &ENTRY_POINTS[..REQUIRED], "")?;
        assert!(
            required.status.success(),
            "{}",
            String::from_utf8_lossy(&required.stderr)
        );
        for (name, _) in ENTRY_POINTS {
            let stray = link(&tools, &ENTRY_POINTS, name)?;
            let stderr = String::from_utf8_lossy(&stray.stderr);
            assert!(!stray.status.success(), "{name}");
            assert!(
                stderr.contains(&format!("error: {name} must resolve to mimalloc")),
                "{stderr}"
            );
        }
        Ok(())
    }

    #[test]
    fn mimalloc_requires_malloc_free_calloc_and_realloc() -> io::Result<()> {
        let Some(tools) = Tools::new("allocator-required")? else {
            return Ok(());
        };
        for index in 0..REQUIRED {
            let mut names = ENTRY_POINTS.to_vec();
            let (name, _) = names.remove(index);
            let missing = link(&tools, &names, "")?;
            let stderr = String::from_utf8_lossy(&missing.stderr);
            assert!(!missing.status.success(), "{name}");
            assert!(
                stderr.contains(&format!("symbol not found: {name}")),
                "{stderr}"
            );
        }
        Ok(())
    }

    const PYTHON_OBJECT: &str = r#"
int _mi_heap_main = 1;
void *mi_malloc(unsigned long size) { (void)size; return &_mi_heap_main; }
void *PyMem_RawMalloc(unsigned long size) { return mi_malloc(size); }
__asm__(".section .text.mi_group,\"axG\",@progbits,mi_group,comdat\n"
        ".globl mi_group\nmi_group: ret\n"
        ".section .text.Py_group,\"axG\",@progbits,Py_group,comdat\n"
        ".globl Py_group\nPy_group: ret\n.text\n");
"#;
    const PYTHON_MEMBER: &str = "libpython3.14-materialized";

    fn localize(tools: &Tools, members: &[PathBuf]) -> io::Result<(PathBuf, PathBuf)> {
        let input = tools.scratch.join("python-fallback.a");
        let private = tools.scratch.join("python-fallback-private.a");
        let _ = fs::remove_file(&input);
        succeed(Command::new(&tools.ar).arg("rcs").arg(&input).args(members))?;
        let mut objcopy = tools.llvm("rust-objcopy");
        objcopy
            .args(MIMALLOC_LOCALIZE_ARGUMENTS)
            .arg(&input)
            .arg(&private);
        succeed(&mut objcopy)?;
        Ok((input, private))
    }

    fn kind<'a>(listing: &'a str, name: &str) -> Option<&'a str> {
        listing.lines().find_map(|line| {
            let (_, symbol) = line.split_once("]: ")?;
            let mut fields = symbol.split_whitespace();
            (fields.next() == Some(name))
                .then(|| fields.next())
                .flatten()
        })
    }

    fn index(tools: &Tools, archive: &Path) -> io::Result<Vec<String>> {
        let map = tools.list("llvm-nm", &["--print-armap"], archive)?;
        let mut names: Vec<String> = map
            .lines()
            .skip_while(|line| *line != "Archive map")
            .skip(1)
            .take_while(|line| !line.is_empty())
            .filter_map(|line| line.split_once(" in ").map(|(name, _)| name.to_owned()))
            .collect();
        names.sort();
        Ok(names)
    }

    #[test]
    fn prefixed_definitions_become_local_and_the_archive_index_is_rebuilt() -> io::Result<()> {
        let Some(tools) = Tools::new("localize-definitions")? else {
            return Ok(());
        };
        let python = tools.compile(PYTHON_MEMBER, PYTHON_OBJECT, &[])?;
        let crt = tools.compile("_awscrt", "void aws_py_get_allocator(void) {}\n", &[])?;
        let (input, private) = localize(&tools, &[python, crt])?;
        let listing = tools.list("llvm-nm", &["-A", "-P"], &private)?;
        check_private_mimalloc(&listing)?;
        for (name, expected) in [
            ("mi_malloc", "t"),
            ("_mi_heap_main", "d"),
            ("mi_group", "t"),
            ("PyMem_RawMalloc", "T"),
            ("Py_group", "T"),
            ("aws_py_get_allocator", "T"),
        ] {
            assert_eq!(kind(&listing, name), Some(expected), "{listing}");
        }
        // lld extracts members by the index, which must drop the local names.
        assert!(index(&tools, &input)?.contains(&"mi_malloc".to_owned()));
        assert_eq!(
            index(&tools, &private)?,
            ["PyMem_RawMalloc", "Py_group", "aws_py_get_allocator"]
        );
        let members = succeed(Command::new(&tools.ar).arg("t").arg(&private))?;
        assert_eq!(
            String::from_utf8_lossy(&members.stdout),
            format!("{PYTHON_MEMBER}.o\n_awscrt.o\n")
        );
        Ok(())
    }

    fn groups(listing: &str) -> Vec<(String, bool)> {
        let mut groups = Vec::new();
        let mut comdat = false;
        for line in listing.lines().map(str::trim) {
            if let Some(kind) = line.strip_prefix("Type: ") {
                comdat = kind.starts_with("COMDAT");
            } else if let Some(signature) = line.strip_prefix("Signature: ") {
                groups.push((signature.to_owned(), comdat));
            }
        }
        groups
    }

    #[test]
    fn a_group_stops_being_comdat_only_when_its_signature_becomes_local() -> io::Result<()> {
        let Some(tools) = Tools::new("localize-groups")? else {
            return Ok(());
        };
        let python = tools.compile(PYTHON_MEMBER, PYTHON_OBJECT, &[])?;
        let (input, private) = localize(&tools, &[python])?;
        let before = tools.list("llvm-readobj", &["--section-groups"], &input)?;
        assert!(check_private_mimalloc_groups(&before).is_err());
        let after = tools.list("llvm-readobj", &["--section-groups"], &private)?;
        check_private_mimalloc_groups(&after)?;
        assert_eq!(
            groups(&after),
            [
                ("mi_group".to_owned(), false),
                ("Py_group".to_owned(), true)
            ]
        );
        Ok(())
    }

    #[test]
    fn undefined_and_common_prefixed_symbols_fail_closed() -> io::Result<()> {
        let Some(tools) = Tools::new("localize-refusals")? else {
            return Ok(());
        };
        let python = tools.compile(PYTHON_MEMBER, PYTHON_OBJECT, &[])?;
        let caller = "void mi_free(void *p);\nvoid aws_release(void *p) { mi_free(p); }\n";
        let caller = tools.compile("_awscrt", caller, &[])?;
        let common = tools.compile("stats", "int mi_stats;\n", &["-fcommon"])?;
        for (member, name) in [(caller, "mi_free"), (common, "mi_stats")] {
            let (_, private) = localize(&tools, &[python.clone(), member])?;
            let listing = tools.list("llvm-nm", &["-A", "-P"], &private)?;
            let refused = check_private_mimalloc(&listing)
                .err()
                .map(|e| e.to_string());
            let message = refused.unwrap_or_default();
            assert!(message.contains(name), "{message}");
        }
        Ok(())
    }
}
