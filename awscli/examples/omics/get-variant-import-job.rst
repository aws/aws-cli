**To view a variant import job**

The following ``get-variant-import-job`` example gets details about a variant import job. ::

    aws omics get-variant-import-job \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "creationTime": "2022-11-23T22:42:50.037812Z",
        "destinationName": "my_var_store",
        "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "items": [
            {
                "jobStatus": "IN_PROGRESS",
                "source": "s3://amzn-s3-demo-bucket/Homo_sapiens_assembly38.known_indels.vcf.gz"
            }
        ],
        "roleArn": "arn:aws:iam::123456789012:role/omics-service-role-serviceRole-W8O1XMPL7QZ",
        "runLeftNormalization": false,
        "status": "IN_PROGRESS",
        "updateTime": "2022-11-23T22:43:05.898309Z"
    }

For more information, see `Omics Analytics <https://docs.aws.amazon.com/omics/latest/dev/omics-analytics.html>`__ in the *Amazon Omics Developer Guide*.
