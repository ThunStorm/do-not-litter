"""Run with .venv/bin/python scripts/test_build_complete_project_spec.py."""

import unittest

from build_complete_project_spec import DOCS, ORDER, OUTPUT, build, rebase_parent_links


class CompleteSpecTests(unittest.TestCase):
    def test_nested_parent_links(self):
        self.assertEqual(
            rebase_parent_links(
                "[status](../IMPLEMENTATION_STATUS.md) [root](../../README.md)",
                "video/input.md",
            ),
            "[status](IMPLEMENTATION_STATUS.md) [root](../README.md)",
        )
        self.assertEqual(
            rebase_parent_links("[root](../README.md)", "README.md"),
            "[root](../README.md)",
        )

    def test_source_set(self):
        self.assertEqual(len(ORDER), len(set(ORDER)))
        self.assertTrue(all((DOCS / name).is_file() for name in ORDER))
        self.assertFalse(any(name.startswith(("history/", "planning/")) for name in ORDER))
        for excluded in (
            "CURRENT_HANDOFF.md",
            "planning/FUTURE_ROADMAP.md",
            "PROJECT_PLAN.md",
            "planning/PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md",
            "LOGGING_ARCHITECTURE.md",
            "LOGGING_IMPLEMENTATION.md",
        ):
            self.assertNotIn(excluded, ORDER)

    def test_generated_file_is_current(self):
        self.assertEqual(OUTPUT.read_text(encoding="utf-8"), build())

    def test_nested_sibling_links(self):
        self.assertEqual(
            rebase_parent_links(
                "[part](02-input-transcript.md#input) [web](https://example.com/a) "
                "[anchor](#local) [root](/root.md)",
                "video/VIDEO_AI_NOTE_PIPELINE.md",
            ),
            "[part](video/02-input-transcript.md#input) [web](https://example.com/a) "
            "[anchor](#local) [root](/root.md)",
        )

    def test_literal_link_examples_are_unchanged(self):
        body = "Markdown `[title](URL)`\n```md\n[title](file.md)\n```"
        self.assertEqual(rebase_parent_links(body, "video/input.md"), body)


if __name__ == "__main__":
    unittest.main()
