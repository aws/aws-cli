# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy
import os

import pytest

import botocore.configprovider
import botocore.session as session
from botocore.configprovider import (
    BaseProvider,
    ChainProvider,
    ConfigChainFactory,
    ConfiguredEndpointProvider,
    ConfigValueStore,
    ConstantProvider,
    DefaultConfigResolver,
    EnvironmentProvider,
    InstanceVarProvider,
    ScopedConfigProvider,
    SectionConfigProvider,
    SmartDefaultsConfigStoreFactory,
)
from botocore.exceptions import ConnectTimeoutError
from botocore.utils import IMDSRegionProvider
from tests import mock, unittest


class TestConfigChainFactory(unittest.TestCase):
    def assert_chain_does_provide(
        self,
        instance_map,
        environ_map,
        scoped_config_map,
        create_config_chain_args,
        expected_value,
    ):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = scoped_config_map
        fake_session.instance_variables.return_value = instance_map
        builder = ConfigChainFactory(fake_session, environ=environ_map)
        chain = builder.create_config_chain(**create_config_chain_args)
        value = chain.provide()
        self.assertEqual(value, expected_value)

    def test_chain_builder_can_provide_instance(self):
        self.assert_chain_does_provide(
            instance_map={'instance_var': 'from-instance'},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={
                'instance_name': 'instance_var',
            },
            expected_value='from-instance',
        )

    def test_chain_builder_can_skip_instance(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'instance'},
            environ_map={'ENV_VAR': 'env'},
            scoped_config_map={},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
            },
            expected_value='env',
        )

    def test_chain_builder_can_provide_env_var(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={'ENV_VAR': 'from-env'},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': 'ENV_VAR',
            },
            expected_value='from-env',
        )

    def test_does_provide_none_if_no_variable_exists_in_env_var_list(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': ['FOO'],
            },
            expected_value=None,
        )

    def test_does_provide_value_if_variable_exists_in_env_var_list(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={'FOO': 'bar'},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': ['FOO'],
            },
            expected_value='bar',
        )

    def test_does_provide_first_non_none_value_first_in_env_var_list(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={'FOO': 'baz'},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': ['FOO', 'BAR'],
            },
            expected_value='baz',
        )

    def test_does_provide_first_non_none_value_second_in_env_var_list(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={'BAR': 'baz'},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': ['FOO', 'BAR'],
            },
            expected_value='baz',
        )

    def test_does_provide_none_if_all_list_env_vars_are_none(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': ['FOO', 'BAR'],
            },
            expected_value=None,
        )

    def test_does_provide_first_value_when_both_env_vars_exist(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={'FOO': 'baz', 'BAR': 'buz'},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': ['FOO', 'BAR'],
            },
            expected_value='baz',
        )

    def test_chain_builder_can_provide_config_var(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'config_var': 'from-config'},
            create_config_chain_args={
                'config_property_names': 'config_var',
            },
            expected_value='from-config',
        )

    def test_chain_builder_can_provide_nested_config_var(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'config_var': {'nested-key': 'nested-val'}},
            create_config_chain_args={
                'config_property_names': ('config_var', 'nested-key'),
            },
            expected_value='nested-val',
        )

    def test_provide_value_from_config_list(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'var': 'val'},
            create_config_chain_args={
                'config_property_names': ['var'],
            },
            expected_value='val',
        )

    def test_provide_value_from_config_list_looks_for_non_none_vals(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'non_none_var': 'non_none_val'},
            create_config_chain_args={
                'config_property_names': ['none_var', 'non_none_var'],
            },
            expected_value='non_none_val',
        )

    def test_provide_value_from_config_list_retrieves_first_non_none_val(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'first': 'first_val', 'second': 'second_val'},
            create_config_chain_args={
                'config_property_names': ['first', 'second'],
            },
            expected_value='first_val',
        )

    def test_provide_value_from_config_list_if_all_vars_are_none(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={
                'config_property_names': ['config1', 'config2'],
            },
            expected_value=None,
        )

    def test_provide_value_from_list_with_nested_var(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'section': {'nested_var': 'nested_val'}},
            create_config_chain_args={
                'config_property_names': [('section', 'nested_var')],
            },
            expected_value='nested_val',
        )

    def test_chain_builder_can_provide_default(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={'default': 'from-default'},
            expected_value='from-default',
        )

    def test_chain_provider_does_follow_priority_instance_var(self):
        self.assert_chain_does_provide(
            instance_map={'instance_var': 'from-instance'},
            environ_map={'ENV_VAR': 'from-env'},
            scoped_config_map={'config_var': 'from-config'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_names': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-instance',
        )

    def test_chain_provider_does_follow_priority_env_var(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'from-instance'},
            environ_map={'ENV_VAR': 'from-env'},
            scoped_config_map={'config_var': 'from-confi'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_names': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-env',
        )

    def test_chain_provider_does_follow_priority_config(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'from-instance'},
            environ_map={'WRONG_ENV_VAR': 'from-env'},
            scoped_config_map={'config_var': 'from-config'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_names': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-config',
        )

    def test_chain_provider_does_follow_priority_default(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'from-instance'},
            environ_map={'WRONG_ENV_VAR': 'from-env'},
            scoped_config_map={'wrong_config_var': 'from-config'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_names': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-default',
        )


class TestConfigValueStore(unittest.TestCase):
    def test_does_provide_none_if_no_variable_exists(self):
        provider = ConfigValueStore()
        value = provider.get_config_variable('fake_variable')
        self.assertIsNone(value)

    def test_does_provide_value_if_variable_exists(self):
        mock_value_provider = mock.Mock(spec=BaseProvider)
        mock_value_provider.provide.return_value = 'foo'
        provider = ConfigValueStore(
            mapping={
                'fake_variable': mock_value_provider,
            }
        )
        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'foo')

    def test_can_set_variable(self):
        provider = ConfigValueStore()
        provider.set_config_variable('fake_variable', 'foo')
        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'foo')

    def test_can_set_config_provider(self):
        foo_value_provider = mock.Mock(spec=BaseProvider)
        foo_value_provider.provide.return_value = 'foo'
        provider = ConfigValueStore(
            mapping={
                'fake_variable': foo_value_provider,
            }
        )

        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'foo')

        bar_value_provider = mock.Mock(spec=BaseProvider)
        bar_value_provider.provide.return_value = 'bar'
        provider.set_config_provider('fake_variable', bar_value_provider)

        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'bar')

    def test_can_get_config_provider(self):
        chain_provider = ChainProvider(
            providers=[ConstantProvider(value='bar')]
        )
        config_value_store = ConfigValueStore(
            mapping={
                'fake_variable': chain_provider,
            }
        )
        provider = config_value_store.get_config_provider('fake_variable')
        value = config_value_store.get_config_variable('fake_variable')
        self.assertIsInstance(provider, ChainProvider)
        self.assertEqual(value, 'bar')

    def test_can_get_config_provider_non_chain_provider(self):
        constant_provider = ConstantProvider(value='bar')
        config_value_store = ConfigValueStore(
            mapping={
                'fake_variable': constant_provider,
            }
        )
        provider = config_value_store.get_config_provider('fake_variable')
        value = config_value_store.get_config_variable('fake_variable')
        self.assertIsInstance(provider, ConstantProvider)
        self.assertEqual(value, 'bar')

    def test_deepcopy_preserves_overrides(self):
        provider = ConstantProvider(100)
        config_store = ConfigValueStore(mapping={'fake_variable': provider})
        config_store.set_config_variable('fake_variable', 'override-value')

        config_store_deepcopy = copy.deepcopy(config_store)

        value = config_store_deepcopy.get_config_variable('fake_variable')
        self.assertEqual(value, 'override-value')

    def test_copy_preserves_provider_identities(self):
        fake_variable_provider = ConstantProvider(100)
        config_store = ConfigValueStore(
            mapping={
                'fake_variable': fake_variable_provider,
            }
        )

        config_store_copy = copy.copy(config_store)

        self.assertIs(
            config_store.get_config_provider('fake_variable'),
            config_store_copy.get_config_provider('fake_variable'),
        )

    def test_copy_preserves_overrides(self):
        provider = ConstantProvider(100)
        config_store = ConfigValueStore(mapping={'fake_variable': provider})
        config_store.set_config_variable('fake_variable', 'override-value')

        config_store_copy = copy.copy(config_store)

        value = config_store_copy.get_config_variable('fake_variable')
        self.assertEqual(value, 'override-value')

    def test_copy_update_does_not_mutate_source_config_store(self):
        fake_variable_provider = ConstantProvider(100)
        config_store = ConfigValueStore(
            mapping={
                'fake_variable': fake_variable_provider,
            }
        )

        config_store_copy = copy.copy(config_store)

        another_variable_provider = ConstantProvider('ABC')

        config_store_copy.set_config_provider(
            'fake_variable', another_variable_provider
        )

        assert config_store.get_config_variable('fake_variable') == 100
        assert config_store_copy.get_config_variable('fake_variable') == 'ABC'


class TestInstanceVarProvider(unittest.TestCase):
    def assert_provides_value(self, name, instance_map, expected_value):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.instance_variables.return_value = instance_map

        provider = InstanceVarProvider(
            instance_var=name,
            session=fake_session,
        )
        value = provider.provide()
        self.assertEqual(value, expected_value)

    def test_can_provide_value(self):
        self.assert_provides_value(
            name='foo',
            instance_map={'foo': 'bar'},
            expected_value='bar',
        )

    def test_does_provide_none_if_value_not_in_dict(self):
        self.assert_provides_value(
            name='foo',
            instance_map={},
            expected_value=None,
        )


class TestEnvironmentProvider(unittest.TestCase):
    def assert_does_provide(self, env, name, expected_value):
        provider = EnvironmentProvider(name=name, env=env)
        value = provider.provide()
        self.assertEqual(value, expected_value)

    def test_does_provide_none_if_no_variable_exists(self):
        self.assert_does_provide(
            name='FOO',
            env={},
            expected_value=None,
        )

    def test_does_provide_value_if_variable_exists(self):
        self.assert_does_provide(
            name='FOO',
            env={
                'FOO': 'bar',
            },
            expected_value='bar',
        )


class TestScopedConfigProvider(unittest.TestCase):
    def assert_provides_value(
        self, config_file_values, config_var_name, expected_value
    ):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = config_file_values
        property_provider = ScopedConfigProvider(
            config_var_name=config_var_name,
            session=fake_session,
        )
        value = property_provider.provide()
        self.assertEqual(value, expected_value)

    def test_can_provide_value(self):
        self.assert_provides_value(
            config_file_values={'foo': 'bar'},
            config_var_name='foo',
            expected_value='bar',
        )

    def test_does_provide_none_if_var_not_in_config(self):
        self.assert_provides_value(
            config_file_values={'foo': 'bar'},
            config_var_name='no_such_var',
            expected_value=None,
        )

    def test_provide_nested_value(self):
        self.assert_provides_value(
            config_file_values={'section': {'nested_var': 'nested_val'}},
            config_var_name=('section', 'nested_var'),
            expected_value='nested_val',
        )

    def test_provide_nested_value_but_not_section(self):
        self.assert_provides_value(
            config_file_values={'section': 'not-nested'},
            config_var_name=('section', 'nested_var'),
            expected_value=None,
        )


def _make_provider_that_returns(return_value):
    provider = mock.Mock(spec=BaseProvider)
    provider.provide.return_value = return_value
    return provider


def _make_providers_that_return(return_values):
    mocks = []
    for return_value in return_values:
        provider = _make_provider_that_returns(return_value)
        mocks.append(provider)
    return mocks


def assert_chain_does_provide(providers, expected_value):
    provider = ChainProvider(
        providers=providers,
    )
    assert provider.provide() == expected_value


@pytest.mark.parametrize(
    'case',
    (
        (None, []),
        (None, [None]),
        ('foo', ['foo']),
        ('foo', ['foo', 'bar']),
        ('bar', [None, 'bar']),
        ('foo', ['foo', None]),
        ('baz', [None, None, 'baz']),
        ('bar', [None, 'bar', None]),
        ('foo', ['foo', 'bar', None]),
        ('foo', ['foo', 'bar', 'baz']),
    ),
)
def test_chain_provider(case):
    # Each case is a tuple with the first element being the expected return
    # value from the ChainProvider. The second value being a list of return
    # values from the individual providers that are in the chain.
    assert_chain_does_provide(_make_providers_that_return(case[1]), case[0])


class TestChainProvider(unittest.TestCase):
    def test_can_convert_provided_value(self):
        chain_provider = ChainProvider(
            providers=_make_providers_that_return(['1']),
            conversion_func=int,
        )
        value = chain_provider.provide()
        self.assertIsInstance(value, int)
        self.assertEqual(value, 1)


class TestConstantProvider(unittest.TestCase):
    def test_can_provide_value(self):
        provider = ConstantProvider(value='foo')
        value = provider.provide()
        self.assertEqual(value, 'foo')


class TestSectionConfigProvider(unittest.TestCase):
    def assert_provides_value(
        self,
        config_file_values,
        section_name,
        expected_value,
        override_providers=None,
    ):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = config_file_values
        provider = SectionConfigProvider(
            section_name=section_name,
            session=fake_session,
            override_providers=override_providers,
        )
        value = provider.provide()
        self.assertEqual(value, expected_value)

    def test_provide_section_config(self):
        self.assert_provides_value(
            config_file_values={'mysection': {'section_var': 'section_val'}},
            section_name='mysection',
            expected_value={'section_var': 'section_val'},
        )

    def test_provide_service_config_missing_service(self):
        self.assert_provides_value(
            config_file_values={},
            section_name='mysection',
            expected_value=None,
        )

    def test_provide_service_config_not_a_section(self):
        self.assert_provides_value(
            config_file_values={'myservice': 'not-a-section'},
            section_name='mysection',
            expected_value=None,
        )

    def test_provide_section_config_with_overrides(self):
        self.assert_provides_value(
            config_file_values={
                'mysection': {
                    'override_var': 'from_config_file',
                    'no_override_var': 'from_config_file',
                }
            },
            section_name='mysection',
            override_providers={'override_var': ConstantProvider('override')},
            expected_value={
                'override_var': 'override',
                'no_override_var': 'from_config_file',
            },
        )

    def test_provide_section_config_with_only_overrides(self):
        self.assert_provides_value(
            config_file_values={},
            section_name='mysection',
            override_providers={'override_var': ConstantProvider('override')},
            expected_value={
                'override_var': 'override',
            },
        )


class TestSmartDefaults:
    def _template(self):
        return {
            "base": {
                "retryMode": "standard",
                "stsRegionalEndpoints": "regional",
                "s3UsEast1RegionalEndpoints": "regional",
                "connectTimeoutInMillis": 1000,
                "tlsNegotiationTimeoutInMillis": 1000,
            },
            "modes": {
                "standard": {
                    "connectTimeoutInMillis": {"multiply": 2},
                    "tlsNegotiationTimeoutInMillis": {"multiply": 2},
                },
                "in-region": {
                    "connectTimeoutInMillis": {"multiply": 1},
                    "tlsNegotiationTimeoutInMillis": {"multiply": 1},
                },
                "cross-region": {
                    "connectTimeoutInMillis": {"multiply": 2.8},
                    "tlsNegotiationTimeoutInMillis": {"multiply": 2.8},
                },
                "mobile": {
                    "connectTimeoutInMillis": {"override": 10000},
                    "tlsNegotiationTimeoutInMillis": {"add": 10000},
                    "retryMode": {"override": "adaptive"},
                },
            },
        }

    def _create_default_config_resolver(self):
        return DefaultConfigResolver(self._template())

    @pytest.fixture
    def smart_defaults_factory(self):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = {}
        default_config_resolver = self._create_default_config_resolver()
        return SmartDefaultsConfigStoreFactory(
            default_config_resolver, imds_region_provider=mock.Mock()
        )

    @pytest.fixture
    def fake_session(self):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = {}
        return fake_session

    def _create_config_value_store(self, s3_mapping={}, **override_kwargs):
        constant_provider = ConstantProvider(value='my_sts_regional_endpoint')
        environment_provider = EnvironmentProvider(
            name='AWS_RETRY_MODE', env={'AWS_RETRY_MODE': None}
        )
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = {}
        # Testing with three different providers to validate
        # SmartDefaultsConfigStoreFactory._get_new_chain_provider
        mapping = {
            'sts_regional_endpoints': ChainProvider(
                providers=[constant_provider]
            ),
            'retry_mode': ChainProvider(providers=[environment_provider]),
            's3': SectionConfigProvider('s3', fake_session, s3_mapping),
        }
        mapping.update(**override_kwargs)
        config_store = ConfigValueStore(mapping=mapping)
        return config_store

    def _create_os_environ_patcher(self):
        return mock.patch.object(
            botocore.configprovider.os, 'environ', mock.Mock(wraps=os.environ)
        )

    def test_config_store_deepcopy(self):
        config_store = ConfigValueStore()
        config_store.set_config_provider(
            'constant_value', ConstantProvider('ABC')
        )
        config_store_copy = copy.deepcopy(config_store)
        config_store_copy.set_config_provider(
            'constant_value_copy', ConstantProvider('123')
        )
        assert config_store.get_config_variable('constant_value_copy') is None
        assert config_store_copy.get_config_variable('constant_value') == 'ABC'

    def _create_config_value_store_to_test_merge(self):
        environment_provider = EnvironmentProvider(
            name='AWS_S3_US_EAST_1_REGIONAL_ENDPOINT',
            env={},
        )

        s3_mapping = {
            'us_east_1_regional_endpoint': ChainProvider(
                providers=[environment_provider]
            )
        }

        override_kwargs = {'connect_timeout': ConstantProvider(value=None)}

        config_value_store = self._create_config_value_store(
            s3_mapping=s3_mapping, **override_kwargs
        )

        return config_value_store

    @pytest.mark.parametrize(
        'config_variable,expected_value_before,expected_value_after',
        [
            ['retry_mode', None, 'standard'],
            ['sts_regional_endpoints', 'my_sts_regional_endpoint', 'regional'],
            ['connect_timeout', None, 2],
            ['s3', None, {'us_east_1_regional_endpoint': 'regional'}],
        ],
    )
    def test_config_store_providers_not_mutated_after_merge(
        self,
        config_variable,
        expected_value_before,
        expected_value_after,
        smart_defaults_factory,
    ):
        """Test uses the standard default mode from the template"""

        config_value_store = self._create_config_value_store_to_test_merge()

        provider = config_value_store.get_config_provider(config_variable)

        smart_defaults_factory.merge_smart_defaults(
            config_value_store, 'standard', 'some-region'
        )

        assert provider.provide() == expected_value_before

        assert (
            config_value_store.get_config_variable(config_variable)
            == expected_value_after
        )

    @pytest.mark.parametrize(
        'defaults_mode, retry_mode, sts_regional_endpoints,'
        ' us_east_1_regional_endpoint, connect_timeout',
        [
            ('standard', 'standard', 'regional', 'regional', 2000),
            ('in-region', 'standard', 'regional', 'regional', 1000),
            ('cross-region', 'standard', 'regional', 'regional', 2800),
            ('mobile', 'adaptive', 'regional', 'regional', 10000),
        ],
    )
    def test_get_defualt_config_values(
        self,
        defaults_mode,
        retry_mode,
        sts_regional_endpoints,
        us_east_1_regional_endpoint,
        connect_timeout,
    ):
        default_config_resolver = self._create_default_config_resolver()
        default_values = default_config_resolver.get_default_config_values(
            defaults_mode
        )
        assert default_values['retryMode'] == retry_mode
        assert default_values['stsRegionalEndpoints'] == sts_regional_endpoints
        assert (
            default_values['s3UsEast1RegionalEndpoints']
            == us_east_1_regional_endpoint
        )
        assert default_values['connectTimeoutInMillis'] == connect_timeout

    def test_resolve_default_values_on_config(
        self, smart_defaults_factory, fake_session
    ):
        config_store = self._create_config_value_store()
        smart_defaults_factory.merge_smart_defaults(
            config_store, 'standard', 'foo'
        )
        s3_config = config_store.get_config_variable('s3')
        assert s3_config['us_east_1_regional_endpoint'] == 'regional'
        assert config_store.get_config_variable('retry_mode') == 'standard'
        assert (
            config_store.get_config_variable('sts_regional_endpoints')
            == 'regional'
        )
        assert config_store.get_config_variable('connect_timeout') == 2

    def test_no_resolve_default_s3_values_on_config(
        self, smart_defaults_factory
    ):
        environment_provider = EnvironmentProvider(
            name='AWS_S3_US_EAST_1_REGIONAL_ENDPOINT',
            env={'AWS_S3_US_EAST_1_REGIONAL_ENDPOINT': 'legacy'},
        )
        s3_mapping = {
            'us_east_1_regional_endpoint': ChainProvider(
                providers=[environment_provider]
            )
        }
        config_store = self._create_config_value_store(s3_mapping=s3_mapping)
        smart_defaults_factory.merge_smart_defaults(
            config_store, 'standard', 'foo'
        )
        s3_config = config_store.get_config_variable('s3')
        assert s3_config['us_east_1_regional_endpoint'] == 'legacy'
        assert config_store.get_config_variable('retry_mode') == 'standard'
        assert (
            config_store.get_config_variable('sts_regional_endpoints')
            == 'regional'
        )
        assert config_store.get_config_variable('connect_timeout') == 2

    def test_resolve_default_s3_values_on_config(
        self, smart_defaults_factory, fake_session
    ):
        s3_mapping = {
            'use_arn_region': ChainProvider(
                providers=[ConstantProvider(value=False)]
            )
        }
        config_store = self._create_config_value_store(s3_mapping=s3_mapping)
        smart_defaults_factory.merge_smart_defaults(
            config_store, 'standard', 'foo'
        )
        s3_config = config_store.get_config_variable('s3')
        assert s3_config['us_east_1_regional_endpoint'] == 'regional'
        assert config_store.get_config_variable('retry_mode') == 'standard'
        assert (
            config_store.get_config_variable('sts_regional_endpoints')
            == 'regional'
        )
        assert config_store.get_config_variable('connect_timeout') == 2

    @pytest.mark.parametrize(
        'execution_env_var, region_env_var, default_region_env_var, '
        'imds_region, client_region, resolved_mode',
        [
            (
                'AWS_Lambda_python3.6',
                'us-east-1',
                None,
                None,
                'us-east-1',
                'in-region',
            ),
            (
                'AWS_Lambda_python3.6',
                'us-west-2',
                'us-west-2',
                None,
                'us-east-1',
                'cross-region',
            ),
            (
                'AWS_Lambda_python3.6',
                None,
                None,
                'us-west-2',
                'us-east-1',
                'cross-region',
            ),
            (None, None, 'us-east-1', 'us-east-1', 'us-east-1', 'in-region'),
            (None, None, None, 'us-west-2', 'us-east-1', 'cross-region'),
            (None, None, None, None, 'us-west-2', 'standard'),
        ],
    )
    def test_resolve_auto_mode(
        self,
        execution_env_var,
        region_env_var,
        default_region_env_var,
        imds_region,
        client_region,
        resolved_mode,
    ):
        imds_region_provider = mock.Mock(spec=IMDSRegionProvider)
        imds_region_provider.provide.return_value = imds_region
        default_config_resolver = mock.Mock()
        with mock.patch.object(
            botocore.configprovider.os, 'environ', mock.Mock(wraps=os.environ)
        ) as os_environ_patcher:
            os_environ_patcher.get.side_effect = [
                execution_env_var,
                default_region_env_var,
                region_env_var,
            ]
            smart_defaults_factory = SmartDefaultsConfigStoreFactory(
                default_config_resolver, imds_region_provider
            )
            mode = smart_defaults_factory.resolve_auto_mode(client_region)
            assert mode == resolved_mode

    def test_resolve_auto_mode_imds_region_provider_connect_timeout(self):
        imds_region_provider = mock.Mock(spec=IMDSRegionProvider)
        imds_region_provider.provide.side_effect = ConnectTimeoutError(
            endpoint_url='foo'
        )
        default_config_resolver = mock.Mock()
        with mock.patch.object(
            botocore.configprovider.os, 'environ', mock.Mock(wraps=os.environ)
        ) as os_environ_patcher:
            os_environ_patcher.get.side_effect = [None] * 3
            smart_defaults_factory = SmartDefaultsConfigStoreFactory(
                default_config_resolver, imds_region_provider
            )
            mode = smart_defaults_factory.resolve_auto_mode('us-west-2')
            assert mode == 'standard'


def create_cases():
    service = 'batch'

    return [
        dict(
            service=service,
            environ_map={},
            full_config_map={},
            expected_value=None,
        ),
        dict(
            service=service,
            environ_map={'AWS_ENDPOINT_URL': 'global-from-env'},
            full_config_map={},
            expected_value='global-from-env',
        ),
        dict(
            service=service,
            environ_map={
                f'AWS_ENDPOINT_URL_{service.upper()}': 'service-from-env',
                'AWS_ENDPOINT_URL': 'global-from-env',
            },
            full_config_map={},
            expected_value='service-from-env',
        ),
        dict(
            service=service,
            environ_map={
                'AWS_ENDPOINT_URL': 'global-from-env',
                'AWS_ENDPOINT_URL_S3': 's3-endpoint-url',
            },
            full_config_map={},
            expected_value='global-from-env',
        ),
        dict(
            service=service,
            environ_map={},
            full_config_map={
                'profiles': {'default': {'endpoint_url': 'global-from-config'}}
            },
            expected_value='global-from-config',
        ),
        dict(
            service=service,
            environ_map={},
            full_config_map={
                'profiles': {
                    'default': {
                        'services': 'my-services',
                    }
                },
                'services': {
                    'my-services': {
                        service: {'endpoint_url': "service-from-config"}
                    }
                },
            },
            expected_value='service-from-config',
        ),
        dict(
            service=service,
            environ_map={},
            full_config_map={
                'profiles': {
                    'default': {
                        'services': 'my-services',
                        'endpoint_url': 'global-from-config',
                    }
                },
                'services': {
                    'my-services': {
                        service: {'endpoint_url': "service-from-config"}
                    }
                },
            },
            expected_value='service-from-config',
        ),
        dict(
            service=service,
            environ_map={
                'AWS_ENDPOINT_URL': 'global-from-env',
            },
            full_config_map={
                'profiles': {
                    'default': {
                        'endpoint_url': 'global-from-config',
                    }
                },
            },
            expected_value='global-from-env',
        ),
        dict(
            service=service,
            environ_map={
                f'AWS_ENDPOINT_URL_{service.upper()}': 'service-from-env',
            },
            full_config_map={
                'profiles': {
                    'default': {
                        'endpoint_url': 'global-from-config',
                    }
                },
            },
            expected_value='service-from-env',
        ),
        dict(
            service='s3',
            environ_map={},
            full_config_map={
                'profiles': {
                    'default': {
                        'services': 'my-services',
                        'endpoint_url': 'global-from-config',
                    }
                },
                'services': {
                    'my-services': {
                        service: {'endpoint_url': "service-from-config"}
                    }
                },
            },
            expected_value='global-from-config',
        ),
        dict(
            service='runtime.sagemaker',
            environ_map={},
            full_config_map={
                'profiles': {
                    'default': {
                        'services': 'my-services',
                    }
                },
                'services': {
                    'my-services': {
                        'sagemaker_runtime': {
                            'endpoint_url': "service-from-config"
                        }
                    }
                },
            },
            expected_value='service-from-config',
        ),
        dict(
            service='apigateway',
            environ_map={},
            full_config_map={
                'profiles': {
                    'default': {
                        'services': 'my-services',
                    }
                },
                'services': {
                    'my-services': {
                        'api_gateway': {'endpoint_url': "service-from-config"}
                    }
                },
            },
            expected_value='service-from-config',
        ),
    ]


class TestConfiguredEndpointProvider:
    def assert_does_provide(
        self,
        service,
        environ_map,
        full_config_map,
        expected_value,
    ):
        scoped_config_map = full_config_map.get('profiles', {}).get(
            'default', {}
        )

        chain = ConfiguredEndpointProvider(
            scoped_config=scoped_config_map,
            full_config=full_config_map,
            client_name=service,
            environ=environ_map,
        )
        value = chain.provide()
        assert value == expected_value

    @pytest.mark.parametrize('test_case', create_cases())
    def test_does_provide(self, test_case):
        self.assert_does_provide(**test_case)

    def test_is_deepcopyable(self):
        env = {'AWS_ENDPOINT_URL_BATCH': 'https://endpoint-override'}
        provider = ConfiguredEndpointProvider(
            full_config={}, scoped_config={}, client_name='batch', environ=env
        )

        provider_deepcopy = copy.deepcopy(provider)
        assert provider is not provider_deepcopy
        assert provider.provide() == 'https://endpoint-override'
        assert provider_deepcopy.provide() == 'https://endpoint-override'

        env['AWS_ENDPOINT_URL_BATCH'] = 'https://another-new-endpoint-override'
        assert provider.provide() == 'https://another-new-endpoint-override'
        assert provider_deepcopy.provide() == 'https://endpoint-override'
