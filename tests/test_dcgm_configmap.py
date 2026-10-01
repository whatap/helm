from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CHARTS = ("whatap-operator", "kube")
CONFIG_MAP_NAME = "dcgm-exporter-csv"
CSV_KEY = "whatap-gpu.csv"
NAMESPACE = "dcgm-test"
BASELINE_ARCHIVES = {
    "whatap-operator": "whatap-operator-1.9.11.tgz",
    "kube": "kube-1.13.2.tgz",
}
EXTRA_METRICS = (
    "DCGM_FI_DEV_APP_SM_CLOCK, gauge, Application SM clock frequency (in MHz).\n"
    "DCGM_FI_DEV_APP_MEM_CLOCK, gauge, Application memory clock frequency (in MHz)."
)
CUSTOM_METRICS = (
    "# Minimal metrics selected by the user\n"
    "DCGM_FI_DEV_GPU_UTIL, gauge, GPU utilization (in %).\n"
    "DCGM_FI_DEV_FB_USED, gauge, Used framebuffer memory (in MiB)."
)


def render(chart_name, config=None, chart_path=None, gpu_enabled=True, extra_values=None):
    values = {}
    if config is not None:
        values["dcgmExporter"] = {"configMap": config}
    if chart_name == "kube":
        values["whatap"] = {"createSecret": False}
        values["addon"] = {"gpu": {"enabled": gpu_enabled}}
    if extra_values:
        values.update(extra_values)
    return subprocess.run(
        [
            "helm", "template", "dcgm-test",
            str(chart_path or ROOT / "charts" / chart_name),
            "--namespace", NAMESPACE, "--values", "-",
        ],
        input=yaml.safe_dump(values),
        capture_output=True,
        text=True,
        env={**os.environ, "KUBECONFIG": os.devnull},
        timeout=30,
    )


def is_dcgm_configmap(document):
    return (
        document["kind"] == "ConfigMap"
        and document["metadata"]["name"] == CONFIG_MAP_NAME
    )


class DcgmConfigMapTest(unittest.TestCase):
    def documents(self, chart_name, config=None, **kwargs):
        result = render(chart_name, config, **kwargs)
        self.assertEqual(0, result.returncode, result.stderr)
        return [document for document in yaml.safe_load_all(result.stdout) if document]

    def csv(self, chart_name, config=None, **kwargs):
        configmaps = [
            doc for doc in self.documents(chart_name, config, **kwargs)
            if is_dcgm_configmap(doc)
        ]
        self.assertEqual(1, len(configmaps))
        self.assertEqual(NAMESPACE, configmaps[0]["metadata"]["namespace"])
        self.assertEqual({CSV_KEY}, set(configmaps[0]["data"]))
        return configmaps[0]["data"][CSV_KEY]

    def test_disable_omits_only_dcgm_configmap(self):
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                default = self.documents(chart_name)
                self.assertEqual(1, sum(is_dcgm_configmap(doc) for doc in default))
                disabled = self.documents(chart_name, {"enabled": False})
                self.assertTrue(
                    [doc for doc in default if not is_dcgm_configmap(doc)] == disabled,
                    "Disabling the DCGM ConfigMap must leave all other resources unchanged",
                )

    def test_defaults_preserve_published_csv_exactly(self):
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                baseline = self.csv(chart_name, chart_path=ROOT / BASELINE_ARCHIVES[chart_name])
                self.assertEqual(baseline, self.csv(chart_name))

    def test_extra_metrics_append_to_unchanged_defaults(self):
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                baseline = self.csv(chart_name, chart_path=ROOT / BASELINE_ARCHIVES[chart_name])
                actual = self.csv(chart_name, {"extraMetrics": EXTRA_METRICS})
                self.assertEqual(baseline + "\n" + EXTRA_METRICS, actual)

    def test_custom_metrics_replace_defaults(self):
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                actual = self.csv(chart_name, {"customMetrics": CUSTOM_METRICS})
                self.assertEqual(CUSTOM_METRICS, actual)

    def test_extra_metrics_append_to_custom_base_when_both_are_set(self):
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                actual = self.csv(chart_name, {
                    "customMetrics": CUSTOM_METRICS,
                    "extraMetrics": EXTRA_METRICS,
                })
                self.assertEqual(CUSTOM_METRICS + "\n" + EXTRA_METRICS, actual)

    def test_invalid_option_types_are_rejected_by_schema(self):
        invalid_configs = (
            {"enabled": "false"}, {"enabled": 0},
            {"customMetrics": False}, {"customMetrics": []},
            {"extraMetrics": False}, {"extraMetrics": {"metric": "value"}},
        )
        for chart_name in CHARTS:
            for config in invalid_configs:
                with self.subTest(chart=chart_name, config=config):
                    result = render(chart_name, config)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("dcgmExporter.configMap", result.stderr)
                    self.assertIn("Invalid type", result.stderr)
            for value in (False, "disabled", []):
                with self.subTest(chart=chart_name, dcgmExporter=value):
                    result = render(chart_name, extra_values={"dcgmExporter": value})
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("Invalid type", result.stderr)

    def test_gpu_disabled_never_renders_exporter_or_configmap(self):
        for enabled in (False, True):
            with self.subTest(configmap_enabled=enabled):
                docs = self.documents("kube", {"enabled": enabled}, gpu_enabled=False)
                self.assertFalse(any(is_dcgm_configmap(doc) for doc in docs))
                daemonset = next(doc for doc in docs if doc["kind"] == "DaemonSet")
                pod = daemonset["spec"]["template"]["spec"]
                self.assertNotIn("dcgm-exporter", [item["name"] for item in pod["containers"]])
                self.assertNotIn(CONFIG_MAP_NAME, [
                    item.get("configMap", {}).get("name") for item in pod["volumes"]
                ])

    def test_missing_legacy_defaults_and_partial_maps_remain_compatible(self):
        legacy_values = (
            {}, {"dcgmExporter": {}}, {"dcgmExporter": {"configMap": {}}},
            {"dcgmExporter": {"configMap": {"extraMetrics": EXTRA_METRICS}}},
        )
        for chart_name in CHARTS:
            baseline = self.csv(chart_name)
            with tempfile.TemporaryDirectory() as directory:
                chart = Path(directory) / chart_name
                shutil.copytree(ROOT / "charts" / chart_name, chart)
                values_path = chart / "values.yaml"
                original = yaml.safe_load(values_path.read_text())
                original.pop("dcgmExporter")
                for legacy in legacy_values:
                    with self.subTest(chart=chart_name, legacy=legacy):
                        values_path.write_text(yaml.safe_dump({**original, **legacy}))
                        expected = baseline
                        if legacy.get("dcgmExporter", {}).get("configMap", {}).get("extraMetrics"):
                            expected += "\n" + EXTRA_METRICS
                        self.assertEqual(expected, self.csv(chart_name, chart_path=chart))

    def test_empty_or_whitespace_overrides_preserve_defaults(self):
        for chart_name in CHARTS:
            baseline = self.csv(chart_name)
            for empty in ("", " \n\n "):
                with self.subTest(chart=chart_name, empty=empty):
                    self.assertEqual(baseline, self.csv(chart_name, {
                        "enabled": True, "customMetrics": empty, "extraMetrics": empty,
                    }))

    def test_metrics_are_literal_data_not_helm_templates(self):
        metrics = "# {{ fail \"must not execute\" }}\n" + CUSTOM_METRICS
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                self.assertEqual(metrics, self.csv(chart_name, {"customMetrics": metrics}))

    def test_new_options_do_not_change_other_default_resources(self):
        for chart_name in CHARTS:
            with self.subTest(chart=chart_name):
                baseline = self.documents(chart_name, chart_path=ROOT / BASELINE_ARCHIVES[chart_name])
                actual = self.documents(chart_name, {
                    "customMetrics": CUSTOM_METRICS, "extraMetrics": EXTRA_METRICS,
                })
                self.assertTrue(
                    [doc for doc in baseline if not is_dcgm_configmap(doc)]
                    == [doc for doc in actual if not is_dcgm_configmap(doc)],
                    "Unrelated resources changed compared with the published chart",
                )

    def test_packaged_options_match_source(self):
        configs = (
            None, {"enabled": False}, {"extraMetrics": EXTRA_METRICS},
            {"customMetrics": CUSTOM_METRICS},
            {"customMetrics": CUSTOM_METRICS, "extraMetrics": EXTRA_METRICS},
        )
        for chart_name in CHARTS:
            metadata = yaml.safe_load((ROOT / "charts" / chart_name / "Chart.yaml").read_text())
            archive = ROOT / (chart_name + "-" + metadata["version"] + ".tgz")
            for config in configs:
                with self.subTest(chart=chart_name, config=config):
                    self.assertTrue(
                        self.documents(chart_name, config)
                        == self.documents(chart_name, config, chart_path=archive),
                        "Packaged options differ from chart source",
                    )

    def test_readme_configuration_examples_render_as_documented(self):
        for chart_name in CHARTS:
            readme = (ROOT / "charts" / chart_name / "README.md").read_text()
            examples = [
                yaml.safe_load(block)
                for block in re.findall(r"```yaml\n(.*?)\n```", readme, re.DOTALL)
                if "dcgmExporter:" in block
            ]
            self.assertGreaterEqual(len(examples), 3)
            for values in examples:
                with self.subTest(chart=chart_name, values=values):
                    config = values["dcgmExporter"]["configMap"]
                    if config.get("enabled") is False:
                        docs = self.documents(chart_name, extra_values=values)
                        self.assertFalse(any(is_dcgm_configmap(doc) for doc in docs))
                        continue
                    base = config.get("customMetrics", "").strip() or self.csv(chart_name)
                    extra = config.get("extraMetrics", "").strip()
                    expected = base + ("\n" + extra if extra else "")
                    self.assertEqual(expected, self.csv(chart_name, extra_values=values))


if __name__ == "__main__":
    unittest.main()