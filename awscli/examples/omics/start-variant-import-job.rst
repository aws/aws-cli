**To import a variant file**

The following ``start-variant-import-job`` example imports a VCF format variant file. ::

    aws omics start-variant-import-job \
        --destination-name my_var_store \
        --no-run-left-normalization  \
        --role-arn arn:aws:iam::123456789012:role/omics-service-role-serviceRole-W8O1XMPL7QZ \
        --items source=s3://amzn-s3-demo-bucket/Homo_sapiens_assembly38.known_indels.vcf.gz

Output::

    {
        "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Omics Analytics <https://docs.aws.amazon.com/omics/latest/dev/omics-analytics.html>`__ in the *Amazon Omics Developer Guide*.
