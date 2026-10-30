**To deletes a GitHub account connection**

The following ``delete-git-hub-account-token`` example deletes the connection of the specified GitHub account. ::

    aws deploy delete-git-hub-account-token \
        --token-name my-github-account
    
Output::

    {
        "tokenName": "my-github-account"
    }

For more information, see `Integrating CodeDeploy with GitHub <https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-partners-github.html>`__ in the *AWS CodeDeploy User Guide*.
