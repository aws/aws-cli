//! Insertion-ordered raw namespace values and explicit provenance.
pub use crate::json::JsonValue as Value;
/// One destination and its last assignment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub dest: String,
    pub value: Value,
    pub explicit: bool,
}
/// Parsed destinations in their first insertion order.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Namespace {
    pub entries: Vec<Entry>,
}
impl Namespace {
    pub fn value(&self, dest: &str) -> Option<&Value> {
        self.entries
            .iter()
            .find(|e| e.dest == dest)
            .map(|e| &e.value)
    }
    pub fn string(&self, dest: &str) -> Option<&str> {
        self.value(dest).and_then(Value::as_str)
    }
    pub fn os_string(&self, dest: &str) -> Option<&std::ffi::OsStr> {
        self.value(dest).and_then(Value::as_os_str)
    }
    pub fn boolean(&self, dest: &str) -> bool {
        self.value(dest).and_then(Value::as_bool).unwrap_or(false)
    }
    pub fn integer(&self, dest: &str) -> Option<i64> {
        self.value(dest).and_then(Value::as_i64)
    }
    pub fn is_explicit(&self, dest: &str) -> bool {
        self.entries.iter().any(|e| e.dest == dest && e.explicit)
    }
    pub fn put(&mut self, dest: impl Into<String>, value: Value, explicit: bool) {
        let dest = dest.into();
        assert!(!dest.is_empty());
        if let Some(e) = self.entries.iter_mut().find(|e| e.dest == dest) {
            e.value = value;
            e.explicit |= explicit;
        } else {
            self.entries.push(Entry {
                dest,
                value,
                explicit,
            });
        }
    }
    pub fn append(&mut self, dest: &str, value: Value) {
        if self.value(dest).is_none() {
            self.put(dest, Value::Null, false);
        }
        if let Some(e) = self.entries.iter_mut().find(|e| e.dest == dest) {
            if !e.value.is_array() {
                e.value = Value::Array(Vec::new());
            }
            if let Value::Array(a) = &mut e.value {
                a.push(value);
            }
            e.explicit = true;
        }
    }
    pub fn json(&self) -> Value {
        Value::Object(
            self.entries
                .iter()
                .map(|e| (e.dest.clone(), e.value.clone()))
                .collect(),
        )
    }
}
#[cfg(test)]
mod tests;
