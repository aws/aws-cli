"Tests for module support in the package command"

# pylint: disable=fixme
import pytest
from awscli.testutils import unittest
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation import modules
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.parse_sub import SubWord, WordType
from awscli.customizations.cloudformation.parse_sub import parse_sub
from awscli.customizations.cloudformation.module_visitor import Visitor
from awscli.customizations.cloudformation.module_constants import (
    process_constants,
    replace_constants,
)
from awscli.customizations.cloudformation.module_read import read_source

MODULES = "Modules"
RESOURCES = "Resources"
TYPE = "Type"
LOCAL_MODULE = "LocalModule"


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
            "${ ABC }": [SubWord(WordType.REF, "ABC")],
            "${  ABC  }": [SubWord(WordType.REF, "ABC")],
            " ABC ": [SubWord(WordType.STR, " ABC ")],
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

    def test_main(self):
        "Run tests on sample templates that include local modules"

        # pylint: disable=invalid-name
        self.maxDiff = None

        # The tests are in the modules directory.
        # Each test has 3 files:
        # test-template.yaml, test-module.yaml, and test-expect.yaml
        base = "unit/customizations/cloudformation/modules"
        tests = [
            "basic",
            "type",
            "sub",
            "modinmod",
            "output",
            "policy",
            "vpc",
            "map",
            "mapout",
            "conditional",
            "cond-intrinsics",
            "example",
            "getatt",
            "constant",
            "proparray",
            "depends",
            "select",
            "merge",
            "mergetags",
            "insertfile",
            "outsublist",
        ]
        for test in tests:
            t, _ = modules.read_source(f"{base}/{test}-template.yaml")
            td = yamlhelper.yaml_parse(t)
            e, _ = modules.read_source(f"{base}/{test}-expect.yaml")

            constants = process_constants(td)
            if constants is not None:
                replace_constants(constants, td)

            # Modules section
            td = modules.process_module_section(td, base, t, None, True, True)

            processed = yamlhelper.yaml_dump(td)
            self.assertEqual(e, processed, f"{test} failed")

        # These tests should fail to package
        bad_tests = ["badref"]
        for test in bad_tests:
            t, _ = modules.read_source(f"{base}/{test}-template.yaml")
            td = yamlhelper.yaml_parse(t)
            with pytest.raises(exceptions.InvalidModuleError):
                constants = process_constants(td)
                if constants is not None:
                    replace_constants(constants, td)
                td = modules.process_module_section(
                    td, base, t, None, True, True
                )

    def test_visitor(self):
        "Test module_visitor"

        template_dict = {}
        resources = {}
        template_dict["Resources"] = resources
        resources["Bucket"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": "foo",
                "TestList": [
                    "Item0",
                    {"BucketName": "foo"},
                    {"Item2": {"BucketName": "foo"}},
                ],
            },
        }
        v = Visitor(template_dict, None, "")

        def vf(v):
            if isinstance(v.d, str) and v.p is not None:
                if v.k == "BucketName":
                    v.p[v.k] = "bar"

        v.visit(vf)
        self.assertEqual(
            resources["Bucket"]["Properties"]["BucketName"], "bar"
        )
        test_list = resources["Bucket"]["Properties"]["TestList"]
        self.assertEqual(test_list[1]["BucketName"], "bar")
        self.assertEqual(test_list[2]["Item2"]["BucketName"], "bar")

    def test_read_source(self):
        "Test reading a source file"

        base = "unit/customizations/cloudformation/modules"
        _, lines = read_source(f"{base}/example-module.yaml")
        self.assertEqual(lines["Bucket"], 5)
