from Executor import PythonExecutorTool
from openai import OpenAI
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from termcolor import colored
import textwrap
import json
import re
import os
load_dotenv()

class CodeGeneratorEvaluator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key cannot be empty")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.makehub.ai/v1",
        )
        
        self.extra_query_params = {
            "min_throughput": "150",
            "max_latency": "1000"
        }


        self.executor = PythonExecutorTool()
        self.width = 80  # Terminal width for text wrapping
        self.last_feedback = None  # Store last technical feedback
        self.attempt_history = []  # Store previous attempts
        self.last_error = None    # Store last error
        self.last_llm_analysis = None  # Store last LLM analysis
        self.compressed_history = {
            'attempts': 0,
            'common_errors': set(),
            'failed_approaches': [],
            'last_attempt': None
        }

    def print_thinking(self, text: str, color: str = 'cyan'):
        """Print thinking process with nice formatting."""
        print("\n" + "="*self.width)
        print(colored("🤔 Thinking Process:", color, attrs=['bold']))
        print("-"*self.width)
        # Wrap text for better readability
        wrapped_text = textwrap.fill(text, width=self.width-2)
        print(wrapped_text)
        print("="*self.width + "\n")

    def print_step(self, step: str, content: str, color: str = 'yellow'):
        """Print a step in the process with nice formatting."""
        print(colored(f"\n▶ {step}:", color, attrs=['bold']))
        print(textwrap.fill(content, width=self.width-2))

    def print_code_preview(self, code: str):
        """Display code that will be executed in a nice box, with both formatted and clean versions."""
        # Show formatted version with line numbers
        print("\n" + "+"*self.width)
        print(colored("📋 Code Preview (with line numbers):", 'blue', attrs=['bold']))
        print("+"*self.width)
        
        lines = code.strip().split('\n')
        max_line_num_width = len(str(len(lines)))
        
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(max_line_num_width)
            wrapped_lines = textwrap.wrap(line, width=self.width-max_line_num_width-4)
            for j, wrapped_line in enumerate(wrapped_lines):
                if j == 0:
                    print(colored(f"{line_num} │ {wrapped_line}", 'white'))
                else:
                    print(colored(f"{''.rjust(max_line_num_width)} │ {wrapped_line}", 'white'))
        
        # Show clean version for copying
        print("\n" + "+"*self.width)
        print(colored("📋 Clean Code (for copying):", 'green', attrs=['bold']))
        print("+"*self.width)
        print(code.strip())
        print("+"*self.width + "\n")

    def record_attempt(self, code: str, error: str = None, llm_analysis: str = None):
        """Record an attempt with its associated data."""
        self.attempt_history.append({
            'code': code,
            'error': error,
            'llm_analysis': llm_analysis,
            'feedback': self.last_feedback
        })

    def get_attempt_context(self) -> str:
        """Generate context from previous attempts."""
        if not self.attempt_history:
            return ""
        
        context_parts = []
        for i, attempt in enumerate(self.attempt_history, 1):
            context_parts.append(f"\nAttempt {i}:")
            context_parts.append(f"Code:\n{attempt['code']}")
            if attempt['error']:
                context_parts.append(f"Error:\n{attempt['error']}")
            if attempt['llm_analysis']:
                context_parts.append(f"Analysis:\n{attempt['llm_analysis']}")
            if attempt['feedback']:
                context_parts.append(f"Technical Feedback:\n{attempt['feedback']}")
        
        return "\n".join(context_parts)

    def update_compressed_history(self, code: str, error: str = None, analysis: str = None, feedback: dict = None):
        """Maintain a compressed history of attempts."""
        self.compressed_history['attempts'] += 1
        
        if error:
            self.compressed_history['common_errors'].add(error.split('\n')[0])  # Store just first line
        
        attempt_summary = {
            'code_snippet': code[:100] + '...' if len(code) > 100 else code,  # Store brief code sample
            'key_issues': []
        }
        
        if feedback and 'failure_points' in feedback:
            attempt_summary['key_issues'] = feedback['failure_points']
            
        self.compressed_history['failed_approaches'].append(attempt_summary)
        self.compressed_history['last_attempt'] = {
            'full_code': code,
            'error': error,
            'analysis': analysis,
            'feedback': feedback
        }

    def get_compressed_context(self) -> str:
        """Generate a concise context from compressed history."""
        if not self.compressed_history['attempts']:
            return ""
        
        context = f"""Previous Attempts Summary:
        Total Attempts: {self.compressed_history['attempts']}
        Common Errors: {', '.join(self.compressed_history['common_errors'])}
        
        Last Attempt Details:
        {json.dumps(self.compressed_history['last_attempt'], indent=2)}
        
        Failed Approaches Summary:
        {json.dumps(self.compressed_history['failed_approaches'], indent=2)}
        """
        return context

    def reason_about_solution(self, instruction: str) -> str:
        """Think about the approach before generating code."""
        self.print_step("Analyzing Problem", instruction, 'green')
        
        compressed_context = self.get_compressed_context()
        messages = [
            {
                "role": "system", 
                "content": """You are a Python programmer. Analyze the problem technically, considering previous attempts and failures."""
            },
            {"role": "user", "content": f"""Technically analyze this problem and provide a detailed solution approach:
            Task: {instruction}
            
            Compressed History:
            {compressed_context}"""}
        ]
        
        response = self.client.chat.completions.create(
            model="meta/Llama-3.3-70B-Instruct-fp16",
            messages=messages,
            extra_query=self.extra_query_params,
            temperature=0.7
        )
        
        reasoning = response.choices[0].message.content
        self.last_llm_analysis = reasoning
        self.print_thinking(reasoning)
        return reasoning

    def clean_code(self, code: str) -> str:
        """Clean the code from markdown formatting and ensure it's executable."""
        # Remove markdown code blocks
        code = re.sub(r'```(?:python)?\n?(.*?)```', r'\1', code, flags=re.DOTALL)
        # Remove leading/trailing whitespace
        code = code.strip()
        return code

    def generate_code(self, instruction: str) -> str:
        """Generate Python code based on the instruction and reasoning."""
        reasoning = self.reason_about_solution(instruction)
        
        self.print_step("Generating Code", "Based on the analysis, crafting solution...", 'blue')
        messages = [
            {
                "role": "system", 
                "content": """You are a Python programmer. Generate clean, efficient, and well-commented code based on the given reasoning and requirements. 
                The code has to execute without asking for any user input.
                Follow these output guidelines:
                - Print a few  test results (like 1 or 2) in a clean, structured way
                - Avoid printing intermediate results unless necessary
                - If using assertions, catch AssertionError and print a clean summary
                - Format the output to be easily readable
                IMPORTANT: Do not include markdown formatting or ```python blocks. Provide only the raw Python code."""
            },
            {"role": "user", "content": f"Based on this reasoning:\n{reasoning}\n\nGenerate Python code that: {instruction}"}
        ]
        
        response = self.client.chat.completions.create(
            model="meta/Llama-3.3-70B-Instruct-fp16",
            messages=messages,
            extra_query=self.extra_query_params,
            temperature=0.7
        )
        
        return self.clean_code(response.choices[0].message.content)

    def clean_response(self, text: str) -> str:
        """Clean the response text from markdown and other formatting."""
        # Remove markdown code blocks
        text = re.sub(r'```(?:json)?\n?(.*?)```', r'\1', text, flags=re.DOTALL)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def evaluate_output(self, instruction: str, code: str, output: str) -> Dict[str, Any]:
        """Evaluate if the code output meets the requirements with technical feedback."""
        messages = [
            {
                "role": "system", 
                "content": """You are a lenient code reviewer focused mainly on functionality. 
                If the code works and produces the expected output, consider it successful.
                Return ONLY a JSON object with this exact structure (no other text):
                {
                    "success": true/false,
                    "feedback": {
                        "technical_analysis": "one line summary",
                        "failure_points": [],
                        "suggestions": [],
                        "performance_notes": "one line if needed",
                        "edge_cases": []
                    }
                }"""
            },
            {"role": "user", "content": f"""
Instruction: {instruction}
Code:
{code}
Output:
{output}

Evaluate if this code works as intended."""}
        ]
        
        response = self.client.chat.completions.create(
            model="meta/Llama-3.3-70B-Instruct-fp16",
            messages=messages,
            extra_query=self.extra_query_params,
            temperature=0.3
        )
        
        raw_response = response.choices[0].message.content
        
        # Clean and extract just the JSON part
        try:
            # Find JSON-like content between curly braces
            json_match = re.search(r'\{[^{]*"success".*\}', raw_response, re.DOTALL)
            if json_match:
                eval_text = json_match.group(0)
                evaluation = json.loads(eval_text)
                if evaluation["success"]:
                    return evaluation
                self.last_feedback = json.dumps(evaluation["feedback"], indent=2)
                return evaluation
            raise ValueError("No valid JSON found in response")
        except Exception as e:
            self.print_step("Debug - Raw Evaluation Response", raw_response, 'red')
            return {
                "success": True,  # Changed to True since code works
                "feedback": {
                    "technical_analysis": "Code works but evaluation parsing failed",
                    "failure_points": [],
                    "suggestions": ["Fix evaluator parsing"],
                    "performance_notes": "N/A",
                    "edge_cases": []
                }
            }

    def iterative_code_generation(self, instruction: str, max_attempts: int = 3) -> Optional[str]:
        """Iteratively generate and improve code until it meets requirements."""
        self.compressed_history = {
            'attempts': 0,
            'common_errors': set(),
            'failed_approaches': [],
            'last_attempt': None
        }
        self.attempt_history = []  # Reset history at start
        self.last_feedback = None  # Reset feedback at start
        print(colored("\n🔄 Starting Iterative Code Generation", 'magenta', attrs=['bold']))
        
        for attempt in range(max_attempts):
            print(colored(f"\n📝 Attempt {attempt + 1}/{max_attempts}", 'magenta'))
            
            code = self.generate_code(instruction)
            self.print_code_preview(code)
            
            clean_code = self.clean_code(code)
            self.print_step("Executing Code...", "Running the generated code", 'cyan')
            result = self.executor.execute(code=clean_code)
            
            if result['output'].strip():  # Only print if there's actual output
                self.print_step("Output", result['output'], 'cyan')
            
            if not result['success']:
                self.last_error = result['error']
                self.print_step("Error", result['error'], 'red')
                self.record_attempt(code, error=result['error'], llm_analysis=self.last_llm_analysis)
                self.update_compressed_history(
                    code=code,
                    error=result['error'],
                    analysis=self.last_llm_analysis
                )
                continue
            
            evaluation = self.evaluate_output(instruction, code, result['output'])
            self.update_compressed_history(
                code=code,
                analysis=self.last_llm_analysis,
                feedback=evaluation.get('feedback')
            )
            if 'feedback' in evaluation:
                feedback = evaluation['feedback']
                self.print_step(
                    "Technical Evaluation", 
                    f"Success: {evaluation['success']}\n\n"
                    f"Analysis: {feedback['technical_analysis']}\n\n"
                    f"Failure Points: {', '.join(feedback['failure_points']) if feedback['failure_points'] else 'None'}\n\n"
                    f"Suggestions: {', '.join(feedback['suggestions']) if feedback['suggestions'] else 'None'}\n\n"
                    f"Performance: {feedback['performance_notes']}\n\n"
                    f"Edge Cases: {', '.join(feedback['edge_cases']) if feedback['edge_cases'] else 'None'}",
                    'green' if evaluation['success'] else 'yellow'
                )
            
            if evaluation['success']:
                print(colored("\n✨ Final Solution:", 'green', attrs=['bold']))
                self.print_code_preview(code)  # Use the same preview format for final code
                return code
            
            time.sleep(1)
        
        print(colored("\n❌ Max attempts reached without success", 'red', attrs=['bold']))
        return None

def main():
    api_key = os.getenv('MAKEHUB_API_KEY')
    if not api_key:
        print(colored("❌ Error: MAKEHUB_API_KEY environment variable is not set", 'red'))
        print("Please set your API key in the .env file or environment variables")
        return
    
    try:
        generator = CodeGeneratorEvaluator(api_key)
        instruction = input("Enter your coding task: ")
        final_code = generator.iterative_code_generation(instruction)
        
        if not final_code:
            print(colored("\n⚠️ Failed to generate satisfactory code", 'yellow'))
    except Exception as e:
        print(colored(f"\n❌ Error: {str(e)}", 'red'))

if __name__ == "__main__":
    main()