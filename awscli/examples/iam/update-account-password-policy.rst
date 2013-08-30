**To set or change the current account password policy**

The following ``update-account-password-policy`` command sets the password policy to require a minimum length of 8
characters and to require one or more numbers in the password::

    aws iam update-account-password-policy --minimum-password-length 8 --require-numbers

For more information, see `Managing an IAM Password Policy`_ in the *Using IAM* guide.
