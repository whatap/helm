from pathlib import Path
import re
import subprocess
import unittest

import yaml


CHART = Path(__file__).resolve().parents[1] / "charts" / "whatap-operator"
REPOSITORY = CHART.parents[1]
MANAGED_TEMPLATES = (
    "operator-serviceaccount.yaml",
    "operator-clusterrole.yaml",
    "operator-clusterrolebinding.yaml",
    "agent-serviceaccount.yaml",
    "agent-clusterrole.yaml",
    "agent-clusterrolebinding.yaml",
    "agent-node-configmap.yaml",
    "agent-master-configmap.yaml",
    "agent-master-service.yaml",
)
MANAGED_OBJECTS = {
    ("ServiceAccount", "whatap-operator"),
    ("ServiceAccount", "whatap"),
    ("ClusterRole", "whatap-operator"),
    ("ClusterRole", "whatap"),
    ("ClusterRoleBinding", "whatap-operator"),
    ("ClusterRoleBinding", "whatap"),
    ("ConfigMap", "node-start-script"),
    ("ConfigMap", "master-start-script"),
    ("Service", "whatap-master-agent"),
}


class OperatorChartUpgradeSafetyTest(unittest.TestCase):
    def render(self, *extra_args):
        result = subprocess.run(
            ["helm", "template", "whatap-operator", str(CHART), "--namespace", "whatap-monitoring", *extra_args],
            check=True,
            capture_output=True,
            text=True,
        )
        return [document for document in yaml.safe_load_all(result.stdout) if document]

    def test_managed_resources_do_not_depend_on_live_lookup(self):
        offenders = []
        for filename in MANAGED_TEMPLATES:
            text = (CHART / "templates" / filename).read_text()
            if re.search(r"{{[^\n]*\blookup\b", text):
                offenders.append(filename)

        self.assertEqual([], offenders)

    def test_managed_resources_are_rendered_by_default(self):
        documents = self.render()
        rendered = {
            (document["kind"], document.get("metadata", {}).get("name"))
            for document in documents
        }

        self.assertEqual(set(), MANAGED_OBJECTS - rendered)

    def test_missing_managed_resources_map_defaults_to_managed(self):
        documents = self.render("--set-json", "managedResources=null")
        rendered = {
            (document["kind"], document.get("metadata", {}).get("name"))
            for document in documents
        }

        self.assertEqual(set(), MANAGED_OBJECTS - rendered)

    def test_externally_managed_resources_can_be_explicitly_disabled(self):
        documents = self.render(
            "--set", "managedResources.serviceAccounts=false",
            "--set", "managedResources.rbac=false",
            "--set", "managedResources.agentConfigMaps=false",
            "--set", "managedResources.masterService=false",
        )
        rendered = {
            (document["kind"], document.get("metadata", {}).get("name"))
            for document in documents
        }

        self.assertEqual(set(), MANAGED_OBJECTS & rendered)

    def test_image_digest_is_rendered_as_an_optional_value(self):
        documents = self.render(
            "--set", "image.tag=3.0.14",
            "--set", "image.digest=sha256:testdigest",
        )
        deployment = next(
            document
            for document in documents
            if document["kind"] == "Deployment"
            and document["metadata"]["name"] == "whatap-operator"
        )
        image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]

        self.assertEqual(
            "public.ecr.aws/whatap/whatap-operator:3.0.14@sha256:testdigest",
            image,
        )

    def test_chart_defaults_to_operator_3_0_15(self):
        chart_metadata = yaml.safe_load((CHART / "Chart.yaml").read_text())
        values = yaml.safe_load((CHART / "values.yaml").read_text())

        self.assertEqual("1.9.9", chart_metadata["version"])
        self.assertEqual("3.0.15", chart_metadata["appVersion"])
        self.assertEqual("3.0.15", values["image"]["tag"])

    def test_operator_non_resource_urls_default_to_wildcard(self):
        documents = self.render()
        cluster_role = next(
            document
            for document in documents
            if document["kind"] == "ClusterRole"
            and document["metadata"]["name"] == "whatap-operator"
        )
        rules = [rule for rule in cluster_role["rules"] if "nonResourceURLs" in rule]

        self.assertEqual([{"nonResourceURLs": ["*"], "verbs": ["*"]}], rules)

    def test_operator_non_resource_urls_can_be_narrowed(self):
        documents = self.render(
            "--set", "rbac.operator.nonResourceURLs={/metrics,/metrics/slis}",
        )
        cluster_role = next(
            document
            for document in documents
            if document["kind"] == "ClusterRole"
            and document["metadata"]["name"] == "whatap-operator"
        )
        rules = [rule for rule in cluster_role["rules"] if "nonResourceURLs" in rule]

        self.assertEqual(
            [{"nonResourceURLs": ["/metrics", "/metrics/slis"], "verbs": ["*"]}],
            rules,
        )

    def test_operator_non_resource_urls_reject_non_list_values(self):
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            self.render("--set", "rbac.operator.nonResourceURLs=/metrics")

        self.assertIn("must be a list of strings", raised.exception.stderr)

    def test_whatapagent_crd_exposes_open_agent_non_resource_urls(self):
        crd = yaml.safe_load(
            (CHART / "templates" / "crd-whatapagents.yaml").read_text()
        )
        open_agent = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"][
            "properties"
        ]["spec"]["properties"]["features"]["properties"]["openAgent"]["properties"]

        self.assertEqual(
            {"type": "string"}, open_agent["nonResourceURLs"]["items"]
        )
        self.assertEqual("array", open_agent["nonResourceURLs"]["type"])

    def test_readme_documents_safe_upgrade_and_external_resources(self):
        readme = (CHART / "README.md").read_text()

        for required_text in (
            "helm upgrade --install",
            "--take-ownership",
            "managedResources",
            "image.digest",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, readme)

    def test_example_values_do_not_contain_literal_credentials(self):
        for filename in ("custom-values.yaml", "default-values.yaml"):
            values = yaml.safe_load((REPOSITORY / filename).read_text())
            for key in ("license", "host"):
                with self.subTest(filename=filename, key=key):
                    self.assertTrue(
                        values.get("whatap", {}).get(key) in (None, ""),
                        f"{filename}: whatap.{key} must be blank",
                    )


if __name__ == "__main__":
    unittest.main()
