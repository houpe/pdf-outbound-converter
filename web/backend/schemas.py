"""
WMS 转换服务数据模型
包含 Pydantic 模型定义。
"""

from pydantic import BaseModel


class SplitCodeCreate(BaseModel):
    """拆零配置创建/更新请求"""
    code: str
    split: str
    warehouse_code: str = "ZTOWHHY001"


class BatchItem(BaseModel):
    """批量操作项"""
    id: str
    code: str
    split: str
    warehouse_code: str = "ZTOWHHY001"


class CustomerPhoneBatchItem(BaseModel):
    """门店电话批量操作项"""
    id: str
    customer_code: str
    phone: str
    template_key: str = "pl"
