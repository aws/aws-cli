**To import annotations**

The following ``start-annotation-import-job`` example imports annotations from Amazon S3. ::

    aws omics start-annotation-import-job \
        --destination-name tsv_ann_store \
        --no-run-left-normalization \
        --role-arn arn:aws:iam::123456789012:role/omics-service-role-serviceRole-W8O1XMPL7QZ \
        --items source=s3://amzn-s3-demo-bucket/targetedregions.bed.gz

Output::

    {
        "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Omics Analytics <https://docs.aws.amazon.com/omics/latest/dev/omics-analytics.html>`__ in the *Amazon Omics Developer Guide*.
