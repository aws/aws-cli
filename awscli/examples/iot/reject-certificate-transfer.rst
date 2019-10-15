**To reject a certificate transfer**

The following ``reject-certificate-transfer`` example rejects the transfer of the specified device certificate from another AWS account. ::

    aws iot reject-certificate-transfer \
        --certificate-id f0f33678c7c9a046e5cc87b2b1a58dfa0beec26db78addd5e605d630e05c7fc8

This command produces no output.

For more information, see `RejectCertificateTransfer <https://docs.aws.amazon.com/iot/latest/apireference/API_RejectCertificateTransfer.html>`__ in the *AWS IoT API Reference*.
