"""DO NOT rename this file!"""
import os
import json
import textwrap
import time
from string import Template

import openai

from tqdm import tqdm

class MyTemplate(Template):
    delimiter = "%"

class Submission:
    """A submission template. """

    def __init__(self, output_file: str):
        """You need to specify the following arguments."""

        self.output_file = output_file

        self.task = "Automated_Theorem_Generation"
        self.phase = "development"          # [development, final]

        self.base_url = "http://120.77.8.29:12345/v1/"  # The base url of the model server
        # If you are using OpenAI API or have set API key for
        # your own model, please fill in your API key
        self.api_key = "EMPTY"
        self.model = "./Mistral-7B-Instruct-v0.2"       # Your own model path, or GPTs
        self.prompt = MyTemplate("""
            You are a math expert and familar with Metamath formal language. 
            Now please derive new theorems from the following axioms, symbols and proven theorems. 
            Axioms: 
                %Axioms
            Symbols:
                %Symbols
            Proven theorems:
              %proven_theorems
            
            Your output should follow the format as symbols and axioms.
            
            Example:
            {"theorem": "mp2", "type": "$p", "conclusion": "|- ch", "d_vars": "", "f_hypos": ["wff ph", "wff ps", "wff ch"], "e_hypos": ["|- ph", "|- ps", "|- ( ph -> ( ps -> ch ) )"], "proof_steps": "wps wch mp2.2 wph wps wch wi mp2.1 mp2.3 ax-mp ax-mp", "references": ["mp2.1", "mp2.2", "mp2.3", "wi", "ax-mp"]}
                                      
            Note: each proof step refers to the name of the theorem or axiom used in the proof， ``NAME.INDEX`` refers to the INDEX-th hypothesis of theorem NAME. The proof should be able to be verified by Metamath.
                                      
            Your response:
        """)

        # custom generation parameters
        self.max_tokens = 256
        self.temperature = 0.7
        self.top_p = 0.7
        self.frequency_penalty = 0.0

    def generate(self, prompt):
        """We DO NOT recommend modifying this function, as 
        it will be used to test if the model is accessable"""

        # openai.base_url = "https://api.deepseek.com"

        messages = [{"role": "user", "content": prompt},        ]
        # models https://platform.openai.com/docs/models/gpt-4-turbo-and-gpt-4
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo-1106", messages=messages, max_tokens=self.max_tokens,
            temperature=self.temperature, top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,seed=2024
        )
        print('completion',completion)
        print('\n')
        
        # raise Exception(str(completion))

        return completion.choices[0].message.content

    def post_process(self, model_output: str):
        """You can post-process the model output here, such as extract the theorem and verify the proof.
        For more information about proof in Metamath, please refer to:
        https://github.com/david-a-wheeler/mmverify.py"""
        end_of_theorem_index = model_output.index("}") + 1
        print('model_output[:end_of_theorem_index]',model_output[:end_of_theorem_index])
        theorem= json.loads(model_output[:end_of_theorem_index])
        keys = ["theorem", "type", "conclusion", "d_vars", "f_hypos", "e_hypos", "proof_steps", "references"]
        if type(theorem) != dict:
            raise ValueError(f"Output should be a dictionary, got {type(theorem)}.")
        for key in keys:
            if key not in theorem:
                raise ValueError(f"Key {key} not found in the theorem.")

        return theorem

    def run(self, axiom_file: str, symbol_file: str):
        """Run your model on the given input data, and store the 
        predictions into the output file."""

        known_theorems = []
        axioms= []
        with open(axiom_file, 'r', encoding="utf8") as f:
            lines = f.readlines()
            for line in lines:
                axiom = json.loads(line)
                known_theorems.append(axiom)
                axioms.append(axiom)
        symbols=  []
        with open(symbol_file, 'r', encoding="utf8") as f:
            lines = f.readlines()
            for line in lines:
                symbol = json.loads(line)
                known_theorems.append(symbol)
                symbols.append(symbol)

        """You can either parse all known symbols and axioms and input them as prompts, 
        or you can sample them in some way and input them to the model (like we do in self.prompt)."""

        outputs = []

        start = time.time()
        """You can set any termination conditions, but please note that 
          the time to validate a submission is at most 2 hours 
        (including executing your code, and evaluating the theorems you generate)."""
        while time.time() - start < 60 * 5:    
            # Your model are expected to generate new theorems from its previous outputs.
            prompt = self.prompt.safe_substitute(proven_theorems="\n".join(outputs),Axioms=axioms,Symbols=symbols)
            print('prompt is ',prompt)
            print('\n')
            model_output = self.generate(prompt)
            try:
                theorem = self.post_process(model_output)
            except:
                print("Error in post-processing, skip this output.")
                continue
            print(theorem)
            outputs.append(json.dumps(theorem))

        if not os.path.exists(self.output_file):
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, 'w+', encoding='utf8') as f:
            for output in outputs:
                f.write(output)
                f.write('\n')
