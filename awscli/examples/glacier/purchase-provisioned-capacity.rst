**To purchase a provisioned capacity unit**

The following ``purchase-provisioned-capacity`` example purchases a provisioned capacity unit. ::

    aws glacier purchase-provisioned-capacity \
        --account-id 123456789012

Output::

    {
        "capacityId": "HpASAuvfRFiVDbOjMfEIcr8K"
    }

For more information, see `Retrieving Amazon Glacier Archives <https://docs.aws.amazon.com/amazonglacier/latest/dev/downloading-an-archive-two-steps.html>`__ in the *Amazon Glacier Developer Guide*.
