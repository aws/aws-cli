import unittest
from awscli.customizations.cloudformation.modules.flatten import _extract_by_pattern

class TestExtractByPattern(unittest.TestCase):
    """Tests for the _extract_by_pattern function in flatten.py"""

    def test_root_pattern(self):
        """Test extraction with root pattern"""
        source = {"a": 1, "b": 2}
        self.assertEqual(_extract_by_pattern(source, "$"), [source])
        self.assertEqual(_extract_by_pattern(source, ""), [source])

    def test_direct_property_access(self):
        """Test extraction of direct properties"""
        source = {"users": [{"name": "user1"}, {"name": "user2"}]}
        self.assertEqual(_extract_by_pattern(source, "$.users"), [source["users"]])
        self.assertEqual(_extract_by_pattern(source, "users"), [source["users"]])

    def test_wildcard_for_dictionaries(self):
        """Test wildcard extraction for dictionaries"""
        source = {"a": 1, "b": 2, "c": 3}
        result = _extract_by_pattern(source, "$.*")
        self.assertEqual(sorted(result), [1, 2, 3])

    def test_wildcard_for_lists(self):
        """Test wildcard extraction for lists"""
        source = {"items": [1, 2, 3]}
        self.assertEqual(_extract_by_pattern(source, "$.items[*]"), [1, 2, 3])

    def test_nested_property_access(self):
        """Test extraction of nested properties"""
        source = {"user": {"profile": {"name": "John", "age": 30}}}
        self.assertEqual(_extract_by_pattern(source, "$.user.profile.name"), ["John"])

    def test_array_index_access(self):
        """Test extraction with specific array index"""
        source = {"items": [10, 20, 30, 40]}
        self.assertEqual(_extract_by_pattern(source, "$.items[2]"), [30])

    def test_nested_array_wildcard(self):
        """Test extraction from nested arrays with wildcard"""
        source = {"groups": [
            {"users": [{"id": 1}, {"id": 2}]},
            {"users": [{"id": 3}, {"id": 4}]}
        ]}
        expected = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        self.assertEqual(_extract_by_pattern(source, "$.groups[*].users[*]"), expected)

    def test_property_from_array_items(self):
        """Test extraction of specific properties from array items"""
        source = {"users": [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
            {"name": "Charlie", "age": 35}
        ]}
        self.assertEqual(_extract_by_pattern(source, "$.users[*].name"), 
                         ["Alice", "Bob", "Charlie"])

    def test_direct_array_access_on_property(self):
        """Test direct array access on a property"""
        source = {"users": [
            {"name": "user1", "roles": ["admin", "developer"]},
            {"name": "user2", "roles": ["reader"]}
        ]}
        expected = ["admin", "developer", "reader"]
        self.assertEqual(_extract_by_pattern(source, "$.users[*].roles[*]"), expected)

    def test_nonexistent_path(self):
        """Test extraction with nonexistent path"""
        source = {"a": {"b": 1}}
        self.assertEqual(_extract_by_pattern(source, "$.c"), [])
        self.assertEqual(_extract_by_pattern(source, "$.a.c"), [])

    def test_complex_nested_structure(self):
        """Test extraction from a complex nested structure"""
        source = {
            "services": [
                {
                    "name": "api",
                    "environments": ["dev", "prod"]
                },
                {
                    "name": "worker",
                    "environments": ["dev", "prod"]
                },
                {
                    "name": "scheduler",
                    "environments": ["prod"]
                }
            ]
        }
        
        # Extract all environment arrays
        env_arrays = _extract_by_pattern(source, "$.services[*].environments")
        self.assertEqual(env_arrays, [["dev", "prod"], ["dev", "prod"], ["prod"]])
        
        # Extract all environments as flattened list
        envs = _extract_by_pattern(source, "$.services[*].environments[*]")
        self.assertEqual(sorted(envs), ["dev", "dev", "prod", "prod", "prod"])
        
    def test_service_config_structure(self):
        """Test extraction from a structure similar to ServiceConfig"""
        source = {
            "services": [
                {
                    "name": "api",
                    "environments": ["dev", "prod"]
                },
                {
                    "name": "worker",
                    "environments": ["dev", "prod"]
                }
            ]
        }
        
        # Test direct access to the services array
        services = _extract_by_pattern(source, "services")
        self.assertEqual(services, [source["services"]])
        
        # Test access to individual services
        individual_services = _extract_by_pattern(source, "services[*]")
        self.assertEqual(len(individual_services), 2)
        self.assertEqual(individual_services[0]["name"], "api")
        self.assertEqual(individual_services[1]["name"], "worker")
        
    def test_empty_list(self):
        """Test extraction from an empty list"""
        source = {"items": []}
        self.assertEqual(_extract_by_pattern(source, "$.items[*]"), [])
        
    def test_malformed_pattern(self):
        """Test extraction with malformed patterns"""
        source = {"a": 1}
        # Unclosed bracket
        self.assertEqual(_extract_by_pattern(source, "a["), [])
        # Invalid index
        self.assertEqual(_extract_by_pattern(source, "a[abc]"), [])

if __name__ == '__main__':
    unittest.main()
