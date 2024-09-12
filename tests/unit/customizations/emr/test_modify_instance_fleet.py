# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
from tests.unit.customizations.emr import test_constants_instance_fleets as \
    CONSTANTS_FLEET


class TestModifyInstanceFleet(BaseAWSCommandParamsTest):
    prefix = f"emr modify-instance-fleet --cluster-id {CONSTANTS_FLEET.DEFAULT_CLUSTER_NAME} --instance-fleet "

    def test_modify_instance_fleet_with_instance_type_configs(self):
        self.assert_params_for_cmd(
            self.prefix + CONSTANTS_FLEET.MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS,
            CONSTANTS_FLEET.RES_MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS)

    def test_modify_instance_fleet_with_allocation_strategy_spot_and_od(self):
        self.assert_params_for_cmd(
            self.prefix + CONSTANTS_FLEET.MODIFY_INSTANCE_FLEET_WITH_SPOT_AND_OD_RESIZE_SPECIFICATIONS,
            CONSTANTS_FLEET.RES_MODIFY_INSTANCE_FLEET_WITH_SPOT_AND_OD_RESIZE_SPECIFICATIONS)

    def test_modify_instance_fleet_with_allocation_strategy_spot_and_od_and_instance_type_configs(self):
        self.assert_params_for_cmd(
            self.prefix + CONSTANTS_FLEET.MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS_AND_SPOT_AND_OD_RESIZE_SPECIFICATIONS,
            CONSTANTS_FLEET.RES_MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS_AND_SPOT_AND_OD_RESIZE_SPECIFICATIONS)


if __name__ == "__main__":
    unittest.main()
