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
VALUES_KEYS_1_9_12 = {
    "affinity", "credentials", "credentials.create", "credentials.host", "credentials.license",
    "credentials.port", "dcgmExporter", "dcgmExporter.configMap", "dcgmExporter.configMap.customMetrics",
    "dcgmExporter.configMap.enabled", "dcgmExporter.configMap.extraMetrics", "env", "image",
    "image.digest", "image.pullPolicy", "image.repository", "image.tag", "imagePullSecret",
    "imagePullSecret.name", "managedResources", "managedResources.agentConfigMaps",
    "managedResources.masterService", "managedResources.rbac", "managedResources.serviceAccounts",
    "namespace", "nodeName", "nodeSelector", "priorityClassName", "tolerations",
}
TEMPLATES_1_9_12 = {
    "agent-clusterrole.yaml", "agent-clusterrolebinding.yaml", "agent-master-configmap.yaml",
    "agent-master-service.yaml", "agent-node-configmap.yaml", "agent-serviceaccount.yaml",
    "crd-whatapagents.yaml", "crd-whatappodmonitors.yaml", "crd-whatapservicemonitors.yaml",
    "crd-whatapstaticendpoints.yaml", "gpu-configmap.yaml", "operator-clusterrole.yaml",
    "operator-clusterrolebinding.yaml", "operator-deployment.yaml", "operator-serviceaccount.yaml",
    "secret-whatap-credentials.yaml",
}
PREVIOUS_RELEASE_ARCHIVE = "whatap-operator-1.9.14.tgz"


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

    def test_chart_defaults_to_operator_3_0_26(self):
        chart_metadata = yaml.safe_load((CHART / "Chart.yaml").read_text())
        values = yaml.safe_load((CHART / "values.yaml").read_text())

        self.assertEqual("1.9.15", chart_metadata["version"])
        self.assertEqual("3.0.26", chart_metadata["appVersion"])
        self.assertEqual("3.0.26", values["image"]["tag"])

    def test_values_and_template_structure_are_unchanged_since_1_9_12(self):
        # Users who patch the chart re-apply their edits on every upgrade. Changing this
        # structure must be a deliberate, documented decision rather than a side effect.
        def key_paths(node, prefix=""):
            paths = set()
            if isinstance(node, dict):
                for key, value in node.items():
                    path = f"{prefix}.{key}" if prefix else key
                    paths.add(path)
                    paths |= key_paths(value, path)
            return paths

        values = yaml.safe_load((CHART / "values.yaml").read_text())
        self.assertEqual(VALUES_KEYS_1_9_12, key_paths(values))
        templates = {path.name for path in (CHART / "templates").iterdir() if path.is_file()}
        self.assertEqual(TEMPLATES_1_9_12, templates)

    def test_changes_since_previous_release_are_image_and_additive_crd_only(self):
        def by_object(chart_path):
            result = subprocess.run(
                ["helm", "template", "whatap-operator", str(chart_path), "--namespace", "whatap-monitoring"],
                check=True, capture_output=True, text=True,
            )
            documents = [document for document in yaml.safe_load_all(result.stdout) if document]
            return {(document["kind"], document["metadata"]["name"]): document for document in documents}

        def is_additive(old, new):
            if isinstance(old, dict) and isinstance(new, dict):
                return all(key in new and is_additive(value, new[key]) for key, value in old.items())
            if isinstance(old, list) and isinstance(new, list):
                return len(old) == len(new) and all(is_additive(a, b) for a, b in zip(old, new))
            return old == new

        previous = by_object(REPOSITORY / PREVIOUS_RELEASE_ARCHIVE)
        current = by_object(CHART)
        self.assertEqual(set(previous), set(current))
        crd_key = ("CustomResourceDefinition", "whatapagents.monitoring.whatap.com")
        changed = {key for key in previous if previous[key] != current[key]}
        self.assertEqual({("Deployment", "whatap-operator")}, changed - {crd_key})

        old_deployment = previous[("Deployment", "whatap-operator")]
        new_deployment = current[("Deployment", "whatap-operator")]
        self.assertEqual(
            "public.ecr.aws/whatap/whatap-operator:3.0.26",
            new_deployment["spec"]["template"]["spec"]["containers"][0]["image"],
        )
        new_deployment["spec"]["template"]["spec"]["containers"][0]["image"] = (
            old_deployment["spec"]["template"]["spec"]["containers"][0]["image"]
        )
        self.assertEqual(old_deployment, new_deployment)
        self.assertTrue(is_additive(previous[crd_key], current[crd_key]), "CRD changes must only add fields")

    def test_crd_exposes_kubevirt_and_network_agent_disabled_by_default(self):
        crd = next(
            document
            for document in self.render()
            if document["kind"] == "CustomResourceDefinition"
            and document["metadata"]["name"] == "whatapagents.monitoring.whatap.com"
        )
        version = next(version for version in crd["spec"]["versions"] if version["name"] == "v2alpha1")
        features = version["schema"]["openAPIV3Schema"]["properties"]["spec"]["properties"]["features"]["properties"]

        kubevirt = features["kubeVirt"]
        self.assertIs(False, kubevirt["properties"]["enabled"]["default"])
        target = kubevirt["properties"]["targets"]["items"]
        self.assertEqual(["host", "name", "namespace", "vmSelector"], sorted(target["required"]))
        for field in ("license", "licenseSecretRef", "port", "enabled"):
            self.assertIn(field, target["properties"])
        agent_version = target["properties"]["agentVersion"]
        # Omitted means "the operator's built-in default", resolved at VM creation.
        self.assertNotIn("default", agent_version)
        self.assertEqual(32, agent_version["maxLength"])
        self.assertRegex("2.9.25", agent_version["pattern"])
        for invalid in ("latest", "v2.9.25", "2.9"):
            self.assertNotRegex(invalid, agent_version["pattern"])

        self.assertIs(False, features["networkAgent"]["properties"]["enabled"]["default"])

    def test_readme_documents_1_9_15_upgrade(self):
        readme = (CHART / "README.md").read_text()
        for required_text in (
            "1.9.15", "3.0.26", "--set-string image.tag=3.0.26", "CRD는 1.9.14와 같습니다",
            "APMInjectionWebhookUnreachable", "APMInjectionMissing", "apm-probe.monitoring.whatap.com",
            "Pod: `create`",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, readme)

    def test_readme_documents_1_9_14_upgrade(self):
        readme = (CHART / "README.md").read_text()
        for required_text in (
            "1.9.14", "3.0.25", "--set-string image.tag=3.0.25", "agentVersion: 2.9.25",
            "kubectl edit whatapagent whatap", "virtualmachineinstances",
            "values와 템플릿 구조는 1.9.12와 같습니다",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, readme)

    def test_readme_documents_1_9_13_upgrade(self):
        readme = (CHART / "README.md").read_text()
        for required_text in (
            "1.9.13", "3.0.24", "--set-string image.tag=3.0.24",
            "spec.features.kubeVirt", "kubectl explain whatapagent.spec.features.kubeVirt",
            "values와 템플릿 구조는 1.9.12와 같습니다",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, readme)

    def test_crd_exposes_optional_gpu_pod_resources_path(self):
        crd = next(
            document
            for document in self.render()
            if document["kind"] == "CustomResourceDefinition"
            and document["metadata"]["name"] == "whatapagents.monitoring.whatap.com"
        )
        version = next(version for version in crd["spec"]["versions"] if version["name"] == "v2alpha1")
        properties = version["schema"]["openAPIV3Schema"]["properties"]
        gpu = properties["spec"]["properties"]["features"]["properties"]["k8sAgent"]["properties"]["gpuMonitoring"]
        self.assertIn("podResourcesPath", gpu["properties"])
        field = gpu["properties"]["podResourcesPath"]
        self.assertEqual("string", field["type"])
        self.assertNotIn("podResourcesPath", gpu.get("required", []))
        for valid in ("", "/var/lib/kubelet/pod-resources", "/repo.p/kubelet/pod-resources"):
            self.assertRegex(valid, field["pattern"])
        self.assertNotRegex("relative/pod-resources", field["pattern"])

    def test_readme_documents_gpu_path_and_image_upgrade(self):
        readme = (CHART / "README.md").read_text()
        for required_text in (
            "1.9.11", "3.0.20", "podResourcesPath",
            "/repo.p/kubelet/pod-resources", "--set-string image.tag=3.0.20",
            "--set-string image.digest=", "kubectl explain",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, readme)

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
