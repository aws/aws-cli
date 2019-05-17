**To list the context keys referenced by one or more custom JSON policies**

The following ``get-context-keys-for-custom-policy`` command parses each supplied policy and lists the context keys used by those policies. Use this command to identify which context key values you must supply to successfully use the policy simulator commands ``simulate-custom-policy`` and ``simulate-custom-policy``. You can also retrieve the list of context keys used by all policies associated by an IAM user or role by using the ``get-context-keys-for-custom-policy`` command. Parameter values that begin with ``file://`` instruct the command to read the file and use the contents as the value for the parameter instead of the file name itself.::

    aws iam get-context-keys-for-custom-policy \
        --policy-input-list '{"Version":"2012-10-17","Statement":{"Effect":"Allow","Action":"dynamodb:*","Resource":"arn:aws:dynamodb:us-west-2:123456789012:table/${aws:username}","Condition":{"DateGreaterThan":{"aws:CurrentTime":"2015-08-16T12:00:00Z"}}}}'

**Known issue**: At this time, you can't submit a file to the ``--policy-input-list`` parameter using the ``file://`` syntax. You must instead collapse the content into a single line and submit the policy content directly on the command line as shown in the previous example.

Output::

    {
        "ContextKeyNames": [
            "aws:username",
            "aws:CurrentTime"
        ]
    }

For more information, see `Using the IAM Policy Simulator (AWS CLI and AWS API)`_ in the *Using IAM* guide.

.. _`Using the IAM Policy Simulator (AWS CLI and AWS API)`: https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html#policies-simulator-using-api
