**To disable a standard**

The following ``batch-disable-standards`` example disables the standard associated with the specified subscription ARN. ::

    aws securityhub batch-disable-standards \
        --standards-subscription-arns "arn:aws:securityhub:us-west-2:123456789012:subscription/pci-dss/v/3.2.1"

Output::

    {
        "StandardsSubscriptions": [ 
            { 
                "StandardsArn": "arn:aws:securityhub:us-west-2::standards/pci-dss/v/3.2.1",
                "StandardsInput": { },
                "StandardsStatus": "DELETING",
                "StandardsSubscriptionArn": "arn:aws:securityhub:us-west-2:123456789012:subscription/pci-dss/v/3.2.1"
            }
        ]
    }

For more information, see `Disabling a security standard <https://docs.aws.amazon.com/securityhub/latest/userguide/disable-standards.html>`__ in the *AWS Security Hub User Guide*.
