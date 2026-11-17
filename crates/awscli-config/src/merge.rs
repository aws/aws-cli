use crate::Sections;

pub(crate) fn profiles(config: &Sections, credentials: &Sections) -> Sections {
    let mut result = config.clone();
    for (name, entries) in credentials.iter() {
        if let Some(profile) = result.get_mut(name) {
            for (key, entry) in entries.iter() {
                profile.insert(key.to_owned(), entry.clone());
            }
        } else {
            result.insert(name.to_owned(), entries.clone());
        }
    }
    debug_assert!(result.len() >= config.len().max(credentials.len()));
    result
}
