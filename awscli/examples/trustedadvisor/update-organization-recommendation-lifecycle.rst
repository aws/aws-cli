**To update an organization recommendation lifecycle**

The following ``update-organization-recommendation-lifecycle`` example updates the lifecycle of an organization recommendation by its identifier. ::

    aws trustedadvisor update-organization-recommendation-lifecycle \
        --organization-recommendation-identifier arn:aws:trustedadvisor:::organization-recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --lifecycle-stage dismissed \
        --update-reason-code not_applicable

This command produces no output.

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.