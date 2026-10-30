**To disable a policy type in a root**

The following ``disable-policy-type`` example disables the service control policy (SCP) policy type in a root. The output shows that the ``PolicyTypes`` response element no longer includes ``SERVICE_CONTROL_POLICY``. ::

    aws organizations disable-policy-type \
        --root-id r-examplerootid111 \
        --policy-type SERVICE_CONTROL_POLICY

Output::

    {
        "Root": {
            "PolicyTypes": [],
            "Name": "Root",
            "Id": "r-examplerootid111",
            "Arn": "arn:aws:organizations::123456789012:root/o-exampleorgid/r-examplerootid111"
        }
    }

For more information, see `Disabling a policy type <https://docs.aws.amazon.com/organizations/latest/userguide/disable-policy-type.html>`__ in the *AWS Organizations User Guide*.
