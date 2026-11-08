from __future__ import annotations

import re
from importlib.resources import files
from typing import Any

SOURCE_REPOSITORY = "msitarzewski/agency-agents"
SOURCE_REVISION = "b859c515d813efcfc4755d3471dd9e7686c7706d"

_PROFILES = (
    ("software-architect", "engineering", "engineering-software-architect.md"),
    ("backend-architect", "engineering", "engineering-backend-architect.md"),
    ("desktop-app-engineer", "engineering", "engineering-desktop-app-engineer.md"),
    ("ai-engineer", "engineering", "engineering-ai-engineer.md"),
    (
        "multi-agent-systems-architect",
        "engineering",
        "engineering-multi-agent-systems-architect.md",
    ),
    (
        "minimal-change-engineer",
        "engineering",
        "engineering-minimal-change-engineer.md",
    ),
    ("code-reviewer", "engineering", "engineering-code-reviewer.md"),
    ("privacy-engineer", "engineering", "engineering-privacy-engineer.md"),
    ("test-automation-engineer", "testing", "testing-test-automation-engineer.md"),
    (
        "project-shepherd",
        "project-management",
        "project-management-project-shepherd.md",
    ),
)
_PROFILE_BY_ID = {profile[0]: profile for profile in _PROFILES}
_METADATA_LINE = re.compile(r"^(name|description):\s*(.*?)\s*$")


class AgentProfileNotFoundError(LookupError):
    pass


def list_agent_profiles() -> list[dict[str, Any]]:
    return [_read_profile_metadata(profile) for profile in _PROFILES]


def get_agent_profile(profile_id: str) -> dict[str, Any]:
    profile = _PROFILE_BY_ID.get(profile_id)
    if profile is None:
        raise AgentProfileNotFoundError(profile_id)
    content = _read_profile(profile[2])
    return {
        **_profile_metadata(profile, content),
        "profile_markdown": content,
    }


def _read_profile_metadata(profile: tuple[str, str, str]) -> dict[str, Any]:
    return _profile_metadata(profile, _read_profile(profile[2]))


def _read_profile(filename: str) -> str:
    return (
        files("app.control_plane.agency_profiles")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


def _profile_metadata(
    profile: tuple[str, str, str], content: str
) -> dict[str, Any]:
    frontmatter = _extract_frontmatter(content)
    metadata: dict[str, str] = {}
    for line in frontmatter.splitlines():
        match = _METADATA_LINE.fullmatch(line.strip())
        if match:
            metadata[match.group(1)] = match.group(2)
    if not metadata.get("name") or not metadata.get("description"):
        raise RuntimeError(f"Agent profile metadata is incomplete: {profile[2]}")

    profile_id, division, filename = profile
    return {
        "id": profile_id,
        "name": metadata["name"],
        "description": metadata["description"],
        "division": division,
        "source_repository": SOURCE_REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "source_file": f"{division}/{filename}",
        "source_url": (
            f"https://github.com/{SOURCE_REPOSITORY}/blob/"
            f"{SOURCE_REVISION}/{division}/{filename}"
        ),
        "source_license": "MIT",
        "enabled": False,
        "execution_enabled": False,
        "capabilities": [],
        "tools": [],
    }


def _extract_frontmatter(content: str) -> str:
    if not content.startswith("---\n"):
        raise RuntimeError("Agent profile is missing YAML frontmatter.")
    frontmatter, separator, _ = content[4:].partition("\n---")
    if not separator:
        raise RuntimeError("Agent profile frontmatter is not terminated.")
    return frontmatter
