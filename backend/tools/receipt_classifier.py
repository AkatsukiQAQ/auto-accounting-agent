import re

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.tools import load_config
from backend.tools.ocr_result_parser import ParsedOcrResult


categories = load_config('ReceiptCategories.yaml')['categories']

# -------------------- Pydantic Models --------------------  #
class ReceiptCategory(BaseModel):
    main_category: str = Field(..., description="Main category of the receipt. Saved in categories list.")
    sub_category: Optional[str] = Field(None, description="Sub category of the receipt. Saved in categories list. Can be found in subCatogories of main category.")

class ClassificationResult(BaseModel):
    classification_results: List[ReceiptCategory] = Field(..., description="Classification results for all receipts")

# -------------------- Tool Functions --------------------  #
def regex_match_category():
    pass

""" 
匹配流程: 
1. 绑定idx，不保证不乱序
2. 正则匹配，获得classified和pending两类
3. 对pending去重，得到待分类的列表unclassified （因为有些商户名会重复出现，如 2个Steam 在我的test例子里）
4. 对unclassified进行LLM分类
5. 根据unclassified分类结果，修改pending
6. 保持idx顺序，合并classified和pending，返回最终结果

TODO:
以上全部没做
正准备先做正则匹配

"""
# REGEX patterns for category matching