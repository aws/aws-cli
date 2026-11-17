**Example 1: To rename a policy**

The following ``update-policy`` example renames a policy and gives it a new description. The output shows the new name and description. ::

    aws organizations update-policy \
        --policy-id p-examplepolicyid111 \
        --name Renamed-Policy \
        --description "This description replaces the original."

Output::

    {
        "Policy": {
            "Content": "{\n  \"Version\":\"2012-10-17\",\n  \"Statement\":{\n    \"Effect\":\"Allow\",\n    \"Action\":\"ec2:*\",\n    \"Resource\":\"*\"\n  }\n}\n",
            "PolicySummary": {
                "Id": "p-examplepolicyid111",
                "AwsManaged": false,
                "Arn": "arn:aws:organizations::123456789012:policy/o-exampleorgid/service_control_policy/p-examplepolicyid111",
                "Description": "This description replaces the original.",
                "Name": "Renamed-Policy",
                "Type": "SERVICE_CONTROL_POLICY"
            }
        }
    }

For more information, see `Updating organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_update.html>`__ in the *AWS Organizations User Guide*.

**Example 2: To replace a policy's JSON text content**

The following ``update-policy`` example replaces the JSON text of the SCP in the previous example with a new JSON policy text string that allows S3 instead of EC2. The output shows the new content. ::

    aws organizations update-policy \
        --policy-id p-examplepolicyid111 \
        --content "{\"Version\":\"2012-10-17\",\"Statement\":{\"Effect\":\"Allow\",\"Action\":\"s3:*\",\"Resource\":\"*\"}}"

Output::

    {
        "Policy": {
            "Content": "{ \"Version\": \"2012-10-17\", \"Statement\": { \"Effect\": \"Allow\", \"Action\": \"s3:*\", \"Resource\": \"*\" } }",
            "PolicySummary": {
                "Arn": "arn:aws:organizations::123456789012:policy/o-exampleorgid/service_control_policy/p-examplepolicyid111",
                "AwsManaged": false,
                "Description": "This description replaces the original.",
                "Id": "p-examplepolicyid111",
                "Name": "Renamed-Policy",
                "Type": "SERVICE_CONTROL_POLICY"
            }
        }
    }

For more information, see `Updating organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_update.html>`__ in the *AWS Organizations User Guide*.
