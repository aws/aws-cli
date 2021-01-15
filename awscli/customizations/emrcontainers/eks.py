# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


class EKS(object):
    def __init__(self, eks_client):
        self.eks_client = eks_client
        self.cluster_info = {}

    def get_oidc_issuer_id(self, cluster_name):
        """Method to get OIDC issuer id for the given EKS cluster"""
        if cluster_name not in self.cluster_info:
            self.cluster_info[cluster_name] = self.eks_client.describe_cluster(
                name=cluster_name
            )

        oidc_issuer = self.cluster_info[cluster_name].get("cluster", {}).get(
            "identity", {}).get("oidc", {}).get("issuer", "")

        return oidc_issuer.split('https://')[1]

    def get_account_id(self, cluster_name):
        """Method to get account id for the given EKS cluster"""
        if cluster_name not in self.cluster_info:
            self.cluster_info[cluster_name] = self.eks_client.describe_cluster(
                name=cluster_name
            )

        cluster_arn = self.cluster_info[cluster_name].get("cluster", {}).get(
            "arn", "")

        return cluster_arn.split(':')[4]
