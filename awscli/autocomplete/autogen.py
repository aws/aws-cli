"""This module is used to auto-generate server side completion data.

This module can be used during the build process to generate any new
server side autocompletions based on updated service models.
It can also be used to regen completion data as new heuristics are added.

"""
import logging
from difflib import SequenceMatcher
from collections import namedtuple


LOG = logging.getLogger(__name__)
Resource = namedtuple('Resource', ['resource_name', 'ident_name',
                                   'input_parameters', 'operation', 'jp_expr'])


class ServerCompletionHeuristic(object):
    # Prefix that typically indicates listing resources,
    # e.g ListResources, DescribeResources, etc.
    _RESOURCE_VERB_PREFIX = ('list', 'describe')
    _OPERATION_EXCLUDES = ('create',)

    def __init__(self, singularize=None):
        if singularize is None:
            singularize = BasicSingularize()
        self._singularize = singularize

    def generate_completion_descriptions(self, service_model,
                                         prune_completions=True):
        """

        :param service_model: A botocore.model.ServiceModel.
        :param prune_completions: If True, the generated file will be
            pruned of unused resources not used by completion operations.

        """
        # This method is a best-effort attempt at generating server side
        # auto-completion data based on a set of heuristics.  It's not
        # completely accurate and the results should be manually vetted.

        # candidate -> a potential operation that can be used to
        #   to describe a resource (e.g ListResources, DescribeResources)
        # non_candidate -> a potential operation that can use
        #   auto-completion data (e.g DeleteResource, UpdateResource)
        candidates = []
        for op_name in service_model.operation_names:
            if op_name.lower().startswith(self._RESOURCE_VERB_PREFIX):
                candidates.append(op_name)
        all_resources = self._generate_resource_descriptions(
            candidates, service_model)
        all_operations = self._generate_operations(
            self._filter_operation_names(service_model.operation_names),
            all_resources, service_model)
        if prune_completions:
            self._prune_resource_identifiers(all_resources, all_operations)
        return {
            'version': '1.0',
            'resources': all_resources,
            'operations': all_operations,
        }

    def _filter_operation_names(self, op_names):
        return [name for name in op_names
                if not name.lower().startswith(self._OPERATION_EXCLUDES)]

    def _generate_resource_descriptions(self, candidates, service_model):
        all_resources = {}
        for op_name in candidates:
            resources = self._resource_for_single_operation(
                op_name, service_model)
            if resources is not None:
                for resource in resources:
                    self._inject_resource(all_resources, resource)
        return all_resources

    def _generate_operations(self, op_names, resources, service_model):
        # member_name -> resource
        # This is a simplification we're making for now, it's not at all
        # an actual limitation of auto-generating completion data.
        # If there is a resource that has ``inputParameters`` (i.e required
        # params), then we don't generate completions for you.
        reverse_mapping = {}
        for name, identifier_map in resources.items():
            if identifier_map.get('inputParameters', {}):
                # If there are required inputParameters for a resource
                # we're going to skip them for now.  We should come back
                # to this, it's possible to auto generate these parameters
                # in many cases.
                continue
            for key in identifier_map['resourceIdentifier']:
                reverse_mapping[key] = name
        op_map = {}
        for op_name in op_names:
            self._add_completion_data_for_operation(
                op_map, op_name, service_model, reverse_mapping
            )
        return op_map

    def _add_completion_data_for_operation(self, op_map, op_name,
                                           service_model, reverse_mapping):
        op_model = service_model.operation_model(op_name)
        input_shape = op_model.input_shape
        if not input_shape:
            return
        for member in input_shape.members:
            member_name = self._find_matching_member_name(
                member, reverse_mapping)
            if member_name is None:
                continue
            resource_name = reverse_mapping[member_name]
            op = op_map.setdefault(op_name, {})
            param = op.setdefault(member, {})
            param['completions'] = [
                {'parameters': {},
                 'resourceName': resource_name,
                 'resourceIdentifier': member_name}
            ]

    def _find_matching_member_name(self, member, reverse_mapping):
        # Try to find something in the reverse mapping that's close
        # to the member name.  This is really inefficient but this is
        # a build time step so we don't really care about perf.
        if member in reverse_mapping:
            return member
        matcher = SequenceMatcher()
        matcher.set_seq2(member)
        for candidate in reverse_mapping:
            matcher.set_seq1(candidate)
            match_ratio = matcher.ratio()
            if match_ratio > 0.9:
                return candidate

    def _inject_resource(self, all_resources, resource):
        r = all_resources.setdefault(resource.resource_name, {})
        r['operation'] = resource.operation
        ident = r.setdefault('resourceIdentifier', {})
        if resource.input_parameters:
            r['inputParameters'] = resource.input_parameters
        ident[resource.ident_name] = resource.jp_expr

    def _resource_for_single_operation(self, op_name, service_model):
        # This heuristic works if there's a List/Describe operation
        # that has only one shape in the output that's of type list.
        # It will then find that inspect that list member to find
        # the best guess at which identifier maps to the resource.
        # This is a best effort attempt and relies heavily on naming
        # conventions.
        op_model = service_model.operation_model(op_name)
        output = op_model.output_shape
        list_members = [member for member, shape in output.members.items()
                        if shape.type_name == 'list']
        if len(list_members) != 1:
            LOG.debug("Operation does not have exactly one list member, "
                      "skipping: %s (%s)", op_name, list_members)
            return
        resource_member_name = list_members[0]
        list_member = output.members[resource_member_name].member
        required_members = []
        if op_model.input_shape is not None:
            required_members = op_model.input_shape.required_members
        if list_member.type_name == 'structure':
            return self._resource_from_structure(
                op_name, resource_member_name, list_member, required_members)
        elif list_member.type_name == 'string':
            return [self._resource_from_string(
                op_name, resource_member_name, required_members,
            )]

    def _resource_from_structure(self, op_name,
                                 resource_member_name, list_member,
                                 required_members):
        op_with_prefix_removed = self._remove_verb_prefix(op_name)
        singular_name = self._singularize.make_singular(
            op_with_prefix_removed)
        resources = []
        for member_name in list_member.members:
            jp_expr = (
                '{resource_member_name}[].{member_name}').format(
                    resource_member_name=resource_member_name,
                    member_name=member_name)
            r = Resource(singular_name, member_name, required_members,
                         op_name, jp_expr)
            resources.append(r)
        return resources

    def _resource_from_string(self, op_name, resource_member_name,
                              required_members):
        op_with_prefix_removed = self._remove_verb_prefix(op_name)
        singular_name = self._singularize.make_singular(
            op_with_prefix_removed)
        singular_member_name = self._singularize.make_singular(
            resource_member_name)
        r = Resource(singular_name, singular_member_name, required_members,
                     op_name,
                     '{resource_member_name}[]'.format(
                         resource_member_name=resource_member_name))
        return r

    def _remove_verb_prefix(self, op_name):
        for prefix in self._RESOURCE_VERB_PREFIX:
            # 'ListResources' -> 'Resources'
            if op_name.lower().startswith(prefix):
                op_with_prefix_removed = op_name[len(prefix):]
                return op_with_prefix_removed

    def _prune_resource_identifiers(self, all_resources, all_operations):
        used_identifiers = self._get_identifiers_referenced_by_operations(
            all_operations)
        for resource, resource_data in list(all_resources.items()):
            identifiers = resource_data['resourceIdentifier']
            known_ids_for_resource = used_identifiers.get(resource, set())
            for identifier_name in list(identifiers):
                if identifier_name not in known_ids_for_resource:
                    del identifiers[identifier_name]
            if not identifiers:
                # If there's no identifiers used by an autocompletion
                # operation, then we don't need the resource.
                del all_resources[resource]

    def _get_identifiers_referenced_by_operations(self, operations):
        # Dict of resourceName -> Set[resourceIdentifiers]j
        used_identifiers = {}
        for completion in self._all_completions(operations):
            used_identifiers.setdefault(completion['resourceName'], set()).add(
                completion['resourceIdentifier'])
        return used_identifiers

    def _all_completions(self, operations):
        for params in operations.values():
            for completions in params.values():
                for completion in completions['completions']:
                    yield completion


class BasicSingularize(object):
    """Simple implementation of making a word singular.

    Where possible, you should use nltk.stem.WordNetLemmatizer.
    It's not included here as a default to avoid a hard dependency
    on nltk.

    """

    def make_singular(self, name):
        # Certificates -> Certificate
        if name.endswith('ies'):
            return name[:-3] + 'y'
        elif name.endswith('es'):
            return name[:-1]
        elif name.endswith('s'):
            return name[:-1]
        else:
            return name
