from __future__ import annotations

import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "dev docs"
OUTPUT = DOCS / "COMPLETE_PROJECT_SPEC.md"

# Explicit source set: no production snapshots, archived plans or unfrozen drafts.
ORDER = [
    "README.md",
    "CODEX_CONTEXT.md",
    "CODEX_TASK_TEMPLATES.md",
    "REGRESSION_AND_CHANGE_GUARD.md",
    "jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md",
    "IMPLEMENTATION_STATUS.md",
    "operations/DEPLOYMENT_OPTIONS.md",
    "product/PRODUCT_REQUIREMENTS.md",
    "architecture/SYSTEM_ARCHITECTURE.md",
    "architecture/DATA_MODEL.md",
    "product/RECRUITMENT_PIPELINE.md",
    "product/TRAVEL_FOOD_PIPELINE.md",
    "video/VIDEO_AI_NOTE_PIPELINE.md",
    "video/01-scope-upstream.md",
    "video/02-input-transcript.md",
    "video/03-generation-materialization.md",
    "video/04-jobs-data-api.md",
    "video/05-views-safety-acceptance.md",
    "video/VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md",
    "video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md",
    "video/VIDEO_NOTE_LIST_V043_SPEC.md",
    "jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md",
    "video/VIDEO_NOTE_DELETE_V044_SPEC.md",
    "ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md",
    "ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md",
    "jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md",
    "operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md",
    "operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md",
    "jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md",
    "ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md",
    "ai-gateway/AI_RUNTIME_AND_PROVIDERS.md",
    "ai-gateway/AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md",
    "ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md",
    "ai-gateway/01-architecture-models.md",
    "ai-gateway/02-gateway-context.md",
    "ai-gateway/03-pipeline-providers.md",
    "ai-gateway/04-stage-policy.md",
    "ai-gateway/05-job-policy.md",
    "ai-gateway/06-rollout-acceptance.md",
    "product/CONTROL_CENTER.md",
    "operations/OPERATIONS_UI_SPEC.md",
    "architecture/API_DESIGN.md",
    "architecture/SECURITY_PRIVACY.md",
    "testing/TESTING_AND_ACCEPTANCE.md",
    "operations/LOGGING.md",
    "architecture/ARCHITECTURE_DECISIONS.md",
    "testing/GOLDEN_SAMPLES.md",
]


def rebase_parent_links(body: str, name: str) -> str:
    """Rebase local links, including siblings, to the generated file's directory."""
    def replace(match: re.Match[str]) -> str:
        if match[1] is not None:  # Literal code examples are not navigation links.
            return match[0]
        target = urlsplit(match[2])
        if target.scheme or target.netloc or not target.path or target.path.startswith("/"):
            return match[0]
        path = posixpath.normpath(posixpath.join(posixpath.dirname(name), target.path))
        return "](" + urlunsplit(target._replace(path=path)) + ")"

    return re.sub(r"(```[\s\S]*?```|`[^`\n]*`)|\]\(([^)\s]+)\)", replace, body)


def build() -> str:
    sections = [
        "# AI Personal Inbox / Personal Scout\n",
        "## Complete Project Specification\n\n",
        (
            "> GENERATED FILE. Edit the source documents in this directory, then run "
            "`.venv/bin/python scripts/build_complete_project_spec.py`.\n"
        ),
    ]
    for name in ORDER:
        source = DOCS / name
        body = source.read_text(encoding="utf-8").rstrip()
        body = rebase_parent_links(body, name)
        sections.append(f"\n\n---\n\n# FILE: {name}\n\n{body}\n")
    return "".join(sections)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
