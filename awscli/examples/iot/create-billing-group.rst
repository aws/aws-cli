**To create a billing group**

The following ``create-billing-group`` example creates a simple billing group named ``GroupOne``. ::

    aws iot create-billing-group \
        --billing-group-name GroupOne

Output::

    {
        "billingGroupName": "GroupOne",
        "billingGroupArn": "arn:aws:iot:us-west-2:123456789012:billinggroup/GroupOne",
        "billingGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Billing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/tagging-iot-billing-groups.html>`__ in the *AWS IoT Developers Guide*.
