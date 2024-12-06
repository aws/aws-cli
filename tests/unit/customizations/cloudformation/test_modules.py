"Tests for module support in the package command"

# pylint: disable=fixme

from awscli.testutils import unittest
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation import modules
from awscli.customizations.cloudformation.parse_sub import SubWord, WordType
from awscli.customizations.cloudformation.parse_sub import parse_sub

MODULES = "Modules"


class TestPackageModules(unittest.TestCase):
    "Module tests"

    def setUp(self):
        "Initialize the tests"

    def test_parse_sub(self):
        "Test the parse_sub function"
        cases = {
            "ABC": [SubWord(WordType.STR, "ABC")],
            "ABC-${XYZ}-123": [
                SubWord(WordType.STR, "ABC-"),
                SubWord(WordType.REF, "XYZ"),
                SubWord(WordType.STR, "-123"),
            ],
            "ABC-${!Literal}-1": [SubWord(WordType.STR, "ABC-${Literal}-1")],
            "${ABC}": [SubWord(WordType.REF, "ABC")],
            "${ABC.XYZ}": [SubWord(WordType.GETATT, "ABC.XYZ")],
            "ABC${AWS::AccountId}XYZ": [
                SubWord(WordType.STR, "ABC"),
                SubWord(WordType.AWS, "AccountId"),
                SubWord(WordType.STR, "XYZ"),
            ],
            "BAZ${ABC$XYZ}FOO$BAR": [
                SubWord(WordType.STR, "BAZ"),
                SubWord(WordType.REF, "ABC$XYZ"),
                SubWord(WordType.STR, "FOO$BAR"),
            ],
        }

        for sub, expect in cases.items():
            words = parse_sub(sub, False)
            self.assertEqual(
                len(expect),
                len(words),
                f'"{sub}": words len is {len(words)}, expected {len(expect)}',
            )
            for i, w in enumerate(expect):
                self.assertEqual(
                    words[i].t, w.t, f'"{sub}": got {words[i]}, expected {w}'
                )
                self.assertEqual(
                    words[i].w, w.w, f'"{sub}": got {words[i]}, expected {w}'
                )

        # Invalid strings should fail
        sub = "${AAA"
        with self.assertRaises(Exception, msg=f'"{sub}": should have failed'):
            parse_sub(sub, False)

    def test_merge_props(self):
        "Test the merge_props function"

        original = {"b": "c", "d": {"e": "f", "i": [1, 2, 3]}}
        overrides = {"b": "cc", "d": {"e": "ff", "g": "h", "i": [4, 5]}}
        expect = {"b": "cc", "d": {"e": "ff", "g": "h", "i": [1, 2, 3, 4, 5]}}
        merged = modules.merge_props(original, overrides)
        self.assertEqual(merged, expect)
        # TODO: More complex examples (especially merging Policies)

    def test_main(self):
        "Run tests on sample templates that include local modules"

        # TODO: Port tests over from Rain
        base = "tests/unit/customizations/cloudformation/modules"
        t = modules.read_source(f"{base}/basic-template.yaml")
        td = yamlhelper.yaml_parse(t)
        e = modules.read_source(f"{base}/basic-expect.yaml")

        for module_name, module_config in td[MODULES].items():
            module_config[modules.NAME] = module_name
            relative_path = module_config[modules.SOURCE]
            module_config[modules.SOURCE] = f"{base}/{relative_path}"
            module = modules.Module(td, module_config)
            td = module.process()

        del td[MODULES]
        processed = yamlhelper.yaml_dump(td)
        self.assertEqual(e, processed)
