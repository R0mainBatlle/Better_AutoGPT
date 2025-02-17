# Ultimate Code Generator and Evaluator

An AI-powered Python code generator and evaluator that uses OpenAI's GPT models to create, test, and improve code solutions iteratively.

## Features

- 🤖 AI-powered code generation
- 🔄 Iterative improvement with feedback
- 📊 Technical evaluation of solutions
- 🎨 Beautiful terminal output
- ⚡ Performance consideration
- 🐛 Error handling and edge case detection

## Prerequisites

- Python 3.8+
- OpenAI API key

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Ultimate-Everything.git
cd Ultimate-Everything
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install openai python-dotenv termcolor
```

4. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the main script:
```bash
python main.py
```

When prompted, enter your coding task. The system will:
1. Analyze the problem
2. Generate a solution
3. Test the code
4. Evaluate the results
5. Iterate if necessary

## Example

Input:
```
Enter your coding task: Write a function that finds the longest palindrome in a string
```

The system will:
- Analyze the requirements
- Generate optimal code
- Test the solution
- Provide technical feedback
- Improve the solution if needed

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
