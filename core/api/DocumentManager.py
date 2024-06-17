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

from typing import Tuple, Type, Dict, List, Optional

from core.RingObjects.Ring import Ring

from core.Analysis.AnalysisEngine import AnalysisEngine
from core.Analysis.OperationOntology import OperationOntology
from core.LanguageGeneration.GPT35Interface import GPT35Interface
from core.LanguageGeneration.GPT4Interface import GPT4Interface

from core.Planning.StatementGenerator import StatementGenerator, GenerationMode

class DocumentManager:

    def __init__(self,
                 ring: Ring,
                 operation_ontology: OperationOntology,
                 statement_generation_mode: GenerationMode = GenerationMode.OneStatementPerPlan,
                 qa_index_path: Optional[str] = None,
                 language_model = GPT4Interface(),
                 plan_statement_generator = StatementGenerator):
        self.ring = ring
        self.operation_ontology = operation_ontology
        self.analysis_engine = AnalysisEngine(self.ring)
        self.language_model = language_model
        self.plan_statement_generator = plan_statement_generator(self.ring, self.operation_ontology, mode=statement_generation_mode)
