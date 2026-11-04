import unittest
from pathlib import Path

import yaml

from verify_action_pinning import find_uses, is_pinned


START_MARKER = "# BEGIN verify_action_pinning.py"
END_MARKER = "# END verify_action_pinning.py"


class IsPinnedTests(unittest.TestCase):
    def test_local_actions_are_allowed(self):
        for uses in ("./local/action", "$/local/action"):
            with self.subTest(uses=uses):
                self.assertTrue(is_pinned(uses))

    def test_internal_actions_require_a_ref_but_allow_tags(self):
        for uses in (
            "3lvia/action@latest",
            "3lvia/action@v1",
            "3LVIA/action@trunk",
        ):
            with self.subTest(uses=uses):
                self.assertTrue(is_pinned(uses))

        self.assertFalse(is_pinned("3lvia/action"))
        self.assertFalse(is_pinned("3lvia/@latest"))

    def test_external_actions_require_a_full_sha(self):
        self.assertTrue(is_pinned(f"external/action@{'a' * 40}"))
        self.assertTrue(is_pinned(f"external/action/path@{'A' * 40}"))
        self.assertFalse(is_pinned("external/action@v1"))
        self.assertFalse(is_pinned(f"external/action@{'a' * 39}"))

    def test_docker_actions_require_a_sha256_digest(self):
        self.assertTrue(is_pinned(f"docker://image@sha256:{'b' * 64}"))
        self.assertFalse(is_pinned("docker://image:latest"))
        self.assertFalse(is_pinned(f"docker://image@sha256:{'b' * 63}"))

    def test_malformed_action_references_are_rejected(self):
        for uses in ("malformed", "owner@", "owner/repo@"):
            with self.subTest(uses=uses):
                self.assertFalse(is_pinned(uses))

    def test_find_uses_recursively_collects_action_references(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"uses": "./local"},
                    ]
                }
            }
        }

        self.assertEqual(
            list(find_uses(workflow)),
            ["actions/checkout@v4", "./local"],
        )

    def test_policy_workflow_contains_the_tested_script(self):
        workflow_path = Path(__file__).parents[1] / "workflows" / "verify-action-pinning.yml"
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        run = next(
            step["run"]
            for step in workflow["jobs"]["verify"]["steps"]
            if step.get("name") == "Validate workflows"
        )
        lines = run.splitlines()
        start = [index for index, line in enumerate(lines) if line == START_MARKER]
        end = [index for index, line in enumerate(lines) if line == END_MARKER]

        self.assertEqual(len(start), 1)
        self.assertEqual(len(end), 1)
        self.assertLess(start[0], end[0])

        embedded_script = "\n".join(lines[start[0] + 1 : end[0]])
        tested_script = Path(__file__).with_name("verify_action_pinning.py")
        self.assertEqual(
            embedded_script,
            tested_script.read_text(encoding="utf-8").rstrip("\n"),
        )


if __name__ == "__main__":
    unittest.main()
