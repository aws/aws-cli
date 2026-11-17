use super::*;
#[test]
fn dropping_an_unstarted_processor_releases_its_queued_events() {
    let processor = Processor::new(None);
    let publisher = processor.publisher();
    let weak = Arc::downgrade(&publisher.0);
    publisher.publish(Event::Warning(vec![b'x'; 4096]));
    assert!(weak.upgrade().is_some());
    drop(publisher);
    drop(processor);
    assert!(weak.upgrade().is_none());
}
