<div align="center">

# Auto-Accounting Agent
![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
</div>

// TODO: Add demo result here


<!-- --- -->

## Table of Contents
1. [Introduction](#introduction)
2. [Usage](#usage)
   - [Installation](#installation)
   - [Quick Start](#quick_start)


<!-- --- -->

## Introduction <a name="introduction"></a>
Accounting, as a means of expense management, is essential in daily life. However, accounting software on the market requires users to manually fill in for each income and expense. For daily life, we may have dozens of expenses every day for purchasing daily necessities and food. Therefore, manual accounting is a very troublesome thing.

This project has built an agent that can help users **automate the accounting process**, allowing users to complete the accounting of multiple income and expenses through very simple operations.


<!-- --- -->

## Usage <a name="usage"></a>
### Installation <a name="installation"></a>
**1. Clone the repository**
```bash
git clone https://github.com/AkatsukiQAQ/auto-accounting-agent
cd auto-accounting-agent
```

**2. Environment setup**

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. `pyproject.toml` + `uv.lock` are source of truth; there is no `requirements.txt`.

```bash
# Install uv if you don't have it (one-off)
pip install uv

# Create .venv/ and install runtime + dev deps (pinned by uv.lock)
uv sync --dev
```

**PyCharm:** point **Settings → Project → Python Interpreter** at `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux). PyCharm 2024.1+ can also select the uv interpreter type directly from `pyproject.toml`.

**3. Set up API keys**

Create `.env` file and write in your OpenAI API key.
```bash
echo "API_KEY=your_api_key_here" > .env
```

**4. Run tests**
```bash
uv run pytest backend/tests/core/
```

### Quick Start <a name="quick_start"></a>

Prepare a screenshot in you payment App, such as PayPay.
Then, create a file named `test.py`, and run the following script.
```python
# test.py
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from backend.tools import ocr_tool, model_ocr_result_parser, classification_tool
from langgraph.prebuilt import create_react_agent

load_dotenv(override=True)

tools = [ocr_tool, model_ocr_result_parser, classification_tool]

llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
agent = create_react_agent(llm, tools)

test_data_path = "your_screenshot_path_here"
prompt = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text":
                 (
                     "Help my to extract receipt information from a screenshot. You can use the tools I gave to you.\n"
                     "Tell me how much I spent for different category and give me some advices about how to reduce expense.\n"
                     "The image path is provided below.\n"
                     f"{test_data_path}"
                 )
            }
        ],
    }
]


result = agent.invoke({"messages": prompt})
print(result['messages'][-1].content)
```
The agent will give a report about how much you spend in pre-defined category, and also give some advices about how to reduce the expense.


<!-- --- -->

## TO-DO & Next Step <a name="usage"></a>
- [ ] Build a Web UI for the pipeline using FastAPI and React


<!-- --- -->