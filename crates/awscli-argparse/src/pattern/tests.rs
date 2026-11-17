#![expect(
    clippy::unwrap_used,
    clippy::panic,
    reason = "pinned test fixtures and assertions"
)]
use super::*;
use crate::Action;
#[test]
fn exhaustive_cpython_regex_equivalence_through_six_tokens() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/src/testdata/patterns.json");
    let corpus = crate::json::parse(&std::fs::read(path).unwrap()).unwrap();
    for capture in corpus["patterns"].as_array().unwrap() {
        let mut arg = Argument {
            positional: capture["positional"].as_bool().unwrap(),
            ..Argument::new("value")
        };
        arg.nargs = match &capture["nargs"] {
            crate::Value::Null => None,
            crate::Value::Number(n) => {
                let n = n.parse::<u8>().unwrap();
                if n == 0 {
                    arg.action = Action::StoreTrue;
                    None
                } else {
                    Some(Nargs::Count(n))
                }
            }
            crate::Value::String(s) => Some(match s.as_str() {
                "?" => Nargs::Optional,
                "*" => Nargs::ZeroOrMore,
                "+" => Nargs::OneOrMore,
                _ => panic!("bad corpus"),
            }),
            _ => panic!("bad corpus"),
        };
        let mut offset = 0;
        for len in 0..7u32 {
            for encoded in 0..3usize.pow(len) {
                let mut kinds = vec![Kind::Argument; len as usize];
                let mut number = encoded;
                for kind in kinds.iter_mut().rev() {
                    *kind = [Kind::Argument, Kind::Option, Kind::Separator][number % 3];
                    number /= 3;
                }
                assert_eq!(
                    match_argument(arg, &kinds),
                    capture["counts"][offset].as_u64().map(|n| n as usize),
                    "{arg:?} {kinds:?}"
                );
                offset += 1;
            }
        }
        assert_eq!(offset, capture["counts"].as_array().unwrap().len());
    }
}
#[test]
fn greedy_positional_groups_backtrack_and_defer_trailing_empty_matches() {
    let args = [
        Argument {
            positional: true,
            nargs: Some(Nargs::ZeroOrMore),
            ..Argument::new("first")
        },
        Argument {
            positional: true,
            ..Argument::new("second")
        },
        Argument {
            positional: true,
            nargs: Some(Nargs::Optional),
            ..Argument::new("third")
        },
    ];
    assert_eq!(
        match_arguments_partial(&args, &[Kind::Argument, Kind::Argument]),
        [1, 1, 0]
    );
    assert_eq!(
        match_arguments_partial(&args, &[Kind::Argument, Kind::Argument, Kind::Option]),
        [1, 1]
    );
    assert_eq!(match_arguments_partial(&args, &[Kind::Separator]), [1]);
}
