**To list generated templates**

The following ``list-generated-templates`` example lists all generated templates. ::

    aws cloudformation list-generated-templates

Output::

    {
        "Summaries": [
            {
                "GeneratedTemplateId": "arn:aws:cloudformation:us-east-1:123456789012:generatedtemplate/7fc8512c-d8cb-4e02-b266-d39c48344e48",
                "GeneratedTemplateName": "MyTemplate",
                "Status": "COMPLETE",
                "StatusReason": "All resources complete",
                "CreationTime": "2025-09-23T20:13:24.283000+00:00",
                "LastUpdatedTime": "2025-09-23T20:13:28.610000+00:00",
                "NumberOfResources": 4
            },
            {
                "GeneratedTemplateId": "arn:aws:cloudformation:us-east-1:123456789012:generatedTemplate/f10dd1c4-edc6-4823-8153-ab6112b8d051",
                "GeneratedTemplateName": "MyEC2InstanceTemplate",
                "Status": "COMPLETE",
                "StatusReason": "All resources complete",
                "CreationTime": "2024-08-08T19:35:49.790000+00:00",
                "LastUpdatedTime": "2024-08-08T19:35:52.207000+00:00",
                "NumberOfResources": 3
            },
            {
                "GeneratedTemplateId": "arn:aws:cloudformation:us-east-1:123456789012:generatedTemplate/e5a1c89f-7ce2-41bd-9bdf-75b7c852e3ca",
                "GeneratedTemplateName": "MyEKSNodeGroupTemplate",
                "Status": "COMPLETE",
                "StatusReason": "All resources complete",
                "CreationTime": "2024-07-16T20:39:27.883000+00:00",
                "LastUpdatedTime": "2024-07-16T20:39:35.766000+00:00",
                "NumberOfResources": 4
            }
        ]
    }

For more information, see `Generating templates from existing resources <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/generate-IaC.html>`__ in the *AWS CloudFormation User Guide*.
