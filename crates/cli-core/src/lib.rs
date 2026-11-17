//! Shared command-line settings, formatting, and injected process inputs.

pub mod aws_profile;
pub mod cli_error;
pub mod client_config;
pub mod command;
pub mod endpoint_config;
pub mod interrupt;
pub mod output;
#[cfg(unix)]
mod passwd;
pub mod proxy;
pub mod region;
pub mod shared_config;
#[cfg(any(windows, test))]
mod snapshot_env;
pub mod startup;
#[cfg(unix)]
pub mod subprocess;
pub mod thread;

#[doc(inline)]
pub use awscli_config::Fs;

/// The version the AWS CLI names itself by, `aws-cli/<version>`, in every
/// request's User-Agent, `--debug`'s `CLI version` line, and `aws --version`
/// on both routes: upstream's `__version__` with the preview's tag, so
/// requests from the preview can be told from upstream's.
pub const AWS_CLI_VERSION: &str = concat!(env!("AWS_CLI_UPSTREAM_VERSION"), "-preview1");

/// Immutable view of a captured environment, preserving present empty values.
pub trait EnvMap {
    /// Returns a Unicode value. A present value that is not Unicode reads as
    /// absent here, so a reader that tests presence, or whose source chain
    /// must stop at a present variable, uses [`EnvMap::var_os`].
    fn var(&self, name: &str) -> Option<&str>;
    /// Returns an operating-system value without requiring Unicode encoding.
    fn var_os(&self, name: &str) -> Option<&std::ffi::OsStr> {
        self.var(name).map(std::ffi::OsStr::new)
    }
    fn names(&self) -> Vec<&str> {
        Vec::new()
    }
}

/// Owned environment snapshot retaining operating-system values, including non-Unicode paths.
///
/// Construction never changes the process environment. String accessors expose only Unicode values.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct SnapshotEnv(std::collections::BTreeMap<String, std::ffi::OsString>);
impl SnapshotEnv {
    pub fn iter(&self) -> impl Iterator<Item = (&str, &str)> {
        self.0
            .iter()
            .filter_map(|(name, value)| Some((name.as_str(), value.to_str()?)))
    }
    pub fn capture() -> Self {
        Self::from_pairs(
            std::env::vars_os().filter_map(|(name, value)| Some((name.into_string().ok()?, value))),
        )
    }
    pub fn from_pairs<K: Into<String>, V: Into<std::ffi::OsString>>(
        pairs: impl IntoIterator<Item = (K, V)>,
    ) -> Self {
        let pairs = pairs
            .into_iter()
            .map(|(key, value)| (key.into(), value.into()));
        #[cfg(windows)]
        let values = snapshot_env::collect(pairs, snapshot_env::names_equal);
        #[cfg(not(windows))]
        let values = pairs.collect();
        Self(values)
    }
}
impl EnvMap for SnapshotEnv {
    fn var(&self, name: &str) -> Option<&str> {
        self.var_os(name).and_then(std::ffi::OsStr::to_str)
    }
    fn var_os(&self, name: &str) -> Option<&std::ffi::OsStr> {
        #[cfg(windows)]
        let value = snapshot_env::get(&self.0, name, snapshot_env::names_equal);
        #[cfg(not(windows))]
        let value = self.0.get(name);
        value.map(std::ffi::OsString::as_os_str)
    }
    fn names(&self) -> Vec<&str> {
        self.0.keys().map(String::as_str).collect()
    }
}
impl EnvMap for std::collections::BTreeMap<String, String> {
    fn var(&self, name: &str) -> Option<&str> {
        self.get(name).map(String::as_str)
    }
    fn names(&self) -> Vec<&str> {
        self.keys().map(String::as_str).collect()
    }
}

/// Injected output destinations and terminal capability.
pub trait Streams {
    fn stdout(&mut self) -> &mut dyn std::io::Write;
    fn stderr(&mut self) -> &mut dyn std::io::Write;
    fn stdout_is_tty(&self) -> bool;
}

pub trait InterruptState {
    fn is_requested(&self) -> bool;
}
pub trait InterruptHook: Send + Sync {
    fn cancel(&self);
}

#[cfg(test)]
mod tests;
