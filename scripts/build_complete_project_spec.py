from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "dev docs"
OUTPUT = DOCS / "COMPLETE_PROJECT_SPEC.md"

ORDER = [
    "README.md",
    "CODEX_CONTEXT.md",
    "CODEX_TASK_TEMPLATES.md",
    "REGRESSION_AND_CHANGE_GUARD.md",
    "TASK_STATUS_AND_BEIJING_TIME_SPEC.md",
    "IMPLEMENTATION_STATUS.md",
    "DEPLOYMENT_OPTIONS.md",
    "PRODUCT_REQUIREMENTS.md",
    "SYSTEM_ARCHITECTURE.md",
    "DATA_MODEL.md",
    "RECRUITMENT_PIPELINE.md",
    "TRAVEL_FOOD_PIPELINE.md",
    "VIDEO_AI_NOTE_PIPELINE.md",
    "VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md",
    "VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md",
    "VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md",
    "VIDEO_NOTE_LIST_V043_SPEC.md",
    "PIPELINE_STEP_REPLAY_V044_SPEC.md",
    "VIDEO_NOTE_DELETE_V044_SPEC.md",
    "PROMPT_SUPPLEMENTS_V045_SPEC.md",
    "MODEL_AND_RETENTION_UI_SPEC.md",
    "MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md",
    "RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md",
    "RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md",
    "TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md",
    "AI_RUNTIME_AND_PROVIDERS.md",
    "CONTROL_CENTER.md",
    "OPERATIONS_UI_SPEC.md",
    "API_DESIGN.md",
    "SECURITY_PRIVACY.md",
    "TESTING_AND_ACCEPTANCE.md",
    "LOGGING_ARCHITECTURE.md",
    "LOGGING_IMPLEMENTATION.md",
    "ARCHITECTURE_DECISIONS.md",
    "GOLDEN_SAMPLES.md",
    "FUTURE_ROADMAP.md",
    "PROJECT_PLAN.md",
]


def build() -> str:
    sections = [
        "# AI Personal Inbox / Personal Scout\n",
        "## Complete Project Specification\n\n",
        "> GENERATED FILE. Edit the source documents in this directory, then run "
        "`.venv/bin/python scripts/build_complete_project_spec.py`.\n",
    ]
    for name in ORDER:
        source = DOCS / name
        body = source.read_text(encoding="utf-8").rstrip()
        sections.append(f"\n\n---\n\n# FILE: {name}\n\n{body}\n")
    return "".join(sections)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
