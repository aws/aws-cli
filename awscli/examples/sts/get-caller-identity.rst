**To get details about the current IAM identity**

The following ``get-caller-identity`` example displays information about the IAM identity used to authenticate the request. The caller is an IAM user. ::

    aws sts get-caller-identity

Output::

    {
        "UserId": "AIDASAMPLEUSERID",
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/DevAdmin"
    }

For more information, see `View AWS account identifiers <https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-identifiers.html>`__ in the *AWS Account Management Reference Guide*.
