**To describe a provisioned product plan**

The following ``describe-provisioned-product-plan`` example describes a provisioned product plan. ::

    aws servicecatalog describe-provisioned-product-plan  \
        --plan-id "plan-g7iwsaf3mytwu"

Output::

    {
        "ProvisionedProductPlanDetails": {
            "CreatedTime": "2025-11-09T18:09:37.808000-06:00",
            "PathId": "lpv3-y3fnkeslpoevg",
            "ProductId": "prod-cfrfxmraxxxxx",
            "PlanName": "test-plan",
            "PlanId": "plan-g7iwsaf3mytwu",
            "ProvisionProductId": "pp-mkbnbztzxxxxx",
            "ProvisionProductName": "test-pp",
            "PlanType": "CLOUDFORMATION",
            "ProvisioningArtifactId": "pa-7wz4cu5cxxxxx",
            "Status": "CREATE_SUCCESS",
            "UpdatedTime": "2025-11-09T18:09:46.524000-06:00",
            "Tags": []
        }
    }
