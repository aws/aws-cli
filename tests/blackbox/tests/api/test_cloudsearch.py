"""CloudSearch commands' requests (upstream tests/functional/cloudsearch)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_define_expression_flattens_expression(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        "cloudsearch define-expression --domain-name abc123 --name foo"
        " --expression 10",
        {
            "DomainName": "abc123",
            "Expression": {"ExpressionName": "foo", "ExpressionValue": "10"},
        },
    )


@pytest.mark.parametrize(
    ("field_type", "options"),
    [
        # An int field's default value is a number, a latlon field's a
        # string.
        pytest.param(
            "int",
            {
                "IntOptions": {
                    "DefaultValue": 10,
                    "SearchEnabled": False,
                    "SourceField": "fieldname123",
                }
            },
            id="flattened",
        ),
        pytest.param(
            "latlon",
            {
                "LatLonOptions": {
                    "DefaultValue": "10",
                    "SearchEnabled": False,
                    "SourceField": "fieldname123",
                }
            },
            id="latlon",
        ),
    ],
)
async def test_define_index_field_flattens_options_by_type(
    api: ApiSession, field_type: str, options: dict[str, object]
) -> None:
    await api.assert_params_for_cmd(
        "cloudsearch define-index-field --domain-name abc123 --name foo"
        f" --type {field_type} --default-value 10 --search-enabled false"
        " --source-field fieldname123",
        {
            "DomainName": "abc123",
            "IndexField": {
                "IndexFieldName": "foo",
                "IndexFieldType": field_type,
                **options,
            },
        },
    )
