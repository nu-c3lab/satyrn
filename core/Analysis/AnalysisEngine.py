'''
This file is part of Satyrn.
Satyrn is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.
Satyrn is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Satyrn.
If not, see <https://www.gnu.org/licenses/>.
'''

from typing import List, Dict

from sqlalchemy import nullslast
from sqlalchemy.orm import Session, Query

from core.api import utils
from core.RingObjects.Ring import Ring
from core.Analysis.QueryArguments import QueryArguments
from core.Analysis.AnalysisPlan import AnalysisPlan
from core.Analysis.QueryBuilderSQR import QueryBuilderSQR
from core.Analysis.OperationOntology import OperationOntology
from core.Planning.AnalysisPlanParser import AnalysisPlanParser
from core.Analysis.SQRField import SQRField
from core.Operations.ArgType import ArgType

class AnalysisEngine:
    def __init__(self,
                 ring: Ring = None):
        self.query_builder_sqr = QueryBuilderSQR()
        self.ring = ring
        self.ontology = OperationOntology()
        self.plan_parser = AnalysisPlanParser(self.ontology)

    def sqr_single_ring_analysis(self,
                                 analysis_plan: AnalysisPlan,
                                 ring: Ring,
                                 sess: Session) -> dict:

        new_query_args = self.query_builder_sqr.build_query_arguments_from_sqr_plan(analysis_plan, self.ontology)

        query = self.complex_query(new_query_args, ring, sess)

        units = self.get_units(new_query_args, ring)

        # Run the query
        raw_results = [list(q) for q in query.all()]
        outermost_query = max(map(lambda alias: alias.partition('_')[2], new_query_args.keys()))
        results = {
            "length": len(raw_results),
            "results": raw_results,
            "fieldNames": list(new_query_args[f'alias_{outermost_query}'].select),
            "units": {"results": units}
        }

        return results

    def complex_query(self,
                      query_args: Dict[str, QueryArguments],
                      ring: Ring,
                      sess: Session) -> dict:
        queries = {}
        # for alias in map(lambda alias_num: f'alias_{alias_num}', range(len(query_args))):
        for alias in query_args.keys():
            subqueries = {from_ : queries[from_].subquery(from_) for from_ in query_args[alias].froms if from_ in queries}
            queries[alias] = self.simple_query(query_args[alias], subqueries, ring, sess)
        # return queries[f'alias_{len(queries) - 1}']
        return list(queries.values())[-1]

    def same_fields(self, field, field_name):
        return field.name == field_name

    def convert_select_strings_to_fields(self,
                                          alias_args: QueryArguments):
        return [next(filter(lambda field: self.same_fields(field, select_name), alias_args.query_fields)) for select_name in alias_args.select]

    def convert_groupby_strings_to_fields(self,
                                          alias_args: QueryArguments):
        return [next(filter(lambda field: self.same_fields(field, group_by), alias_args.query_fields)) for group_by in alias_args.group_bys]

    def convert_sortby_strings_to_fields(self,
                                         alias_args: QueryArguments):
        return [{'attribute': next(filter(lambda field: self.same_fields(field, sort_by['attribute']), alias_args.query_fields)), 'direction': sort_by['direction']} for sort_by in alias_args.sort_attributes]

    def get_units(self,
                  query_args: Dict[str, QueryArguments],
                  ring: Ring) -> List[str]:

        units = []
        outermost_query_num = max(map(lambda alias: alias.partition('_')[2], query_args.keys()))
        outermost_query = f'alias_{outermost_query_num}'
        for field_name in query_args[outermost_query].select:
            sqrfield = query_args[outermost_query].sqrfields[field_name]
            try:
                unit_pair = self._get_field_units(ring, sqrfield.has_count_operation, sqrfield.satyrn_entity, sqrfield.satyrn_attribute)
            except ValueError as e:
                unit_pair = ["", ""]
            # per_string = self.get_per_string(sqrfield, query_args, ring)
            per_string = '' # no per strings for now
            units.append([unit + per_string for unit in unit_pair])

        return units

    def _get_field_units(self,
                         ring: Ring,
                         entity_unit: str,
                         entity_name: str,
                         attribute_name: str,
                         base_unit: bool = True) -> List[str]:
        """
        Gets the units for the given attribute.
        Note: Defaults to using the nicename of the entity/attribute if no unit is available.
        :param ring:
        :type ring:
        :param entity_unit:
        :type entity_unit:
        :param entity_name:
        :type entity_name:
        :param attribute_name:
        :type attribute_name:
        :param base_unit:
        :type base_unit:
        :return:
        :rtype:
        """

        if not attribute_name:
            return ["", ""]

        # Get the Ring Entity corresponding to the entity name
        entity_obj = ring.get_entity_by_name(entity_name)

        # Check if the attribute_name has partial date denomination in it (e.g. contributionDate:year)
        date_denomination = utils.contains_date_denomination(attribute_name)
        attr_partial_date_type = None
        if date_denomination:
            attribute_name = date_denomination.group(1)
            attr_partial_date_type = date_denomination.group(2)

        if attribute_name in entity_obj.attributes:
            # Get the attribute obj from attribute_name
            attr_obj = entity_obj.attributes[attribute_name]

            # Get the units for the attribute
            if attr_obj.units:
                return attr_obj.units
            elif entity_unit and ArgType.Identifier in attr_obj.type:
                return entity_obj.nicename
            elif not base_unit:
                return attr_obj.nicename
            else:
                return ['', '']
        else:
            # Get the units as the nicename for this entity
            return entity_obj.nicename

    def get_pers(self,
                 sqrfield: SQRField,
                 query_args):
        def get_base_pers(sqrfield, query_args=None):
            if type(sqrfield.field) == SQRField:
                return get_base_pers(sqrfield.field, query_args)
            elif type(sqrfield.field) == dict:
                return get_base_pers(sqrfield.field['arguments'][0], query_args)
            else: # base case
                return query_args[sqrfield.subplan_name].group_bys

        last_subquery = f'alias_{len(query_args) - 1}'
        return filter(lambda group_by_field:
                          utils.entity_from_subquery_name(group_by_field, query_args) not in map(lambda group_by: utils.entity_from_subquery_name(group_by, query_args), query_args[last_subquery].group_bys),
                      get_base_pers(sqrfield, query_args)) if sqrfield.is_analysis_operation else []

    def get_per_string(self,
                       sqrfield: SQRField,
                       query_args,
                       ring: Ring) -> str:
        per_string = ""
        for per in self.get_pers(sqrfield, query_args):
            per_field_dict = utils.entity_from_subquery_name(per, list(query_args.keys()))
            per_string += f" per {self._get_field_units(ring, True, per_field_dict['entity'], per_field_dict['field'], False)[0]}"
        return per_string

    def simple_query(self,
                     alias_args: QueryArguments,
                     subqueries: List[Query],
                     ring: Ring,
                     session: Session):
        """
        Build a basic SQL Alchemy query from the provided Satyrn plan.
        The query includes the fields to select, filters, joins, and groupbys.
        :param alias_args:
        :type alias_args:
        :param subqueries:
        :type subqueries:
        :param ring:
        :type ring:
        :param session:
        :type session:
        :return:
        :rtype:
        """

        # Build the basic query (including fields to select, filters, joins, multi-table entity joins)
        self.query_builder_sqr.update_query_arguments(alias_args, subqueries, ring, self.ontology)

        remaining_fields = self.convert_select_strings_to_fields(alias_args)
        query = session.query()
        # Create the SQL Alchemy query object (add one column at a time until there is a table in the query)
        while not (query.selectable.columns and query.selectable.froms):
            first_field = remaining_fields[0]
            remaining_fields = remaining_fields[1:]
            query = query.add_columns(first_field)

        alias_args.tables.add(query.selectable.froms[0].name)
        if len(query.selectable.froms) > 1:
            print("WARNING: this case is not handled")

        # Add joins
        query = self.query_builder_sqr.add_joins_to_query(query, alias_args, ring)

        # Add remaining fields
        query = query.add_columns(*remaining_fields)

        # Add filters
        if alias_args.filter:
            filter_field, _ = ring.db_interface.get_field_label_and_joins_for_operation(ring, alias_args.filter, self.ontology, subqueries)
            query = query.filter(filter_field)
        if alias_args.having:
            filter_field, _ = ring.db_interface.get_field_label_and_joins_for_operation(ring, alias_args.having, self.ontology, subqueries)
            query = query.having(filter_field)

        # Add groupby to SQLAlchemy query
        query = query.group_by(*self.convert_groupby_strings_to_fields(alias_args))

        # Add sorts to the query, if they are specified
        query = query.order_by(*map(lambda sort:
                                        nullslast(sort['attribute'].desc() if sort['direction'] == 'desc' else sort['attribute'].asc()),
                                    self.convert_sortby_strings_to_fields(alias_args)))

        # Add limit
        query = query.limit(alias_args.limit)

        return query
