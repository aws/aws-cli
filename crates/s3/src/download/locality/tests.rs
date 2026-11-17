#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;
use crate::download::testing::fakes::FakePlatform;
use std::sync::atomic::Ordering;
fn topology() -> numa::Topology {
    struct Reader;
    impl numa::NodeReader for Reader {
        fn read(&self, _: u32) -> Result<String, numa::NumaError> {
            Ok("0".into())
        }
    }
    let mut cpus = numa::CpuSet::default();
    cpus.set(0).unwrap();
    let nodes = numa::parse_node_mask("0-2").unwrap();
    numa::discover_from_node_reader(&nodes, &cpus, &Reader).unwrap()
}
#[test]
fn download_locality_single_shard_maps_every_offset_and_node_to_shard_zero() {
    let disabled = LocalityContext::default();
    let offsets = [0, u64::MAX].map(|offset| disabled.shard_for_offset(offset));
    assert_eq!((disabled.shard_count(), offsets), (1, [0, 0]));
    assert_eq!(disabled.shard_index_for_node(0), None);
    assert_eq!(disabled.shard_for_body(1, Some(7)), 0);

    let locality = placed(&pool_platform("7"), &[7]);
    let offsets = [0, STRIPE_BYTES * 5].map(|offset| locality.shard_for_offset(offset));
    assert_eq!((locality.shard_count(), offsets), (1, [0, 0]));
    let shards = [7, 0].map(|node| locality.shard_index_for_node(node));
    assert_eq!((shards, locality.nodes[0].id), ([Some(0), None], 7));
}
#[test]
fn download_locality_stripes_offsets_across_shards() {
    let locality = LocalityContext {
        nodes: topology().nodes,
    };
    assert_eq!(locality.shard_count(), 3);
    for index in 0..10 {
        assert_eq!(
            locality.shard_for_offset(index * STRIPE_BYTES),
            index as usize % 3
        );
    }
    let boundaries = [STRIPE_BYTES - 1, STRIPE_BYTES, 4 * STRIPE_BYTES + 12345]
        .map(|offset| locality.shard_for_offset(offset));
    assert_eq!(boundaries, [0, 1, 1]);
    let nodes = [2, 3].map(|shard| locality.nodes.get(shard).map(|node| node.id));
    assert_eq!(
        (locality.shard_index_for_node(1), nodes),
        (Some(1), [Some(2), None])
    );
    assert_eq!(locality.shard_for_body(0, Some(2)), 2);
    assert_eq!(locality.shard_for_body(STRIPE_BYTES, Some(99)), 1);
}
#[test]
fn applying_a_shard_past_the_placed_nodes_is_an_invalid_shard() {
    let platform = pool_platform("0,1");
    let locality = placed(&platform, &[0, 1]);
    let applied = std::thread::spawn(move || {
        let result = locality.apply_to_shard(2, platform.as_ref());
        (result, crate::download::testing::fakes::placed_node())
    })
    .join()
    .unwrap();
    assert_eq!(applied, (Err(numa_failure("NumaInvalidShard")), None));
    let platform = pool_platform("0,1");
    let applied = std::thread::spawn(move || {
        let result = LocalityContext::default().apply_to_shard(5, platform.as_ref());
        (result, crate::download::testing::fakes::placed_node())
    })
    .join()
    .unwrap();
    assert_eq!(applied, (Ok(()), None));
}
#[test]
fn same_node_placement_rejects_a_node_list_before_looking_it_up() {
    let config = |mode, nodes| NumaConfig {
        mode,
        nodes,
        requirement: Requirement::Required,
    };
    let platform = pool_platform("0,1");
    let error =
        LocalityContext::resolve(&config(NumaMode::SameNode, vec![0, 99]), platform).unwrap_err();
    assert_eq!(error, numa_failure("NumaInvalidNodeSelection"));
    let platform = pool_platform("0,1");
    let error =
        LocalityContext::resolve(&config(NumaMode::SameNode, vec![99]), platform).unwrap_err();
    assert_eq!(error, numa_failure("NumaRequestedNodeUnavailable"));
    let platform = pool_platform("0,1");
    let error =
        LocalityContext::resolve(&config(NumaMode::AllNodes, vec![0, 99]), platform).unwrap_err();
    assert_eq!(error, numa_failure("NumaRequestedNodeUnavailable"));
    let platform = pool_platform("0,1");
    let locality =
        LocalityContext::resolve(&config(NumaMode::AllNodes, vec![1, 0]), platform).unwrap();
    let ids: Vec<_> = locality.nodes.iter().map(|node| node.id).collect();
    assert_eq!(ids, [1, 0]);
    let platform = pool_platform("");
    let error =
        LocalityContext::resolve(&config(NumaMode::AllNodes, Vec::new()), platform).unwrap_err();
    assert_eq!(error, numa_failure("NumaNoUsableNode"));
}
#[test]
fn numa_preferred_discovery_failure_falls_back_but_required_is_preserved() {
    let platform: Arc<dyn Platform> = Arc::new(FakePlatform::default());
    let mut config = NumaConfig {
        mode: NumaMode::SameNode,
        requirement: Requirement::Preferred,
        ..NumaConfig::default()
    };
    assert_eq!(
        LocalityContext::resolve(&config, Arc::clone(&platform))
            .unwrap()
            .shard_count(),
        1
    );
    config.requirement = Requirement::Required;
    assert!(LocalityContext::resolve(&config, platform).is_err());
}

fn pool_platform(ids: &str) -> Arc<FakePlatform> {
    let mut cpus = numa::CpuSet::default();
    cpus.set(0).unwrap();
    let nodes = if ids.is_empty() {
        Vec::new()
    } else {
        let mask = numa::parse_node_mask(ids).unwrap();
        (0..numa::MAX_NODES)
            .filter(|id| mask.contains(*id))
            .map(|id| numa::NodeInfo::new(id as u32, cpus, "0"))
            .collect()
    };
    let platform = FakePlatform::default();
    *platform.topology.lock().unwrap() = Some(numa::Topology { nodes });
    Arc::new(platform)
}
fn placed(platform: &FakePlatform, ids: &[u32]) -> LocalityContext {
    let topology = platform.topology.lock().unwrap().clone().unwrap();
    LocalityContext {
        nodes: ids
            .iter()
            .map(|id| topology.node_for_id(*id).unwrap().clone())
            .collect(),
    }
}
fn numa_failure(name: &str) -> WriteError {
    WriteError::Numa(name.into())
}
#[test]
fn unset_or_disabled_source_pool_follows_or_drops_placement() {
    let platform = pool_platform("4,6");
    let locality = placed(&platform, &[4, 6]);
    assert_eq!(
        locality
            .resolve_source_pool(None, platform.as_ref())
            .unwrap(),
        Some(vec![4, 6])
    );
    let inactive = LocalityContext::default();
    assert_eq!(
        inactive
            .resolve_source_pool(None, platform.as_ref())
            .unwrap(),
        None
    );
    let disabled = locality
        .resolve_source_pool(Some(NumaPoolMode::Disabled), platform.as_ref())
        .unwrap();
    assert_eq!(disabled, None);
    assert_eq!(locality.shard_count(), 2);
    assert!(platform.bound_nodes.lock().unwrap().is_empty());
    assert_eq!(platform.thread_probes.load(Ordering::Relaxed), 0);
}
#[test]
fn enabled_source_pool_takes_placement_nodes_and_probes_each() {
    let platform = pool_platform("4,6");
    let locality = placed(&platform, &[6, 4]);
    let pool = locality
        .resolve_source_pool(Some(NumaPoolMode::Enabled), platform.as_ref())
        .unwrap();
    assert_eq!(pool, Some(vec![6, 4]));
    assert_eq!(*platform.bound_nodes.lock().unwrap(), [6, 4]);
    assert_eq!(platform.thread_probes.load(Ordering::Relaxed), 0);
}
#[test]
fn enabled_source_pool_without_placement_selects_its_own_node() {
    let platform = pool_platform("9");
    let disabled = NumaConfig {
        mode: NumaMode::Disabled,
        ..NumaConfig::default()
    };
    let unplaced = LocalityContext::resolve(&disabled, platform.clone()).unwrap();
    let pool = unplaced
        .resolve_source_pool(Some(NumaPoolMode::Enabled), platform.as_ref())
        .unwrap();
    assert_eq!(pool, Some(vec![9]));
    assert_eq!(*platform.bound_nodes.lock().unwrap(), [9]);
    assert_eq!(unplaced.shard_count(), 1);
    assert_eq!(platform.thread_probes.load(Ordering::Relaxed), 0);

    let platform = pool_platform("5");
    let preferred = NumaConfig {
        mode: NumaMode::SameNode,
        requirement: Requirement::Preferred,
        ..NumaConfig::default()
    };
    let single = LocalityContext::resolve(&preferred, platform.clone()).unwrap();
    assert!(single.nodes.is_empty());
    let pool = single
        .resolve_source_pool(Some(NumaPoolMode::Enabled), platform.as_ref())
        .unwrap();
    assert_eq!(pool, Some(vec![5]));
    assert_eq!(platform.thread_probes.load(Ordering::Relaxed), 0);

    if let Ok(current) = numa::current_cpu() {
        let other = u32::from(current.node == 0);
        let platform = pool_platform(&format!("{other},{}", current.node));
        let pool = LocalityContext::default()
            .resolve_source_pool(Some(NumaPoolMode::Enabled), platform.as_ref())
            .unwrap();
        assert_eq!(pool, Some(vec![current.node]));
    }
}
fn required_same_node() -> NumaConfig {
    NumaConfig {
        mode: NumaMode::SameNode,
        nodes: Vec::new(),
        requirement: Requirement::Required,
    }
}
#[test]
fn native_download_resolves_placement_and_its_pool() {
    let platform = pool_platform("0,1");
    let native = LocalityContext::resolve_download(
        &required_same_node(),
        WriterMode::Pwrite,
        None,
        platform,
    )
    .unwrap();
    assert_eq!(native.locality.shard_count(), 1);
    assert_eq!(
        native.source_pool,
        Some(native.locality.nodes.iter().map(|node| node.id).collect())
    );
}
#[test]
fn crt_download_resolves_no_placement_and_its_pool_follows_its_setting() {
    for pool_mode in [None, Some(NumaPoolMode::Disabled)] {
        let platform = pool_platform("0,1");
        let crt = LocalityContext::resolve_download(
            &required_same_node(),
            WriterMode::Crt,
            pool_mode,
            platform.clone(),
        )
        .unwrap();
        assert!(crt.locality.nodes.is_empty());
        assert_eq!(crt.source_pool, None);
        assert_eq!(platform.discoveries.load(Ordering::Relaxed), 0);
    }
    let platform = pool_platform("1");
    let enabled = LocalityContext::resolve_download(
        &required_same_node(),
        WriterMode::Crt,
        Some(NumaPoolMode::Enabled),
        platform.clone(),
    )
    .unwrap();
    assert!(enabled.locality.nodes.is_empty());
    assert_eq!(enabled.source_pool, Some(vec![1]));
    assert_eq!(platform.discoveries.load(Ordering::Relaxed), 1);
    assert_eq!(*platform.bound_nodes.lock().unwrap(), [1]);
    assert_eq!(platform.thread_probes.load(Ordering::Relaxed), 0);
}
#[test]
fn enabled_source_pool_fails_before_any_client_when_it_cannot_place() {
    let enabled = Some(NumaPoolMode::Enabled);
    let unplaced = LocalityContext::default();
    let platform = FakePlatform::default();
    let error = unplaced
        .resolve_source_pool(enabled, &platform)
        .unwrap_err();
    assert_eq!(error, numa_failure("NumaUnsupported"));

    let platform = pool_platform("");
    let error = unplaced
        .resolve_source_pool(enabled, platform.as_ref())
        .unwrap_err();
    assert_eq!(error, numa_failure("NumaNoUsableNode"));

    let platform = pool_platform("3");
    platform.bind_fails.store(true, Ordering::Relaxed);
    let error = unplaced
        .resolve_source_pool(enabled, platform.as_ref())
        .unwrap_err();
    assert_eq!(error, numa_failure("NumaSystemCallFailed"));
    let error = placed(&platform, &[3])
        .resolve_source_pool(enabled, platform.as_ref())
        .unwrap_err();
    assert_eq!(error, numa_failure("NumaSystemCallFailed"));
}
#[test]
fn enabled_source_pool_binds_real_memory_where_the_host_can() {
    use crate::download::platform::NativePlatform;
    let platform = NativePlatform;
    let Ok(topology) = platform.discover_numa() else {
        return;
    };
    let Some(first) = topology.first_node() else {
        return;
    };
    if platform.probe_numa_memory(first.id).is_err() {
        return;
    }
    let unplaced = LocalityContext::default();
    assert_eq!(unplaced.resolve_source_pool(None, &platform).unwrap(), None);
    assert_eq!(
        unplaced
            .resolve_source_pool(Some(NumaPoolMode::Disabled), &platform)
            .unwrap(),
        None
    );
    let pool = unplaced
        .resolve_source_pool(Some(NumaPoolMode::Enabled), &platform)
        .unwrap()
        .unwrap();
    assert_eq!(pool.len(), 1);
    assert!(topology.node_for_id(pool[0]).is_some());
}
#[cfg(unix)]
#[test]
fn numa_failures_are_named_by_the_failing_call() {
    use numa::{NumaCall, NumaError};
    use std::io;
    let os = |call, errno| NumaError::Os {
        call,
        error: io::Error::from_raw_os_error(errno),
    };
    for (error, name) in [
        (
            os(NumaCall::Open, libc::ENOENT),
            "No such file or directory",
        ),
        (os(NumaCall::Open, libc::ESRCH), "No such file or directory"),
        (os(NumaCall::Open, libc::EACCES), "Permission denied"),
        (os(NumaCall::Open, libc::EPERM), "Operation not permitted"),
        (os(NumaCall::Open, libc::ENOTDIR), "Not a directory"),
        (
            os(NumaCall::Open, libc::ELOOP),
            "Too many levels of symbolic links",
        ),
        (os(NumaCall::Open, libc::EMFILE), "Too many open files"),
        (
            os(NumaCall::Open, libc::ENFILE),
            "Too many open files in system",
        ),
        (
            os(NumaCall::Open, libc::ENOMEM),
            "Insufficient system resources",
        ),
        (os(NumaCall::Open, libc::EIO), "Unexpected error"),
        (os(NumaCall::Read, libc::EIO), "Input/output error"),
        (os(NumaCall::Read, libc::EISDIR), "Is a directory"),
        (
            os(NumaCall::Read, libc::ENOMEM),
            "Insufficient system resources",
        ),
        (os(NumaCall::Read, libc::EACCES), "Unexpected error"),
        (
            os(NumaCall::GetAffinity, libc::EPERM),
            "Operation not permitted",
        ),
        (os(NumaCall::GetAffinity, libc::ENOSYS), "Unexpected error"),
        (
            NumaError::CpuOutsideAffinityMask,
            "NumaCpuOutsideAffinityMask",
        ),
        (os(NumaCall::SetAffinity, libc::EPERM), "Unexpected error"),
        (os(NumaCall::SetAffinity, libc::EINVAL), "Unexpected error"),
        (
            NumaError::Os {
                call: NumaCall::Open,
                error: io::ErrorKind::NotFound.into(),
            },
            "No such file or directory",
        ),
        (NumaError::StreamTooLong, "Input too long"),
        (NumaError::MappingFailed, "MappingFailed"),
        (
            NumaError::Io(io::Error::from_raw_os_error(libc::EPERM)),
            "NumaSystemCallFailed",
        ),
    ] {
        assert_eq!(numa_error(error), numa_failure(name), "{name}");
    }
}

#[cfg(feature = "download-writer-debug")]
fn resolve_lines(
    platform: Arc<FakePlatform>,
    mode: NumaMode,
    requirement: Requirement,
) -> Vec<String> {
    let config = NumaConfig {
        mode,
        requirement,
        ..NumaConfig::default()
    };
    crate::download::diagnostics::capture(|| {
        let _ = LocalityContext::resolve(&config, platform);
    })
}

#[test]
#[cfg(feature = "download-writer-debug")]
fn inactive_placement_logs_why() {
    let line = |reason: &str| {
        format!("debug(download_locality_context): locality numa_active=false reason={reason}")
    };
    let os = format!("os os={}", crate::download::platform::NAME);
    assert_eq!(
        resolve_lines(
            pool_platform("0,1"),
            NumaMode::Disabled,
            Requirement::Preferred
        ),
        [line("disabled")]
    );
    let platform = Arc::new(FakePlatform::default());
    assert_eq!(
        resolve_lines(platform, NumaMode::SameNode, Requirement::Preferred),
        [line(&os), line("unavailable err=NumaUnsupported")]
    );
    let platform = Arc::new(FakePlatform::default());
    assert_eq!(
        resolve_lines(platform, NumaMode::SameNode, Requirement::Required),
        [line(&os)]
    );
    assert_eq!(
        resolve_lines(
            pool_platform("3"),
            NumaMode::AllNodes,
            Requirement::Preferred
        ),
        [line("single-node")]
    );
    let config = NumaConfig {
        mode: NumaMode::AllNodes,
        nodes: vec![9],
        requirement: Requirement::Preferred,
    };
    let lines = crate::download::diagnostics::capture(|| {
        let _ = LocalityContext::resolve(&config, pool_platform("0,1"));
    });
    assert_eq!(
        lines,
        [line("unavailable err=NumaRequestedNodeUnavailable")]
    );
}

#[test]
#[cfg(feature = "download-writer-debug")]
fn active_placement_logs_its_shards_and_dropped_nodes() {
    let prefix = "debug(download_locality_context): locality";
    assert_eq!(
        resolve_lines(
            pool_platform("4,6"),
            NumaMode::AllNodes,
            Requirement::Required
        ),
        [
            format!("{prefix} numa_active=true mode=all_nodes shards=2 stripe_bytes=67108864"),
            format!("{prefix} shard=0 node=4 cpus=1 cpu_list=0"),
            format!("{prefix} shard=1 node=6 cpus=1 cpu_list=0"),
        ]
    );
    let lines = resolve_lines(
        pool_platform("0-16"),
        NumaMode::AllNodes,
        Requirement::Required,
    );
    assert_eq!(
        lines[..2],
        [
            format!("{prefix} dropping nodes beyond shard limit limit=16 topology_nodes=17"),
            format!("{prefix} numa_active=true mode=all_nodes shards=16 stripe_bytes=67108864"),
        ]
    );
    assert_eq!(lines.len(), 2 + MAX_NODES);
    assert_eq!(
        lines[17],
        format!("{prefix} shard=15 node=15 cpus=1 cpu_list=0")
    );
    let lines = resolve_lines(
        pool_platform("2,5"),
        NumaMode::SameNode,
        Requirement::Preferred,
    );
    assert!(lines[0].starts_with(&format!(
        "{prefix} numa_active=true mode=same_node shards=1 "
    )));
    assert_eq!(lines.len(), 2);
}
