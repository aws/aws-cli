"""
Test runner for the JSON Schema official test suite

Tests comprehensive correctness of each draft's validator.

See https://github.com/json-schema-org/JSON-Schema-Test-Suite for details.
"""

import sys

from jsonschema.tests._helpers import bug
from jsonschema.tests._suite import Suite
import jsonschema

SUITE = Suite()
DRAFT3 = SUITE.version(name="draft3")
DRAFT4 = SUITE.version(name="draft4")
DRAFT6 = SUITE.version(name="draft6")
DRAFT7 = SUITE.version(name="draft7")
DRAFT201909 = SUITE.version(name="draft2019-09")
DRAFT202012 = SUITE.version(name="draft2020-12")


def skip(message, **kwargs):
    def skipper(test):
        if all(value == getattr(test, attr) for attr, value in kwargs.items()):
            return message
    return skipper


def missing_format(checker):
    def missing_format(test):  # pragma: no cover
        schema = test.schema
        if (
            schema is True
            or schema is False
            or "format" not in schema
            or schema["format"] in checker.checkers
            or test.valid
        ):
            return

        return "Format checker {0!r} not found.".format(schema["format"])
    return missing_format


def complex_email_validation(test):
    if test.subject != "email":
        return

    message = "Complex email validation is (intentionally) unsupported."
    return skip(
        message=message,
        description="an invalid domain",
    )(test) or skip(
        message=message,
        description="an invalid IPv4-address-literal",
    )(test) or skip(
        message=message,
        description="dot after local part is not valid",
    )(test) or skip(
        message=message,
        description="dot before local part is not valid",
    )(test) or skip(
        message=message,
        description="two subsequent dots inside local part are not valid",
    )(test)


is_narrow_build = sys.maxunicode == 2 ** 16 - 1
if is_narrow_build:  # pragma: no cover
    message = "Not running surrogate Unicode case, this Python is narrow."

    def narrow_unicode_build(test):  # pragma: no cover
        return skip(
            message=message,
            description=(
                "one supplementary Unicode code point is not long enough"
            ),
        )(test) or skip(
            message=message,
            description="two supplementary Unicode code points is long enough",
        )(test)
else:
    def narrow_unicode_build(test):  # pragma: no cover
        return


if sys.version_info < (3, 9):  # pragma: no cover
    message = "Rejecting leading zeros is 3.9+"
    allowed_leading_zeros = skip(
        message=message,
        subject="ipv4",
        description=(
            "leading zeroes should be rejected, as they are treated as octals"
        ),
    )
else:
    def allowed_leading_zeros(test):  # pragma: no cover
        return


def leap_second(test):
    message = "Leap seconds are unsupported."
    return skip(
        message=message,
        subject="time",
        description="a valid time string with leap second",
    )(test) or skip(
        message=message,
        subject="time",
        description="a valid time string with leap second, Zulu",
    )(test) or skip(
        message=message,
        subject="time",
        description="a valid time string with leap second with offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, positive time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, negative time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, large positive time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, large negative time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, zero time-offset",
    )(test) or skip(
        message=message,
        subject="date-time",
        description="a valid date-time with a leap second, UTC",
    )(test) or skip(
        message=message,
        subject="date-time",
        description="a valid date-time with a leap second, with minus offset",
    )(test)


TestDraft3 = DRAFT3.to_unittest_testcase(
    DRAFT3.tests(),
    DRAFT3.format_tests(),
    DRAFT3.optional_tests_of(name="bignum"),
    DRAFT3.optional_tests_of(name="non-bmp-regex"),
    DRAFT3.optional_tests_of(name="zeroTerminatedFloats"),
    Validator=jsonschema.Draft3Validator,
    format_checker=jsonschema.draft3_format_checker,
    skip=lambda test: (
        narrow_unicode_build(test)
        or missing_format(jsonschema.draft3_format_checker)(test)
        or complex_email_validation(test)
        or skip(
            message=bug(371),
            subject="ref",
            case_description=(
                "$ref prevents a sibling id from changing the base uri"
            ),
        )(test)
    ),
)


TestDraft4 = DRAFT4.to_unittest_testcase(
    DRAFT4.tests(),
    DRAFT4.format_tests(),
    DRAFT4.optional_tests_of(name="bignum"),
    DRAFT4.optional_tests_of(name="float-overflow"),
    DRAFT4.optional_tests_of(name="non-bmp-regex"),
    DRAFT4.optional_tests_of(name="zeroTerminatedFloats"),
    Validator=jsonschema.Draft4Validator,
    format_checker=jsonschema.draft4_format_checker,
    skip=lambda test: (
        narrow_unicode_build(test)
        or allowed_leading_zeros(test)
        or leap_second(test)
        or missing_format(jsonschema.draft4_format_checker)(test)
        or complex_email_validation(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description="Recursive references between schemas",
        )(test)
        or skip(
            message=bug(371),
            subject="ref",
            case_description=(
                "Location-independent identifier with "
                "base URI change in subschema"
            ),
        )(test)
        or skip(
            message=bug(371),
            subject="ref",
            case_description=(
                "$ref prevents a sibling id from changing the base uri"
            ),
        )(test)
        or skip(
            message=bug(371),
            subject="id",
            description="match $ref to id",
        )(test)
        or skip(
            message=bug(371),
            subject="id",
            description="no match on enum or $ref to id",
        )(test)
        or skip(
            message=bug(),
            subject="refRemote",
            case_description="base URI change - change folder in subschema",
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "id must be resolved against nearest parent, "
                "not just immediate parent"
            ),
        )(test)
    ),
)


TestDraft6 = DRAFT6.to_unittest_testcase(
    DRAFT6.tests(),
    DRAFT6.format_tests(),
    DRAFT6.optional_tests_of(name="bignum"),
    DRAFT6.optional_tests_of(name="float-overflow"),
    DRAFT6.optional_tests_of(name="non-bmp-regex"),
    Validator=jsonschema.Draft6Validator,
    format_checker=jsonschema.draft6_format_checker,
    skip=lambda test: (
        narrow_unicode_build(test)
        or allowed_leading_zeros(test)
        or leap_second(test)
        or missing_format(jsonschema.draft6_format_checker)(test)
        or complex_email_validation(test)
        or skip(
            message="id is incorrectly finding non-ids",
            subject="id",
            description="const at const_not_anchor does not match",
        )(test)
        or skip(
            message="id is incorrectly finding non-ids",
            subject="id",
            description="const at const_not_id does not match",
        )(test)
        or skip(
            message=bug(),
            subject="refRemote",
            case_description="base URI change - change folder in subschema",
        )(test)
        or skip(
            message=bug(371),
            subject="ref",
            case_description=(
                "$ref prevents a sibling $id from changing the base uri"
            ),
        )(test)
    ),
)


TestDraft7 = DRAFT7.to_unittest_testcase(
    DRAFT7.tests(),
    DRAFT7.format_tests(),
    DRAFT7.optional_tests_of(name="bignum"),
    DRAFT7.optional_tests_of(name="content"),
    DRAFT7.optional_tests_of(name="float-overflow"),
    DRAFT7.optional_tests_of(name="non-bmp-regex"),
    Validator=jsonschema.Draft7Validator,
    format_checker=jsonschema.draft7_format_checker,
    skip=lambda test: (
        narrow_unicode_build(test)
        or allowed_leading_zeros(test)
        or leap_second(test)
        or missing_format(jsonschema.draft7_format_checker)(test)
        or complex_email_validation(test)
        or skip(
            message=bug(),
            subject="refRemote",
            case_description="base URI change - change folder in subschema",
        )(test)
        or skip(
            message=bug(371),
            subject="ref",
            case_description=(
                "$ref prevents a sibling $id from changing the base uri"
            ),
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "$id must be resolved against nearest parent, "
                "not just immediate parent"
            ),
        )(test)
        or skip(
            message=bug(593),
            subject="content",
            valid=False,
            case_description=(
                "validation of string-encoded content based on media type"
            ),
        )(test)
        or skip(
            message=bug(593),
            subject="content",
            valid=False,
            case_description="validation of binary string-encoding",
        )(test)
        or skip(
            message=bug(593),
            subject="content",
            valid=False,
            case_description=(
                "validation of binary-encoded media type documents"
            ),
        )(test)
    ),
)


TestDraft201909 = DRAFT201909.to_unittest_testcase(
    DRAFT201909.tests(),
    DRAFT201909.optional_tests_of(name="bignum"),
    DRAFT201909.optional_tests_of(name="float-overflow"),
    DRAFT201909.optional_tests_of(name="non-bmp-regex"),
    DRAFT201909.optional_tests_of(name="refOfUnknownKeyword"),
    Validator=jsonschema.Draft201909Validator,
    skip=lambda test: (
        skip(
            message="unevaluatedItems is different in 2019-09 (needs work).",
            subject="unevaluatedItems",
        )(test)
        or skip(
            message="dynamicRef support isn't working yet.",
            subject="recursiveRef",
        )(test)
        or skip(
            message="These tests depends on dynamicRef working.",
            subject="id",
            case_description=(
                "Invalid use of fragments in location-independent $id"
            ),
        )(test)
        or skip(
            message="These tests depends on dynamicRef working.",
            subject="defs",
            description="invalid definition schema",
        )(test)
        or skip(
            message="These tests depends on dynamicRef working.",
            subject="anchor",
            case_description="same $anchor with different base uri",
        )(test)
        or skip(
            message="Vocabulary support is not yet present.",
            subject="vocabulary",
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "$id must be resolved against nearest parent, "
                "not just immediate parent"
            ),
        )(test)
    ),
)


TestDraft201909Format = DRAFT201909.to_unittest_testcase(
    DRAFT201909.format_tests(),
    Validator=jsonschema.Draft201909Validator,
    format_checker=jsonschema.draft201909_format_checker,
    skip=lambda test: (
        complex_email_validation(test)
        or allowed_leading_zeros(test)
        or leap_second(test)
        or missing_format(jsonschema.draft201909_format_checker)(test)
        or complex_email_validation(test)
    ),
)


TestDraft202012 = DRAFT202012.to_unittest_testcase(
    DRAFT202012.tests(),
    DRAFT202012.optional_tests_of(name="bignum"),
    DRAFT202012.optional_tests_of(name="float-overflow"),
    DRAFT202012.optional_tests_of(name="non-bmp-regex"),
    DRAFT202012.optional_tests_of(name="refOfUnknownKeyword"),
    Validator=jsonschema.Draft202012Validator,
    skip=lambda test: (
        narrow_unicode_build(test)
        or skip(
            message="dynamicRef support isn't working yet.",
            subject="dynamicRef",
        )(test)
        or skip(
            message="These tests depends on dynamicRef working.",
            subject="defs",
        )(test)
        or skip(
            message="These tests depends on dynamicRef working.",
            subject="anchor",
            case_description="same $anchor with different base uri",
        )(test)
        or skip(
            message="Vocabulary support is not yet present.",
            subject="vocabulary",
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "$id must be resolved against nearest parent, "
                "not just immediate parent"
            ),
        )(test)
    ),
)


TestDraft202012Format = DRAFT202012.to_unittest_testcase(
    DRAFT202012.format_tests(),
    Validator=jsonschema.Draft202012Validator,
    format_checker=jsonschema.draft202012_format_checker,
    skip=lambda test: (
        complex_email_validation(test)
        or allowed_leading_zeros(test)
        or leap_second(test)
        or missing_format(jsonschema.draft202012_format_checker)(test)
        or complex_email_validation(test)
    ),
)
