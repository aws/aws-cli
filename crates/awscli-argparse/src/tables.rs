//! Complete pinned AWS CLI argument tables and command tree.
use crate::{Action, Argument, CliType, DefaultValue, Nargs};
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommandKind {
    Basic,
    Service,
    Operation,
}
#[derive(Debug, Clone, Copy)]
pub struct Command {
    pub name: &'static str,
    pub kind: CommandKind,
    pub usage: Option<&'static str>,
    pub arguments: &'static [Argument],
    pub subcommands: Option<&'static [Command]>,
}
impl Command {
    pub const fn subcommand(&self, name: &str) -> Option<&Command> {
        let Some(children) = self.subcommands else {
            return None;
        };
        let mut i = 0;
        while i < children.len() {
            if equal(children[i].name, name) {
                return Some(&children[i]);
            }
            i += 1;
        }
        None
    }
}
const fn equal(a: &str, b: &str) -> bool {
    let a = a.as_bytes();
    let b = b.as_bytes();
    if a.len() != b.len() {
        return false;
    }
    let mut i = 0;
    while i < a.len() {
        if a[i] != b[i] {
            return false;
        }
        i += 1;
    }
    true
}
#[derive(Debug, Clone, Copy)]
pub struct Tables {
    pub globals: &'static [Argument],
    pub s3: &'static Command,
}
/// Complete unmodified global option table, in cli.json insertion order and
/// before version conflict resolution.
pub const GLOBALS: &[Argument] = &[
    Argument {
        action: Action::StoreTrue,
        ..Argument::new("debug")
    },
    Argument::new("endpoint-url"),
    Argument {
        action: Action::StoreFalse,
        dest: Some("verify_ssl"),
        ..Argument::new("no-verify-ssl")
    },
    Argument {
        action: Action::StoreFalse,
        dest: Some("paginate"),
        ..Argument::new("no-paginate")
    },
    Argument {
        choices: &["json", "text", "table", "yaml", "yaml-stream", "off"],
        ..Argument::new("output")
    },
    Argument::new("query"),
    Argument::new("profile"),
    Argument::new("region"),
    Argument {
        action: Action::Version,
        ..Argument::new("version")
    },
    Argument {
        choices: &["on", "off", "auto"],
        default: DefaultValue::String("auto"),
        ..Argument::new("color")
    },
    Argument {
        action: Action::StoreFalse,
        dest: Some("sign_request"),
        ..Argument::new("no-sign-request")
    },
    Argument {
        dest: Some("ca_bundle"),
        ..Argument::new("ca-bundle")
    },
    Argument {
        dest: Some("read_timeout"),
        cli_type: Some(CliType::Integer),
        ..Argument::new("cli-read-timeout")
    },
    Argument {
        dest: Some("connect_timeout"),
        cli_type: Some(CliType::Integer),
        ..Argument::new("cli-connect-timeout")
    },
    Argument {
        choices: &["base64", "raw-in-base64-out"],
        ..Argument::new("cli-binary-format")
    },
    Argument {
        action: Action::StoreTrue,
        ..Argument::new("no-cli-pager")
    },
    Argument {
        action: Action::StoreTrue,
        ..Argument::new("cli-auto-prompt")
    },
    Argument {
        action: Action::StoreTrue,
        ..Argument::new("no-cli-auto-prompt")
    },
    Argument {
        choices: &["legacy", "json", "yaml", "text", "table", "enhanced"],
        ..Argument::new("cli-error-format")
    },
    Argument {
        action: Action::StoreTrue,
        ..Argument::new("help")
    },
];
/// FirstPassGlobalArgParser runs over the original argv before main.
pub const FIRST_PASS: &[Argument] = &[
    Argument::new("profile"),
    Argument {
        action: Action::StoreTrue,
        ..Argument::new("debug")
    },
];
/// CLIArgParser's fixed usage, independent of executable spelling.
pub const USAGE: &str = concat!(
    "aws [options] <command> <subcommand> [<subcommand> ...] [parameters]\n",
    "To see help text, you can run:\n\n",
    "  aws help\n",
    "  aws <command> help\n",
    "  aws <command> <subcommand> help\n",
);
/// The main table appends the resolving --version and the command positional.
pub const MAIN_TABLE_EXTRA_COUNT: usize = 2;

const RECURSIVE: Argument = Argument {
    action: Action::StoreTrue,
    dest: Some("dir_op"),
    ..Argument::new("recursive")
};
const HUMAN_READABLE: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("human-readable")
};
const SUMMARIZE: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("summarize")
};
const DRYRUN: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("dryrun")
};
const QUIET: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("quiet")
};
const FORCE: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("force")
};
const FOLLOW_SYMLINKS: Argument = Argument {
    action: Action::StoreTrue,
    default: DefaultValue::Boolean(true),
    ..Argument::new("follow-symlinks")
};
const NO_FOLLOW_SYMLINKS: Argument = Argument {
    action: Action::StoreFalse,
    dest: Some("follow_symlinks"),
    default: DefaultValue::Boolean(true),
    ..Argument::new("no-follow-symlinks")
};
const NO_GUESS_MIME_TYPE: Argument = Argument {
    action: Action::StoreFalse,
    dest: Some("guess_mime_type"),
    default: DefaultValue::Boolean(true),
    ..Argument::new("no-guess-mime-type")
};
const CONTENT_TYPE: Argument = Argument::new("content-type");
const EXCLUDE: Argument = Argument {
    action: Action::AppendNamed,
    nargs: Some(Nargs::Count(1)),
    dest: Some("filters"),
    ..Argument::new("exclude")
};
const INCLUDE: Argument = Argument {
    action: Action::AppendNamed,
    nargs: Some(Nargs::Count(1)),
    dest: Some("filters"),
    ..Argument::new("include")
};
const ACL: Argument = Argument {
    choices: &[
        "private",
        "public-read",
        "public-read-write",
        "authenticated-read",
        "aws-exec-read",
        "bucket-owner-read",
        "bucket-owner-full-control",
        "log-delivery-write",
    ],
    ..Argument::new("acl")
};
const GRANTS: Argument = Argument {
    nargs: Some(Nargs::OneOrMore),
    ..Argument::new("grants")
};
const SSE: Argument = Argument {
    nargs: Some(Nargs::Optional),
    constant: Some(DefaultValue::String("AES256")),
    choices: &["AES256", "aws:kms"],
    ..Argument::new("sse")
};
const SSE_C: Argument = Argument {
    nargs: Some(Nargs::Optional),
    constant: Some(DefaultValue::String("AES256")),
    choices: &["AES256"],
    ..Argument::new("sse-c")
};
const SSE_C_KEY: Argument = Argument {
    cli_type: Some(CliType::Blob),
    ..Argument::new("sse-c-key")
};
const SSE_KMS_KEY_ID: Argument = Argument::new("sse-kms-key-id");
const SSE_C_COPY_SOURCE: Argument = Argument {
    nargs: Some(Nargs::Optional),
    constant: Some(DefaultValue::String("AES256")),
    choices: &["AES256"],
    ..Argument::new("sse-c-copy-source")
};
const SSE_C_COPY_SOURCE_KEY: Argument = Argument {
    cli_type: Some(CliType::Blob),
    ..Argument::new("sse-c-copy-source-key")
};
const STORAGE_CLASS: Argument = Argument {
    choices: &[
        "STANDARD",
        "REDUCED_REDUNDANCY",
        "STANDARD_IA",
        "ONEZONE_IA",
        "INTELLIGENT_TIERING",
        "GLACIER",
        "DEEP_ARCHIVE",
        "GLACIER_IR",
    ],
    ..Argument::new("storage-class")
};
const WEBSITE_REDIRECT: Argument = Argument::new("website-redirect");
const CACHE_CONTROL: Argument = Argument::new("cache-control");
const CONTENT_DISPOSITION: Argument = Argument::new("content-disposition");
const CONTENT_ENCODING: Argument = Argument::new("content-encoding");
const CONTENT_LANGUAGE: Argument = Argument::new("content-language");
const SOURCE_REGION: Argument = Argument::new("source-region");
const EXPIRES: Argument = Argument::new("expires");
const METADATA: Argument = Argument {
    cli_type: Some(CliType::Map),
    ..Argument::new("metadata")
};
const METADATA_DIRECTIVE: Argument = Argument {
    choices: &["COPY", "REPLACE"],
    ..Argument::new("metadata-directive")
};
const COPY_PROPS: Argument = Argument {
    choices: &["none", "metadata-directive", "default", "all"],
    default: DefaultValue::String("default"),
    ..Argument::new("copy-props")
};
const INDEX_DOCUMENT: Argument = Argument::new("index-document");
const ERROR_DOCUMENT: Argument = Argument::new("error-document");
const ONLY_SHOW_ERRORS: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("only-show-errors")
};
const NO_PROGRESS: Argument = Argument {
    action: Action::StoreFalse,
    dest: Some("progress"),
    ..Argument::new("no-progress")
};
const PROGRESS_FREQUENCY: Argument = Argument {
    dest: Some("progress_frequency"),
    cli_type: Some(CliType::Integer),
    default: DefaultValue::Integer(0),
    ..Argument::new("progress-frequency")
};
const PROGRESS_MULTILINE: Argument = Argument {
    dest: Some("progress_multiline"),
    action: Action::StoreTrue,
    ..Argument::new("progress-multiline")
};
const EXPECTED_SIZE: Argument = Argument::new("expected-size");
const PAGE_SIZE: Argument = Argument {
    cli_type: Some(CliType::Integer),
    ..Argument::new("page-size")
};
const IGNORE_GLACIER_WARNINGS: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("ignore-glacier-warnings")
};
const FORCE_GLACIER_TRANSFER: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("force-glacier-transfer")
};
const REQUEST_PAYER: Argument = Argument {
    choices: &["requester"],
    nargs: Some(Nargs::Optional),
    constant: Some(DefaultValue::String("requester")),
    ..Argument::new("request-payer")
};
const VALIDATE_SAME_S3_PATHS: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("validate-same-s3-paths")
};
const CHECKSUM_MODE: Argument = Argument {
    choices: &["ENABLED"],
    ..Argument::new("checksum-mode")
};
const CHECKSUM_ALGORITHM: Argument = Argument {
    choices: &[
        "CRC64NVME",
        "CRC32",
        "SHA256",
        "SHA1",
        "CRC32C",
        "SHA512",
        "XXHASH64",
        "XXHASH3",
        "XXHASH128",
    ],
    ..Argument::new("checksum-algorithm")
};
const BUCKET_NAME_PREFIX: Argument = Argument::new("bucket-name-prefix");
const BUCKET_REGION: Argument = Argument::new("bucket-region");
const NO_OVERWRITE: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("no-overwrite")
};
const TAGS: Argument = Argument {
    action: Action::Append,
    nargs: Some(Nargs::Count(2)),
    ..Argument::new("tags")
};
const OBJECT_TAGS: Argument = TAGS;
const CASE_CONFLICT: Argument = Argument {
    choices: &["ignore", "skip", "warn", "error"],
    default: DefaultValue::String("ignore"),
    ..Argument::new("case-conflict")
};
const SIZE_ONLY: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("size-only")
};
const EXACT_TIMESTAMPS: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("exact-timestamps")
};
const DELETE: Argument = Argument {
    action: Action::StoreTrue,
    ..Argument::new("delete")
};
const TRANSFER_ARGS: &[Argument] = &[
    DRYRUN,
    QUIET,
    INCLUDE,
    EXCLUDE,
    ACL,
    FOLLOW_SYMLINKS,
    NO_FOLLOW_SYMLINKS,
    NO_GUESS_MIME_TYPE,
    SSE,
    SSE_C,
    SSE_C_KEY,
    SSE_KMS_KEY_ID,
    SSE_C_COPY_SOURCE,
    SSE_C_COPY_SOURCE_KEY,
    STORAGE_CLASS,
    OBJECT_TAGS,
    GRANTS,
    WEBSITE_REDIRECT,
    CONTENT_TYPE,
    CACHE_CONTROL,
    CONTENT_DISPOSITION,
    CONTENT_ENCODING,
    CONTENT_LANGUAGE,
    EXPIRES,
    SOURCE_REGION,
    ONLY_SHOW_ERRORS,
    NO_PROGRESS,
    PROGRESS_FREQUENCY,
    PROGRESS_MULTILINE,
    PAGE_SIZE,
    IGNORE_GLACIER_WARNINGS,
    FORCE_GLACIER_TRANSFER,
    REQUEST_PAYER,
    CHECKSUM_MODE,
    CHECKSUM_ALGORITHM,
];

const COPY_USAGE: &str = "<LocalPath> <S3Uri> or <S3Uri> <LocalPath> or <S3Uri> <S3Uri>";
const PATHS: &[Argument] = &[Argument {
    positional: true,
    nargs: Some(Nargs::Count(2)),
    ..Argument::new("paths")
}];
const fn concat_len(parts: &[&[Argument]]) -> usize {
    let mut len = 0;
    let mut p = 0;
    while p < parts.len() {
        len += parts[p].len();
        p += 1;
    }
    len
}
const fn concat<const N: usize>(parts: &[&[Argument]]) -> [Argument; N] {
    let mut joined = [Argument::new(""); N];
    let mut len = 0;
    let mut p = 0;
    while p < parts.len() {
        let mut i = 0;
        while i < parts[p].len() {
            joined[len] = parts[p][i];
            len += 1;
            i += 1;
        }
        p += 1;
    }
    assert!(len == N, "argument runs do not fill the table");
    joined
}
macro_rules! concat_arguments {
    ($($part:expr),+ $(,)?) => {{
        const PARTS: &[&[Argument]] = &[$($part),+];
        const JOINED: [Argument; concat_len(PARTS)] = concat(PARTS);
        &JOINED
    }};
}

pub const LS_ARGUMENTS: &[Argument] = &[
    Argument {
        positional: true,
        nargs: Some(Nargs::Optional),
        default: DefaultValue::String("s3://"),
        ..Argument::new("paths")
    },
    RECURSIVE,
    PAGE_SIZE,
    HUMAN_READABLE,
    SUMMARIZE,
    REQUEST_PAYER,
    BUCKET_NAME_PREFIX,
    BUCKET_REGION,
];
/// List objects or buckets.
pub const LS: Command = Command {
    name: "ls",
    kind: CommandKind::Basic,
    usage: Some("<S3Uri> or NONE"),
    arguments: LS_ARGUMENTS,
    subcommands: None,
};
pub const WEBSITE_ARGUMENTS: &[Argument] = &[
    Argument {
        positional: true,
        nargs: Some(Nargs::Count(1)),
        ..Argument::new("paths")
    },
    INDEX_DOCUMENT,
    ERROR_DOCUMENT,
];
/// Configure bucket website hosting.
pub const WEBSITE: Command = Command {
    name: "website",
    kind: CommandKind::Basic,
    usage: Some("<S3Uri>"),
    arguments: WEBSITE_ARGUMENTS,
    subcommands: None,
};
pub const CP_ARGUMENTS: &[Argument] = concat_arguments!(
    PATHS,
    TRANSFER_ARGS,
    &[
        METADATA,
        COPY_PROPS,
        METADATA_DIRECTIVE,
        EXPECTED_SIZE,
        RECURSIVE,
        CASE_CONFLICT,
        NO_OVERWRITE,
    ],
);
/// Copy files and objects.
pub const CP: Command = Command {
    name: "cp",
    kind: CommandKind::Basic,
    usage: Some(COPY_USAGE),
    arguments: CP_ARGUMENTS,
    subcommands: None,
};
pub const MV_ARGUMENTS: &[Argument] = concat_arguments!(
    PATHS,
    TRANSFER_ARGS,
    &[
        METADATA,
        COPY_PROPS,
        METADATA_DIRECTIVE,
        RECURSIVE,
        VALIDATE_SAME_S3_PATHS,
        CASE_CONFLICT,
        NO_OVERWRITE,
    ],
);
/// Move files and objects.
pub const MV: Command = Command {
    name: "mv",
    kind: CommandKind::Basic,
    usage: Some(COPY_USAGE),
    arguments: MV_ARGUMENTS,
    subcommands: None,
};
pub const RM_ARGUMENTS: &[Argument] = &[
    Argument {
        positional: true,
        nargs: Some(Nargs::Count(1)),
        ..Argument::new("paths")
    },
    DRYRUN,
    QUIET,
    RECURSIVE,
    REQUEST_PAYER,
    INCLUDE,
    EXCLUDE,
    ONLY_SHOW_ERRORS,
    PAGE_SIZE,
];
/// Remove objects.
pub const RM: Command = Command {
    name: "rm",
    kind: CommandKind::Basic,
    usage: Some("<S3Uri>"),
    arguments: RM_ARGUMENTS,
    subcommands: None,
};
pub const SYNC_ARGUMENTS: &[Argument] = concat_arguments!(
    PATHS,
    TRANSFER_ARGS,
    &[
        METADATA,
        COPY_PROPS,
        METADATA_DIRECTIVE,
        CASE_CONFLICT,
        NO_OVERWRITE,
        SIZE_ONLY,
        EXACT_TIMESTAMPS,
        DELETE,
    ],
);
/// Synchronize trees, including strategy-registered options.
pub const SYNC: Command = Command {
    name: "sync",
    kind: CommandKind::Basic,
    usage: Some(COPY_USAGE),
    arguments: SYNC_ARGUMENTS,
    subcommands: None,
};
pub const MB_ARGUMENTS: &[Argument] = &[
    Argument {
        positional: true,
        ..Argument::new("path")
    },
    TAGS,
];
/// Create a bucket.
pub const MB: Command = Command {
    name: "mb",
    kind: CommandKind::Basic,
    usage: Some("<S3Uri>"),
    arguments: MB_ARGUMENTS,
    subcommands: None,
};
pub const RB_ARGUMENTS: &[Argument] = &[
    Argument {
        positional: true,
        ..Argument::new("path")
    },
    FORCE,
];
/// Remove a bucket.
pub const RB: Command = Command {
    name: "rb",
    kind: CommandKind::Basic,
    usage: Some("<S3Uri>"),
    arguments: RB_ARGUMENTS,
    subcommands: None,
};
pub const PRESIGN_ARGUMENTS: &[Argument] = &[
    Argument {
        positional: true,
        ..Argument::new("path")
    },
    Argument {
        default: DefaultValue::Integer(3600),
        cli_type: Some(CliType::Integer),
        ..Argument::new("expires-in")
    },
];
/// Presign an object URL.
pub const PRESIGN: Command = Command {
    name: "presign",
    kind: CommandKind::Basic,
    usage: Some("<S3Uri>"),
    arguments: PRESIGN_ARGUMENTS,
    subcommands: None,
};
/// Root custom command, preserving upstream child order.
pub const S3: Command = Command {
    name: "s3",
    kind: CommandKind::Basic,
    usage: None,
    arguments: &[],
    subcommands: Some(&[LS, WEBSITE, CP, MV, RM, SYNC, MB, RB, PRESIGN]),
};
pub const TABLES_DEFAULT: Tables = Tables {
    globals: GLOBALS,
    s3: &S3,
};
const fn command_fits(command: &Command, depth: usize) {
    assert!(depth <= crate::LINEAGE_DEPTH_MAX);
    assert!(command.arguments.len() < crate::ARGUMENT_COUNT_MAX);
    let mut positional = 0;
    let mut i = 0;
    while i < command.arguments.len() {
        if command.arguments[i].positional {
            positional += 1;
        }
        i += 1;
    }
    if let Some(children) = command.subcommands {
        positional += 1;
        i = 0;
        while i < children.len() {
            command_fits(&children[i], depth + 1);
            i += 1;
        }
    }
    assert!(positional <= crate::POSITIONAL_COUNT_MAX);
}
const fn any_positional(table: &[Argument]) -> bool {
    let mut i = 0;
    while i < table.len() {
        if table[i].positional {
            return true;
        }
        i += 1;
    }
    false
}
const _: () = {
    command_fits(&S3, 1);
    assert!(GLOBALS.len() + MAIN_TABLE_EXTRA_COUNT <= crate::ARGUMENT_COUNT_MAX);
    assert!(FIRST_PASS.len() <= crate::ARGUMENT_COUNT_MAX);
    assert!(!any_positional(GLOBALS), "a global is positional");
    assert!(
        !any_positional(FIRST_PASS),
        "a first-pass option is positional"
    );
};

#[cfg(test)]
mod tests;
