"""RAGAS 평가 스크립트 — RAG 품질 측정.

Usage:
    python scripts/evaluate_rag.py

측정 한계: 5~10개 샘플은 방향성 확인 초기 벤치마크 목적.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from google import genai
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.llms import llm_factory
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    ResponseRelevancy,
)

# scripts/ 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from rag_search_client import search_documents_local

DATA_DIR = Path(__file__).parent.parent / "data"
EVAL_DIR = DATA_DIR / "eval"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.Client(api_key=api_key)


def _generate_answer(client: genai.Client, question: str, contexts: list[str]) -> str:
    """질문 + 검색된 컨텍스트로 답변을 생성한다."""
    context_text = "\n\n---\n\n".join(contexts)
    prompt = (
        f"다음 공시 문서 내용을 바탕으로 질문에 답변하세요.\n\n"
        f"[공시 내용]\n{context_text}\n\n"
        f"[질문]\n{question}"
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text or ""


def main():
    qa_path = EVAL_DIR / "qa_set.json"
    if not qa_path.exists():
        print(f"평가 데이터셋 없음: {qa_path}")
        return

    qa_set = json.loads(qa_path.read_text())
    client = _get_genai_client()

    samples = []
    for qa in qa_set:
        question = qa["question"]
        ground_truth = qa["ground_truth"]
        corp_name = qa.get("corp_name")
        year = qa.get("year")

        # RAG 검색
        contexts = search_documents_local(question, corp_name, year)

        # 답변 생성
        answer = _generate_answer(client, question, contexts)

        samples.append(
            SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=contexts,
                reference=ground_truth,
            )
        )
        print(f"  처리: {question[:30]}...")

    dataset = EvaluationDataset(samples=samples)

    # RAGAS 평가 (Gemini LLM 사용)
    evaluator_llm = llm_factory("gemini-2.0-flash", provider="google")

    metrics = [
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm),
        LLMContextPrecisionWithReference(llm=evaluator_llm),
    ]

    result = evaluate(dataset=dataset, metrics=metrics)

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d")
    result_path = EVAL_DIR / f"results_{timestamp}.json"
    result_dict = {
        "date": timestamp,
        "sample_count": len(qa_set),
        "metrics": {
            "faithfulness": result["faithfulness"],
            "answer_relevancy": result["answer_relevancy"],
            "context_precision": result["llm_context_precision_with_reference"],
        },
        "note": "방향성 확인 초기 벤치마크 (5~10개 샘플)",
    }
    result_path.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2))

    print(f"\n=== RAGAS 평가 결과 ===")
    for metric, value in result_dict["metrics"].items():
        print(f"  {metric}: {value:.3f}")
    print(f"\n결과 저장: {result_path}")


if __name__ == "__main__":
    main()
