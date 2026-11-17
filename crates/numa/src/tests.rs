#![expect(
    clippy::unwrap_used,
    reason = "test assertions require successful fixture parsing"
)]
use super::*;
#[test]
fn parses_cpu_list_ranges() {
    let set = parse_cpu_list("0-2,4,8-9\n").unwrap();
    for cpu in [0, 1, 2, 4, 8, 9] {
        assert!(set.contains(cpu));
    }
    assert!(!set.contains(3));
    assert_eq!(set.count(), 6);
}
#[test]
fn cpu_list_empty_malformed_duplicates_and_boundaries() {
    let empty = parse_cpu_list(" \t\r\n").unwrap();
    assert!(empty.is_empty());
    assert_eq!(empty.count(), 0);
    let duplicate = parse_cpu_list("1,1,1-2,2").unwrap();
    assert_eq!(duplicate.count(), 2);
    assert!(duplicate.contains(1));
    assert!(duplicate.contains(2));
    check_cpu_boundaries();
    check_malformed_cpu_lists();
}
fn check_cpu_boundaries() {
    let boundary = parse_cpu_list(&(MAX_CPUS - 1).to_string()).unwrap();
    assert!(boundary.contains(MAX_CPUS - 1));
    assert_eq!(boundary.count(), 1);
    assert!(matches!(
        parse_cpu_list(&MAX_CPUS.to_string()),
        Err(NumaError::CpuOutsideAffinityMask)
    ));
}
fn check_malformed_cpu_lists() {
    for text in [
        ",", "0,", ",0", "0,,1", "-1", "1-", "1-2-3", "3-2", "one", "0, one",
    ] {
        assert!(
            matches!(parse_cpu_list(text), Err(NumaError::InvalidList)),
            "{text}"
        );
    }
}
#[test]
fn cpu_set_operations_cross_word_boundaries() {
    let mut set = CpuSet::default();
    for cpu in [0, WORD_BITS - 1, WORD_BITS, WORD_BITS + 1] {
        set.set(cpu).unwrap();
        assert!(set.contains(cpu));
    }
    assert!(!set.contains(WORD_BITS + 2));
    assert_eq!(set.count(), 4);
    assert!(!set.is_empty());
}
#[test]
fn cpu_intersection_keeps_only_allowed_cpus() {
    let mut set = parse_cpu_list("0-3,8-11").unwrap();
    set.intersect_with(&parse_cpu_list("1,3,9").unwrap());
    assert_eq!(set.count(), 3);
    for cpu in [1, 3, 9] {
        assert!(set.contains(cpu));
    }
    for cpu in [0, 8, 10] {
        assert!(!set.contains(cpu));
    }
}
#[test]
fn allowed_node_status_and_malformed_inputs() {
    let mask = parse_allowed_node_mask(
        b"Name:\ttest\nMems_allowed_list:\t0,2-3\nCpus_allowed_list:\t0-7\n",
    )
    .unwrap();
    for node in [0, 2, 3] {
        assert!(mask.contains(node));
    }
    assert!(!mask.contains(1));
    for text in [
        b"Name:\ttest\nCpus_allowed_list:\t0-7\n".as_slice(),
        b"Mems_allowed_list:\t\n",
    ] {
        assert!(matches!(
            parse_allowed_node_mask(text),
            Err(NumaError::AllowedListUnavailable)
        ));
    }
    for text in ["0,,1", "3-2", &MAX_NODES.to_string()] {
        assert!(matches!(parse_node_mask(text), Err(NumaError::InvalidList)));
    }
}
#[test]
fn allowed_node_status_is_matched_as_bytes() {
    let mask = parse_allowed_node_mask(
        b"Name:\taws-native-caf\xC3\nMems_allowed_list:\t0-2\nCpus_allowed_list:\t0-7\n",
    )
    .unwrap();
    for node in [0, 1, 2] {
        assert!(mask.contains(node));
    }
    assert!(!mask.contains(3));
    assert!(matches!(
        parse_allowed_node_mask(b"Name:\t\xC3\nMems_allowed_list:\t0-\xC3\n"),
        Err(NumaError::InvalidList)
    ));
}
#[test]
fn topology_lookup_and_nodemask_boundaries() {
    let topology = Topology {
        nodes: [2, 7]
            .into_iter()
            .map(|id| NodeInfo {
                id,
                cpu_set: CpuSet::default(),
                cpu_count: 0,
                cpu_list: String::new(),
            })
            .collect(),
    };
    assert_eq!(topology.first_node().unwrap().id, 2);
    assert_eq!(topology.node_for_id(7).unwrap().id, 7);
    assert!(topology.node_for_id(3).is_none());
    let mut mask = NodeMask::default();
    for node in [0, WORD_BITS - 1, WORD_BITS, MAX_NODES - 1] {
        mask.set(node);
        assert!(mask.contains(node));
    }
    mask.set(MAX_NODES);
    assert!(!mask.contains(MAX_NODES));
    assert_eq!(mask.words[0], 1 | (1 << (WORD_BITS - 1)));
    assert_eq!(mask.words[1], 1);
    assert_eq!(mask.words[MAX_NODES / WORD_BITS - 1], 1 << (WORD_BITS - 1));
}
#[derive(Debug)]
struct FakeNodes<'a>(&'a [(u32, Option<&'a str>)]);
impl NodeReader for FakeNodes<'_> {
    fn read(&self, node: u32) -> Result<String, NumaError> {
        self.0
            .iter()
            .find(|(id, _)| *id == node)
            .and_then(|(_, text)| *text)
            .map(str::to_owned)
            .ok_or(NumaError::Io(std::io::Error::from(
                std::io::ErrorKind::NotFound,
            )))
    }
}
#[test]
fn discovery_uses_deterministic_node_files() {
    let allowed = parse_node_mask("0-4").unwrap();
    let cpus = parse_cpu_list("1,10").unwrap();
    let files = FakeNodes(&[
        (0, Some("0-1\n")),
        (1, None),
        (2, Some(" \n")),
        (3, None),
        (4, Some("8,10\n")),
    ]);
    let topology = discover_from_node_reader(&allowed, &cpus, &files).unwrap();
    assert_eq!(topology.nodes.len(), 2);
    for (node, id, list, kept, rejected) in [
        (&topology.nodes[0], 0, "0-1", 1, 0),
        (&topology.nodes[1], 4, "8,10", 10, 8),
    ] {
        assert_eq!(node.id, id);
        assert_eq!(node.cpu_list(), list);
        assert_eq!(node.cpu_count, 1);
        assert!(node.cpu_set.contains(kept));
        assert!(!node.cpu_set.contains(rejected));
    }
    check_unusable_node_files(&cpus);
}
fn check_unusable_node_files(cpus: &CpuSet) {
    for list in ["\n", "2-3\n"] {
        assert!(matches!(
            discover_from_node_reader(
                &parse_node_mask("0").unwrap(),
                cpus,
                &FakeNodes(&[(0, Some(list))])
            ),
            Err(NumaError::NoUsableNode)
        ));
    }
    assert!(matches!(
        discover_from_node_reader(
            &parse_node_mask("0").unwrap(),
            cpus,
            &FakeNodes(&[(0, Some("3-1\n"))])
        ),
        Err(NumaError::InvalidList)
    ));
}
