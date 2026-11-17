use super::*;
#[test]
fn prefix_upper_bounds_handle_exact_carry_and_terminal_ranges() {
    let mut buffer = [0; 16];
    assert_eq!(
        prefix_upper_bound(&mut buffer, b"abc"),
        Some(b"abd".as_slice())
    );
    assert_eq!(
        prefix_upper_bound(&mut buffer, b"ab\xff"),
        Some(b"ac".as_slice())
    );
    assert_eq!(
        prefix_upper_bound(&mut buffer, b"a\xff\xff"),
        Some(b"b".as_slice())
    );
    assert_eq!(prefix_upper_bound(&mut buffer, b""), None);
    assert_eq!(prefix_upper_bound(&mut buffer, b"\xff\xff"), None);
    assert_eq!(prefix_upper_bound(&mut buffer[..2], b"abc"), None);
}
#[test]
fn immediate_directory_children_reject_misses_and_collapse_descendants() {
    assert_eq!(
        immediate_child(b"pkg/", b"pkg/file.pyc"),
        Some(b"file.pyc".as_slice())
    );
    assert_eq!(
        immediate_child(b"pkg/", b"pkg/child/file.pyc"),
        Some(b"child".as_slice())
    );
    for name in [b"pkg/".as_slice(), b"pkg//file.pyc", b"other/file.pyc"] {
        assert_eq!(immediate_child(b"pkg/", name), None);
    }
}
#[test]
fn model_filename_matching_is_exact() {
    assert!(is_model_file(b"service-2.json", b"service-2"));
    assert!(is_model_file(b"waiters-2.json", b"waiters-2"));
    for name in [
        b"service-2.json.gz".as_slice(),
        b"prefix-service-2.json",
        b"service-2",
    ] {
        assert!(!is_model_file(name, b"service-2"));
    }
}
