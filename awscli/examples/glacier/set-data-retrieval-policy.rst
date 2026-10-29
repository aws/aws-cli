**To set the data retrieval policy for an account**

The following ``set-data-retrieval-policy`` example configures a data retrieval policy for the in-use account. ::

    aws glacier set-data-retrieval-policy \
        --account-id - \
        --policy file://data-retrieval-policy.json

This command produces no output.

``data-retrieval-policy.json`` is a JSON file in the current folder that specifies a data retrieval policy.

Contents of ``data-retrieval-policy.json``::

    {
        "Rules": [
            {
                "Strategy": "BytesPerHour",
                "BytesPerHour": 10737418240
            }
        ]
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

The following ``set-data-retrieval-policy`` example sets the data retrieval policy to ``FreeTier`` using inline JSON. ::

    aws glacier set-data-retrieval-policy \
        --account-id - \
        --policy '{"Rules":[{"Strategy":"FreeTier"}]}'

For more information, see `Amazon Glacier Data Retrieval Policies <https://docs.aws.amazon.com/amazonglacier/latest/dev/data-retrieval-policy.html>`__ in the *Amazon Glacier Developer Guide*.
