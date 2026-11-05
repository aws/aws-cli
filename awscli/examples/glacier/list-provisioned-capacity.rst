**To retrieve the provisioned capacity units**

The following ``list-provisioned-capacity`` example retrieves details for any provisioned capacity units for the specified account. ::

    aws glacier list-provisioned-capacity \
        --account-id 123456789012

Output::

    {
        "ProvisionedCapacityList": [
            {
                "CapacityId": "HpASAuvfRFiVDbOjMfEIcr8K",
                "ExpirationDate": "2020-03-18T19:59:24.000Z",
                "StartDate": "2020-02-18T19:59:24.912Z"
            }
        ]
    }

For more information, see `Retrieving Amazon Glacier Archives <https://docs.aws.amazon.com/amazonglacier/latest/dev/downloading-an-archive-two-steps.html>`__ in the *Amazon Glacier Developer Guide*.
