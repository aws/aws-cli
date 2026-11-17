use super::*;

/// Every diagnostic `check_text` reports for `text` at `path`.
fn diagnostics(path: &str, text: &str) -> Result<Vec<Diagnostic>, TaskError> {
    let mut report = Report::default();
    check_text(Path::new(path), text, &mut report)?;
    Ok(report.diagnostics)
}

fn diagnostic(path: &Path, line: usize, rule: Rule, detail: &str) -> Diagnostic {
    Diagnostic {
        path: path.to_path_buf(),
        line,
        rule,
        detail: detail.into(),
    }
}

fn missing_parent() -> std::io::Error {
    std::io::Error::other("fixture path has no parent")
}

#[test]
fn ignores_identifiers_in_comments_and_strings() -> Result<(), TaskError> {
    let forbidden = ["pro", "duction"].concat();
    let text = format!("// {forbidden}\nconst NAME: &str = \"{forbidden}\";\n");
    assert!(diagnostics("lib.rs", &text)?.is_empty());
    let text = format!("fn {forbidden}_download() {{}}\n");
    assert!(!diagnostics("lib.rs", &text)?.is_empty());
    Ok(())
}

#[test]
fn enforces_separate_test_files() -> Result<(), TaskError> {
    let text = "#[test] fn example() {}\n";
    assert!(!diagnostics("lib.rs", text)?.is_empty());
    assert!(diagnostics("tests.rs", text)?.is_empty());
    Ok(())
}

#[test]
fn checks_comment_width_and_fix_markers() -> Result<(), TaskError> {
    assert!(!diagnostics("lib.rs", &format!("// {}", "x".repeat(99)))?.is_empty());
    let marker = ["// FIX", "ME"].concat();
    assert!(!diagnostics("lib.rs", &marker)?.is_empty());
    Ok(())
}

#[test]
fn reports_every_violation_with_its_line_rule_and_detail() -> Result<(), TaskError> {
    let banned = ["pro", "duction"].concat();
    let long = format!("// {}", "x".repeat(98));
    let text = format!("{long}\nfn {banned}_path() {{}}\n{long}\n#[test]\nfn case() {{}}\n");
    let path = Path::new("src/sample_test.rs");
    let identifier = format!("{banned}_path");
    assert_eq!(
        diagnostics("src/sample_test.rs", &text)?,
        [
            diagnostic(path, 1, Rule::LineColumns, "columns=101 max=100"),
            diagnostic(path, 3, Rule::LineColumns, "columns=101 max=100"),
            diagnostic(path, 2, Rule::BannedIdentifier, &identifier),
            diagnostic(
                path,
                4,
                Rule::TestPlacement,
                "move unit tests into a sibling tests.rs"
            ),
            diagnostic(path, 0, Rule::TestSuffix, "name the file tests.rs"),
        ]
    );
    Ok(())
}

#[test]
fn reports_files_in_path_order_then_fails_with_the_count() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let first = directory.0.join("a.rs");
    let second = directory.0.join("b.rs");
    let long = format!("// {}\n", "x".repeat(98));
    let banned = format!("{}_path", ["pro", "duction"].concat());
    fs::write(&first, &long)?;
    fs::write(&second, format!("fn {banned}() {{}}\n{long}"))?;
    let sources = [second.clone(), first.clone()];
    let diagnostics = check_inventory(&sources, &sources)?;
    assert_eq!(
        diagnostics,
        [
            diagnostic(&first, 1, Rule::LineColumns, "columns=101 max=100"),
            diagnostic(&second, 1, Rule::BannedIdentifier, &banned),
            diagnostic(&second, 2, Rule::LineColumns, "columns=101 max=100"),
        ]
    );
    let mut output = Vec::new();
    let error = report(&directory.0, &diagnostics, &mut output)
        .err()
        .ok_or_else(|| std::io::Error::other("diagnostics must fail the check"))?;
    assert_eq!(error.to_string(), "3 source check violations");
    assert_eq!(
        String::from_utf8_lossy(&output),
        format!(
            "a.rs:1: line_columns columns=101 max=100\n\
             b.rs:1: banned_identifier {banned}\n\
             b.rs:2: line_columns columns=101 max=100\n"
        )
    );
    assert!(report(&directory.0, &[], &mut Vec::new()).is_ok());
    Ok(())
}

#[test]
fn line_columns_count_unicode_code_points_including_comments() -> Result<(), TaskError> {
    let text = format!(
        "//{}\n//{}\n",
        "\u{e9}".repeat(LINE_COLUMNS_MAX - 2),
        "\u{e9}".repeat(LINE_COLUMNS_MAX - 1)
    );
    assert_eq!(
        diagnostics("src/columns.rs", &text)?,
        [diagnostic(
            Path::new("src/columns.rs"),
            2,
            Rule::LineColumns,
            "columns=101 max=100"
        )]
    );
    Ok(())
}

#[test]
fn adding_and_removing_a_module_declaration_changes_orphan_reachability() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("lib.rs");
    let orphan = directory.0.join("orphan.rs");
    fs::write(&root, "")?;
    fs::write(&orphan, "")?;
    let sources = [root.clone(), orphan.clone()];
    let roots = [root.clone()];
    let unreachable = [diagnostic(
        &orphan,
        0,
        Rule::UnreachableSource,
        "no build root reaches it",
    )];
    assert_eq!(check_inventory(&sources, &roots)?, unreachable);
    fs::write(&root, "mod orphan;\n")?;
    assert!(check_inventory(&sources, &roots)?.is_empty());
    fs::write(&root, "#[path = \"orphan.rs\"]\nmod renamed;\n")?;
    assert!(check_inventory(&sources, &roots)?.is_empty());
    fs::write(&root, "")?;
    assert_eq!(check_inventory(&sources, &roots)?, unreachable);
    Ok(())
}

#[test]
fn comments_and_module_looking_strings_do_not_create_edges() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("lib.rs");
    let orphan = directory.0.join("orphan.rs");
    fs::write(
        &root,
        "// mod orphan;\n//! mod orphan;\n/* mod orphan; */\n\
         const TEXT: &str = \"mod orphan;\";\nconst RAW: &str = r#\"mod orphan;\"#;\n",
    )?;
    fs::write(&orphan, "")?;
    let diagnostics = check_inventory(&[root.clone(), orphan.clone()], &[root])?;
    assert_eq!(
        diagnostics,
        [diagnostic(
            &orphan,
            0,
            Rule::UnreachableSource,
            "no build root reaches it"
        )]
    );
    Ok(())
}

#[test]
fn inventory_excludes_build_output_and_vendor_source_while_checking_unreachable_files()
-> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("crates/demo/src/lib.rs");
    let module = directory.0.join("crates/demo/src/target/mod.rs");
    let orphan = directory.0.join("crates/demo/src/orphan_test.rs");
    let excluded = [
        "crates/demo/vendor/external.rs",
        "crates/demo/target/debug/build/out/generated.rs",
        "fuzz/src/.git/hook.rs",
        "xtask/src/node_modules/package.rs",
    ];
    let broken = format!(
        "// {}{}",
        ["FIX", "ME"].concat(),
        "x".repeat(LINE_COLUMNS_MAX)
    );
    for path in excluded.iter().map(|path| directory.0.join(path)) {
        fs::create_dir_all(path.parent().ok_or_else(missing_parent)?)?;
        fs::write(path, &broken)?;
    }
    fs::create_dir_all(module.parent().ok_or_else(missing_parent)?)?;
    fs::write(directory.0.join("crates/demo/Cargo.toml"), "")?;
    fs::write(&root, "mod target;\n")?;
    fs::write(&module, "")?;
    fs::write(&orphan, "")?;
    let sources = inventory(&directory.0)?;
    assert_eq!(sources, [root.clone(), orphan.clone(), module]);
    assert_eq!(
        check_inventory(&sources, &[root])?,
        [
            diagnostic(&orphan, 0, Rule::TestSuffix, "name the file tests.rs"),
            diagnostic(
                &orphan,
                0,
                Rule::UnreachableSource,
                "no build root reaches it"
            ),
        ]
    );
    Ok(())
}

#[test]
fn inventory_rejects_trees_deeper_than_the_depth_bound() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let mut deepest = directory.0.join("crates");
    for _ in 0..DIRECTORY_DEPTH_MAX {
        deepest.push("d");
    }
    fs::create_dir_all(&deepest)?;
    fs::write(deepest.join("lib.rs"), "")?;
    assert_eq!(inventory(&directory.0)?, [deepest.join("lib.rs")]);
    fs::create_dir(deepest.join("d"))?;
    let error = inventory(&directory.0)
        .err()
        .ok_or_else(|| std::io::Error::other("an over-deep tree must fail"))?;
    assert!(
        error
            .to_string()
            .ends_with("exceeds DIRECTORY_DEPTH_MAX=32")
    );
    Ok(())
}

#[test]
fn oversized_sources_fail_with_the_byte_bound() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let path = directory.0.join("lib.rs");
    fs::write(&path, "\n".repeat(SOURCE_BYTES_MAX))?;
    let sources = [path.clone()];
    assert!(check_inventory(&sources, &sources)?.is_empty());
    fs::write(&path, "\n".repeat(SOURCE_BYTES_MAX + 1))?;
    let error = check_inventory(&sources, &sources)
        .err()
        .ok_or_else(|| std::io::Error::other("an oversized source must fail"))?;
    assert_eq!(
        error.to_string(),
        format!("lint: {} exceeds SOURCE_BYTES_MAX=262144", path.display())
    );
    Ok(())
}

#[test]
fn file_and_diagnostic_counts_fail_with_their_named_bounds() -> Result<(), TaskError> {
    let sources = vec![PathBuf::from("lib.rs"); FILE_COUNT_MAX + 1];
    let error = check_inventory(&sources, &[])
        .err()
        .ok_or_else(|| std::io::Error::other("an oversized inventory must fail"))?;
    assert_eq!(
        error.to_string(),
        "lint: source inventory exceeds FILE_COUNT_MAX=2560"
    );
    let mut report = Report::default();
    for _ in 0..DIAGNOSTIC_COUNT_MAX {
        report.add(Path::new("lib.rs"), 1, Rule::Fixme, String::new())?;
    }
    let error = report
        .add(Path::new("lib.rs"), 1, Rule::Fixme, String::new())
        .err()
        .ok_or_else(|| std::io::Error::other("an oversized report must fail"))?;
    assert_eq!(
        error.to_string(),
        "lint: source check report exceeds DIAGNOSTIC_COUNT_MAX=163840"
    );
    Ok(())
}

#[test]
fn fuzz_sources_are_inventoried_and_checked() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let library = directory.0.join("fuzz/src/lib.rs");
    let target = directory.0.join("fuzz/fuzz_targets/model.rs");
    for path in [&library, &target] {
        fs::create_dir_all(path.parent().ok_or_else(missing_parent)?)?;
        fs::write(path, "")?;
    }
    fs::write(&target, format!("// {}\n", "x".repeat(98)))?;
    fs::write(directory.0.join("fuzz/Cargo.toml"), "")?;
    fs::create_dir_all(directory.0.join("fuzz/target/debug"))?;
    fs::write(directory.0.join("fuzz/target/debug/generated.rs"), "")?;
    let sources = inventory(&directory.0)?;
    assert_eq!(sources, [target.clone(), library.clone()]);
    assert_eq!(
        check_inventory(&sources, &[library, target.clone()])?,
        [diagnostic(
            &target,
            1,
            Rule::LineColumns,
            "columns=101 max=100"
        )]
    );
    Ok(())
}

#[test]
fn skips_raw_strings_and_character_literals_without_losing_modules() {
    let source = r###"const C: u8 = b'"';
        const TEXT: &str = r#"quoted "fake" mod absent;"#;
        mod tests;
    "###;
    let result = tokens(source);
    assert!(
        result
            .windows(3)
            .any(|window| window == ["mod", "tests", ";"])
    );
    assert!(!result.contains(&"absent"));
}

#[test]
fn aliased_modules_resolve_nested_paths_from_each_source_file() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("tests/argv/main.rs");
    let sequence = directory.0.join("src/bootstrap/sequence.rs");
    let tests = directory.0.join("src/bootstrap/sequence/tests.rs");
    fs::create_dir_all(
        root.parent()
            .ok_or_else(|| std::io::Error::other("missing root parent"))?,
    )?;
    fs::create_dir_all(
        tests
            .parent()
            .ok_or_else(|| std::io::Error::other("missing test parent"))?,
    )?;
    fs::write(
        &root,
        "#[path = \"../../src/bootstrap/sequence.rs\"] mod startup;",
    )?;
    fs::write(
        &sequence,
        "#[cfg(test)]\n#[path = \"sequence/tests.rs\"] mod tests;",
    )?;
    fs::write(&tests, "")?;
    let mut reached = BTreeSet::new();
    visit_module(&root, true, 0, &mut reached, &mut Report::default())?;
    assert_eq!(
        reached,
        [root, sequence, tests]
            .iter()
            .map(fs::canonicalize)
            .collect::<Result<BTreeSet<_>, _>>()?
    );
    Ok(())
}

#[test]
fn ordinary_modules_keep_flat_and_directory_resolution() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    fs::create_dir_all(directory.0.join("nested"))?;
    fs::create_dir_all(directory.0.join("flat"))?;
    fs::write(directory.0.join("lib.rs"), "mod flat; mod nested;")?;
    fs::write(directory.0.join("flat.rs"), "mod tests;")?;
    fs::write(directory.0.join("flat/tests.rs"), "")?;
    fs::write(directory.0.join("nested/mod.rs"), "")?;
    let mut reached = BTreeSet::new();
    let mut report = Report::default();
    visit_module(
        &directory.0.join("lib.rs"),
        true,
        0,
        &mut reached,
        &mut report,
    )?;
    assert_eq!(reached.len(), 4);
    assert!(report.diagnostics.is_empty());
    Ok(())
}

#[test]
fn missing_explicit_path_does_not_fall_back_to_module_name() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("lib.rs");
    fs::write(&root, "#[path = \"absent.rs\"] mod existing;")?;
    fs::write(directory.0.join("existing.rs"), "")?;
    let mut report = Report::default();
    visit_module(&root, true, 0, &mut BTreeSet::new(), &mut report)?;
    assert_eq!(
        report.diagnostics,
        [diagnostic(&root, 0, Rule::MissingModule, "existing")]
    );
    Ok(())
}

#[test]
fn public_glob_reexports_fail_while_private_globs_and_explicit_lists_pass() -> Result<(), TaskError>
{
    let path = Path::new("src/lib.rs");
    let glob = |line| diagnostic(path, line, Rule::GlobReexport, "use explicit re-exports");
    let text =
        "pub use a::*;\npub(crate) use a::{\n    b,\n    *,\n};\npub(in crate::a) use b::*;\n";
    assert_eq!(
        diagnostics("src/lib.rs", text)?,
        [glob(1), glob(4), glob(6)]
    );
    let text = "use super::*;\n#[cfg(test)]\nuse a::{b::*, c};\npub use a::{B, C};\n";
    assert!(diagnostics("src/lib.rs", text)?.is_empty());
    let text =
        "// pub use a::*;\nconst TEXT: &str = \"pub use a::*;\";\nfn f(a: u8) -> u8 { a * a }\n";
    assert!(diagnostics("src/lib.rs", text)?.is_empty());
    Ok(())
}

#[test]
fn banned_identifiers_match_any_case() -> Result<(), TaskError> {
    let path = Path::new("src/lib.rs");
    let [title, upper] = ["Pro", "PRO"].map(|prefix| format!("{prefix}{}", "duction"));
    let text = format!("struct {title}Runtime;\nconst {upper}_MODE: bool = true;\n");
    assert_eq!(
        diagnostics("src/lib.rs", &text)?,
        [
            diagnostic(path, 1, Rule::BannedIdentifier, &format!("{title}Runtime")),
            diagnostic(path, 2, Rule::BannedIdentifier, &format!("{upper}_MODE")),
        ]
    );
    let text = format!("// {title}\nconst NAME: &str = \"{upper}\";\n");
    assert!(diagnostics("src/lib.rs", &text)?.is_empty());
    Ok(())
}

#[test]
fn c_shim_sources_get_only_the_naming_ban_and_fix_markers() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("crates/demo/src/lib.rs");
    let source = directory.0.join("crates/demo/shim/native.c");
    let header = directory.0.join("crates/demo/shim/native.h");
    let banned = format!("{}_submit", ["pro", "duction"].concat());
    let marker = ["FIX", "ME"].concat();
    fs::create_dir_all(root.parent().ok_or_else(missing_parent)?)?;
    fs::create_dir_all(source.parent().ok_or_else(missing_parent)?)?;
    fs::write(&root, "")?;
    fs::write(
        &source,
        format!(
            "// {banned}\nstatic const char *NAME = \"{banned}\";\n\
             static int {banned}(void);\n/* {} */\n",
            "x".repeat(LINE_COLUMNS_MAX)
        ),
    )?;
    fs::write(&header, format!("/* {marker} */\n#[test]\n"))?;
    let sources = inventory(&directory.0)?;
    assert_eq!(sources, [source.clone(), header.clone(), root.clone()]);
    assert_eq!(
        check_inventory(&sources, &[root])?,
        [
            diagnostic(&source, 3, Rule::BannedIdentifier, &banned),
            diagnostic(
                &header,
                1,
                Rule::Fixme,
                "TODO, or resolve it before merging"
            ),
        ]
    );
    Ok(())
}

#[test]
fn crate_roots_of_any_name_own_their_directory() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("src/bin/argparse-tool.rs");
    let child = directory.0.join("src/bin/util.rs");
    fs::create_dir_all(root.parent().ok_or_else(missing_parent)?)?;
    fs::write(&root, "mod util;\n")?;
    fs::write(&child, "")?;
    assert!(check_inventory(&[root.clone(), child], &[root])?.is_empty());
    Ok(())
}

#[test]
fn non_root_files_named_like_roots_own_a_stem_directory() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("lib.rs");
    let build = directory.0.join("build.rs");
    let sibling = directory.0.join("child.rs");
    let nested = directory.0.join("build/child.rs");
    fs::create_dir_all(nested.parent().ok_or_else(missing_parent)?)?;
    fs::write(&root, "mod build;\n")?;
    fs::write(&build, "mod child;\n")?;
    fs::write(&sibling, "")?;
    let sources = [root.clone(), build.clone(), sibling.clone()];
    assert_eq!(
        check_inventory(&sources, std::slice::from_ref(&root))?,
        [
            diagnostic(&build, 0, Rule::MissingModule, "child"),
            diagnostic(
                &sibling,
                0,
                Rule::UnreachableSource,
                "no build root reaches it"
            ),
        ]
    );
    fs::remove_file(&sibling)?;
    fs::write(&nested, "")?;
    assert!(check_inventory(&[root.clone(), build, nested], &[root])?.is_empty());
    Ok(())
}

#[test]
fn path_attribute_files_own_their_directory_like_mod_rs() -> Result<(), TaskError> {
    let directory = Directory::new()?;
    let root = directory.0.join("lib.rs");
    let alias = directory.0.join("other/alias.rs");
    let child = directory.0.join("other/child.rs");
    fs::create_dir_all(alias.parent().ok_or_else(missing_parent)?)?;
    fs::write(&root, "#[path = \"other/alias.rs\"]\nmod renamed;\n")?;
    fs::write(&alias, "mod child;\n")?;
    fs::write(&child, "")?;
    assert!(check_inventory(&[root.clone(), alias, child], &[root])?.is_empty());
    Ok(())
}

#[test]
fn config_sources_reject_loops_and_erased_errors() -> Result<(), TaskError> {
    let path = Path::new("crates/awscli-config/src/read.rs");
    let looped = |line| diagnostic(path, line, Rule::UnboundedLoop, "bounded iteration");
    let erased = |line| diagnostic(path, line, Rule::ErasedError, "a composed error type");
    let text = "fn a() { loop {} }\nfn b() { 'outer: loop { break 'outer; } }\n\
                type C = Box<dyn std::error::Error>;\nfn d(_: &dyn Error) {}\n\
                type E = Box<dyn core::error::Error + Send + Sync>;\n";
    assert_eq!(
        diagnostics("crates/awscli-config/src/read.rs", text)?,
        [looped(1), looped(2), erased(3), erased(4), erased(5)]
    );
    let text = "// loop dyn Error\nconst TEXT: &str = \"loop\";\n\
                type F = Box<dyn Fn() -> Result<(), Error>>;\nfn loop_count() {}\n";
    assert!(diagnostics("crates/awscli-config/src/read.rs", text)?.is_empty());
    let text = "fn a() { loop {} }\ntype C = Box<dyn std::error::Error>;\n";
    assert!(diagnostics("crates/s3/src/read.rs", text)?.is_empty());
    assert_eq!(
        diagnostics(
            "crates/awscli-config/src/read/tests.rs",
            "fn a() { loop {} }\n"
        )?
        .len(),
        1
    );
    Ok(())
}

/// The function-length diagnostics `check_text` reports for `text` at `path`.
fn function_lines(path: &str, text: &str) -> Result<Vec<Diagnostic>, TaskError> {
    let mut diagnostics = diagnostics(path, text)?;
    diagnostics.retain(|diagnostic| diagnostic.rule == Rule::FunctionLines);
    Ok(diagnostics)
}

#[test]
fn function_length_includes_signatures_and_permits_exactly_the_ceiling() -> Result<(), TaskError> {
    let text = format!(
        "/// Documentation is outside the span.\npub fn boundary(\n) {{\n{}}}",
        "\n".repeat(FUNCTION_LINES_MAX - 3)
    );
    assert!(function_lines("src/boundary.rs", &text)?.is_empty());
    let text = format!(
        "// Header.\n/// Documentation.\n#[must_use]\npub(crate) fn oversized(\n) {{\n{}}}",
        "    // A comment with a misleading brace: }\n".repeat(FUNCTION_LINES_MAX - 2)
    );
    let detail = format!(
        "function=oversized lines={} max={FUNCTION_LINES_MAX}",
        FUNCTION_LINES_MAX + 1
    );
    assert_eq!(
        function_lines("src/oversized.rs", &text)?,
        [diagnostic(
            Path::new("src/oversized.rs"),
            4,
            Rule::FunctionLines,
            &detail
        )]
    );
    Ok(())
}

#[test]
fn function_length_measures_methods_but_not_prototypes_or_tests() -> Result<(), TaskError> {
    let blank = "\n".repeat(FUNCTION_LINES_MAX);
    let text = format!(
        "unsafe extern \"C\" {{\n    fn prototype(\n{blank}    );\n}}\n\
         trait Bodiless {{\n    fn method(&self,\n{blank}    );\n}}\n\
         #[test]\n#[ignore = \"slow\"]\nfn case() {{\n{blank}}}\n\
         const TEXT: &str = \"{}\";\n\
         type Callback = fn(\n{blank}) -> u8;\n\
         impl Container {{\n    fn method(&self) {{\n{}    }}\n}}\n",
        "fn fake() {\n".repeat(FUNCTION_LINES_MAX),
        "\n".repeat(FUNCTION_LINES_MAX - 1)
    );
    let diagnostics = function_lines("src/nested.rs", &text)?;
    assert_eq!(diagnostics.len(), 1);
    assert!(
        diagnostics[0]
            .detail
            .starts_with("function=method lines=71 ")
    );
    let text = format!("fn helper() {{\n{}}}\n", "\n".repeat(100));
    assert_eq!(function_lines("src/helper.rs", &text)?.len(), 1);
    assert!(function_lines("src/helper/tests.rs", &text)?.is_empty());
    Ok(())
}

#[derive(Debug)]
struct Directory(PathBuf);

impl Directory {
    fn new() -> std::io::Result<Self> {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "awscli-lint-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path)?;
        Ok(Self(path))
    }
}

impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
