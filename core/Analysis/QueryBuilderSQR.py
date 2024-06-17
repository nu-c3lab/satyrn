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

from itertools import combinations, count
from typing import Union, Tuple, List, Dict

from sqlalchemy.orm import Query

from core.RingObjects.RingJoin import RingJoin
from core.RingObjects.Ring import Ring
from .QueryArguments import QueryArguments
from core.Analysis.AnalysisPlan import AnalysisPlan, AnalysisSubplan
from .OperationOntology import OperationOntology
from .SQRField import SQRField
from core.api import utils

import networkx as nx


class QueryBuilderSQR:

    def build_query_arguments_from_sqr_plan(self,
                                            analysis_plan: AnalysisPlan,
                                            ontology: OperationOntology) -> Dict[str, QueryArguments]:
        # Init the dictionary that will map each subplans steps to the how they will be referred to by other subplans
        step_to_field = {}
        alias_to_queryargs = {}
        ordered_plan_graph = list(nx.topological_sort(analysis_plan.plan_graph))

        # Iterate from innermost query to outermost
        # for current_alias_idx in range(len(analysis_plan.subplans.keys())):   # This is how it used to be. Look here if something bad happens.
        for current_subplan_alias in analysis_plan.subplans.keys():
            # Keep track of the steps we're resolving in the current subplan
            # current_subplan_alias = f"alias_{current_alias_idx}"
            step_to_field[current_subplan_alias] = {}

            # Get the current subplan we're examining
            current_subplan = analysis_plan.subplans[current_subplan_alias]

            # Init the QueryArguments object for this subquery
            alias_to_queryargs[current_subplan_alias] = QueryArguments([], set(), {}, set(), [], [], [], [], [], [])

            # Map each of the steps of this subquery to the name of the column/entity/operation they refer to
            for step_ref in ordered_plan_graph:
                if step_ref in current_subplan.steps:

                    # Get the current step of the current subplan
                    current_step = current_subplan.steps[step_ref]

                    # Get the columns that this operation is dealing with
                    if ontology.is_retrieval_operation(current_step.operation):
                        if current_step.operation == "retrieve_entity":
                            # Add this to the queryargs for this subquery
                            alias_to_queryargs[current_subplan_alias].froms.append(current_step.args[0])
                        elif current_step.operation == "retrieve_attribute":
                            # Get the parent plan alias if there is one
                            parent_subplan_alias = self.get_parent_subplan(current_step.args[0], current_subplan_alias, analysis_plan.subplans)
                            if parent_subplan_alias and ontology.is_return_operation(analysis_plan.plan_steps[current_step.args[0]].operation):
                                # This step is retrieving an attribute from the return of a parent subplan
                                parent_field = step_to_field[parent_subplan_alias][current_step.args[1]]
                                step_to_field[current_subplan_alias][step_ref] = SQRField(current_subplan_alias, field=parent_field, ontology=ontology)
                                if parent_subplan_alias not in alias_to_queryargs[current_subplan_alias].froms:
                                    alias_to_queryargs[current_subplan_alias].froms.append(parent_subplan_alias)
                            else:
                                # This is the first time we've seen this step
                                entity_name = current_subplan.steps[current_step.args[0]].args[0]
                                attribute_name = current_step.args[1]
                                step_to_field[current_subplan_alias][step_ref] = SQRField(current_subplan_alias, entity_name=entity_name, field=attribute_name, ontology=ontology)
                        else:
                            raise ValueError(f"Unhandled retrieval operation: '{current_step.operation}'")
                    elif ontology.is_boolean_operation(current_step.operation)\
                            or ontology.is_arithmetic_operation(current_step.operation)\
                            or ontology.is_rownum_operation(current_step.operation):
                        def get_arg_field(arg):
                            if arg in step_to_field[current_subplan_alias]:
                                return step_to_field[current_subplan_alias][arg]
                            else:
                                return arg
                        if ontology.is_rownum_operation(current_step.operation):
                            args = current_subplan.steps[current_step.args[0]].args if current_step.args else []
                        else:
                            args = current_step.args
                        raw_filter = {
                            "type": current_step.operation,
                            "arguments": [get_arg_field(arg) for arg in args]
                        }
                        column_name = self._get_op_column_name(raw_filter)
                        filter = SQRField(current_subplan_alias, column_name_override=column_name, field=raw_filter, ontology=ontology)
                        step_to_field[current_subplan_alias][step_ref] = filter
                    elif ontology.is_sort_operation(current_step.operation):
                        pass
                    elif ontology.is_limit_operation(current_step.operation):
                        pass
                    elif ontology.is_aggregation_operation(current_step.operation):
                        if current_step.operation == "groupby":
                            for arg_ref in current_step.args:
                                groupby_name = step_to_field[current_subplan_alias][arg_ref].column_name
                                alias_to_queryargs[current_subplan_alias].group_bys.append(groupby_name)
                                alias_to_queryargs[current_subplan_alias].sqrfields[groupby_name] = step_to_field[current_subplan_alias][arg_ref]
                        else:
                            raise ValueError(f"Unhandled aggregation operation: '{current_step.operation}'")
                    elif ontology.is_analysis_operation(current_step.operation):
                        raw_analysis_field = {
                            "type": current_step.operation,
                            "arguments": [step_to_field[current_subplan_alias][arg_ref] for arg_ref in current_step.args if current_subplan.steps[arg_ref].operation != 'groupby']
                        }
                        column_name = self._get_op_column_name(raw_analysis_field)
                        analysis_field = SQRField(current_subplan_alias,
                                                  column_name_override=column_name,
                                                  field=raw_analysis_field,
                                                  ontology=ontology)
                        step_to_field[current_subplan_alias][step_ref] = analysis_field
                    elif ontology.is_collect_operation(current_step.operation):
                        pass
                    elif ontology.is_return_operation(current_step.operation):
                        collect_step = current_subplan.steps[current_step.args[0]]
                        for arg_ref in collect_step.args:
                            field = step_to_field[current_subplan_alias][arg_ref]
                            column_name = field.column_name
                            alias_to_queryargs[current_subplan_alias].sqrfields[column_name] = field
                            alias_to_queryargs[current_subplan_alias].select.append(column_name)

                        for arg_ref in current_step.args[1:]:
                            # filtering return arg
                            if ontology.is_boolean_operation(current_subplan.steps[arg_ref].operation):
                                if self._contains_aggregate_operator(step_to_field[current_subplan_alias][arg_ref], ontology):
                                    alias_to_queryargs[current_subplan_alias].having = step_to_field[current_subplan_alias][arg_ref]
                                else:
                                    alias_to_queryargs[current_subplan_alias].filter = step_to_field[current_subplan_alias][arg_ref]

                            # sort return arg
                            elif ontology.is_sort_operation(current_subplan.steps[arg_ref].operation):
                                sort_step = current_subplan.steps[arg_ref]
                                for sort_arg_ref, sort_direction in zip(sort_step.args[0::2], sort_step.args[1::2]):
                                    sort_name = step_to_field[current_subplan_alias][sort_arg_ref].column_name
                                    alias_to_queryargs[current_subplan_alias].sort_attributes.append({'attribute': sort_name, 'direction': sort_direction})
                                    alias_to_queryargs[current_subplan_alias].sqrfields[sort_name] = step_to_field[current_subplan_alias][sort_arg_ref]

                            # limit return arg
                            elif ontology.is_limit_operation(current_subplan.steps[arg_ref].operation):
                                alias_to_queryargs[current_subplan_alias].limit = current_subplan.steps[arg_ref].args[0]
                    else:
                        raise ValueError(f"Unhandled operation: '{current_step.operation}'")

        return alias_to_queryargs

    def _contains_aggregate_operator(self,
                                     filter: dict,
                                     ontology: OperationOntology):
        if filter.field['type'] in ['and', 'or', 'not']:
            # Recursive case
            return any(self._contains_aggregate_operator(arg, ontology) for arg in filter.field['arguments'])
        else:
            # Base case
            return any(ontology.is_analysis_operation(arg.field['type']) for arg in filter.field['arguments'] if type(arg) == SQRField and type(arg.field) == dict)

    def get_parent_subplan(self,
                           arg_ref: str,
                           current_alias: str,
                           subplans: Dict[str, AnalysisSubplan]):
        if arg_ref in subplans[current_alias].steps:
            return None
        parent_subplan_aliases = list(filter(lambda subplan_alias: arg_ref in subplans[subplan_alias].steps, subplans.keys()))
        if len(parent_subplan_aliases) > 1:
            raise ValueError("Ambiguous parent plan")
        return parent_subplan_aliases[0] if parent_subplan_aliases else None

    def update_query_arguments(self,
                               alias_args: QueryArguments,
                               subqueries: List[Query],
                               ring: Ring,
                               ontology: OperationOntology) -> None:

        """
        Builds/gathers the arguments needed for querying the database.
        Note: This is the function formerly known as prep_query.
        Note: Called to query across a (or multiple) computed values
        :param alias_args:
        :type alias_args: dict
        :param subqueries:
        :type subqueries:
        :param ring:
        :type ring: Ring
        :return:
        :rtype:
        """

        # Gather necessary fields, tables, and joins for performing any group bys
        for full_field_name, sqrfield in alias_args.sqrfields.items():
            if type(sqrfield.field) == dict:
                if ontology.is_boolean_operation(sqrfield.field['type'])\
                        or ontology.is_analysis_operation(sqrfield.field['type'])\
                        or ontology.is_arithmetic_operation(sqrfield.field['type'])\
                        or ontology.is_rownum_operation(sqrfield.field['type']):
                    the_field, joins_todo_temp = ring.db_interface.get_field_label_and_joins_for_operation(ring, sqrfield, ontology, subqueries)
                    alias_args.joins_todo.update(joins_todo_temp)
            elif not sqrfield.entity_name:
                # Field is from a subquery
                if sqrfield.field.column_name in subqueries[sqrfield.field.subplan_name].columns:
                    # Get the SQL Alchemy field for this attribute
                    field = subqueries[sqrfield.field.subplan_name].columns[sqrfield.field.column_name] #.label(full_field_name)
                else:
                    raise ValueError("Shouldn't happen")

                the_field = ring.db_interface.get_sqlalchemy_field(ring, sqrfield, field=field).label(full_field_name)
            else:
                # Regular field
                the_field, joins_todo_temp = ring.db_interface.get_field_label_and_name_and_joins_todo(ring, sqrfield)
                alias_args.joins_todo.update(joins_todo_temp)
            alias_args.query_fields.append(the_field)
        # get all pair combinations of entities in the query and add to joins
        for entity_a, entity_b in combinations(filter(lambda from_name: from_name in map(lambda entity: entity.name, ring.entities), alias_args.froms), 2):
            alias_args.joins_todo.update(ring.get_joins_between_entities(entity_a, entity_b))


    def add_joins_to_query(self,
                           query: Query,
                           query_args: QueryArguments,
                           ring: Ring) -> Query:
        """
        Add the joins to the query for multi-table entities.
        :param query: The SQLAlchemy query.
        :type query: Query
        :param query_args: The query containing joins to do.
        :type query_args: QueryArguments
        :param ring: The Satyrn Ring object.
        :type ring: Ring
        :return: The updated query.
        :rtype: Query
        """
        # Get the actual join object referred to by the join name
        join_list = [ring.get_join_by_name(join_name) for join_name in query_args.joins_todo]
        while join_list:
            idx = 0
            while True:
                if any(join_table in query_args.tables for join_table in [join_list[idx].from_, join_list[idx].to]):
                    join_obj = join_list.pop(idx)
                    break
                else:
                    idx += 1

            # Add the join to the query
            query, new_table = self.add_join_to_query(query, join_obj, ring, query_args.tables)
            if new_table:
                # Mark this table as joined to the query
                query_args.tables.add(new_table)
        return query

    def add_join_to_query(self,
                          query: Query,
                          join_obj: RingJoin,
                          ring: Ring,
                          added_tables=set()):
        """
        Adds a join to the SQL Alchemy query.
        :param query: The SQL Alchemy query to add the joins to.
        :type query: Query
        :param join_obj: The SQL/table level joins to add the query.
        :type join_obj: Ring_Join
        :param ring: The Satyrn Ring object
        :type ring: Ring
        :param added_tables: The set of tables that have been joined already.
        :type added_tables: set
        :return: The Query with the added join and the table which was joined.
        :rtype: Tuple[Query, str]
        """

        # Determine if there are tables which need to be added
        if join_obj.to not in added_tables:
            add_table = join_obj.to
            prefix = ''
        elif join_obj.from_ not in added_tables:
            add_table = join_obj.from_
            prefix = 'reverse_'
        else:
            print(f"path {join_obj.path} already joined")
            return query, None

        # Fetch the SQL Alchemy table objects (via the db property using the table name)
        fromtable = getattr(ring.db, join_obj.from_)
        totable = getattr(ring.db, join_obj.to)

        # Ensure the SQL Alchemy model corresponding to the table has the join name
        if hasattr(fromtable, prefix + join_obj.name):
            return query.join(totable, getattr(fromtable, prefix + join_obj.name), isouter=True), add_table
        elif hasattr(totable, prefix + join_obj.name):
            return query.join(fromtable, getattr(totable, prefix + join_obj.name), isouter=True), add_table
        else:
            print("Problem in add_join_to_query!")
            return query, None

    def _get_op_column_name(self,
                            column: Union[dict, SQRField]) -> str:
        if type(column) == SQRField:
            return column.column_name
        elif type(column) == dict:
            return self._get_op_column_name(column['arguments'][0]) if column['type'] == 'get_one' \
                else f'{column["type"]}({",".join(self._get_op_column_name(val) for val in column["arguments"])})'
        else:
            return str(column)
