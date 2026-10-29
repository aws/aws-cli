**To enable the use of a policy type in a root**

The following ``enable-policy-type`` example enables the service control policy (SCP) policy type in a root. ::

    aws organizations enable-policy-type \
        --root-id r-examplerootid111 \
        --policy-type SERVICE_CONTROL_POLICY
		
The output shows a root object with a policyTypes response element showing that SCPs are now enabled.

Output::

    {
        "Root": {
            "PolicyTypes": [
                {
                    "Status": "ENABLED",
                    "Type": "SERVICE_CONTROL_POLICY"
                }
            ],
            "Id": "r-examplerootid111",
            "Name": "Root",
            "Arn": "arn:aws:organizations::123456789012:root/o-exampleorgid/r-examplerootid111"
        }
    }

For more information, see `Enabling a policy type <https://docs.aws.amazon.com/organizations/latest/userguide/enable-policy-type.html>`__ in the *AWS Organizations User Guide*.
