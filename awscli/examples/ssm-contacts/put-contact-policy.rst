**To share a contact and engagements**

The following ``put-contact-policy`` example adds a resource policy to the contact Akua that shares the contact and related engagements with the principal. ::

    aws ssm-contacts put-contact-policy \
        --contact-arn "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam" \
        --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"ExampleResourcePolicy\",\"Action\":[\"ssm-contacts:GetContact\",\"ssm-contacts:StartEngagement\",\"ssm-contacts:DescribeEngagement\",\"ssm-contacts:ListPagesByEngagement\",\"ssm-contacts:StopEngagement\"],\"Principal\":{\"AWS\":\"123456789111\"},\"Effect\":\"Allow\",\"Resource\":[\"arn:aws:ssm-contacts:*:123456789012:contact\/akuam\",\"arn:aws:ssm-contacts:*:123456789012:engagement\/akuam\/*\"]}]}"

This command produces no output.

For more information, see `Working with shared contacts and response plans <https://docs.aws.amazon.com/incident-manager/latest/userguide/sharing.html>`__ in the *Incident Manager User Guide*.