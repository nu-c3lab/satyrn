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

import copy
from enum import Enum
from typing import Dict, List

from core.api import utils
from core.RingObjects.Ring import Ring
from core.Planning.utils import oxfordcomma
from core.Analysis.AnalysisPlan import AnalysisPlan
from core.Planning.StepExpressor import StepExpressor
from core.Analysis.OperationOntology import OperationOntology
from core.Planning.AnalysisPlanParser import AnalysisPlanParser
from core.Planning.QuestionGenerator import QuestionGenerator
from core.Operations.ArgType import ArgType

class GenerationMode(Enum):
    OneStatementPerRow = 1
    OneStatementPerPlan = 2

class StatementGenerator:
    def __init__(self,
                 ring: Ring,
                 operation_ontology: OperationOntology,
                 mode: GenerationMode = GenerationMode.OneStatementPerPlan):
        self.ring = ring
        self.operation_ontology = operation_ontology
        self.plan_parser = AnalysisPlanParser(self.operation_ontology)
        self.mode = mode
        self.step_expressor = StepExpressor(self.ring, self.operation_ontology)
        self.question_generator = QuestionGenerator(self.ring, self.operation_ontology)

    def generate_statement_template_from_raw_plan(self,
                                                  raw_plan: Dict) -> str:
        plan = self.plan_parser.parse(raw_plan)
        return self.generate_statement_template_from_plan(plan)

    def generate_statement_template_from_plan(self,
                                              plan: AnalysisPlan) -> str:

        # Get the leaf node (this should be a "return" operation)
        leaf_ref = self.plan_parser.get_leaves(plan.plan_graph)[0]

        # Generate the language template using the given step ref as the base from which to build
        # return self.express_step(leaf_ref, plan)
        return self.express_final_return_step(leaf_ref, plan)

    def express_final_return_step(self,
                                  step_ref: str,
                                  plan: AnalysisPlan) -> str:
        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Express the sort
        sort_statement = ""
        for ret_arg in step.args:
            if self.question_generator.is_sort_step(ret_arg, plan):
                sort_statement =  self.express_step_prefix(ret_arg, plan) + " " + self.step_expressor.express_sort_step(ret_arg, plan)

        # Express the limit
        limit_statement = ""
        for ret_arg in step.args:
            if self.question_generator.is_limit_step(ret_arg, plan):
                limit_statement = self.express_step_prefix(ret_arg, plan) + " " + self.step_expressor.express_limit_step(ret_arg, plan) + " results"

        # Get the filters that are passed into this return statement
        filter_steps_to_add = [ret_arg for ret_arg in step.args if self.operation_ontology.is_boolean_operation(plan.plan_steps[ret_arg].operation)]

        # Express the collect
        collect_statement = ""
        for ret_arg in step.args:
            if self.question_generator.is_collect_step(ret_arg, plan):
                collect_statement = self.express_final_collect_statement(ret_arg, plan, filter_steps_to_add)

        # Put all the parts together into a final question
        if sort_statement and limit_statement:
            final_statement = sort_statement + " and " + limit_statement + ", " + collect_statement
        elif sort_statement and not limit_statement:
            final_statement = sort_statement + ", " + collect_statement
        elif limit_statement and not sort_statement:
            final_statement = limit_statement + ", " + limit_statement
        else:
            final_statement = collect_statement.lstrip()

        # Capitalize the question and add punctuation before returning it
        return final_statement[0].upper() + final_statement[1:].strip() + self.build_statement_ending()

    def express_final_collect_statement(self,
                                        step_ref: str,
                                        plan: AnalysisPlan,
                                        filter_steps_to_add: List[str]) -> str:
        # Get some necessary info
        step = plan.plan_steps[step_ref]
        step_operation = self.operation_ontology.resolve_operation(step.operation)

        # Get all of the attributes/analyses being collected
        statements_for_collected_attributes = self.get_statements_for_collect(step_ref, plan, filter_steps_to_add)

        if self.mode == GenerationMode.OneStatementPerPlan:
            return " and ".join(statements_for_collected_attributes)
        elif self.mode == GenerationMode.OneStatementPerRow:
            # Join the list of all the attributes / analysis results we're going to be returning
            collect_list = []
            for idx, attribute_statement in enumerate(statements_for_collected_attributes):
                step_language = attribute_statement
                step_language = step_language.rstrip() + " is {" + str(idx) + "}"
                collect_list.append(step_language)

            # Put them into a comma separated list
            return oxfordcomma(collect_list)
        else:
            raise ValueError(f"Unknown GenerationMode, {self.mode}")

    def get_statements_for_collect(self,
                                   step_ref: str,
                                   plan: AnalysisPlan,
                                   filter_steps_to_add: List[str]) -> List[str]:
        # Get the step object and operation object for that step
        step = plan.plan_steps[step_ref]

        collect_statements = []
        for arg_ref in step.args:
            # Get the step object and operation object for that step
            arg_step = plan.plan_steps[arg_ref]
            arg_step_operation = self.operation_ontology.resolve_operation(arg_step.operation)

            statement = ""
            if self.operation_ontology.is_retrieval_operation(arg_step_operation.name):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.question_generator.express_retrieval_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.operation_ontology.is_analysis_operation(arg_step_operation.name):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.question_generator.express_analysis_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.question_generator.is_boolean_step(arg_ref, plan):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.question_generator.express_boolean_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.question_generator.is_arithmetic_step(arg_ref, plan):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.question_generator.express_arithmetic_step_with_filters(arg_ref, plan, filter_steps_to_add)
            elif self.question_generator.is_rownum_step(arg_ref, plan):
                statement = self.express_step_prefix(arg_ref, plan) + " " + self.question_generator.express_rownum_step_with_filters(arg_ref, plan, filter_steps_to_add)

            # Save this statement for later
            collect_statements.append(statement)
        return collect_statements

    def build_statement_ending(self) -> str:
        # Add "is/are" to the end of the statement
        if self.mode == GenerationMode.OneStatementPerPlan:
            statement_ending = " is {result}."
        else:
            statement_ending = "."
        return statement_ending

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
        if self.question_generator.is_sort_step(step_ref, plan):
            return "for"
        elif self.question_generator.is_retrieval_step(step_ref, plan) and self.question_generator.is_return_step(plan.plan_steps[step_ref].args[0], plan):
            return self.express_step_prefix(plan.plan_steps[step_ref].args[1], plan)
        elif self.question_generator.is_limit_step(step_ref, plan):
            return "limited to the"
        else:
            return "the"

    def fill_result(self,
                    plan: AnalysisPlan,
                    result_template: str) -> List[str]:
        """
        Uses the results of the plan execution to fill up the results language template associated with the plan.
        :param results: The result dictionary produced by executing a plan in Satyrn.
        :type results: Dict
        :param result_template: The language template which the results will be slotted into.
        :type result_template: str
        :return: The factual statements
        :rtype: List of str
        """
        if self.mode == GenerationMode.OneStatementPerPlan:
            return self.fill_result_one_statement_per_plan(plan, result_template)
        elif self.mode == GenerationMode.OneStatementPerRow:
            return self.fill_result_one_statement_per_row(plan, result_template)
        else:
            raise ValueError(f"Unknown GenerationMode, {self.mode}")

    def fill_result_one_statement_per_row(self,
                                          plan: AnalysisPlan,
                                          result_template: str) -> List[str]:
        """
        Uses the results of the plan execution to fill up the results language template associated with the plan. One
        factual statement is produced for each row of the results.
        :param results: The result dictionary produced by executing a plan in Satyrn.
        :type results: Dict
        :param result_template: The language template which the results will be slotted into.
        :type result_template: str
        :return: The factual statements
        :rtype: List of str
        """

        factual_statements = []
        for result_row in plan.result["results"]:

            #  Make a copy of the result_template
            template_copy = copy.deepcopy(result_template)

            template_fillers = []
            for idx, col_val in enumerate(result_row):
                # Get the value
                answer = str(col_val)

                field_dict = utils.entity_from_subquery_name(plan.result['fieldNames'][idx], list(plan.subplans.keys()))
                if field_dict:
                    entity = self.ring.get_entity_by_name(field_dict['entity'])
                    if ArgType.Identifier in entity.attributes[field_dict['field']].type:
                        answer = self.step_expressor.get_reference_values(field_dict['entity'], field_dict['field'], answer, entity.reference)
                # Get the units for this value (if any)
                elif plan.result['units']['results'][idx] and len(plan.result['units']['results'][idx][1]) > 0:
                    answer += f" {plan.result['units']['results'][idx][1]}"

                template_fillers.append(answer)

            # Replace the slots in the template copy with the
            template_copy = template_copy.format(*template_fillers)

            # Add the filled in template copy to the list of factual statements to return
            factual_statements.append(template_copy)

        return factual_statements

    def fill_result_one_statement_per_plan(self,
                                           plan: AnalysisPlan,
                                           result_template: str) -> List[str]:
        """
        Uses the results of the plan execution to fill up the results language template associated with the plan. One
        factual statement is produced for all of the results.
        :param results: The result dictionary produced by executing a plan in Satyrn.
        :type results: Dict
        :param result_template: The language template which the results will be slotted into.
        :type result_template: str
        :return: The factual statements
        :rtype: List of str
        """

        template_fillers = []
        for result_row in plan.result["results"]:

            # Get all of values for the current row of answers
            answers_with_units = []
            for idx, col_val in enumerate(result_row):
                # Get the value
                answer = str(col_val)

                field_dict = utils.entity_from_subquery_name(plan.result['fieldNames'][idx], list(plan.subplans.keys()))
                if field_dict:
                    entity = self.ring.get_entity_by_name(field_dict['entity'])
                if field_dict and entity.reference and ArgType.Identifier in entity.attributes[field_dict['field']].type:
                    answer = self.step_expressor.get_reference_values(field_dict['entity'], field_dict['field'], answer, entity.reference)
                # Get the units for this value (if any)
                elif plan.result['units']['results'][idx] and len(plan.result['units']['results'][idx][1]) > 0:
                    answer += f" {plan.result['units']['results'][idx][1]}"

                # Save the answer
                answers_with_units.append(answer)

            # Join the columns for the current row of answers
            language_for_one_result = " and ".join(answers_with_units)
            template_fillers.append(language_for_one_result)

        # Join all of the results with commas
        slot_filler = ", ".join(template_fillers)

        # Fill in the result slot
        factual_statement = result_template.replace("{result}", slot_filler)

        return [factual_statement]
