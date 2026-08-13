from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "dev docs"
OUTPUT = DOCS / "COMPLETE_PROJECT_SPEC.md"

ORDER = [
    "README.md",
    "PRODUCT_REQUIREMENTS.md",
    "SYSTEM_ARCHITECTURE.md",
    "DATA_MODEL.md",
    "RECRUITMENT_PIPELINE.md",
    "TRAVEL_FOOD_PIPELINE.md",
    "AI_RUNTIME_AND_PROVIDERS.md",
    "CONTROL_CENTER.md",
    "API_DESIGN.md",
    "SECURITY_PRIVACY.md",
    "TESTING_AND_ACCEPTANCE.md",
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
        "`python scripts/build_complete_project_spec.py`.\n",
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
