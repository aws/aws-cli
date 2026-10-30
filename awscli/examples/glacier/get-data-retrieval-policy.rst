**To get the data retrieval policy for an account**

The following ``get-data-retrieval-policy`` example gets the data retrieval policy for the in-use account. ::

    aws glacier get-data-retrieval-policy \
        --account-id -

Output::

    {
        "Policy": {
            "Rules": [
                {
                    "BytesPerHour": 10737418240,
                    "Strategy": "BytesPerHour"
                }
            ]
        }
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Amazon Glacier Data Retrieval Policies <https://docs.aws.amazon.com/amazonglacier/latest/dev/data-retrieval-policy.html>`__ in the *Amazon Glacier Developer Guide*.
