**To set up the credential helper included in the AWS CLI with AWS CodeCommit**

The following ``credential-helper`` example configures Git to use the credential helper included in the AWS CLI with AWS CodeCommit. The ``credential-helper`` utility is not designed to be called directly from the AWS CLI. Instead it is intended to be used as a parameter with the ``git config`` command to set up your local computer. It enables Git to use HTTPS and a cryptographically signed version of your IAM user credentials or Amazon EC2 instance role whenever Git needs to authenticate with AWS to interact with CodeCommit repositories. ::

    git config --global credential.helper '!aws codecommit credential-helper $@' 
    git config --global credential.UseHttpPath true

Output::

    [credential]    
        helper = !aws codecommit credential-helper $@ 
        UseHttpPath = true

For more information, see `Setting up for AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up.html>`__ in the *AWS CodeCommit User Guide*. Review the content carefully, and then follow the procedures in one of the following topics: `Setup steps for HTTPS connections to AWS CodeCommit repositories on Linux, macOS, or Unix with the AWS CLI credential helper <https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-unixes.html>`__ or `Setup steps for HTTPS connections to AWS CodeCommit repositories on Windows with the AWS CLI credential helper <https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-windows.html>`__ in the *AWS CodeCommit User Guide*.
