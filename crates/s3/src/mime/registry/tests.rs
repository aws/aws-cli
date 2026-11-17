use super::*;
use std::io;

mod fixture;
use fixture::{Fixture, wide};

#[test]
fn empty_registry_fixture_reports_end_of_enumeration() -> io::Result<()> {
    let fixture = Fixture::new()?;
    let mut database = Database::default();
    assert_eq!(read_key(&mut database, fixture.key()?, 0), NO_MORE_ITEMS);
    assert!(database.added.is_empty());
    fixture.finish()
}

#[test]
fn extension_buffer_includes_the_name_terminator() -> io::Result<()> {
    for (units, expected) in [(127, SUCCESS), (128, MORE_DATA)] {
        let fixture = Fixture::new()?;
        let extension = format!(".{}", "x".repeat(units - 1));
        fixture.set_value(&extension, REG_SZ, &wide("application/x-bound"))?;
        let mut database = Database::default();
        assert_eq!(read_key(&mut database, fixture.key()?, 0), expected);
        let value = database.added.get(extension.as_bytes()).map(Vec::as_slice);
        if units == 127 {
            assert_eq!(value, Some(b"application/x-bound".as_slice()));
        } else {
            assert!(value.is_none());
            assert!(database.added.is_empty());
        }
        assert_eq!(read_key(&mut database, fixture.key()?, 1), NO_MORE_ITEMS);
        fixture.finish()?;
    }
    Ok(())
}

#[test]
fn content_type_buffer_accepts_510_bytes_and_rejects_512() -> io::Result<()> {
    for (characters, expected) in [(254, SUCCESS), (255, MORE_DATA)] {
        let fixture = Fixture::new()?;
        let mime_type = "x".repeat(characters);
        fixture.set_value(".bounded", REG_SZ, &wide(&mime_type))?;
        let mut database = Database::default();
        assert_eq!(read_key(&mut database, fixture.key()?, 0), expected);
        let value = database
            .added
            .get(b".bounded".as_slice())
            .map(Vec::as_slice);
        if characters == 254 {
            assert_eq!(value, Some(mime_type.as_bytes()));
        } else {
            assert!(value.is_none());
            assert!(database.added.is_empty());
        }
        fixture.finish()?;
    }
    Ok(())
}

#[test]
fn non_extension_keys_and_non_string_values_are_skipped() -> io::Result<()> {
    for (extension, kind) in [("ordinary", REG_SZ), (".expanded", 2), (".binary", 3)] {
        let fixture = Fixture::new()?;
        fixture.set_value(extension, kind, &wide("application/x-ignored"))?;
        let mut database = Database::default();
        assert_eq!(read_key(&mut database, fixture.key()?, 0), SUCCESS);
        assert!(database.added.is_empty());
        fixture.finish()?;
    }
    Ok(())
}

#[test]
fn missing_and_empty_content_types_do_not_add_mappings() -> io::Result<()> {
    let missing = Fixture::new()?;
    missing.create_empty(".missing")?;
    let mut database = Database::default();
    assert_eq!(read_key(&mut database, missing.key()?, 0), SUCCESS);
    assert!(database.added.is_empty());
    missing.finish()?;

    for value in [Vec::new(), vec![0]] {
        let fixture = Fixture::new()?;
        fixture.set_value(".empty", REG_SZ, &value)?;
        assert_eq!(read_key(&mut database, fixture.key()?, 0), SUCCESS);
        assert!(database.added.is_empty());
        fixture.finish()?;
    }
    Ok(())
}

#[test]
fn registry_values_stop_at_nul_and_preserve_unicode() -> io::Result<()> {
    for (extension, stored, expected) in [
        (".nul", "text/x-first\0ignored", "text/x-first"),
        (
            ".caf\u{e9}\u{1f680}",
            "application/x-\u{3bb}\u{1f680}",
            "application/x-\u{3bb}\u{1f680}",
        ),
    ] {
        let fixture = Fixture::new()?;
        fixture.set_value(extension, REG_SZ, &wide(stored))?;
        let mut database = Database::default();
        assert_eq!(read_key(&mut database, fixture.key()?, 0), SUCCESS);
        assert_eq!(
            database.added.get(extension.as_bytes()).map(Vec::as_slice),
            Some(expected.as_bytes())
        );
        fixture.finish()?;
    }
    Ok(())
}

#[test]
fn system_messages_preserve_unsigned_status_without_locale_assumptions() {
    for status in [NOT_FOUND, ACCESS_DENIED, MORE_DATA, i32::MAX, -1] {
        let message = error_text(status);
        let prefix = format!("[WinError {}] ", status as u32);
        assert!(message.starts_with(prefix.as_bytes()));
        assert!(message.len() > prefix.len());
        assert!(!message.contains(&0));
        assert!(
            message
                .last()
                .is_some_and(|byte| *byte > b' ' && *byte != b'.')
        );
    }
}
