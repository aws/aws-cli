**To list image scan finding aggregations for an image pipeline**

The following ``list-image-scan-finding-aggregations`` example aggregates vulnerability findings for images that the specified pipeline created, with counts grouped by severity level. ::

    aws imagebuilder list-image-scan-finding-aggregations \
        --filter name=imagePipelineArn,values=arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "aggregationType": "imagePipelineArn",
        "responses": [
            {
                "imagePipelineAggregation": {
                    "imagePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline",
                    "severityCounts": {
                        "all": 25,
                        "critical": 1,
                        "high": 7,
                        "medium": 12
                    }
                }
            }
        ]
    }

For more information, see `Manage security findings for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-security-findings.html>`__ in the *EC2 Image Builder User Guide*.
