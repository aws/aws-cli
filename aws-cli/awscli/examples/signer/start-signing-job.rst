**To start a signing job**

The following ``start-signing-job`` example starts a signing job on the code found at the specified source. It uses the specified profile to do the signing and places the signed code in the specified destination. The output is the ID of the signing job. ::

    aws signer start-signing-job \
        --source 's3={bucketName=signer-source,key=MyCode.rb,version=PNyFaUTgsQh5ZdMCcoCe6pT1gOpgB_M4}' \
        --destination 's3={bucketName=signer-destination,prefix=signed-}' \
        --profile-name MyProfile7

Output::

    {
        "jobId": "2065c468-73e2-4385-a6c9-0123456789abc"
    }

For more information, see `Create a signing job for IoT in AWS Signer <https://docs.aws.amazon.com/signer/latest/developerguide/signing-jobs-iot.html>`__ in the *AWS Signer Developer Guide*.
