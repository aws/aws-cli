use super::*;
use awscli_argparse::chain::Level;
#[derive(Debug, Clone, Copy)]
enum GlobalSupport {
    Native,
    IgnoredS3Ls,
    IgnoredS3Subcommands,
    ErrorFormat,
    ConnectTimeout,
    PythonOnly,
}
#[derive(Debug, Clone, Copy)]
struct GlobalClass {
    name: &'static str,
    support: GlobalSupport,
}
impl GlobalClass {
    const fn new(name: &'static str, support: GlobalSupport) -> Self {
        Self { name, support }
    }
}
const GLOBAL_CLASSES: &[GlobalClass] = &[
    GlobalClass::new("debug", GlobalSupport::Native),
    GlobalClass::new("endpoint-url", GlobalSupport::Native),
    GlobalClass::new("no-verify-ssl", GlobalSupport::PythonOnly),
    GlobalClass::new("no-paginate", GlobalSupport::IgnoredS3Ls),
    GlobalClass::new("output", GlobalSupport::IgnoredS3Ls),
    // Upstream compiles the expression before it ignores it, so an invalid one
    // fails ahead of the command and of any later parse failure; native does
    // not compile JMESPath.
    GlobalClass::new("query", GlobalSupport::PythonOnly),
    GlobalClass::new("profile", GlobalSupport::Native),
    GlobalClass::new("region", GlobalSupport::Native),
    GlobalClass::new("color", GlobalSupport::IgnoredS3Subcommands),
    GlobalClass::new("no-sign-request", GlobalSupport::Native),
    GlobalClass::new("ca-bundle", GlobalSupport::Native),
    GlobalClass::new("cli-read-timeout", GlobalSupport::PythonOnly),
    GlobalClass::new("cli-connect-timeout", GlobalSupport::ConnectTimeout),
    GlobalClass::new("cli-binary-format", GlobalSupport::PythonOnly),
    GlobalClass::new("no-cli-pager", GlobalSupport::IgnoredS3Subcommands),
    GlobalClass::new("cli-auto-prompt", GlobalSupport::PythonOnly),
    GlobalClass::new("no-cli-auto-prompt", GlobalSupport::PythonOnly),
    GlobalClass::new("cli-error-format", GlobalSupport::ErrorFormat),
    GlobalClass::new("help", GlobalSupport::PythonOnly),
];
const _: () = {
    let table = awscli_argparse::tables::GLOBALS;
    let mut i = 0;
    while i < table.len() {
        if !matches!(table[i].action, awscli_argparse::Action::Version) {
            assert!(
                classify_global(table[i].name).is_some(),
                "pinned global is unclassified"
            );
        }
        i += 1;
    }
    assert!(
        table.len() == GLOBAL_CLASSES.len() + 1,
        "global classifications are stale"
    );
};
const fn classify_global(name: &str) -> Option<GlobalSupport> {
    let mut i = 0;
    while i < GLOBAL_CLASSES.len() {
        if same(GLOBAL_CLASSES[i].name, name) {
            return Some(GLOBAL_CLASSES[i].support);
        }
        i += 1;
    }
    None
}
const fn same(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut i = 0;
    while i < a.len() {
        if a.as_bytes()[i] != b.as_bytes()[i] {
            return false;
        }
        i += 1;
    }
    true
}

#[expect(
    clippy::expect_used,
    reason = "const table audit proves every global is classified"
)]
pub(super) fn route_parsed_unsupported_global(
    result: &ParseResult,
    lineage: NativeLineage,
) -> Option<PythonReason> {
    let level = &result.globals;
    level
        .table
        .iter()
        .zip(&level.seen)
        .any(|(argument, &seen)| {
            if !seen || argument.positional || argument.action == awscli_argparse::Action::Version {
                return false;
            }
            let support = classify_global(argument.name).expect("all pinned globals classified");
            !is_native_global(support, lineage, level)
        })
        .then_some(PythonReason::PythonOnlyGlobal)
}
fn is_native_global(support: GlobalSupport, lineage: NativeLineage, level: &Level) -> bool {
    match support {
        GlobalSupport::Native => true,
        GlobalSupport::IgnoredS3Ls => lineage == NativeLineage::S3Ls,
        GlobalSupport::IgnoredS3Subcommands => lineage != NativeLineage::S3,
        GlobalSupport::ErrorFormat => level
            .namespace
            .string("cli_error_format")
            .and_then(ErrorFormat::from_name)
            .is_some(),
        GlobalSupport::ConnectTimeout => {
            let timeout = bind_connect_timeout(&level.namespace);
            client_config::connect_timeout_milliseconds(timeout).is_some()
        }
        GlobalSupport::PythonOnly => false,
    }
}
