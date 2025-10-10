import re
import unicodedata

from typing import List, Optional

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from backend.tools import load_config
from pydantic import BaseModel, Field
from backend.tools.ocr_tool import OCR_Results

cfg = load_config('OcrResultParserConfigs.yaml')
accepted_currencies = cfg['currency']['accepted_currencies']

# Currency symbols to codes
CURRENCY_TABLE = {
    "¥": "¥",   # This symbol is used in both CNY and JPY and is not easy to distinguish without context
    "CNY": "CNY", "元": "CNY", "RMB": "CNY", "块": "CNY", "￥": "CNY", "人民币": "CNY",
    "HKD": "HKD", "HK$": "HKD",
    "JPY": "JPY", "円": "JPY", "YEN": "JPY", "〒": "JPY",
    "USD": "USD", "$": "USD", "US$": "USD",
    "EUR": "EUR", "€": "EUR", "euro": "EUR",
    "GBP": "GBP", "£": "GBP", "pound": "GBP",
    "KRW": "KRW", "₩": "KRW",
}

CURRENCY_HINTS = [
    r"¥",
    r"CNY|元|RMB|块|￥|人民币",
    r"HKD|HK\$",
    r"JPY|円|YEN|〒",
    r"USD|US\$|\$",
    r"EUR|€|euro",
    r"GBP|£|pound",
    r"KRW|₩",
]

# Definition of data structures
# Input is 'OCR_Full_Output' defined in backend/tools/ocr_tool.py
class ParsedReceipt(BaseModel):
    raw_text: str = Field(..., description="Full verbatim transcription of text, preserving line breaks of one receipt")
    currency: Optional[str] = Field(None, description="Detected currency code, e.g. USD, CNY, JPY")
    amount: Optional[float] = Field(None, description="Detected amount")
    date: Optional[str] = Field(None, description="Detected date in YYYY-MM-DD format")
    time: Optional[str] = Field(None, description="Detected time in HH:MM format")
    merchant: Optional[str] = Field(None, description="Detected merchant name")

class ParsedOcrResult(BaseModel):
    parsed_ocr_results: List[ParsedReceipt] = Field(..., description="Parsed results for all receipts")


# Normalization
class Normalizer:
    @ staticmethod
    def _normalize_text(text: str) -> str:
        text = unicodedata.normalize("NFKC", text)  # Normalize unicode characters
        text = text.replace('\r\n', '\n').replace('\r', '\n')  # Normalize line endings
        text = re.sub(r"[ \t\u200b\u3000]+", " ", text)  # Normalize spaces
        return text.strip()

    @ staticmethod
    def _split_lines(text: str) -> List[str]:
        return [line.strip() for line in text.split('\n') if line.strip()]

class CurrencyParser:
    def __init__(self):
        cfg = load_config('OcrResultParserConfigs.yaml')
        self.symbol_defaults = cfg['currency']['symbol_defaults']

    def detect_currency(self, text: str) -> Optional[str]:
        for pat in CURRENCY_HINTS:
            if re.search(pat, text, flags=re.IGNORECASE):
                # 取第一个命中的符号→ISO
                m = re.search(pat, text, flags=re.IGNORECASE)
                token = m.group(0)
                # 标准化键
                for k, iso in CURRENCY_TABLE.items():
                    if k.lower() == token.lower():
                        return iso

                # Special processing for $
                if token == "$":
                    # Some other country also use $. If it can not determine the currency is USD, return None first.
                    if self.symbol_defaults[token]:
                        return self.symbol_defaults[token]
                    if "US" in text or "USD" in text.upper():
                        return "USD"

                if token == "¥":
                    # This symbol is used in both CNY and JPY and is not easy to distinguish without context
                    # If there is no other hint, return None first.
                    if self.symbol_defaults[token]:
                        return self.symbol_defaults[token]
                    if "CNY" in text.upper() or "元" in text or "人民币" in text:
                        return "CNY"
                    if "JPY" in text.upper() or "円" in text or "YEN" in text:
                        return "JPY"
                    return None

                return CURRENCY_TABLE.get(token, None)

        return None

# TODO: Non-AI parser development -> Amount parser, Date parser, Vendor parser, Category parser, etc.


@ tool('llm_ocr_result_parser', args_schema=OCR_Results, return_direct=False)
def llm_ocr_result_parser(ocr_results) -> ParsedOcrResult:
    """
    Extract receipt information from the OCR result using LLM and return it as JSON.
    :param ocr_results: List of OCR results for all receipts, OCR_Full_Output object
    :return: List of extracted receipt information in structured format
    """
    # Step 1: Prepare text for LLM
    text = (
                "Extract receipt information from the OCR result and return it as JSON (strictly matching fields). Rules:\n"
                "1) Extract information for each receipt in the OCR result. You should process each receipt separately.\n"
                "2) For each receipt, detect the currency type and amount. If you can't find it, return null.\n"
                "3) For each receipt, detect the date in YYYY-MM-DD format. If you can't find it, return null. Do not report time here.\n"
                "4) For each receipt, detect the time in HH:MM format. If you can't find it, return null. Do not report date here.\n"
                "5) For each receipt, detect the merchant name. Do not translate it. You should report it in the origin language. If you can't find it, return null.\n"
                "6) We only accept the following currency types: " + ", ".join(accepted_currencies) + ". If you detect other currency types, ignore that receipt and do not reply anything.\n"
                "7) Do not report points, taxes, or any other information.\n"
                "8) Do not make it up.\n"
                "\n"
                "Here is the OCR result:\n"
            )

    # Step 2: Append each receipt's raw text
    for i, receipt in enumerate(ocr_results):
        normalized_text = Normalizer._normalize_text(receipt.raw_text) # Normalize text
        text += (
            f"Receipt {i + 1}:\n"
            f"{normalized_text}\n\n"
        )

    # Step 3: Prepare the final prompt
    prompt = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text":
                    text
                },
            ],
        }
    ]

    # Step 4: Invoke LLM and return result
    model = ChatOpenAI(model="gpt-5-nano", temperature=0)
    structured_llm = model.with_structured_output(ParsedOcrResult)
    result: ParsedOcrResult = structured_llm.invoke(prompt)

    # Step 5: Post-process to ensure currency is in accepted list
    cleaned_results = []
    for receipt in result.parsed_ocr_results:
        if not receipt.currency or receipt.currency in accepted_currencies:  # Only keep accepted currencies or None
            cleaned_results.append(receipt)
    result.parsed_ocr_results = cleaned_results
    return result

if __name__ == "__main__":
    test_texts = [
        "Total: ¥123.45",
        "Amount: 100元",
        "Payment: $50.00",
        "Charge: US$75.00",
        "Cost: 200円",
        "Fee: €30.00",
        "Price: 400₩",
        "Amount: 150 HK$",
        "Amount: 150 YEN",
        "No currency here",
    ]
    parser = CurrencyParser()
    for text in test_texts:
        print(f"Text: {text} -> Currency: {parser.detect_currency(text)}")