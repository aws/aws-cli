from awscli.testutils import unittest
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation import modules

MODULES = "Modules"


class TestPackageModules(unittest.TestCase):

    def setUp(self):
        pass

    def test_main(self):
        base = "tests/unit/customizations/cloudformation/modules"
        t = modules.read_source(f"{base}/basic-template.yaml")
        td = yamlhelper.yaml_parse(t)
        # m = modules.read_source(f"{base}/basic-module.yaml")
        e = modules.read_source(f"{base}/basic-expect.yaml")

        for module_name, module_config in td[MODULES].items():
            module_config[modules.NAME] = module_name
            relative_path = module_config[modules.SOURCE]
            module_config[modules.SOURCE] = f"{base}/{relative_path}"
            module = modules.Module(td, module_config)
            td2 = module.process()
            t2 = yamlhelper.yaml_dump(td2)
            self.assertEqual(e, t2)

        # self.assertEqual(1, 0)
