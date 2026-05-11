import pytest

from eval.metrics import (
    bertscore_f1,
    citation_accuracy,
    faithfulness_score,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
)


def test_retrieval_metric_stubs_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        mrr_at_k(["a", "b"], ["b"], k=5)

    with pytest.raises(NotImplementedError):
        ndcg_at_k(["a", "b"], ["b"], k=5)

    with pytest.raises(NotImplementedError):
        recall_at_k(["a", "b"], ["b"], k=10)


def test_generation_metric_stubs_return_zero() -> None:
    assert faithfulness_score("answer", []) == 0.0
    assert bertscore_f1("generated", "gold") == 0.0
    assert citation_accuracy([], []) == 0.0
