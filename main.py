from Executor import PythonExecutorTool
from openai import OpenAI
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from termcolor import colored
import textwrap
import json
import re

load_dotenv()

class CodeGeneratorEvaluator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.executor = PythonExecutorTool()
        self.width = 80  # Terminal width for text wrapping
        self.last_feedback = None  # Store last technical feedback

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

    def reason_about_solution(self, instruction: str) -> str:
        """Think about the approach before generating code."""
        self.print_step("Analyzing Problem", instruction, 'green')
        
        # Include previous feedback if available
        feedback_context = ""
        if self.last_feedback:
            feedback_context = f"\nPrevious attempt failed with following technical feedback:\n{self.last_feedback}\nConsider this feedback while planning the solution."
        
        messages = [
            {
                "role": "system", 
                "content": """You are a Python programmer. Analyze the problem technically, considering:
                - Input/Output specifications
                - Edge cases and potential failure points
                - Performance considerations
                - Implementation constraints
                If provided, analyze previous failure feedback to avoid similar issues."""
            },
            {"role": "user", "content": f"Technically analyze this problem and provide a detailed solution approach: {instruction}{feedback_context}"}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        
        reasoning = response.choices[0].message.content
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
                - Print test results in a clean, structured way
                - Avoid printing intermediate results unless necessary
                - If using assertions, catch AssertionError and print a clean summary
                - Format the output to be easily readable
                IMPORTANT: Do not include markdown formatting or ```python blocks. Provide only the raw Python code."""
            },
            {"role": "user", "content": f"Based on this reasoning:\n{reasoning}\n\nGenerate Python code that: {instruction}"}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
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
                "content": """You are a technical code reviewer. Evaluate the code implementation and output.
                Return a dictionary with the following structure:
                {
                    "success": boolean,
                    "feedback": {
                        "technical_analysis": "Detailed technical analysis of the implementation",
                        "failure_points": ["List of specific technical issues if any"],
                        "suggestions": ["Specific technical improvements"],
                        "performance_notes": "Notes about code efficiency and performance",
                        "edge_cases": ["Edge cases that might cause issues"]
                    }
                }
                Focus on technical aspects like algorithm choice, error handling, edge cases, and performance."""
            },
            {"role": "user", "content": f"""
Instruction: {instruction}
Code:
{code}
Output:
{output}

Provide a technical evaluation of this implementation."""}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3
        )
        
        raw_response = response.choices[0].message.content
        eval_text = self.clean_response(raw_response)
        
        try:
            evaluation = json.loads(eval_text)
            # Store technical feedback for next iteration
            if not evaluation["success"]:
                self.last_feedback = json.dumps(evaluation["feedback"], indent=2)
            return evaluation
        except (json.JSONDecodeError, KeyError):
            self.print_step("Debug - Raw Evaluation Response", raw_response, 'red')
            return {
                "success": False,
                "feedback": {
                    "technical_analysis": "Failed to parse evaluation response",
                    "failure_points": ["Evaluation response parsing error"],
                    "suggestions": ["Check the raw response format"],
                    "performance_notes": "N/A",
                    "edge_cases": []
                }
            }

    def iterative_code_generation(self, instruction: str, max_attempts: int = 3) -> Optional[str]:
        """Iteratively generate and improve code until it meets requirements."""
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
                self.print_step("Error", result['error'], 'red')
                continue
            
            evaluation = self.evaluate_output(instruction, code, result['output'])
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
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    generator = CodeGeneratorEvaluator(api_key)
    
    instruction = input("Enter your coding task: ")
    final_code = generator.iterative_code_generation(instruction)
    
    if (final_code):
        # Remove redundant printing of final code since it's already shown in the success message
        pass

if __name__ == "__main__":
    main()