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
import json

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

from .viewHelpers import api_key_check, get_or_create_ring
from core.Analysis.AnalysisEngine import AnalysisEngine
from core.Analysis.OperationOntology import OperationOntology
from core.LanguageGeneration.GPT35Interface import GPT35Interface
from core.LanguageGeneration.GPT4Interface import GPT4Interface
from core.LanguageGeneration.Mixtral8x7BInterface import Mixtral8x7BInterface
from core.LanguageGeneration.CodeInterpreterInterface import CodeInterpreterInterface
from core.LanguageGeneration.StableBelugaInterface import StableBelugaInterface
from core.Planning.StatementGenerator import StatementGenerator, GenerationMode
from core.Planning.StatementGeneratorTemplateBased import StatementGeneratorTemplateBased
from core.api.DocumentManager import DocumentManager
from core.Planning.SQRComposer import SQRComposer
from core.Document.Blueprints.SQRPlanFiller import SQRPlanFiller
from core.Analysis.AnalysisPlan import AnalysisPlan
from core.Document.Blueprints.RankingBlueprint import RankingBlueprint
from core.Document.Blueprints.ComparativeBenchmarkBlueprint import ComparativeBenchmarkBlueprint
from core.Document.Blueprints.TimeOverTimeBlueprint import TimeOverTimeBlueprint
from core.Operations.ArgType import ArgType
from prettytable import PrettyTable

from functools import reduce
from typing import Dict, Tuple

# # some "local globals"
app = current_app # this is now the same app instance as defined in appBundler.py
api = Blueprint("api", __name__)
cache = app.cache

# THE ROUTES
# base route as a pseudo health check
@api.route("/")
@api_key_check
def base():
    return json.dumps({
        "status": "API is up and running"
    })

@api.route("/sqr_analysis/<ring_id>/<version>/", methods=["GET", "POST"])
@cross_origin(supports_credentials=True)
@api_key_check
def analysis(ring_id: str,
             version: str) -> Dict:
    """
    Runs the analysis specified by the SQR plan in the JSON of the request.
    :param ring_id: The ID of the ring.
    :type ring_id: str
    :param version: The ring version.
    :type version: str
    :return: A dictionary of the analysis results.
    :rtype: dict
    """

    # Get our ring and extractor
    ring = get_or_create_ring(ring_id, version)
    if type(ring) is tuple:
        # ring will now be an error message
        return json.dumps(ring)

    # Init the analysis engine
    analysis_engine = AnalysisEngine(ring)

    # The analysis plan come in via a JSON body
    raw_analysis_plan = request.json

    # Parse the analysis plan
    analysis_plan = analysis_engine.plan_parser.parse(raw_analysis_plan)

    # Run the analysis
    results = analysis_engine.sqr_single_ring_analysis(analysis_plan, ring, ring.db.session())

    if "score" in results:
        results["score"] = results["score"]
    # this next line is a bit of a hack to deal with un-jsonable things by coercing them
    # to strings without having to write quick managers for every possible type (date, datetime, int64, etc)
    results = json.loads(json.dumps(results, default=str))
    # doing jsonify here manages the mimetype
    return jsonify(results)

@api.route("/generate_report/<ring_id>/<version>/", methods=["GET", "POST"])
@api_key_check
def generate_report(ring_id, version):

    # Get the request dictionary out of the JSON body
    request_dict = request.json if request.content_type == "application/json" else {}

    # Given a dict with:
    # {
    #     "report_type": "<report_type>",
    #     "entity_name": "<entity_name>",
    #     "entity_instance_identifier_attribute_name": "<filter_attribute_name>",
    #     "entity_instance_identifier_value": "<filter_value>",
    #     "metric_entity_name": "<entity_name>",
    #     "metric_attribute_name": "<attribute_name>",
    #     "metric_aggregation": "<aggregation_operation>",
    #     "metric_preference_direction": <"+inf", "-inf">,
    #     "metric_sort_direction": <"desc", "asc">,
    #     "metric_set_filter": "<dict with SQR filters>",
    #     "statement_generation_method": <"template" | "table" | "recursive">,
    #     "prompt_type": <"baseline" | "baseline_with_reqs" | "baseline_with_facts">
    #     "llm": <"gpt3.5" | "gpt4" | "mistral" | "mixtral" | "stablebeluga2" | "code_interpreter" | "none">
    #     "llm_url": "<url_to_mixtral_or_mistral_endpoint>"
    # }

    if not request_dict:
        return "No request provided."

    ring = get_or_create_ring(ring_id, version)
    operation_ontology = OperationOntology()
    llm = None
    if 'llm' in request_dict and request_dict['llm'] == 'gpt4':
        llm = GPT4Interface()
    elif 'llm' in request_dict and request_dict['llm'] == 'gpt3.5':
        llm = GPT35Interface()
    elif 'llm' in request_dict and request_dict['llm'] == 'stablebeluga2':
        llm = StableBelugaInterface()
    elif 'llm' in request_dict and request_dict['llm'] == 'mistral':
        if not request_dict['llm_url']:
            return "Please provide 'llm_url' for Mistral."
        llm = Mixtral8x7BInterface(request_dict['llm_url'])
    elif 'llm' in request_dict and request_dict['llm'] == 'mixtral':
        if not request_dict['llm_url']:
            return "Please provide 'llm_url' for Mixtral."
        llm = Mixtral8x7BInterface(request_dict['llm_url'])
    elif 'llm' in request_dict and request_dict['llm'] == 'code_interpreter':
        llm = CodeInterpreterInterface(ring.name)
    doc_manager = DocumentManager(ring,
                                  operation_ontology,
                                  statement_generation_mode=GenerationMode.OneStatementPerPlan,
                                  language_model=llm,
                                  plan_statement_generator=StatementGeneratorTemplateBased if request_dict['statement_generation_method'] == 'template' else StatementGenerator)
    sqr_composer = SQRComposer(ring, operation_ontology)
    plan_filler = SQRPlanFiller(ring)

    # Extract some directions used in the reports
    metric_sort_direction = 'desc'
    if 'metric_sort_direction' in request_dict:
        metric_sort_direction = "asc" if request_dict['metric_sort_direction'] == 'asc' else 'desc'

    metric_preference_direction = '+inf'
    if 'metric_preference_direction' in request_dict:
        metric_preference_direction = "-inf" if request_dict['metric_preference_direction'] == '-inf' else '+inf'

    def get_entity_reference(entity_name: str,
                             entity_instance_identifier_attribute_name: str,
                             entity_instance_identifier_value: str) -> str:
        entity = ring.get_entity_by_name(entity_name)
        if entity.reference and ArgType.Identifier in entity.attributes[entity_instance_identifier_attribute_name].type:
            return doc_manager.plan_statement_generator.step_expressor.get_reference_values(entity_name,
                                                                                            entity_instance_identifier_attribute_name,
                                                                                            entity_instance_identifier_value,
                                                                                            entity.reference)
        else:
            return request_dict['entity_instance_identifier_value']

    # Pull out features from the request dictionary
    report_type = eval(request_dict['report_type'])

    # Determine the entity reference for the target entity
    entity_reference = get_entity_reference(request_dict['entity_name'],
                                            request_dict['entity_instance_identifier_attribute_name'],
                                            request_dict['entity_instance_identifier_value'])

    metric_set_filter = request_dict['metric_set_filter'] if 'metric_set_filter' in request_dict else {}

    if report_type == RankingBlueprint:
        report = report_type(request_dict['entity_name'],
                             request_dict['entity_instance_identifier_attribute_name'],
                             request_dict['entity_instance_identifier_value'],
                             entity_reference,
                             request_dict['metric_entity_name'],
                             request_dict['metric_attribute_name'],
                             request_dict['metric_aggregation'],
                             metric_set_filter,
                             metric_sort_direction,
                             metric_preference_direction,
                             ring)
    elif report_type == ComparativeBenchmarkBlueprint:
        report = report_type(request_dict['entity_name'],
                             request_dict['entity_instance_identifier_attribute_name'],
                             request_dict['entity_instance_identifier_value'],
                             entity_reference,
                             request_dict['metric_entity_name'],
                             request_dict['metric_attribute_name'],
                             request_dict['metric_aggregation'],
                             metric_set_filter,
                             metric_sort_direction,
                             metric_preference_direction,
                             request_dict['benchmark_target'],
                             ring)
    elif report_type == TimeOverTimeBlueprint:
        report = report_type(request_dict['entity_name'],
                             request_dict['entity_instance_identifier_attribute_name'],
                             request_dict['entity_instance_identifier_value'],
                             entity_reference,
                             request_dict['metric_entity_name'],
                             request_dict['metric_attribute_name'],
                             request_dict['metric_aggregation'],
                             metric_set_filter,
                             metric_preference_direction,
                             request_dict['time_attribute_name'],
                             request_dict['time_zero'],
                             request_dict['time_one'],
                             ring)
    else:
        raise ValueError(f"Unknown report type being requested: {request_dict['report_type']}")

    # Get the list of {"plan_name": ..., "base_plan": ..., "access_plans": ..., "slot_fillers": ...}
    composition_specs = report.get_plan_composition_specs()

    # Remove any empty access plan filters from the composition specs
    for spec in composition_specs:
        for access_plan_ref, access_plan_spec in spec['access_plans'].items():
            access_plan_spec['access_plan_filters']['filters'] = list(filter(None, access_plan_spec['access_plan_filters']['filters']))

    def fill_and_compose(composition_specification: Dict) -> Tuple[AnalysisPlan, Dict]:

        # Build up the final composition_specification (this is essentially a copy of composition_specification that will get updated)
        final_spec = {
            "plan_name": composition_specification["plan_name"],
            "base_plan": {},
            "access_plans": {},
            "slot_fillers": composition_specification["slot_fillers"]
        }

        # Produce the base_plan
        base_plan_steps = doc_manager.analysis_engine.plan_parser.create_analysis_steps(composition_specification['base_plan']['plan_template'])
        base_plan_steps = plan_filler.fill_plan(base_plan_steps, composition_specification['slot_fillers'])
        final_spec["base_plan"] = base_plan_steps

        # Produce the access_plans
        for access_plan_ref, access_plan_spec in composition_specification["access_plans"].items():

            # Parse the raw plan into AnalysisStep objects
            access_plan_steps = doc_manager.analysis_engine.plan_parser.create_analysis_steps(access_plan_spec['access_plan'])

            # Fill in the plans with the specified slot fillers
            access_plan_steps = plan_filler.fill_plan(access_plan_steps, composition_specification['slot_fillers'])

            # Parse the raw SQR filters into AnalysisStep objects and compose them into a single filtering plan
            parsed_access_plan_filters = [doc_manager.analysis_engine.plan_parser.create_analysis_steps(filter_plan) for filter_plan in access_plan_spec["access_plan_filters"]["filters"]]
            access_plan_filter_steps = sqr_composer.compose_filter_plans(parsed_access_plan_filters, access_plan_spec["access_plan_filters"]["filter_joiner"])

            # Compose the access plan with its filter
            final_access_plan = sqr_composer.compose_filter_and_access_plan(access_plan_steps, access_plan_filter_steps)

            # Store the final access plan
            final_spec['access_plans'][access_plan_ref] = final_access_plan

        # Compose the access plan and base plan
        composed_plan_steps, slots_to_ref = sqr_composer.compose(final_spec['base_plan'], final_spec['access_plans'])

        # Create the AnalysisPlan objects which will be executed by the AnalysisEngine
        composed_plan = doc_manager.analysis_engine.plan_parser.parse_from_analysis_steps(composed_plan_steps)

        return composed_plan, slots_to_ref

    # Generate the plans and gather useful metadata for generating factual statements
    plans_and_metadata = []
    for spec in composition_specs:
        # Gather all the info
        composed_plan, slots_to_ref = fill_and_compose(spec)
        base_plan_name = spec['plan_name']
        slot_fillers = spec['slot_fillers']

        # Gather the info
        plans_and_metadata.append({
            "plan": composed_plan,
            "base_plan_name": base_plan_name,
            "slot_fillers": slot_fillers,
            "slots_to_ref": slots_to_ref,
            "results": None
        })

    # Perform the analysis
    all_results = [doc_manager.analysis_engine.sqr_single_ring_analysis(plan['plan'], doc_manager.ring, doc_manager.ring.db.session()) for plan in plans_and_metadata]

    for plan, result in zip(plans_and_metadata, all_results):
        plan['results'] = result
        plan['plan'].result = result

    # Generate statement_templates and fill with results
    if request_dict['statement_generation_method'] == 'recursive':
        # Express these plans in natural language by generating a template where the results can be slotted in
        statement_templates = [doc_manager.plan_statement_generator.generate_statement_template_from_plan(p['plan']) for p in plans_and_metadata]
        factual_statements = reduce(
            lambda a, plans_and_template: a + doc_manager.plan_statement_generator.fill_result(*plans_and_template),
            zip([p['plan'] for p in plans_and_metadata], statement_templates), [])

        # Clean the factual_statements by removing extra spaces
        factual_statements = [" ".join(f.split()) for f in factual_statements]

    elif request_dict['statement_generation_method'] == 'table':
        # Express the results of these plans as a table of results
        factual_statements = []
        for p in plans_and_metadata:
            # Build the table that will comprise one of the factual statements
            x = PrettyTable()
            x.field_names = p['results']['fieldNames']
            x.add_rows(p['results']['results'])

            # Save the factual statement
            factual_statements.append(str(x))

    else:
        # Express these plans in natural language by using a stored template where the results can be slotted in
        factual_statements = [doc_manager.plan_statement_generator.generate_statement(p['base_plan_name'],
                                                                                      p['results'],
                                                                                      p['slot_fillers'],
                                                                                      p['slots_to_ref'],
                                                                                      report.metric_nicename,
                                                                                      p['plan'],
                                                                                      metric_set_filter) for p in plans_and_metadata]

        # Clean the factual_statements by removing extra spaces
        factual_statements = [" ".join(f.split()) for f in factual_statements]

    # Generate prompt that can be used for generation
    def get_filter_statement(filter_steps: Dict[str, str]) -> str:
        # Parse in raw filter steps from the API endpoint (metric_set_filter from the request_dict) into an AnalysisPlan
        filter_plan = doc_manager.analysis_engine.plan_parser.parse_plan_snippet(filter_steps)

        # Get the reference of the final filter step
        final_step_ref = filter_plan.get_leaves()[0]

        # Call the step_expressor to express the filter step in natural language
        filter_statement = "for " + doc_manager.plan_statement_generator.step_expressor.express_filter_step(final_step_ref, filter_plan)

        return filter_statement

    filter_statement = get_filter_statement(metric_set_filter) if metric_set_filter else ""
    prompt_type = request_dict["prompt_type"] if "prompt_type" in request_dict else "baseline_with_facts"
    if prompt_type == 'baseline':
        prompt = report.build_baseline_prompt(entity_reference, filter_statement)
    elif prompt_type == 'baseline_with_reqs':
        prompt = report.build_baseline_prompt_with_info_reqs(entity_reference, filter_statement)
    else:
        prompt = report.build_baseline_prompt_with_facts(entity_reference, filter_statement, factual_statements)

    if llm:
        # Produce reports using the LLM conditioned on the factual statements
        report = doc_manager.language_model.generate(prompt)
    else:
        # Produce reports consisting of just the factual statements concatenated together
        report = " ".join(factual_statements)

    output = {
        'plans': [p['plan'].to_json() for p in plans_and_metadata],
        'facts': factual_statements,
        'prompt': prompt,
        'report': report
    }

    return output
