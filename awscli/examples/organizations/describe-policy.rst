**To get information about a policy**

The following ``describe-policy`` example requests information about a policy. ::

    aws organizations describe-policy \
        --policy-id p-examplepolicyid111
	
Output::

    {
        "Policy": {
            "Content": "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"Effect\": \"Allow\",\n      \"Action\": \"*\",\n      \"Resource\": \"*\"\n    }\n  ]\n}",
            "PolicySummary": {
                "Arn": "arn:aws:organizations::123456789012:policy/o-exampleorgid/service_control_policy/p-examplepolicyid111",
                "Type": "SERVICE_CONTROL_POLICY",
                "Id": "p-examplepolicyid111",
                "AwsManaged": false,
                "Name": "AllowAllS3Actions",
                "Description": "Enables admins to delegate S3 permissions"
            }
        }
    }

For more information, see `Getting information about your organization's policies <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_info-operations.html>`__ in the *AWS Organizations User Guide*.
