import dataclasses
import re, unicodedata

from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from backend.tools import load_config
from backend.tools.ocr_result_parser import ParsedReceipt, ParsedOcrResult


# -------------------- Pydantic Models --------------------  #
class ReceiptCategory(BaseModel):
    idx: int = Field(..., description="Pre-set idx of the receipt.")
    category: str = Field(..., description="Main category of the receipt.")
    sub_category: Optional[str] = Field(None, description="Sub-category of the receipt. This should be None if there is no sub-category matched.")
    matched: bool = Field(..., description="Whether this receipt is matched. If both category and sub_category are not matched, set this to False.")
    keyword: Optional[str] = Field(None, description="Keyword that matched the category or sub_category.")

class ClassificationResult(BaseModel):
    classification_results: List[ReceiptCategory] = Field(..., description="Classification results for all receipts")

class subCategory(BaseModel):
    name: str
    parent_name: str
    keywords: List[str]
    regex: Optional[re.Pattern] = None

class Category(BaseModel):
    name: str
    keywords: List[str]
    sub_categories: Optional[List[subCategory]] = None
    regex: Optional[re.Pattern] = None


# -------------------- Load Configs --------------------  #
def _compile_regex_pattern(keywords: List[str]) -> Optional[re.Pattern]:
    """
    Compile regex patterns based on keywords list.
    :param categories: list of keywords
    :return: conpliled regex pattern or None (when no keywords set)
    """
    if keywords:
        parts = []
        for kw in keywords:
            # 1) Normalizaiton
            kw = unicodedata.normalize("NFKC", kw)
            kw = re.escape(kw)
            kw = kw.replace(r"\ ", r"\s+")
            # 2) Add word boundary (Add to English only. Chinese and Japanese characters do not need word boundary)
            if re.fullmatch(r"[A-Za-z\s\+\'\-]+", kw):
                parts.append(rf"\b{kw}\b")
            else:
                parts.append(kw)
            # 3) Combine parts
        pattern_str = "|".join(parts)
        return re.compile(pattern_str, re.IGNORECASE)
    else:
        return None

def _load_categories() -> list[Category]:
    """
    Load categories config file and return a dictionary of categories and their keywords.
    :return: dict, {main_category: [keywords], ...}
    """
    categories = []
    cfg = load_config('CategoryConfigs.yaml')
    for cat in cfg['categories']:
        if cat['subCategories']:
            subCategories = []
            for subcat in cat['subCategories']:
                subCategories.append(subCategory(name=subcat['name'], parent_name=cat['name'], keywords=subcat['keywords'], regex=_compile_regex_pattern(subcat['keywords'])))
            categories.append(Category(name=cat['name'], keywords=cat['keywords'], subCategories=subCategories, regex=_compile_regex_pattern(cat['keywords'])))
        else:
            categories.append(Category(name=cat['name'], keywords=cat['keywords'], subCategories=None))
    return categories


# -------------------- Tool Functions --------------------  #
def regex(text: str, regex: re.Pattern) -> (bool, Optional[str]):
    """
    Using Regex match for briefly classification
    :param Keywords: a list of predefined keywords list (e.g. ['seven eleven', 'lawson', 'FamilyMart'] -> Convenience Store)
    :param text: text to be matched
    :return matched: bool, keyword: str | None
    1. If matched, return True and the matched keyword
    2. If not matched, return False and None
    """
    if regex.search(text):
        m = regex.search(text)
        return True, m.group(0)
    else:
        return False, None

def sort(results: List[ReceiptCategory]) -> ClassificationResult:
    pass    # TODO

# -------------------- Main class --------------------  #



class Classifier:
    def __init__(self):
        self.categories = _load_categories()

    def regex_search_one(self, merchant: str, categories: List[Optional[Category, subCategory]]) -> Tuple[bool, Optional[str], Optional[Category, subCategory]]:
        """
        Using Regex match for briefly classification for single merchant name
        :param merchant: merchant name
        :return: A tuple of matched results
        """
        for cat in categories:
            matched, keyword = regex(merchant, cat.regex)
            if matched:
                return matched, keyword, cat
        return False, None, None

    def regex_search(self, idx_merchants: List[Tuple[int, str]]) -> Tuple[List, List, List]:
        """
        Using Regex match for briefly classification
        :param idx_merchants: A list of tuples (idx, merchant_name)
        :return: classified: classified items
                 pending: items that are not yet classified
        """
        classified = []
        sub_cat_pending = []
        pending = []

        for idx, merchant in idx_merchants:
            matched, keyword, cat = self.regex_search_one(merchant, self.categories)
            if matched:
                if cat.sub_categories: # TODO: consider how to process cat with sub_cat, especially when cat matched and sub_cat not matched
                    sub_matched, sub_keyword, sub_cat = self.regex_search_one(merchant, cat.sub_categories)
                    if sub_matched:
                        classified.append(ReceiptCategory(idx=idx, category=cat.name, sub_category=sub_cat.name, matched=True, keyword=sub_keyword))
                    else:
                        sub_cat_pending.append((idx, None, cat))
                else:
                    classified.append((idx, keyword, cat))
            else:
                pending.append(ReceiptCategory(idx=idx, category=merchant, sub_category=None, matched=True, keyword=keyword))

        return classified, sub_cat_pending, pending

    def model_search_cat(self, pending: List[Tuple]) -> ClassificationResult:
        """
        Use model to search for category
        :param pending:
        :return:
        """
        # 1) Prepare category texts
        cat_texts = ""
        for cat in self.categories:
            cat_text = f"{cat.name}: "
            if cat.sub_categories:
                for sub_cat in cat.sub_categories:
                    cat_text += f"{sub_cat.name}, "
            else:
                cat_text += "No sub_category"
            cat_text.strip(", ")
            cat_texts += cat_text + "\n"
        cat_texts.strip()

        # 2) Prepare pending text
        pending_texts = ""
        for pend in pending:
            pending_texts += f"Receipt {pend[0]}: {pend[1]}\n"
        pending_texts.strip()

        # 3) Prepare prompt
        text = ("Classify the receipts into pre-defined category. The rules are provided as below:\n"
                "1. The categories are defined in format <category>: <sub_category_1>, ..., <sub_category_n>. Categories with no sub-categories are defined as <category>: No sub_category.\n"
                "2. The receipts are defined in format Receipt <idx>: <merchant_name>. You should classify them based on the merchant_name and also return the idx. Be aware that the idx of the receipt may not be continues or in ascending order.\n"
                "3. You should process each receipt separately and return the result one by one.\n"
                "4. You should return idx, category, sub_category, matched and keyword for each receipt. The idx here is the pre-set idx, not the order of receipts in the list.\n"
                "5. If a receipt only matched the category and didn't matched any sub_category, return the matched category and keep sub_category as None.\n"
                "6. If a receipt didn't matched any category, return the category as others and keep sub_category as None.\n"
                "7. If a receipt matched a category or sub_category, set matched to True. Otherwise, it should be False.\n"
                "8. If a receipt matched a category or sub_category, return the keyword string that can be the evidence for classification.\n"
                "\n"
                "The pre-defined categories are provided as below:"
                f"{cat_texts}\n"
                "\n"
                "Here are the receipts:\n"
                f"{pending_texts}")
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

        # 4) Step 4: Invoke LLM and return result
        model = ChatOpenAI(model="gpt-5-nano", temperature=0)
        structured_llm = model.with_structured_output(ClassificationResult)
        result: ClassificationResult = structured_llm.invoke(prompt)
        return result

    def model_search_sub_cat(self, sub_cat_pending: List[Tuple]) -> ClassificationResult:
        """
        Use model to search sub category
        :param sub_cat_pending:
        :return:
        """
        pass

    def classify(self, parsed_ocr_results: List[ParsedReceipt]) -> ClassificationResult:
        """
        Classify receipts based on merchant names using regex and LLM (if needed)
        :param parsed_ocr_results: ParsedOcrResult object containing the parsed OCR results
        :return: ClassificationResult object containing the classification results
        """
        # 1) Bind idx to ensure order
        idx_merchants = [(idx, parsed_receipt.merchant) for idx, parsed_receipt in enumerate(parsed_ocr_results)]

        # 2) Brief classification using regex
        classified, sub_cat_pending, pending = self.regex_search(idx_merchants)

        # 3) Use LLM to process pending results
        if sub_cat_pending:
            sub_cat_results: List[ReceiptCategory] = self.model_search_sub_cat(sub_cat_pending).classification_results
            classified += sub_cat_results
        if pending:
            pending_results: List[ReceiptCategory] = self.model_search_cat(pending).classification_results
            classified += pending_results

        # 4) Sort concatenated results in ascending order and return it
        return sort(classified)


# Warp up to LangChain tools
@ tool('classification_tool', args_schema=ParsedOcrResult, return_direct=False)
def classification_tool(parsed_ocr_results) -> ClassificationResult:
    """
    Classify the structured ocr results based on pre-defined categories and sub_categories
    :param parsed_ocr_results:
    :return:
    """
    return Classifier().classify(parsed_ocr_results)

""" 
匹配流程: 
1. 绑定idx，保证不乱序
1.5 正则化字符串 -> 全小写 半角
2. 正则匹配，获得classified和pending两类
3. 对pending去重，得到待分类的列表unclassified （因为有些商户名会重复出现，如 2个Steam 在我的test例子里）
4. 对unclassified进行LLM分类
5. 根据unclassified分类结果，修改pending
6. 保持idx顺序，合并classified和pending，返回最终结果

TODO:
以上全部没做
正准备先做正则匹配
_load_keywords() -> _compile_regex_patterns() -> regex()

"""
# REGEX patterns for category matching

if __name__ == "__main__":
    text = [
        'Steam 2,800円\n2025年10月6日 23時53分\nポイント 残高\n支払い完了',
        'ローソン\n410円\n中原木月四丁目\n2025年10月4日 13時25分'
    ]
    keywords = ['steam', 'lawson']
    # keywords = []
    pat = _compile_regex_pattern(keywords)
    for t in text:
        matched, kw = regex(t, pat)
        print(matched, kw)
