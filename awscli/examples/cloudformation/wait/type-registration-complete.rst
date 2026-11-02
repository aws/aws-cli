**To wait for CloudFormation to register a resource type**

The following ``wait type-registration-complete`` example pauses and resumes only after it can confirm that CloudFormation has registered the specified resource type. ::

    aws cloudformation wait type-registration-complete \
        --registration-token "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Managing extensions with the CloudFormation registry <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html>`__ in the *AWS CloudFormation User Guide*.
