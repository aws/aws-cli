**To register information about an already-uploaded application revision**

The following ``register-application-revision`` example registers information about an already-uploaded application revision stored in Amazon S3 with AWS CodeDeploy. ::

    aws deploy register-application-revision \
        --application-name WordPress_App \
        --description "Revised WordPress application" \
        --s3-location bucket=CodeDeployDemoBucket,key=RevisedWordPressApp.zip,bundleType=zip,eTag=cecc9b8a08eac650a6e71fdb88EXAMPLE

This command produces no output.

For more information, see `Register an application revision in Amazon S3 with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/application-revisions-register.html>`__ in the *AWS CodeDeploy User Guide*.
