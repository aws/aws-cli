**To describe assessment templates**

The following ``describe-assessment-templates`` example describes the assessment template with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-4r1V2mAw``. ::

    aws inspector describe-assessment-templates \
        --assessment-template-arns arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-4r1V2mAw

Output::

    {
        "assessmentTemplates": [
            {
                "arn": "arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-4r1V2mAw",
                "assessmentTargetArn": "arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq",
                "createdAt": 1458074191.844,
                "durationInSeconds": 3600,
                "name": "ExampleAssessmentTemplate",
                "rulesPackageArns": [
                    "arn:aws:inspector:us-west-2:758058086616:rulespackage/0-X1KXtawP"
                ],
                "userAttributesForFindings": []
            }
        ],
        "failedItems": {}
    }

