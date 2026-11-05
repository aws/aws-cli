**To list generated templates**

The following ``list-generated-templates`` example lists all generated templates. ::

    aws cloudformation list-generated-templates

Output::

    {
        "Summaries": [
            {
                "GeneratedTemplateId": "arn:aws:cloudformation:us-west-2:123456789012:generatedtemplate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "GeneratedTemplateName": "MyTemplate",
                "Status": "COMPLETE",
                "StatusReason": "All resources complete",
                "CreationTime": "2025-09-23T20:13:24.283000+00:00",
                "LastUpdatedTime": "2025-09-23T20:13:28.610000+00:00",
                "NumberOfResources": 4
            },
            {
                "GeneratedTemplateId": "arn:aws:cloudformation:us-west-2:123456789012:generatedTemplate/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "GeneratedTemplateName": "MyEC2InstanceTemplate",
                "Status": "COMPLETE",
                "StatusReason": "All resources complete",
                "CreationTime": "2024-08-08T19:35:49.790000+00:00",
                "LastUpdatedTime": "2024-08-08T19:35:52.207000+00:00",
                "NumberOfResources": 3
            },
            {
                "GeneratedTemplateId": "arn:aws:cloudformation:us-west-2:123456789012:generatedTemplate/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
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
