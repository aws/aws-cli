**To create a publishing destination to export GuardDuty findings in the current region to.**

The following ``create-publishing-destination`` example shows how to set up a publishing destination to export current (not archived) GuardDuty findings to keep track of historical findings data. ::

    aws guardduty create-publishing-destination \
        --detector-id b6b992d6d2f48e64bc59180bfexample \
        --destination-type S3 \
        --destination-properties 'DestinationArn=arn:aws:s3:::amzn-s3-demo-bucket,KmsKeyArn=arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111'

Output::

    {
        "DestinationId": "46b99823849e1bbc242dfbe3cexample"
    }

For more information, see `Exporting generated GuardDuty findings to Amazon S3 buckets <https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_exportfindings.html>`__ in the *GuardDuty User Guide*.