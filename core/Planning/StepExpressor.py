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

import networkx as nx
import re

from core.RingObjects.Ring import Ring
from core.api.utils import is_arg_reference, contains_date_denomination
from core.Planning.utils import oxfordcomma
from core.Analysis.AnalysisEngine import AnalysisEngine
from core.Analysis.AnalysisPlan import AnalysisPlan
from core.Analysis.OperationOntology import OperationOntology
from core.Operations.ArgType import ArgType

class StepExpressor:
    """
    A class for expressing steps that are agnostic to overall sentence syntax and structure.
    """
    def __init__(self,
                 ring: Ring,
                 operation_ontology: OperationOntology,
                 ):
        self.ring = ring
        self.operation_ontology = operation_ontology

    def express_step(self,
                     step_ref: str,
                     plan: AnalysisPlan) -> str:
        """
        A function that converts a step (and any steps it depends on) to natural language.
        :param step_ref: The reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: A language template into which the plan's execution results can be inserted.
        :rtype: str
        """
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        if self.operation_ontology.is_analysis_operation(step_operation.name):
            return self.express_analysis_step(step_ref, plan)
        elif self.operation_ontology.is_retrieval_operation(step_operation.name):
            return self.express_retrieval_step(step_ref, plan)
        elif self.operation_ontology.is_aggregation_operation(step_operation.name):
            return self.express_aggregation_step(step_ref, plan)
        elif self.operation_ontology.is_boolean_operation(step_operation.name):
            return self.express_filter_step(step_ref, plan)
        elif self.operation_ontology.is_sort_operation(step_operation.name):
            return self.express_sort_step(step_ref, plan)
        elif self.operation_ontology.is_arithmetic_operation(step_operation.name):
            return self.express_arithmetic_step(step_ref, plan)
        elif self.operation_ontology.is_rownum_operation(step_operation.name):
            return self.express_rownum_operation(step_ref, plan)
        else:
            raise NotImplementedError(f"Unhandled operation type to resolve: '{step_operation.name}'")

    def express_rownum_operation(self,
                                 step_ref: str,
                                 plan: AnalysisPlan) -> str:
        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        statement = step_operation.template

        for arg_idx in range(0, step_operation.input_args[0].min_num_args):
            if is_arg_reference(step.args[arg_idx]):
                arg_step = plan.plan_steps[step.args[arg_idx]]
                arg_operation = self.operation_ontology.resolve_operation(arg_step.operation)
                if self.operation_ontology.is_sort_operation(arg_operation.name):
                    statement = statement.replace(f"{{{arg_idx}}}", self.express_sort_step(step.args[arg_idx], plan))
                else:
                    raise ValueError("Argument passed to 'rownum' operation is not a 'sort' operation.")
            else:
                raise ValueError("Argument passed to 'rownum' operation is not a reference.")

        return statement

    def get_entity_name(self,
                        step_ref: str,
                        plan: AnalysisPlan) -> str:
        return self.get_retrieval_step_name(step_ref, plan, 'entity')

    def get_attribute_name(self,
                        step_ref: str,
                        plan: AnalysisPlan) -> str:
        return self.get_retrieval_step_name(step_ref, plan, 'attribute')

    def get_retrieval_step_name(self,
                        step_ref: str,
                        plan: AnalysisPlan,
                        retrieval_type = 'entity') -> str:
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        if self.operation_ontology.is_analysis_operation(step_operation.name):
            return self.get_retrieval_step_name(step.args[0], plan, retrieval_type)
        elif self.operation_ontology.is_retrieval_operation(step_operation.name):
            if step_operation.name == 'retrieve_attribute':
                if retrieval_type == 'attribute':
                    if is_arg_reference(step.args[1]):
                        return self.get_retrieval_step_name(step.args[1], plan, retrieval_type)
                    else:
                        return step.args[1]
                elif retrieval_type == 'entity':
                    if self.operation_ontology.is_return_operation(plan.plan_steps[step.args[0]].operation):
                        return self.get_retrieval_step_name(step.args[1], plan, retrieval_type)
                    else:
                        return self.get_retrieval_step_name(step.args[0], plan, retrieval_type)
            elif step_operation.name == 'retrieve_entity' and retrieval_type == 'entity':
                return step.args[0]
        if self.operation_ontology.is_return_operation(step_operation.name):
            return self.get_retrieval_step_name(step.args[0], plan, retrieval_type)
        elif self.operation_ontology.is_aggregation_operation(step_operation.name):
            return self.get_retrieval_step_name(step.args[0], plan, retrieval_type)
        # elif self.operation_ontology.is_boolean_operation(step_operation.name):
        #     return self.express_filter_step(step_ref, plan)
        # elif self.operation_ontology.is_sort_operation(step_operation.name):
        #     return self.express_sort_step(step_ref, plan)
        # elif self.operation_ontology.is_arithmetic_operation(step_operation.name):
        #     return self.express_arithmetic_step(step_ref, plan)
        # elif self.operation_ontology.is_rownum_operation(step_operation.name):
        #     return self.express_rownum_operation(step_ref, plan)

    def express_aggregation_step(self,
                                 step_ref: str,
                                 plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Check if this aggregation has any ancestors which are also groupbys
        if self.has_groupby_ancestor(step_ref, plan):
            # Join the list of all the attributes / analysis results we're going to be grouping on
            return " ".join([f"grouped by {self.express_step(arg, plan)}" for arg in step.args])
        else:
            return ""

    def has_groupby_ancestor(self,
                             step_ref: str,
                             plan: AnalysisPlan) -> bool:
        """
        Checks if the step with the given ref has any ancestors which are a groupby operation.
        :param step_ref: The step for which the groupby ancestor will be found (or not).
        :type step_ref: str
        :param plan: The original analysis plan.
        :type plan: AnalysisPlan
        :return: A boolean denoting whether this is the innermost groupby
        :rtype: bool
        """
        # Get all the ancestor nodes for this step in the plan
        ancestor_node_refs = nx.ancestors(plan.plan_graph, step_ref)

        # Check if any of the ancestor nodes are a groupby
        for ancestor_ref in ancestor_node_refs:
            if plan.plan_steps[ancestor_ref].operation == 'groupby':
                return False
        return True

    def express_analysis_step(self,
                              step_ref: str,
                              plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Get the analysis and groupby steps to be resolved
        analysis_steps = [step.args[0]]
        groupby_steps = step.args[1:] if len(step.args) > 1 else []

        results = []
        # Replace the {target} of the analysis operation with the resolve reference
        results.extend([step_operation.template.replace("{target}", self.express_step(analysis_steps[0], plan))])

        results.extend([self.express_step(groupby_step, plan) for groupby_step in groupby_steps])

        return " ".join(results)

    def express_retrieval_step(self,
                               step_ref: str,
                               plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        if step_operation.name == "retrieve_attribute":

            # Get the Entity this attribute is coming from
            ent_step_ref = step.args[0]
            ent_step = plan.plan_steps[ent_step_ref]
            if ent_step.operation == 'retrieve_entity':
                ent_name = ent_step.args[0]
                the_ent = [ent for ent in self.ring.entities if ent.name == ent_name][0]

                # Check if there is a partial date selection for this attribute]
                attr_name = step.args[1]
                date_denomination = contains_date_denomination(attr_name)
                attr_partial_date_type = None
                if date_denomination:
                    attr_name = date_denomination.group(1)
                    attr_partial_date_type = date_denomination.group(2)

                # Resolve the attribute to the RingAttribute
                if attr_name in the_ent.attributes:
                    the_attribute = the_ent.attributes[attr_name]
                    if ArgType.Identifier in the_attribute.type:
                        return the_ent.nicename[0].lower()  # currently we always use the singular version
                elif attr_name == 'id':
                    # Return the nicename of the entity
                    return the_ent.nicename[0].lower()  # currently we always use the singular version
                else:
                    raise ValueError(f"Unknown attribute '{attr_name}'")

                # Get the nicename of the RingAttribute
                attr_nicename = the_attribute.nicename[0].lower()  # currently we always use the singular version

                # Add any partial date nicenames that were in the original attribute to be retrieved
                if attr_partial_date_type:
                    if attr_partial_date_type == ":year":
                        return "year of " + attr_nicename
                    elif attr_partial_date_type == ":month":
                        return "year/month of " + attr_nicename
                    elif attr_partial_date_type == ":day":
                        return "year/month/day of " + attr_nicename
                    elif attr_partial_date_type == ":onlymonth":
                        return "month of " + attr_nicename
                    elif attr_partial_date_type == ":onlyday":
                        return "day of " + attr_nicename
                    elif attr_partial_date_type == ":dayofweek":
                        return "day of the week of " + attr_nicename
                else:
                    return attr_nicename

            elif ent_step.operation == 'return':
                return self.express_step(step.args[1], plan)

    def express_filter_step(self,
                            step_ref: str,
                            plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Express the step
        filter_joiners = ['and', 'or']
        filter_prefixers = ['not']
        filter_equalities = ['greaterthan', 'lessthan', 'greaterthan_eq', 'lessthan_eq', 'exact', 'contains']

        if step_operation.name in filter_joiners:
            return f" {step_operation.name} ".join([self.express_step(arg, plan) for arg in step.args])
        elif step_operation.name in filter_prefixers:
            return f"{step_operation.name} " + " ".join([self.express_step(arg, plan) for arg in step.args])
        elif step_operation.name in filter_equalities:
            # entity_name = self.express_step('[entity_name]', plan)
            entity_name = self.get_entity_name(step.args[0], plan)
            attribute_name = self.get_attribute_name(step.args[0], plan)
            entity = self.ring.get_entity_by_name(entity_name)
            identifiers = entity.get_attributes_with_type(ArgType.Identifier)

            if entity.reference and attribute_name in map(lambda att: att.name, identifiers):
                value = self.express_step(step.args[1], plan) if is_arg_reference(step.args[1]) else str(step.args[1])
                statement = self.get_reference_values(entity_name, attribute_name, value, entity.reference)
            else:
                statement = step_operation.template.replace("{0}", self.express_step(step.args[0], plan) if is_arg_reference(step.args[0]) else str(step.args[0]))
                statement = statement.replace("{1}", self.express_step(step.args[1], plan) if is_arg_reference(step.args[1]) else str(step.args[1]))
            return statement
        else:
            raise NotImplementedError(f"Unhandled filter operation type to resolve: '{step_operation.name}'")

    def get_reference_values(self,
                             entity: str,
                             identifier: str,
                             value: str,
                             reference_template: str) -> str:
        # Init the analysis engine
        analysis_engine = AnalysisEngine(self.ring)

        reference_attributes = re.findall(r'\{(\w+)\}', reference_template)

        reference_attribute_steps = {f'|r{i+1}|': f'(retrieve_attribute |1| {attribute})' for i, attribute in enumerate(reference_attributes)}

        raw_analysis_plan = {
            '|1|': f'(retrieve_entity {entity})',
            '|2|': f'(retrieve_attribute |1| \'{identifier}\')',
            '|3|': f'(exact |2| \'{value}\')',
            '|4|': f'(collect {" ".join(reference_attribute_steps.keys())})',
            '|5|': f'(return |4| |3|)'
        }

        raw_analysis_plan.update(reference_attribute_steps)

        # Parse the analysis plan
        analysis_plan = analysis_engine.plan_parser.parse(raw_analysis_plan)

        # Run the analysis
        results = analysis_engine.sqr_single_ring_analysis(analysis_plan, self.ring, self.ring.db.session())

        if results['length'] > 1:
            raise ValueError('Error: Expected only one result for refrerece retrieval.')

        return reference_template.format(**{attribute_name: result for attribute_name, result in zip(reference_attributes, results['results'][0])})

    def express_sort_step(self,
                          step_ref: str,
                          plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        sort_statements = []
        it = iter(step.args)
        for sort_attr, sort_type in list(zip(it, it)):
            sort_statements.append(f"{self.express_step(sort_attr, plan)} sorted in {'ascending' if sort_type == 'asc' else 'descending'} order")

        return oxfordcomma(sort_statements)

    def express_arithmetic_step(self,
                                step_ref: str,
                                plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # statement = step_operation.template.replace("{0}", self.express_step(step.args[0], plan) if is_arg_reference(step.args[0]) else str(step.args[0]))
        # statement = statement.replace("{1}", self.express_step(step.args[1], plan) if is_arg_reference(step.args[1]) else str(step.args[1]))

        statement = step_operation.template
        for arg_idx in range(0, step_operation.input_args[0].min_num_args):
            if is_arg_reference(step.args[arg_idx]):
                statement = statement.replace(f"{{{arg_idx}}}", self.express_step(step.args[arg_idx], plan))
            else:
                # Arg is a hardcoded value, so just use that for the comparison
                statement = statement.replace(f"{{{arg_idx}}}", str(step.args[arg_idx]))

        return statement

    def express_limit_step(self,
                           step_ref: str,
                           plan: AnalysisPlan) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        statement = step_operation.template.replace("{0}", str(step.args[0])) if str(step.args[0]) != "1" else step_operation.template.replace("{0}", "").strip()

        return statement
