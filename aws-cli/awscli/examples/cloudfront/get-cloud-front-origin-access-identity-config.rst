**To get a CloudFront origin access identity configuration**

The following ``get-cloud-front-origin-access-identity-config`` example gets metadata about the CloudFront origin access identity
(OAI) with the ID ``E74FTE3AEXAMPLE``, including its ``ETag``. The OAI ID is
returned in the output of the
`create-cloud-front-origin-access-identity
<create-cloud-front-origin-access-identity.html>`_ and
`list-cloud-front-origin-access-identities
<list-cloud-front-origin-access-identities.html>`_ commands. ::

    aws cloudfront get-cloud-front-origin-access-identity-config \
        --id E74FTE3AEXAMPLE

Output::

    {
        "ETag": "E2QWRUHEXAMPLE",
        "CloudFrontOriginAccessIdentityConfig": {
            "CallerReference": "cli-example",
            "Comment": "Example OAI"
        }
    }

For more information, see `Restrict access to an Amazon S3 origin <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html>`__ in the *Amazon CloudFront Developer Guide*.
