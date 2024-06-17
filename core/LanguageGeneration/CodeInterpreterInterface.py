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

import json, os, time
import openai
from pathlib import Path
from typing import Dict

class CodeInterpreterInterface:
    def __init__(self,
                 ring_name):
        # Init access to OpenAI's API
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.client = openai.OpenAI(self.openai_api_key)

        p = os.path.join(Path(__file__).with_name('local_datasets'), ring_name)

        existing_files = self.client.files.list().data

        self.files = [self.client.files.retrieve(next(filter(lambda f: f.filename == file_name, existing_files)).id) if file_name in map(lambda f: f.filename, existing_files) else self.client.files.create(file=open(os.path.join(p, file_name), 'rb'), purpose="assistants") for file_name in os.listdir(p) if file_name.endswith('.csv')]

        self.assistant = self.client.beta.assistants.create(
            instructions='Write and run code to generate reports about the given data.',
            tools=[{"type": "code_interpreter"}],
            # model="gpt-3.5-turbo",
            model="gpt-4",
            file_ids=[file.id for file in self.files]
        )
        self.thread = self.client.beta.threads.create()

    def generate(self,
                 prompt: str) -> str:
        # Feed the prompt to the language model
        response = self.get_response(prompt)

        # Extract the generation from the response
        qdmr = self.extract_generation_from_response(response)

        return qdmr

    def get_response(self,
                     prompt: str) -> Dict:
        # Make the API call off to GPT
        print(f"Prompt:\n{prompt}")

        message = self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt
        )

        run = self.client.beta.threads.runs.create(
            thread_id = self.thread.id,
            assistant_id = self.assistant.id
        )

        while run.status in ['queued', 'in_progress']:
            print('evaluating')
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(
                thread_id = self.thread.id,
                run_id = run.id
            )
        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread.id
            )
        else:
            raise Exception('Connection most likely timed out.')
        # Save the raw output
        print("RAW OPENAI RESPONSE")
        print(messages)

        return messages

    def extract_generation_from_response(self,
                                         response: Dict) -> str:
        # Pull out the generated text from the response
        message_content = '\n\n'.join(reversed([thread_message.content[0].text.value for thread_message in response.data]))

        # Clean up the string
        message_content = message_content.strip()

        return message_content

if __name__ == "__main__":
    code_interpreter = CodeInterpreterInterface('ZillowRent')
    # report = code_interpreter.generate("Give me a report about the contributions of contributor with name UAW REGION 4.")
    report = code_interpreter.generate("Generate a report for Chicago, IL ranking it according to max average rent for date greater than or equal to 01-01-2015. The metric is max average rent. In the report, include information about the value of the metric for Chicago, IL, the total number of entities being ranked, the rank of Chicago, IL according to the metric, the top three entities according to the metric, how far away from the top of the ranking Chicago, IL is according to the metric, the average value of the metric for all entities, and whether or not the metric value for Chicago, IL is greater than the average value of the metric for all entities.")
    print(report)
