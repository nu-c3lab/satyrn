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

from typing import Dict, List

import networkx as nx

from core.RingObjects.Ring import Ring
from core.api.utils import is_arg_reference
from core.Planning.utils import oxfordcomma
from core.Analysis.AnalysisPlan import AnalysisPlan
from core.Planning.StepExpressor import StepExpressor
from core.Analysis.OperationOntology import OperationOntology
from core.Planning.AnalysisPlanParser import AnalysisPlanParser


class QuestionGenerator:
    """
    A class for generating questions from SQR plans.
    """

    def __init__(self,
                 ring: Ring,
                 operation_ontology: OperationOntology):
        self.ring = ring
        self.operation_ontology = operation_ontology
        self.plan_parser = AnalysisPlanParser(self.operation_ontology)
        self.step_expressor = StepExpressor(self.ring, self.operation_ontology)

    def generate_question_from_raw_plan(self,
                                        raw_plan: Dict) -> str:
        """
        Generate a question string from an unparsed SQR plan dictionary.
        :param raw_plan: The unparsed SQR plan in dictionary form.
        :type raw_plan: dict
        :return: The question string
        :rtype: str
        """

        plan = self.plan_parser.parse(raw_plan)
        return self.generate_question_from_plan(plan)

    def generate_question_from_plan(self,
                                    plan: AnalysisPlan) -> str:
        """
        Generates a question string from a parsed SQR plan object.
        :param plan: The parsed SQR plan object.
        :type plan: AnalysisPlan
        :return: The question string
        :rtype: str
        """

        # Get the leaf node (this should be a "return" operation)
        leaf_ref = self.plan_parser.get_leaves(plan.plan_graph)[0]

        # Generate the language template using the given step ref as the base from which to build
        return self.express_final_return_step(leaf_ref, plan)

    def express_final_return_step(self,
                                  step_ref: str,
                                  plan: AnalysisPlan) -> str:
        """
        Generates the question string representing the plan assuming this is the final return in the plan.
        Because this is the final return in the plan, filters are expressed for each step in the final subquery of the plan.
        :param step_ref: The reference to the final return step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: The question string
        :rtype: str
        """

        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Express the sort
        sort_statement = ""
        for ret_arg in step.args:
            if self.is_sort_step(ret_arg, plan):
                sort_statement = self.express_step_prefix(ret_arg, plan) + " " + self.step_expressor.express_sort_step(ret_arg, plan)

        # Express the limit
        limit_statement = ""
        for ret_arg in step.args:
            if self.is_limit_step(ret_arg, plan):
                limit_statement = self.express_step_prefix(ret_arg, plan) + " " + self.step_expressor.express_limit_step(ret_arg, plan) + " results"

        # Get the filters that are passed into this return statement
        filter_steps_to_add = [ret_arg for ret_arg in step.args if self.operation_ontology.is_boolean_operation(plan.plan_steps[ret_arg].operation)]

        # Express the collect
        collect_statement = ""
        for ret_arg in step.args:
            if self.is_collect_step(ret_arg, plan):
                collect_statement = self.express_final_collect_statement(ret_arg, plan, filter_steps_to_add)

        # Put all the parts together into a final question
        if sort_statement and limit_statement:
            question = sort_statement + " and " + limit_statement + ", " + collect_statement
        elif sort_statement and not limit_statement:
            question = sort_statement + ", " + collect_statement
        elif limit_statement and not sort_statement:
            question = limit_statement + ", " + limit_statement
        else:
            question = collect_statement

        # Capitalize the question and add punctuation before returning it
        return question[0].upper() + question[1:].strip() + "?"

    def express_final_collect_statement(self,
                                        step_ref: str,
                                        plan: AnalysisPlan,
                                        filter_steps_to_add: List[str]) -> str:
        """
        Generates the question string representing the plan assuming this is the final collect in the plan.
        Because this is the final collect in the plan, filters are expressed for each step in the final subquery of the plan.
        :param step_ref: The reference to the final return step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: The question string
        :rtype: str
        """

        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]

        collect_statements = []
        for arg_ref in step.args:
            # Get the step object and operation object for that step
            arg_step = plan.plan_steps[arg_ref]
            arg_step_operation = self.operation_ontology.resolve_operation(arg_step.operation)

            statement = ""
            if self.operation_ontology.is_retrieval_operation(arg_step_operation.name):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.express_retrieval_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.operation_ontology.is_analysis_operation(arg_step_operation.name):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.express_analysis_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.is_boolean_step(arg_ref, plan):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.express_boolean_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.is_arithmetic_step(arg_ref, plan):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.express_arithmetic_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.is_rownum_step(arg_ref, plan):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.express_rownum_step_with_filters(arg_ref, plan, filter_steps_to_add)

            # Save this statement for later
            collect_statements.append(statement)

        return oxfordcomma(collect_statements)

    def express_retrieval_step_with_filters(self,
                                            step_ref: str,
                                            plan: AnalysisPlan,
                                            filter_steps_to_add: List[str]) -> str:
        """
        Produces a natural language expression of the given retrieval step.
        :param step_ref: The reference to the retrieval step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :param filter_steps_to_add: References to filter steps to include in the expression of this step.
        :type filter_steps_to_add: List of str
        :return: The retrieval step as language with filters
        :rtype: str
        """

        # Get the filters in previous subqueries of the plan
        ancestor_filters = self.get_return_filter_ancestors(step_ref, plan)
        all_filters = ancestor_filters + filter_steps_to_add
        if len(all_filters) > 0:
            # Express all of the filters for this step
            filter_expression = "for " + " and ".join([self.step_expressor.express_filter_step(filter_ref, plan) for filter_ref in all_filters])

            # Add them to the final expression for this step
            return self.step_expressor.express_retrieval_step(step_ref, plan) + " " + filter_expression
        else:
            return self.step_expressor.express_retrieval_step(step_ref, plan)

    def express_analysis_step_with_filters(self,
                                           step_ref: str,
                                           plan: AnalysisPlan,
                                           filter_steps_to_add: List[str]) -> str:
        """
        Produces a natural language expression of the given analysis step.
        :param step_ref: The reference to the analysis step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :param filter_steps_to_add: References to filter steps to include in the expression of this step.
        :type filter_steps_to_add: List of str
        :return: The analysis step as language with filters
        :rtype: str
        """

        # Get the ancestor filters
        ancestor_filters = self.get_return_filter_ancestors(step_ref, plan)
        all_filters = ancestor_filters + filter_steps_to_add
        if len(all_filters) > 0:
            # Express all of the filters for this step
            filter_expression = " for " + " and ".join([self.step_expressor.express_filter_step(filter_ref, plan) for filter_ref in all_filters])

            # Add them to the final expression for this step
            return self.step_expressor.express_analysis_step(step_ref, plan) + filter_expression
        else:
            return self.step_expressor.express_analysis_step(step_ref, plan)

    def express_arithmetic_step_with_filters(self,
                                             step_ref: str,
                                             plan: AnalysisPlan,
                                             filter_steps_to_add: List[str]) -> str:
        """
        Produces a natural language expression of the given arithmetic step.
        :param step_ref: The reference to the arithmetic step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :param filter_steps_to_add: References to filter steps to include in the expression of this step.
        :type filter_steps_to_add: List of str
        :return: The arithmetic step as language with filters
        :rtype: str
        """
        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        statement = step_operation.template
        for arg_idx in range(0, step_operation.input_args[0].min_num_args):
            if is_arg_reference(step.args[arg_idx]):
                # Check if the referenced step is a retrieval or analysis step and express it with filters
                if self.is_retrieval_step(step.args[arg_idx], plan):
                    statement = statement.replace(f"{{{arg_idx}}}", self.express_retrieval_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                elif self.is_analysis_step(step.args[arg_idx], plan):
                    statement = statement.replace(f"{{{arg_idx}}}", self.express_analysis_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                elif self.is_boolean_step(step.args[arg_idx], plan):
                    statement = statement.replace(f"{{{arg_idx}}}", self.express_boolean_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                elif self.is_arithmetic_step(step.args[arg_idx], plan):
                    statement = statement.replace(f"{{{arg_idx}}}", self.express_arithmetic_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                elif self.is_rownum_step(step.args[arg_idx], plan):
                    statement = statement.replace(f"{{{arg_idx}}}", self.express_rownum_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
            else:
                # Arg is a hardcoded value, so just use that for the comparison
                statement = statement.replace(f"{{{arg_idx}}}", str(step.args[arg_idx]))

        return statement

    def express_boolean_step_with_filters(self,
                                          step_ref: str,
                                          plan: AnalysisPlan,
                                          filter_steps_to_add: List[str]) -> str:
        """
        Produces a natural language expression of the given boolean step.
        Looks at each of the arguments of the boolean step, expresses the step and its filters where necessary (i.e. the arg is a reference to a retrieval or analysis output step)
        :param step_ref: The reference to the boolean step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :param filter_steps_to_add: References to filter steps to include in the expression of this step.
        :type filter_steps_to_add: List of str
        :return: The boolean step as language with filters
        :rtype: str
        """

        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Express the step
        filter_joiners = ['and', 'or']
        filter_prefixers = ['not']
        filter_equalities = ['greaterthan', 'lessthan', 'greaterthan_eq', 'lessthan_eq', 'exact', 'contains']

        if step_operation.name in filter_joiners:
            return f" {step_operation.name} ".join([self.express_boolean_step_with_filters(arg, plan, filter_steps_to_add) for arg in step.args])
        elif step_operation.name in filter_prefixers:
            return f"{step_operation.name} " + " ".join([self.express_boolean_step_with_filters(arg, plan, filter_steps_to_add) for arg in step.args])
        elif step_operation.name in filter_equalities:
            # Handle the first argument: args are expressed with applied filters where necessary (i.e. the arg is a reference to a retrieval or analysis output step and not a hardcoded comparison value like "5" or "COMPUTER")
            if is_arg_reference(step.args[0]):
                statement = step_operation.template
                for arg_idx in range(0, step_operation.input_args[0].min_num_args):
                    if is_arg_reference(step.args[arg_idx]):
                        # Check if the referenced step is a retrieval or analysis step and express it with filters
                        if self.is_retrieval_step(step.args[arg_idx], plan):
                            statement = statement.replace(f"{{{arg_idx}}}", self.express_retrieval_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                        elif self.is_analysis_step(step.args[arg_idx], plan):
                            statement = statement.replace(f"{{{arg_idx}}}", self.express_analysis_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                        elif self.is_boolean_step(step.args[arg_idx], plan):
                            statement = statement.replace(f"{{{arg_idx}}}", self.express_boolean_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                        elif self.is_arithmetic_step(step.args[arg_idx], plan):
                            statement = statement.replace(f"{{{arg_idx}}}", self.express_arithmetic_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                        elif self.is_rownum_step(step.args[arg_idx], plan):
                            statement = statement.replace(f"{{{arg_idx}}}", self.express_rownum_step_with_filters(step.args[arg_idx], plan, filter_steps_to_add))
                    else:
                        # Arg is a hardcoded value, so just use that for the comparison
                        statement = statement.replace(f"{{{arg_idx}}}", str(step.args[arg_idx]))

                return statement
        else:
            raise NotImplementedError(f"Unhandled filter operation type to resolve: '{step_operation.name}'")

    def express_rownum_step_with_filters(self,
                                         step_ref: str,
                                         plan: AnalysisPlan,
                                         filter_steps_to_add: List[str]) -> str:
        """
        Produces a natural language expression of the given rownum step.
        :param step_ref: The reference to the rownum step
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :param filter_steps_to_add: References to filter steps to include in the expression of this step.
        :type filter_steps_to_add: List of str
        :return: The rownum step as language with filters
        :rtype: str
        """

        # Get the filters in previous subqueries of the plan
        ancestor_filters = self.get_return_filter_ancestors(step_ref, plan)
        all_filters = ancestor_filters + filter_steps_to_add
        if len(all_filters) > 0:
            # Express all of the filters for this step
            filter_expression = "for " + " and ".join(
                [self.step_expressor.express_filter_step(filter_ref, plan) for filter_ref in all_filters])

            # Add them to the final expression for this step
            return self.step_expressor.express_rownum_operation(step_ref, plan) + " " + filter_expression
        else:
            return self.step_expressor.express_rownum_operation(step_ref, plan)

    def get_return_filter_ancestors(self,
                                    step_ref: str,
                                    plan: AnalysisPlan) -> List[str]:
        """
        Gets a list of step references that are both filter steps and in ancestor return steps.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: List of step_refs that are filter steps
        :rtype: List of str
        """

        # Get all the ancestor nodes for this step in the plan
        ancestor_node_refs = nx.ancestors(plan.plan_graph, step_ref)

        step_refs = []
        for ancestor_ref in ancestor_node_refs:
            # Check if any of the ancestor nodes are a "return" step
            if plan.plan_steps[ancestor_ref].operation == 'return':
                # Check if any of the return args are a boolean operation
                for arg in plan.plan_steps[ancestor_ref].args:
                    ancestor_arg_step = plan.plan_steps[arg]
                    ancestor_arg_step_operation = self.operation_ontology.resolve_operation(ancestor_arg_step.operation)
                    if self.operation_ontology.is_boolean_operation(ancestor_arg_step_operation.name):
                        # Add the boolean step ref to the list of refs to return
                        step_refs.append(arg)

        return sorted(step_refs, reverse=True)      # Sorting is done to ensure deterministic behavior

    def express_step_prefix(self,
                            step_ref: str,
                            plan: AnalysisPlan) -> str:
        """
        Builds the natural language that should precede the expression of the reference step provided.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: The natural language prefix string
        :rtype: str
        """
        if self.is_boolean_step(step_ref, plan):
            return "is the"
        elif self.is_sort_step(step_ref, plan):
            return "for"
        elif self.is_retrieval_step(step_ref, plan) and self.is_return_step(plan.plan_steps[step_ref].args[0], plan):
            return self.express_step_prefix(plan.plan_steps[step_ref].args[1], plan)
        elif self.is_arithmetic_step(step_ref, plan):
            return "what is"
        elif self.is_limit_step(step_ref, plan):
            return "limited to the"
        else:
            return "what is the"

    ###############################################################################################
    #                                     Step Type Checkers
    ###############################################################################################

    def is_arithmetic_step(self,
                           step_ref: str,
                           plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is an arithmetic step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is an arithmetic step.
        :rtype: bool
        """
        return self.operation_ontology.is_arithmetic_operation(plan.plan_steps[step_ref].operation)

    def is_return_step(self,
                       step_ref: str,
                       plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a return step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a return step.
        :rtype: bool
        """
        return self.operation_ontology.is_return_operation(plan.plan_steps[step_ref].operation)

    def is_retrieval_step(self,
                          step_ref: str,
                          plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a retrieval step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a retrieval step.
        :rtype: bool
        """
        return self.operation_ontology.is_retrieval_operation(plan.plan_steps[step_ref].operation)

    def is_analysis_step(self,
                          step_ref: str,
                          plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is an analysis step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is an analysis step.
        :rtype: bool
        """
        return self.operation_ontology.is_analysis_operation(plan.plan_steps[step_ref].operation)

    def is_sort_step(self,
                     step_ref: str,
                     plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a sort step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a sort step.
        :rtype: bool
        """
        return plan.plan_steps[step_ref].operation == 'sort'

    def is_collect_step(self,
                     step_ref: str,
                     plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a collect step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a collect step.
        :rtype: bool
        """
        return plan.plan_steps[step_ref].operation == 'collect'

    def is_filter_step(self,
                       step_ref: str,
                       plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a filter step (i.e. a boolean operation that is passed directly to a return step).
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a filter step.
        :rtype: bool
        """
        child_step_refs = dict(nx.bfs_successors(plan.plan_graph, source=step_ref))
        return self.operation_ontology.is_boolean_operation(plan.plan_steps[step_ref].operation) and \
               any([self.operation_ontology.is_return_operation(plan.plan_steps[ref].operation) for ref in child_step_refs])

    def is_boolean_step(self,
                        step_ref: str,
                        plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a boolean step (i.e. a boolean operation that is passed directly to a collect step).
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a boolean step.
        :rtype: bool
        """
        child_step_refs = dict(nx.bfs_successors(plan.plan_graph, source=step_ref))
        return self.operation_ontology.is_boolean_operation(plan.plan_steps[step_ref].operation) and \
               any([self.operation_ontology.is_collect_operation(plan.plan_steps[ref].operation) for ref in child_step_refs])

    def is_limit_step(self,
                      step_ref: str,
                      plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a limit step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a boolean step.
        :rtype: bool
        """
        return plan.plan_steps[step_ref].operation == 'limit'

    def is_rownum_step(self,
                      step_ref: str,
                      plan: AnalysisPlan) -> bool:
        """
        Determines if the given step is a rownum step.
        :param step_ref: A reference to a step in the analysis plan.
        :type step_ref: str
        :param plan: The analysis plan the step reference belongs to.
        :type plan: AnalysisPlan
        :return: Boolean denoted whether or not this is a boolean step.
        :rtype: bool
        """
        return plan.plan_steps[step_ref].operation == 'rownum'