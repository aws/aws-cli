# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
class TestPluginModule:
    """A mock plugin module for testing client plugin loading."""

    def __init__(self):
        self.events_seen = []

    def register_event(self, client):
        client.meta.events.register('before-call', self.increment_calls)

    def increment_calls(self, **kwargs):
        self.events_seen.append(kwargs)


plugin_instance = TestPluginModule()


def initialize_client_plugin(client):
    plugin_instance.register_event(client)
    return plugin_instance
