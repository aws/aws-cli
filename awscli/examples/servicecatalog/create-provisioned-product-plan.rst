**To create a plan**

The following ``create-provisioned-product-plan`` example creates a plan. ::

    aws servicecatalog create-provisioned-product-plan \
        --plan-name test-plan \
        --plan-type CLOUDFORMATION \
        --product-id prod-cfrfxmraxxxxx \
        --provisioned-product-name test-pp \
        --provisioning-artifact-id pa-7wz4cu5cxxxxx

Output::

    {
        "PlanName": "test-plan",
        "PlanId": "plan-cuxae3z6gxxxx",
        "ProvisionProductId": "pp-7kh7wbc4xxxxx",
        "ProvisionedProductName": "test-pp",
        "ProvisioningArtifactId": "pa-7wz4cu5cxxxxx"
    }

For more information, see `Creating a launch plan <https://docs.aws.amazon.com/servicecatalog/latest/userguide/launch-plan.html>`__ in the *AWS Service Catalog User Guide*.
