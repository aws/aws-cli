use super::{Request, decode_request, formatter_width};
#[test]
fn columns_parse_trimmed_positive_decimals_with_inner_underscores() {
    for (text, width) in [
        ("40", 38),
        ("4_0", 38),
        ("+4_0", 38),
        ("4__0", 38),
        (" \t+4_0\r\n", 38),
        ("1", 0),
        ("2", 0),
        ("_40", 78),
        ("40_", 78),
        ("0", 78),
        ("0_0", 78),
        ("-0", 78),
        ("-40", 78),
        ("", 78),
        ("++40", 78),
        ("0x28", 78),
        ("٤٠", 78),
        ("40\u{b}", 78),
    ] {
        assert_eq!(formatter_width(Some(text)), width, "{text:?}");
    }
    assert_eq!(formatter_width(None), 78);
    assert_eq!(
        formatter_width(Some(&usize::MAX.to_string())),
        usize::MAX - 2
    );
    assert_eq!(formatter_width(Some(&format!("{}0", usize::MAX))), 78);
}
#[test]
fn requests_decode_argv_and_an_optional_boolean_color() {
    assert_eq!(
        decode_request(r#"{"argv":["s3","ls"],"color":true}"#, 0),
        Ok(Request {
            argv: vec!["s3".into(), "ls".into()],
            color: true,
        })
    );
    assert_eq!(
        decode_request(r#"{"argv":[],"unknown":1}"#, 0),
        Ok(Request {
            argv: Vec::new(),
            color: false,
        })
    );
}
#[test]
fn a_non_boolean_color_is_a_request_error() {
    for color in [r#""yes""#, "1", "null", "[]"] {
        let line = format!(r#"{{"argv":["s3","ls"],"color":{color}}}"#);
        assert_eq!(
            decode_request(&line, 0),
            Err("color must be a boolean".into()),
            "{line}"
        );
    }
}
#[test]
fn an_oversized_request_names_its_record() {
    let argument = "x".repeat(awscli_argparse::ARG_LEN_MAX + 1);
    let line = format!(r#"{{"argv":["s3","ls","{argument}"]}}"#);
    assert_eq!(
        decode_request(&line, 3),
        Err("request exceeds host argv limits record=3".into())
    );
    let argument = "x".repeat(awscli_argparse::ARG_LEN_MAX);
    let line = format!(r#"{{"argv":["s3","ls","{argument}"]}}"#);
    assert!(decode_request(&line, 3).is_ok());
}
