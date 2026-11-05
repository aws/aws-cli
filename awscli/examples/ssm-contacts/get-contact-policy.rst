**To list the resource policies of a contact**

The following ``get-contact-policy`` example lists the resource policies associated with the specified contact. ::

    aws ssm-contacts get-contact-policy \
        --contact-arn "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam"

Output::

    {
        "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
        "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"SharePolicyForDocumentationDralia\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"123456789111\"},\"Action\":[\"ssm-contacts:GetContact\",\"ssm-contacts:StartEngagement\",\"ssm-contacts:DescribeEngagement\",\"ssm-contacts:ListPagesByEngagement\",\"ssm-contacts:StopEngagement\"],\"Resource\":[\"arn:aws:ssm-contacts:*:123456789012:contact/akuam\",\"arn:aws:ssm-contacts:*:123456789012:engagement/akuam/*\"]}]}"
    }

For more information, see `Working with shared contacts and response plans <https://docs.aws.amazon.com/incident-manager/latest/userguide/sharing.html>`__ in the *Incident Manager User Guide*.