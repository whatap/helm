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

    def test_default_rbac_allows_all_non_resource_urls(self):
        documents = self.render()

        for role_name in ("whatap-operator", "whatap"):
            role = next(
                document
                for document in documents
                if document["kind"] == "ClusterRole"
                and document["metadata"]["name"] == role_name
            )
            non_resource_rules = [
                rule for rule in role["rules"] if "nonResourceURLs" in rule
            ]
            self.assertEqual(1, len(non_resource_rules), role_name)
            self.assertEqual(["*"], non_resource_rules[0]["nonResourceURLs"])

    def test_crd_exposes_open_agent_non_resource_urls(self):
        documents = self.render()
        crd = next(
            document
            for document in documents
            if document["kind"] == "CustomResourceDefinition"
            and document["metadata"]["name"] == "whatapagents.monitoring.whatap.com"
        )
        properties = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]
        field = properties["spec"]["properties"]["features"]["properties"]["openAgent"]["properties"]["nonResourceURLs"]

        self.assertEqual("array", field["type"])
        self.assertEqual("string", field["items"]["type"])
        self.assertIn('Defaults to ["*"]', field["description"])

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
            "--set", "image.tag=3.0.19",
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
            "public.ecr.aws/whatap/whatap-operator:3.0.19@sha256:testdigest",
            image,
        )

    def test_chart_defaults_to_operator_3_0_19(self):
        chart_metadata = yaml.safe_load((CHART / "Chart.yaml").read_text())
        values = yaml.safe_load((CHART / "values.yaml").read_text())

        self.assertEqual("1.9.10", chart_metadata["version"])
        self.assertEqual("3.0.19", chart_metadata["appVersion"])
        self.assertEqual("3.0.19", values["image"]["tag"])

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
