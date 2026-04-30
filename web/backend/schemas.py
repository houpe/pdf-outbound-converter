"""
WMS 转换服务数据模型
包含 Pydantic 模型定义。
"""

from pydantic import BaseModel


class SplitCodeCreate(BaseModel):
    """拆零配置创建/更新请求"""
    code: str
    split: str


class BatchItem(BaseModel):
    """批量操作项"""
    id: str
    code: str
    split: str