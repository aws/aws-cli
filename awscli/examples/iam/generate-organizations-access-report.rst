**Example 1: To generate an access report for a root in an organization**

The following ``generate-organizations-access-report`` example starts a background job to create an access report for the specified root in an organization. You can display the report after it's created by running the ``get-organizations-access-report`` command. ::

    aws iam generate-organizations-access-report \
        --entity-path o-4fxmplt198/r-c3xb

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

**Example 2: To generate an access report for an account in an organization**

The following ``generate-organizations-access-report`` example starts a background job to create an access report for account ID ``123456789012`` in the organization ``o-4fxmplt198``. You can display the report after it's created by running the ``get-organizations-access-report`` command. ::

    aws iam generate-organizations-access-report \
        --entity-path o-4fxmplt198/r-c3xb/123456789012

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

**Example 3: To generate an access report for an account in an organizational unit in an organization**

The following ``generate-organizations-access-report`` example starts a background job to create an access report for account ID ``123456789111`` in organizational unit ``ou-c3xb-lmu7j2yg`` in the organization ``o-4fxmplt198``. You can display the report after it's created by running the ``get-organizations-access-report`` command. ::

    aws iam generate-organizations-access-report \
        --entity-path o-4fxmplt198/r-c3xb/ou-c3xb-lmu7j2yg/123456789111

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

To get details about roots and organizational units in your organization, use the ``organizations list-roots`` and ``organizations list-organizational-units-for-parent`` commands.

For more information, see `Refining permissions in AWS using last accessed information <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html>`__ in the *AWS IAM User Guide*.