from pathlib import Path
import subprocess
import unittest

import yaml


CHART = Path(__file__).resolve().parents[1] / "charts" / "kube"
OPEN_AGENT_MANIFEST = CHART / "yaml" / "open" / "open-agent.yaml"


def assert_wildcard_non_resource_rules(test, role):
    rules = [rule for rule in role["rules"] if "nonResourceURLs" in rule]
    test.assertGreaterEqual(len(rules), 1, role["metadata"]["name"])
    for rule in rules:
        test.assertEqual(["*"], rule["nonResourceURLs"])


class KubeChartRbacTest(unittest.TestCase):
    def render(self, *extra_args):
        result = subprocess.run(
            [
                "helm",
                "template",
                "whatap-kube",
                str(CHART),
                "--namespace",
                "whatap-monitoring",
                "--set-string",
                "whatap.license=test-license",
                "--set-string",
                "whatap.host=127.0.0.1",
                "--set-string",
                "whatap.port=6600",
                *extra_args,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return [document for document in yaml.safe_load_all(result.stdout) if document]

    def test_default_agent_and_open_agent_allow_all_non_resource_urls(self):
        documents = self.render("--set", "deploymentOpen.enabled=true")
        roles = {
            document["metadata"]["name"]: document
            for document in documents
            if document["kind"] == "ClusterRole"
        }

        assert_wildcard_non_resource_rules(self, roles["whatap"])
        assert_wildcard_non_resource_rules(self, roles["whatap-open-agent-role"])

    def test_chart_version_is_1_13_2(self):
        chart_metadata = yaml.safe_load((CHART / "Chart.yaml").read_text())

        self.assertEqual("1.13.2", chart_metadata["version"])

    def test_packaged_open_agent_manifest_allows_all_non_resource_urls(self):
        documents = [
            document
            for document in yaml.safe_load_all(OPEN_AGENT_MANIFEST.read_text())
            if document
        ]
        roles = [
            document for document in documents if document.get("kind") == "ClusterRole"
        ]

        self.assertGreaterEqual(len(roles), 1)
        for role in roles:
            assert_wildcard_non_resource_rules(self, role)


if __name__ == "__main__":
    unittest.main()
