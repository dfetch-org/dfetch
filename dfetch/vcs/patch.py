"""Various patch utilities for VCS systems."""

from collections.abc import Sequence

import patch_ng


def filter_patch(patch_text: bytes, ignore: Sequence[str]) -> str:
    """Filter out files from a patch text."""
    if not patch_text:
        return ""

    filtered_patchset = patch_ng.PatchSet()
    unfiltered_patchset = patch_ng.fromstring(patch_text) or []

    for patch in unfiltered_patchset:
        if patch.target.decode("utf-8") not in ignore:
            filtered_patchset.items += [patch]

    return dump_patch(filtered_patchset)


def dump_patch(patch_set: patch_ng.PatchSet) -> str:
    """Dump a patch to string."""
    patch_lines: list[str] = []
    for p in patch_set.items:
        for headline in p.header:
            patch_lines.append(headline.rstrip(b"\n").decode("utf-8"))
        patch_lines.append(f"--- {p.source.decode('utf-8')}")
        patch_lines.append(f"+++ {p.target.decode('utf-8')}")
        for h in p.hunks:
            patch_lines.append(
                f"@@ -{h.startsrc},{h.linessrc} +{h.starttgt},{h.linestgt} @@"
            )
            for line in h.text:
                patch_lines.append(line.rstrip(b"\n").decode("utf-8"))
    return "\n".join(patch_lines)
