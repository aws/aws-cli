use super::*;
const LIST: &Command = match S3.subcommand("ls") {
    Some(command) => command,
    None => panic!("missing ls"),
};
#[test]
fn const_command_lookup_selects_the_child() {
    assert_eq!(LIST.name, "ls");
}
