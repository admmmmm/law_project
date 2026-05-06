# [2026-05-05 15:03] mimo模型编辑
# 用户输入：错误信息 "No module named 'hipporag.evaluation'"
# 修改内容：创建evaluation模块的stub实现

"""Stub implementation for retrieval evaluation metrics."""


class RetrievalRecall:
    """Stub for retrieval recall evaluation."""

    def __init__(self, global_config=None):
        self.global_config = global_config

    def calculate_metric_scores(self, gold_docs=None, retrieved_docs=None, k_list=None):
        """Return empty evaluation results."""
        return {}, []
