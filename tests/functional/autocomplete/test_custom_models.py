# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Shell completion for models installed with ``aws configure add-model``.

These tests replace the builtin botocore data directory with a single
synthetic service so that a complete "bundled" index can be generated in
well under a second.
"""

import glob
import json
import os
import shutil
import sqlite3
import threading
from unittest import mock

from botocore.loaders import Loader

from awscli.autocomplete import db, generator
from awscli.autocomplete import main as autocomplete_main
from awscli.clidriver import create_clidriver
from awscli.testutils import FileCreator, capture_output, unittest

BUILTIN_SERVICE = 'basesvc'


def make_model(
    endpoint_prefix, api_version, operations, full_name='Synthetic Service'
):
    shapes = {'String': {'type': 'string'}}
    ops = {}
    for name, members in operations.items():
        input_shape = f'{name}Request'
        shapes[input_shape] = {
            'type': 'structure',
            'members': {m: {'shape': 'String'} for m in members},
        }
        ops[name] = {
            'name': name,
            'http': {'method': 'POST', 'requestUri': '/'},
            'input': {'shape': input_shape},
        }
    metadata = {
        'apiVersion': api_version,
        'endpointPrefix': endpoint_prefix,
        'jsonVersion': '1.1',
        'protocol': 'json',
        'serviceId': endpoint_prefix,
        'signatureVersion': 'v4',
        'targetPrefix': 'Synthetic',
    }
    if full_name is not None:
        metadata['serviceFullName'] = full_name
    return {
        'version': '2.0',
        'metadata': metadata,
        'operations': ops,
        'shapes': shapes,
    }


class BaseCustomModelCompletionTest(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        root = self.files.rootdir
        self.builtin_models = os.path.join(root, 'builtin')
        self.customer_models = os.path.join(root, 'home', '.aws', 'models')
        self.cache_dir = os.path.join(root, 'home', '.aws', 'cli', 'cache')
        self.index_file = os.path.join(self.cache_dir, '2.0.0.index')
        self.bundled_index = os.path.join(root, 'bundled', 'ac.index')
        os.makedirs(self.customer_models)
        self._write_builtin_model()

        config_file = self.files.create_file('config', '')
        credentials_file = self.files.create_file('credentials', '')
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_CONFIG_FILE': config_file,
            'AWS_SHARED_CREDENTIALS_FILE': credentials_file,
        }
        patches = [
            mock.patch('os.environ', self.environ),
            mock.patch.object(
                Loader, 'BUILTIN_DATA_PATH', self.builtin_models
            ),
            mock.patch.object(
                Loader, 'CUSTOMER_DATA_PATH', self.customer_models
            ),
            mock.patch.object(db, 'INDEX_FILE', self.index_file),
            mock.patch.object(db, 'BUILTIN_INDEX_FILE', self.bundled_index),
            mock.patch.object(db, 'CUSTOMER_MODELS_DIR', self.customer_models),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        # Build the bundled index before any custom models are installed,
        # the same way it is built when the CLI is packaged.
        generator.generate_index(self.bundled_index)

    def tearDown(self):
        self.files.remove_all()

    def _write_builtin_model(self):
        path = os.path.join(
            self.builtin_models,
            BUILTIN_SERVICE,
            '2020-01-01',
            'service-2.json',
        )
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as f:
            json.dump(
                make_model(
                    BUILTIN_SERVICE,
                    '2020-01-01',
                    {'ListThings': ['MaxItems'], 'GetThing': ['ThingId']},
                    full_name='Builtin Synthetic Service',
                ),
                f,
            )

    def add_model(self, model, service_name=None):
        model_file = self.files.create_file(
            f'model-{len(os.listdir(self.files.rootdir))}.json',
            json.dumps(model),
        )
        cmd = [
            'configure',
            'add-model',
            '--service-model',
            f'file://{model_file}',
        ]
        if service_name is not None:
            cmd += ['--service-name', service_name]
        with capture_output() as captured:
            rc = create_clidriver().main(cmd)
        return rc, captured.stderr.getvalue()

    def complete(self, command_line):
        # Goes through the same entry point as the aws_completer executable.
        with capture_output() as captured:
            autocomplete_main.autocomplete(command_line)
        return sorted(captured.stdout.getvalue().split())

    def assert_add_model(self, model, service_name=None):
        rc, stderr = self.add_model(model, service_name)
        self.assertEqual(rc, 0, stderr)
        self.assertEqual(stderr, '')

    def query_index(self, query, **params):
        conn = sqlite3.connect(self.index_file)
        try:
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()


class TestAddModelCompletion(BaseCustomModelCompletionTest):
    def test_completes_new_custom_service(self):
        self.assert_add_model(
            make_model(
                'widgets',
                '2024-01-01',
                {'ListWidgets': ['MaxItems'], 'DescribeWidget': ['WidgetId']},
            )
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        self.assertEqual(
            self.complete('aws widgets '), ['describe-widget', 'list-widgets']
        )
        self.assertEqual(
            self.complete('aws widgets describe-widget --widg'),
            ['--widget-id'],
        )
        # Builtin services are still completed.
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])
        self.assertEqual(
            self.complete(f'aws {BUILTIN_SERVICE} get-thing --thi'),
            ['--thing-id'],
        )

    def test_add_model_does_not_touch_completion_cache(self):
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        self.assertFalse(os.path.exists(self.cache_dir))

    def test_index_written_only_to_user_cache(self):
        with open(self.bundled_index, 'rb') as f:
            bundled_contents = f.read()
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        self.assertTrue(os.path.isfile(self.index_file))
        with open(self.bundled_index, 'rb') as f:
            self.assertEqual(f.read(), bundled_contents)
        # Only the index remains; no temporary files.
        self.assertEqual(os.listdir(self.cache_dir), ['2.0.0.index'])

    def test_removed_model_is_removed_from_completion(self):
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        shutil.rmtree(os.path.join(self.customer_models, 'widgets'))
        self.assertEqual(self.complete('aws widg'), [])
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])

    def test_replacing_model_removes_stale_entries(self):
        self.assert_add_model(
            make_model(
                'widgets',
                '2024-01-01',
                {'ListWidgets': ['MaxItems'], 'DeleteWidget': ['WidgetId']},
            )
        )
        self.assertIn('delete-widget', self.complete('aws widgets '))
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': ['Filter']})
        )
        self.assertEqual(self.complete('aws widgets '), ['list-widgets'])
        self.assertEqual(
            self.complete('aws widgets list-widgets --fil'), ['--filter']
        )
        self.assertEqual(self.complete('aws widgets list-widgets --max'), [])

    def test_indexes_latest_installed_api_version(self):
        self.assert_add_model(
            make_model('widgets', '2025-01-01', {'ListWidgets': ['NewArg']})
        )
        # Installing an older version afterwards does not change which
        # version the CLI uses, so completions must not change either.
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': ['OldArg']})
        )
        self.assertEqual(
            self.complete('aws widgets list-widgets --new'), ['--new-arg']
        )
        self.assertEqual(self.complete('aws widgets list-widgets --old'), [])

    def test_service_name_override(self):
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []}),
            service_name='my-widgets',
        )
        self.assertEqual(self.complete('aws my-wid'), ['my-widgets'])
        self.assertEqual(self.complete('aws widg'), [])
        self.assertEqual(self.complete('aws my-widgets '), ['list-widgets'])

    def test_override_builtin_service_without_duplicates(self):
        self.assert_add_model(
            make_model(
                BUILTIN_SERVICE, '2030-01-01', {'ReplaceThing': ['ThingId']}
            )
        )
        self.assertEqual(
            self.complete(f'aws {BUILTIN_SERVICE} '), ['replace-thing']
        )
        self.assertEqual(
            self.query_index(
                "SELECT COUNT(*) FROM command_table "
                "WHERE parent = 'aws' AND command = :name",
                name=BUILTIN_SERVICE,
            ),
            [(1,)],
        )
        self.assertEqual(
            self.query_index(
                "SELECT COUNT(*) FROM param_table "
                "WHERE parent = :parent AND command = 'replace-thing' "
                "AND argname = 'thing-id'",
                parent=f'aws.{BUILTIN_SERVICE}',
            ),
            [(1,)],
        )

    def test_preserves_other_custom_services(self):
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        self.assert_add_model(
            make_model('gadgets', '2024-01-01', {'ListGadgets': []})
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        self.assertEqual(self.complete('aws gadg'), ['gadgets'])
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])

    def test_model_without_service_full_name(self):
        self.assert_add_model(
            make_model(
                'widgets', '2024-01-01', {'ListWidgets': []}, full_name=None
            )
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])


class TestIndexingFailures(BaseCustomModelCompletionTest):
    def test_unwritable_cache_keeps_model_and_builtin_completion(self):
        # Make the cache directory impossible to create.
        os.makedirs(os.path.dirname(self.cache_dir))
        self.files.create_file(
            os.path.join('home', '.aws', 'cli', 'cache'), 'not a directory'
        )
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        model_path = os.path.join(
            self.customer_models, 'widgets', '2024-01-01', 'service-2.json'
        )
        self.assertTrue(os.path.isfile(model_path))
        # Completion falls back to the bundled index.
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])
        self.assertEqual(self.complete('aws widg'), [])
        # Commands for the model still work.
        command_table = create_clidriver().subcommand_table
        self.assertIn(
            'list-widgets', command_table['widgets'].subcommand_table
        )

    def test_unindexable_model_falls_back_to_bundled_index(self):
        broken = make_model('widgets', '2024-01-01', {'ListWidgets': []})
        broken['operations']['ListWidgets']['input'] = {'shape': 'Missing'}
        self.assert_add_model(broken)
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])
        self.assertEqual(self.complete('aws widg'), [])
        self.assertTrue(os.path.isfile(f'{self.index_file}.failed'))
        # Fixing the model is picked up on the next completion.
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        self.assertFalse(os.path.exists(f'{self.index_file}.failed'))


class TestUserIndexUpdates(BaseCustomModelCompletionTest):
    def install_model(self, name, operations):
        path = os.path.join(
            self.customer_models, name, '2024-01-01', 'service-2.json'
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(make_model(name, '2024-01-01', operations), f)

    def test_requires_bundled_index(self):
        os.remove(self.bundled_index)
        self.install_model('widgets', {'ListWidgets': []})
        with self.assertRaises(OSError):
            generator.update_user_index()
        self.assertFalse(os.path.exists(self.index_file))

    def test_corrupt_bundled_index_fails_without_partial_index(self):
        with open(self.bundled_index, 'wb') as f:
            f.write(b'corrupt')
        self.install_model('widgets', {'ListWidgets': []})
        with self.assertRaises(sqlite3.DatabaseError):
            generator.update_user_index()
        self.assertFalse(os.path.exists(self.index_file))
        self.assertEqual(glob.glob(f'{self.index_file}.*.temp'), [])

    def test_concurrent_updates_converge(self):
        # There is no lock: concurrent updates each write a complete index,
        # and a stale result is rebuilt on the next completion.
        names = [f'svc{i}' for i in range(4)]
        errors = []

        def install_and_update(name):
            try:
                self.install_model(name, {'ListThings': []})
                generator.update_user_index()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=install_and_update, args=(name,))
            for name in names
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.complete('aws svc'), names)

    def test_readers_never_see_partial_index(self):
        self.install_model('widgets', {'ListWidgets': []})
        generator.update_user_index()
        stop = threading.Event()
        reads = []
        errors = []

        def read_continuously():
            while not stop.is_set():
                try:
                    conn = sqlite3.connect(self.index_file)
                    try:
                        rows = conn.execute(
                            "SELECT command FROM command_table "
                            "WHERE parent = 'aws'"
                        ).fetchall()
                    finally:
                        conn.close()
                    names = {row[0] for row in rows}
                    if not {'widgets', BUILTIN_SERVICE} <= names:
                        errors.append(names)
                    reads.append(1)
                except sqlite3.Error as e:
                    errors.append(e)

        reader = threading.Thread(target=read_continuously)
        reader.start()
        try:
            for _ in range(5):
                generator.update_user_index()
        finally:
            stop.set()
            reader.join()
        self.assertEqual(errors, [])
        self.assertGreater(len(reads), 0)


class TestRefreshOnCompletion(BaseCustomModelCompletionTest):
    def simulate_upgrade(self):
        # The user index name contains the CLI version, so a new version
        # starts without one.
        new_index = os.path.join(self.cache_dir, '2.0.1.index')
        patch = mock.patch.object(db, 'INDEX_FILE', new_index)
        patch.start()
        self.addCleanup(patch.stop)
        return new_index

    def marker(self):
        return f'{self.index_file}.failed'

    def test_first_completion_after_upgrade_rebuilds_index(self):
        self.assert_add_model(
            make_model('widgets', '2024-01-01', {'ListWidgets': []})
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        new_index = self.simulate_upgrade()
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        self.assertTrue(os.path.isfile(new_index))
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])

    def test_no_index_created_without_custom_models(self):
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])
        self.assertFalse(os.path.exists(self.cache_dir))

    def test_up_to_date_index_is_not_rebuilt(self):
        self.install_widgets()
        autocomplete_main.refresh_user_index()
        with mock.patch.object(generator, 'update_user_index') as update:
            autocomplete_main.refresh_user_index()
        update.assert_not_called()

    def test_rebuilds_index_without_fingerprint(self):
        # For example, an index generated by an older CLI or by
        # scripts/gen-ac-index.
        self.install_widgets()
        os.makedirs(self.cache_dir)
        shutil.copyfile(self.bundled_index, self.index_file)
        self.assertEqual(self.complete('aws widg'), ['widgets'])

    def test_replaces_corrupt_user_index(self):
        self.install_widgets()
        os.makedirs(self.cache_dir)
        with open(self.index_file, 'wb') as f:
            f.write(b'not a sqlite database')
        self.assertEqual(self.complete('aws widg'), ['widgets'])

    def test_skips_without_bundled_index(self):
        os.remove(self.bundled_index)
        self.install_widgets()
        with mock.patch.object(generator, 'update_user_index') as update:
            autocomplete_main.refresh_user_index()
        update.assert_not_called()

    def test_failure_is_retried_only_after_models_change(self):
        self.install_widgets()
        with mock.patch.object(
            generator, 'update_user_index', side_effect=ValueError('boom')
        ) as update:
            autocomplete_main.refresh_user_index()
            autocomplete_main.refresh_user_index()
        self.assertEqual(update.call_count, 1)
        self.assertTrue(os.path.isfile(self.marker()))
        # Completion still works from the bundled index.
        self.assertEqual(self.complete('aws bases'), [BUILTIN_SERVICE])
        # Changing the installed models retries and clears the marker.
        self.assert_add_model(
            make_model('gadgets', '2024-01-01', {'ListGadgets': []})
        )
        self.assertEqual(self.complete('aws widg'), ['widgets'])
        self.assertEqual(self.complete('aws gadg'), ['gadgets'])
        self.assertFalse(os.path.exists(self.marker()))

    def install_widgets(self):
        path = os.path.join(
            self.customer_models, 'widgets', '2024-01-01', 'service-2.json'
        )
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as f:
            json.dump(
                make_model('widgets', '2024-01-01', {'ListWidgets': []}), f
            )
