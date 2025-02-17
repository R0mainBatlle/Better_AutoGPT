# This file defines the PythonExecutorTool which executes Python code in an isolated environment.
import subprocess
import tempfile
import os
import sys
from typing import List, Dict, Any
# Updated absolute import for base_tool
from base_tool import BaseTool, ToolParameter, ParameterType

class PythonExecutorTool(BaseTool):
    """
    Tool for executing user-provided Python code in an isolated environment.
    """
    def __init__(self):
        # Initialize the PythonExecutorTool with its name and description.
        super().__init__(
            name="execute_python",
            description="Exécute du code Python et retourne le résultat. Le code est exécuté dans un environnement isolé."
        )

    def _define_parameters(self) -> List[ToolParameter]:
        # Define the tool parameters including code to execute and optional timeout.
        return [
            ToolParameter(
                name="code",
                param_type=ParameterType.STRING,
                description="Le code Python à exécuter",
                required=True
            ),
            ToolParameter(
                name="timeout",
                param_type=ParameterType.INTEGER,
                description="Temps maximum d'exécution en secondes",
                required=False,
                default=10,
                constraints={"min": 1, "max": 30}
            )
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        # Retrieve provided parameters.
        code = kwargs.get('code')
        timeout = kwargs.get('timeout', 10)

        # Create a temporary file to write the user-provided Python code.
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        # Entertainment: print LLM thinking message in yellow.
        print("\033[33mLLM is thinking...\033[0m")
        print("\033[33mLLM is trying some code now...\033[0m")

        try:
            # Execute the temporary Python file using the current interpreter
            process = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Entertainment: print execution output in green for stdout and red for stderr.
            if process.stdout:
                print("\033[32mOutput:\n" + process.stdout + "\033[0m")
            if process.stderr:
                print("\033[31mError:\n" + process.stderr + "\033[0m")

            result = {
                "success": process.returncode == 0,
                "output": process.stdout,
                "error": process.stderr,
                "return_code": process.returncode
            }

        except subprocess.TimeoutExpired:
            error_msg = f"L'exécution a dépassé le délai de {timeout} secondes"
            print("\033[31m" + error_msg + "\033[0m")
            result = {
                "success": False,
                "output": "",
                "error": error_msg,
                "return_code": -1
            }
        except Exception as e:
            print("\033[31mError: " + str(e) + "\033[0m")
            result = {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1
            }
        finally:
            # Clean up the temporary file regardless of execution outcome.
            try:
                os.unlink(temp_file_path)
            except:
                # Ignoring cleanup errors.
                pass

        return result