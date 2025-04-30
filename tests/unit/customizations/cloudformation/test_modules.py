"Tests for module support in the package command"

# pylint: disable=fixme
from awscli.testutils import unittest
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.parse_sub import (
    SubWord,
    WordType,
)
from awscli.customizations.cloudformation.modules.parse_sub import parse_sub
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.constants import (
    process_constants,
    replace_constants,
)
from awscli.customizations.cloudformation.modules.read import (
    read_source,
    get_packaged_module_path,
)
from awscli.customizations.cloudformation.modules.merge import merge_props
from awscli.customizations.cloudformation.modules.process import (
    process_module_section,
)
from tests.unit.customizations.cloudformation.yaml_compare import (
    compare_yaml_strings,
    find_yaml_differences,
)
from tests.unit.customizations.cloudformation.yaml_diff import show_yaml_diff
from tests.unit.customizations.cloudformation.test_yaml_compare import (
    TestYamlCompare,
)

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
        merged = merge_props(original, overrides)
        self.assertEqual(merged, expect)

    # pylint: disable=broad-exception-caught,too-many-locals
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
            "foreach",
            "foreachout",
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
            "outjoin",
            "invoke",
            "zip",
            "same-mod",
            "cond-unres",
            "transform",
            "fnforeach",
            "getatt-map",
            "getatt-map-sub",
            "getatt-map-nested",
            "mappings",
            "flatten",
            "flatten-transform",
            "flatten-groupby",
            "flatten-foreach",
            "flatten-basic",
        ]

        # Collect all errors to report at the end
        errors = []

        for test in tests:
            try:
                t, _ = read_source(f"{base}/{test}-template.yaml")
                td = yamlhelper.yaml_parse(t)
                e, _ = read_source(f"{base}/{test}-expect.yaml")

                constants = process_constants(td)
                if constants is not None:
                    replace_constants(constants, td)

                # Modules section
                td = process_module_section(td, base, t, None, True, True)

                processed = yamlhelper.yaml_dump(td)

                # Check to make sure the expected output and the actual
                # output is equivalent yaml, ignoring key order
                is_equivalent = compare_yaml_strings(e, processed)
                if not is_equivalent:
                    differences = find_yaml_differences(e, processed)
                    error_msg = (
                        f"\n{test} failed: YAML not equivalent\nDifferences:\n"
                    )
                    for diff in differences:
                        error_msg += f"  - {diff}\n"

                    # Add traditional diff output
                    error_msg += "\nYAML Diff:\n"
                    error_msg += show_yaml_diff(e, processed)

                    errors.append(error_msg)
            except Exception as ex:
                errors.append(f"\n{test} failed with exception: {str(ex)}")

        # These tests should fail to package
        bad_tests = ["badref"]
        for test in bad_tests:
            try:
                t, _ = read_source(f"{base}/{test}-template.yaml")
                td = yamlhelper.yaml_parse(t)

                constants = process_constants(td)
                if constants is not None:
                    replace_constants(constants, td)
                td = process_module_section(td, base, t, None, True, True)

                # If we get here, the test didn't fail as expected
                errors.append(f"\n{test} should have failed but didn't")
            except exceptions.InvalidModuleError:
                # This is expected, so no error
                pass
            except Exception as ex:
                # Wrong type of exception
                errors.append(
                    f"\n{test} failed with unexpected exception: {str(ex)}"
                )

        # Report all errors at the end
        if errors:
            error_summary = f"\n\n{len(errors)} test(s) failed:\n"
            error_summary += "\n".join(errors)
            self.fail(error_summary)

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

    def test_yaml_compare(self):
        """Test the YAML comparison function"""

        # Create an instance of the test class
        test_instance = TestYamlCompare()

        # Run a few key tests to verify the comparison function works
        test_instance.test_different_key_order()
        test_instance.test_nested_dictionaries_different_order()
        test_instance.test_lists_different_order()
        test_instance.test_complex_nested_structure()
        test_instance.test_different_values()

    def test_get_packaged_module_path(self):
        "Test converting a package path"
        template = {"Packages": {"abc": {"Source": "package.zip"}}}
        p = get_packaged_module_path(template, "$abc/module.yaml")
        self.assertEqual(p, "package.zip/module.yaml")
