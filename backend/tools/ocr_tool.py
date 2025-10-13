import base64
import mimetypes
from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

class OCR_Input(BaseModel):
    image_path: str = Field(..., description="Path to the image file to be processed")

# class receipt(BaseModel): # FIXME: To be deleted
#     date: str = Field(..., description="return data in YYYY-MM-DD format, do not report time")
#     amount: str = Field(..., description="return amount with currency type in format amount-type, e.g. 100-YEN, 10-USD")
#     merchant: str = Field(..., description="merchant name, if not found, return '[UNKNOWN]'")
#     raw_text: str = Field(..., description="Full verbatim transcription of text, preserving line breaks")

class OCR_Receipt(BaseModel):
    raw_text: str = Field(..., description="Full verbatim transcription of text, preserving line breaks for one receipt")

class OCR_Results(BaseModel):
    ocr_results: List[OCR_Receipt] = Field(..., description="OCR result for all receipts found in the image")

prompt_template = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text":
                ("Extract receipt information from a screenshot and return it as JSON (strictly matching fields). Rules:\n"
                "1) First, transcribe full raw_text verbatim (preserving line breaks).\n"
                "2) Then, Divide the full raw_text into each receipts.\n"
                "3) Don't make it up.\n"
                )
            },
        ],
    }
]

def image_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    b64 = base64.b64encode(open(path, "rb").read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

@tool('ocr_tool', args_schema=OCR_Input, return_direct=False)
def ocr_tool(image_path) -> OCR_Results:
    """
    Extract receipt information from an image using OCR and a language model.
    :param input: OCR_Input object containing the image path
    :param model: Optional ChatOpenAI model instance. If None, a default model will be created.
    :return: OCR_Output object containing the extracted receipt information
    """

    # Step 1: Setting up model
    model = ChatOpenAI(model="gpt-5-nano", temperature=0)
    structured_llm = model.with_structured_output(OCR_Results)

    # Step 2: Convert image to data URL
    img_url = image_to_data_url(image_path)

    # Step 3: Prepare prompt with image URL
    OCR_PROMPT = prompt_template
    OCR_PROMPT[0]["content"].append({"type": "image_url", "image_url": {"url": img_url}})

    # Step 4: Invoke model and return result
    result: OCR_Results = structured_llm.invoke(OCR_PROMPT)
    return result

if __name__ == "__main__":
    from dotenv import load_dotenv
    test_file = "D:\Personal_Projects/auto-accounting-agent/test_data/test.jpg"
    load_dotenv(override=True)
    response = ocr_tool.invoke(input=test_file)
    for i in response.ocr_results:
        print(i)
        print('-----------------------------------')

#