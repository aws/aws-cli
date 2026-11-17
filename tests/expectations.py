from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ExpectationKind(Enum):
    PARITY_GAP = "parity-gap"
    SHARED_HARNESS_FAILURE = "shared-harness-failure"
    PYTHON_ONLY_HARNESS_FAILURE = "python-only-harness-failure"
    HARNESS_INCONCLUSIVE = "harness-inconclusive"
    UPSTREAM_ISSUE = "upstream-issue"
    # A deliberate difference of code both routes share, the launcher, from
    # the public AWS CLI's, so the built binary fails the test on either.
    LAUNCHER_DIFFERENCE = "launcher-difference"


@dataclass(frozen=True)
class ExpectedResult:
    node_id: str
    kind: ExpectationKind
    reason: str

    def expects_failure(self, *, python_router: bool) -> bool:
        if self.kind is ExpectationKind.PARITY_GAP:
            return not python_router
        if self.kind is ExpectationKind.PYTHON_ONLY_HARNESS_FAILURE:
            return python_router
        return self.kind in (
            ExpectationKind.SHARED_HARNESS_FAILURE,
            ExpectationKind.UPSTREAM_ISSUE,
            ExpectationKind.LAUNCHER_DIFFERENCE,
        )


def read_expectations(manifest: Path) -> list[ExpectedResult]:
    expectations: list[ExpectedResult] = []
    seen: set[str] = set()
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        node_id, separator, annotation = line.partition("#")
        node_id = node_id.strip()
        if not separator or not annotation.strip():
            raise SystemExit(
                f"{manifest}:{line_number}: expected a trailing category "
                "and reason"
            )
        category, category_separator, reason = annotation.partition(":")
        if not category_separator or not reason.strip():
            raise SystemExit(
                f"{manifest}:{line_number}: expected '<category>: <reason>'"
            )
        try:
            kind = ExpectationKind(category.strip())
        except ValueError as error:
            raise SystemExit(
                f"{manifest}:{line_number}: unknown category: "
                f"{category.strip()}"
            ) from error
        if node_id in seen:
            raise SystemExit(
                f"{manifest}:{line_number}: duplicate node id: {node_id}"
            )
        seen.add(node_id)
        expectations.append(
            ExpectedResult(
                node_id=node_id,
                kind=kind,
                reason=reason.strip(),
            )
        )
    return expectations


def read_combined_expectations(
    manifests: Sequence[Path],
) -> list[ExpectedResult]:
    """Read several ledgers as one; each node id may appear in only one."""
    expectations: list[ExpectedResult] = []
    sources: dict[str, Path] = {}
    for manifest in manifests:
        for expectation in read_expectations(manifest):
            previous = sources.setdefault(expectation.node_id, manifest)
            if previous != manifest:
                raise SystemExit(
                    f"{manifest}: {expectation.node_id} is also listed in "
                    f"{previous}"
                )
            expectations.append(expectation)
    return expectations


def python_router_forced(router: str | None) -> bool:
    """Only the exact value ``python`` forces the Python reference route."""
    return router == "python"


def parity_summary_lines(
    selected: Mapping[str, ExpectedResult],
    *,
    python_router: bool,
    stats: Mapping[str, Sequence[Any]],
) -> list[str]:
    """Render the classified parity summary from pytest's report stats."""
    parity = _expectations_of_kind(selected, ExpectationKind.PARITY_GAP)
    shared = _expectations_of_kind(
        selected,
        ExpectationKind.SHARED_HARNESS_FAILURE,
    )
    python_only = _expectations_of_kind(
        selected,
        ExpectationKind.PYTHON_ONLY_HARNESS_FAILURE,
    )
    inconclusive = _expectations_of_kind(
        selected,
        ExpectationKind.HARNESS_INCONCLUSIVE,
    )
    upstream = _expectations_of_kind(selected, ExpectationKind.UPSTREAM_ISSUE)
    xfailed_node_ids = {report.nodeid for report in stats.get("xfailed", ())}
    if python_router:
        parity_line = _python_reference_parity_line(parity, stats)
    else:
        parity_failures = len(parity & xfailed_node_ids)
        parity_line = (
            "Native parity gaps: "
            f"{counted_tests(parity_failures)} failed "
            "(Python reference passes)"
        )
    shared_failures = len(shared & xfailed_node_ids)
    upstream_failures = len(upstream & xfailed_node_ids)
    harness_count = counted_tests(
        len(shared) + len(python_only) + len(inconclusive) + len(upstream)
    )
    return [
        parity_line,
        (
            "Not parity evidence: "
            f"{harness_count} "
            f"({shared_failures}/{len(shared)} shared harness failures, "
            f"{len(python_only)} Python-only harness "
            f"{'failure' if len(python_only) == 1 else 'failures'}, "
            f"{upstream_failures}/{len(upstream)} upstream "
            f"{'issue' if len(upstream) == 1 else 'issues'}, "
            f"{len(inconclusive)} inconclusive passes)"
        ),
    ]


def _python_reference_parity_line(
    parity: set[str],
    stats: Mapping[str, Sequence[Any]],
) -> str:
    # A parity gap is evidence only when its test completed and passed
    # through the Python reference; selected-but-unfinished cases (-x,
    # --collect-only, skips) and failures must not count as passes.
    passed_node_ids = {report.nodeid for report in stats.get("passed", ())}
    failed_node_ids = {
        report.nodeid
        for category in ("failed", "error")
        for report in stats.get(category, ())
    }
    failed = parity & failed_node_ids
    passed = (parity & passed_node_ids) - failed_node_ids
    not_run = parity - passed - failed
    line = (
        "Native parity gaps: "
        f"{counted_tests(len(passed))} passed through the Python reference"
    )
    caveats: list[str] = []
    if failed:
        caveats.append(f"{counted_tests(len(failed))} failed")
    if not_run:
        caveats.append(f"{counted_tests(len(not_run))} did not run")
    if caveats:
        line += f" ({', '.join(caveats)})"
    return line


def _expectations_of_kind(
    expectations: Mapping[str, ExpectedResult],
    kind: ExpectationKind,
) -> set[str]:
    return {
        node_id
        for node_id, expectation in expectations.items()
        if expectation.kind is kind
    }


def counted_tests(count: int) -> str:
    noun = "test" if count == 1 else "tests"
    return f"{count} {noun}"
