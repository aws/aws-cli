**To create an assessment target**

The following ``create-assessment-target`` example creates an assessment target named ``ExampleAssessmentTarget`` using the resource group with the ARN of ``arn:aws:inspector:us-west-2:123456789012:resourcegroup/0-AB6DMKnv``. ::

    aws inspector create-assessment-target \
        --assessment-target-name ExampleAssessmentTarget \
        --resource-group-arn arn:aws:inspector:us-west-2:123456789012:resourcegroup/0-AB6DMKnv

Output::

    {
        "assessmentTargetArn": "arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX"
    }

