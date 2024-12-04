from awscli.testutils import unittest
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation import modules

MODULES = "Modules"


class TestPackageModules(unittest.TestCase):

    def setUp(self):
        pass

    def test_merge_props(self):
        original = {"b": "c", "d": {"e": "f", "i": [1, 2, 3]}}
        overrides = {"b": "cc", "d": {"e": "ff", "g": "h", "i": [4, 5]}}
        expect = {"b": "cc", "d": {"e": "ff", "g": "h", "i": [1, 2, 3, 4, 5]}}
        merged = modules.merge_props(original, overrides)
        self.assertEqual(merged, expect)
        # TODO: More complex examples (especially merging Policies)

    def test_main(self):
        base = "tests/unit/customizations/cloudformation/modules"
        t = modules.read_source(f"{base}/basic-template.yaml")
        td = yamlhelper.yaml_parse(t)
        e = modules.read_source(f"{base}/basic-expect.yaml")

        for module_name, module_config in td[MODULES].items():
            module_config[modules.NAME] = module_name
            relative_path = module_config[modules.SOURCE]
            module_config[modules.SOURCE] = f"{base}/{relative_path}"
            module = modules.Module(td, module_config)
            td2 = module.process()
            t2 = yamlhelper.yaml_dump(td2)
            self.assertEqual(e, t2)
