**To view an annotation import job**

The following ``get-annotation-import-job`` example gets details about an annotation import job. ::

    aws omics get-annotation-import-job \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "creationTime": "2022-11-30T01:40:11.017746Z",
        "destinationName": "tsv_ann_store",
        "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "items": [
            {
                "jobStatus": "COMPLETED",
                "source": "s3://amzn-s3-demo-bucket/targetedregions.bed.gz"
            }
        ],
        "roleArn": "arn:aws:iam::123456789012:role/omics-service-role-serviceRole-W8O1XMPL7QZ",
        "runLeftNormalization": false,
        "status": "COMPLETED",
        "updateTime": "2022-11-30T01:42:39.134009Z"
    }

For more information, see `Omics Analytics <https://docs.aws.amazon.com/omics/latest/dev/omics-analytics.html>`__ in the *Amazon Omics Developer Guide*.
