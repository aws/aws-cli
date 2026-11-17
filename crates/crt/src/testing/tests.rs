use super::*;

#[test]
fn exhausted_input_reads_every_choice_as_its_minimum() {
    let mut choices = Choices::new(&[]);
    assert_eq!(choices.range(3, 9), 3);
    assert_eq!(choices.index(4), 0);
    assert!(!choices.flag());
    assert_eq!(choices.word(), 0);
    assert_eq!(choices.bytes(8), b"");
    assert!(choices.is_empty());
}

#[test]
fn ranges_read_the_fewest_bytes_most_significant_first() {
    let mut choices = Choices::new(&[7, 0x01, 0x02, 3, 0xff, 9]);
    // 7 modulo the five values of 1..=5.
    assert_eq!(choices.range(1, 5), 3);
    // Two bytes cover a span of 999, and 0x0102 is below it.
    assert_eq!(choices.range(0, 999), 0x0102);
    assert!(choices.flag());
    // A range of one value reads nothing.
    assert_eq!(choices.range(4, 4), 4);
    assert_eq!(choices.index(1), 0);
    assert_eq!(choices.index(0), 0);
    assert_eq!(choices.index(256), 0xff);
    // A short tail is what remains: the last byte of a word.
    assert_eq!(choices.word(), 9);
    assert!(choices.is_empty());
}

#[test]
fn bytes_read_a_length_then_at_most_the_bytes_that_remain() {
    let mut choices = Choices::new(&[3, b'a', b'b', b'c', 9, b'd']);
    assert_eq!(choices.bytes(8), b"abc");
    // A length of 9 modulo the nine lengths 0..=8 is 0.
    assert_eq!(choices.bytes(8), b"");
    let mut choices = Choices::new(&[5, b'x']);
    assert_eq!(choices.bytes(8), b"x");
}

#[test]
fn scripts_encode_the_values_their_choices_read() {
    let script = Script::new()
        .range(1, 5, 4)
        .range(0, 999, 700)
        .flag(true)
        .range(4, 4, 4)
        .index(256, 200)
        .word(u64::MAX - 1)
        .bytes(4, b"ab")
        .repeat(3, |script| script.flag(false));
    let mut choices = Choices::new(script.encoded());
    let numbers = [
        choices.range(1, 5),
        choices.range(0, 999),
        usize::from(choices.flag()),
        choices.range(4, 4),
        choices.index(256),
    ];
    assert_eq!(numbers, [4, 700, 1, 4, 200]);
    assert_eq!(choices.word(), u64::MAX - 1);
    assert_eq!(choices.bytes(4), b"ab");
    assert_eq!([choices.flag(), choices.flag(), choices.flag()], [false; 3]);
    assert!(choices.is_empty());
    assert_eq!(choices.trace().len(), 11);
}

#[test]
fn a_replay_accepts_a_model_that_makes_the_scripted_choices_first() {
    Script::new().range(0, 9, 7).flag(true).replay(|choices| {
        assert_eq!(choices.range(0, 9), 7);
        assert!(choices.flag());
        // Past the script, choices read their minimum.
        assert_eq!(choices.range(2, 9), 2);
    });
}

#[test]
#[should_panic(expected = "choice 0 is not the script's")]
fn a_replay_rejects_a_model_whose_choices_differ_from_the_script() {
    Script::new().range(0, 9, 7).replay(|choices| {
        let _ = choices.range(0, 10);
    });
}

#[test]
fn generators_repeat_per_seed_and_differ_across_seeds() {
    let words = |seed| {
        let mut generator = SplitMix64::new(seed);
        [generator.next_word(), generator.next_word()]
    };
    assert_eq!(words(7), words(7));
    assert_ne!(words(7), words(8));
    // A seed of zero, as exhausted input gives, still yields nonzero words.
    assert!(words(0).iter().all(|word| *word != 0));
    let mut choices = Choices::new(&[]);
    assert_eq!(choices.generator(), SplitMix64::new(0));
}

#[test]
fn sweep_cases_are_distinct_inputs_of_the_requested_length() {
    let mut inputs = Vec::new();
    sweep(13, |bytes| inputs.push(bytes.to_vec()));
    assert_eq!(inputs.len() as u64, script::SWEEP_CASES);
    assert!(inputs.iter().all(|bytes| bytes.len() == 13));
    inputs.sort();
    inputs.dedup();
    assert_eq!(inputs.len() as u64, script::SWEEP_CASES);
}
