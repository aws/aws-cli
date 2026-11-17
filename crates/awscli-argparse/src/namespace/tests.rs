#![expect(clippy::unwrap_used, reason = "pinned test fixtures and assertions")]
use super::*;
fn json(text: &str) -> Value {
    crate::json::parse(text.as_bytes()).unwrap()
}
#[test]
fn append_owns_values_and_respects_intervening_assignments() {
    let mut ns = Namespace::default();
    ns.put("tags", json(r#"["default"]"#), false);
    let mut tag = String::from("new");
    ns.append("tags", vec![tag.clone()].into());
    tag.replace_range(..1, "x");
    assert_eq!(ns.value("tags").unwrap(), &json(r#"["default",["new"]]"#));
    assert!(ns.is_explicit("tags"));
    ns.put("tags", json(r#"["reset"]"#), true);
    ns.append("tags", "last".into());
    assert_eq!(ns.value("tags").unwrap(), &json(r#"["reset","last"]"#));
    ns.put("tags", "scalar".into(), true);
    ns.append("tags", "only".into());
    assert_eq!(ns.value("tags").unwrap(), &json(r#"["only"]"#));
}
