from unittest import TestCase

from jsonschema import validators


class TestDeprecations(TestCase):
    def test_version(self):
        """
        As of v4.0.0, __version__ is deprecated in favor of importlib.metadata.
        """

        with self.assertWarns(DeprecationWarning) as w:
            from jsonschema import __version__  # noqa

        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "Accessing jsonschema.__version__ is deprecated",
            ),
        )

    def test_validators_ErrorTree(self):
        """
        As of v4.0.0, importing ErrorTree from jsonschema.validators is
        deprecated in favor of doing so from jsonschema.exceptions.
        """

        with self.assertWarns(DeprecationWarning) as w:
            from jsonschema.validators import ErrorTree  # noqa

        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "Importing ErrorTree from jsonschema.validators is deprecated",
            ),
        )

    def test_validators_validators(self):
        """
        As of v4.0.0, accessing jsonschema.validators.validators is
        deprecated.
        """

        with self.assertWarns(DeprecationWarning) as w:
            value = validators.validators
        self.assertEqual(value, validators._VALIDATORS)

        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "Accessing jsonschema.validators.validators is deprecated",
            ),
        )

    def test_validators_meta_schemas(self):
        """
        As of v4.0.0, accessing jsonschema.validators.meta_schemas is
        deprecated.
        """

        with self.assertWarns(DeprecationWarning) as w:
            value = validators.meta_schemas
        self.assertEqual(value, validators._META_SCHEMAS)

        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "Accessing jsonschema.validators.meta_schemas is deprecated",
            ),
        )

    def test_RefResolver_in_scope(self):
        """
        As of v4.0.0, RefResolver.in_scope is deprecated.
        """

        resolver = validators.RefResolver.from_schema({})
        with self.assertWarns(DeprecationWarning) as w:
            with resolver.in_scope("foo"):
                pass

        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "jsonschema.RefResolver.in_scope is deprecated ",
            ),
        )

    def test_Validator_is_valid_two_arguments(self):
        """
        As of v4.0.0, calling is_valid with two arguments (to provide a
        different schema) is deprecated.
        """

        validator = validators.Draft7Validator({})
        with self.assertWarns(DeprecationWarning) as w:
            result = validator.is_valid("foo", {"type": "number"})

        self.assertFalse(result)
        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "Passing a schema to Validator.is_valid is deprecated ",
            ),
        )

    def test_Validator_iter_errors_two_arguments(self):
        """
        As of v4.0.0, calling iter_errors with two arguments (to provide a
        different schema) is deprecated.
        """

        validator = validators.Draft7Validator({})
        with self.assertWarns(DeprecationWarning) as w:
            error, = validator.iter_errors("foo", {"type": "number"})

        self.assertEqual(error.validator, "type")
        self.assertEqual(w.filename, __file__)
        self.assertTrue(
            str(w.warning).startswith(
                "Passing a schema to Validator.iter_errors is deprecated ",
            ),
        )
