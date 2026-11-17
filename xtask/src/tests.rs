#[test]
fn deps_system_crt_alone_is_routed_to_the_system_mode_preparation() {
    let args = |values: &[&str]| {
        values
            .iter()
            .map(|value| (*value).to_owned())
            .collect::<Vec<_>>()
    };
    let roots = args(&["system-crt", "--print-roots"]);
    assert_eq!(crate::system_crt_args("deps", &roots), Some(&roots[1..]));
    let bare = args(&["system-crt"]);
    assert_eq!(crate::system_crt_args("deps", &bare), Some(&[][..]));
    for (command, rest) in [
        ("deps", args(&[])),
        ("deps", args(&["crt"])),
        ("deps", args(&["--print-roots", "system-crt"])),
        ("fetch", args(&["system-crt"])),
        ("build", args(&["system-crt"])),
    ] {
        assert_eq!(
            crate::system_crt_args(command, &rest),
            None,
            "{command} {rest:?}"
        );
    }
}
