use std::collections::HashMap;

/// A string-keyed map retaining insertion order when values are replaced.
#[derive(Clone, Debug)]
pub struct OrderedMap<V> {
    entries: Vec<(String, V)>,
    indices: HashMap<String, usize>,
}
impl<V> Default for OrderedMap<V> {
    fn default() -> Self {
        Self {
            entries: Vec::new(),
            indices: HashMap::new(),
        }
    }
}
impl<V: PartialEq> PartialEq for OrderedMap<V> {
    fn eq(&self, other: &Self) -> bool {
        self.entries == other.entries
    }
}
impl<V: Eq> Eq for OrderedMap<V> {}
impl<V> OrderedMap<V> {
    pub fn len(&self) -> usize {
        self.entries.len()
    }
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
    pub fn contains_key(&self, key: &str) -> bool {
        self.indices.contains_key(key)
    }
    pub fn get(&self, key: &str) -> Option<&V> {
        self.indices.get(key).map(|&index| &self.entries[index].1)
    }
    pub fn get_mut(&mut self, key: &str) -> Option<&mut V> {
        self.indices
            .get(key)
            .map(|&index| &mut self.entries[index].1)
    }
    pub fn insert(&mut self, key: String, value: V) -> Option<V> {
        if let Some(&index) = self.indices.get(&key) {
            return Some(std::mem::replace(&mut self.entries[index].1, value));
        }
        self.indices.insert(key.clone(), self.entries.len());
        self.entries.push((key, value));
        None
    }
    pub fn iter(&self) -> impl Iterator<Item = (&str, &V)> {
        self.entries
            .iter()
            .map(|(key, value)| (key.as_str(), value))
    }
    pub fn keys(&self) -> impl Iterator<Item = &str> {
        self.entries.iter().map(|(key, _)| key.as_str())
    }
}
