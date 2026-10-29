**To disable data stream encryption**

The following ``stop-stream-encryption`` example disables server-side encryption for the specified stream, using the specified AWS KMS key. ::

    aws kinesis start-stream-encryption \
        --encryption-type KMS \
        --key-id arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --stream-name samplestream

This command produces no output.

For more information, see `Data Protection in Amazon Kinesis Data Streams <https://docs.aws.amazon.com/streams/latest/dev/server-side-encryption.html>`__ in the *Amazon Kinesis Data Streams Developer Guide*.
