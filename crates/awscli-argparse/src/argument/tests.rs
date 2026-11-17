use super::*;
#[test]
fn destinations_follow_dest_and_dash_rules() {
    assert!(Argument::new("page-size").matches_dest("page_size"));
    assert!(!Argument::new("page-size").matches_dest("page-size"));
    let recursive = Argument {
        dest: Some("dir_op"),
        ..Argument::new("recursive")
    };
    assert!(recursive.matches_dest("dir_op"));
    assert!(!recursive.matches_dest("recursive"));
    let paths = Argument {
        positional: true,
        ..Argument::new("paths")
    };
    assert!(paths.matches_dest("paths"));
    assert!(!paths.matches_dest("path"));
}
