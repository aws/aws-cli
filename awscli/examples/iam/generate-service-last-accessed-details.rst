**Example 1: To generate a service access report for a custom policy**

The following ``generate-service-last-accessed-details`` example starts a background job to generate a report that lists the services accessed by IAM users and other entities with a custom policy named ``intern-boundary``. You can display the report after it is created by running the ``get-service-last-accessed-details`` command. ::

    aws iam generate-service-last-accessed-details \
        --arn arn:aws:iam::123456789012:policy/intern-boundary

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

**Example 2: To generate a service access report for the AWS managed AdministratorAccess policy**

The following ``generate-service-last-accessed-details`` example starts a background job to generate a report that lists the services accessed by IAM users and other entities with the AWS managed ``AdministratorAccess`` policy. You can display the report after it is created by running the ``get-service-last-accessed-details`` command. ::

    aws iam generate-service-last-accessed-details \
        --arn arn:aws:iam::aws:policy/AdministratorAccess

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Refining permissions in AWS using last accessed information <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html>`__ in the *AWS IAM User Guide*.