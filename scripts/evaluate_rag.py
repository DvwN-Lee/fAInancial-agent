"""RAGAS 평가 스크립트 — RAG 품질 측정.

Usage:
    python scripts/evaluate_rag.py

측정 한계: 5~10개 샘플은 방향성 확인 초기 벤치마크 목적.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai.errors import ClientError
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
import warnings

from ragas.llms import llm_factory
from ragas.run_config import RunConfig

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
    )

# scripts/ 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from rag_search_client import search_documents_local

DATA_DIR = Path(__file__).parent.parent / "data"
EVAL_DIR = DATA_DIR / "eval"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
RATE_LIMIT_DELAY = 5  # 초 — RPM 제한 대응 (요청 간 간격)
MAX_RETRIES = 3


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
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text or ""
        except ClientError as e:
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                wait = RATE_LIMIT_DELAY * (2 ** attempt)
                print(f"    Rate limit — {wait}초 대기 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise
    return ""


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
        time.sleep(RATE_LIMIT_DELAY)  # RPM 제한 대응

    evaluator_llm = llm_factory(GEMINI_MODEL, provider="google", client=client)
    run_config = RunConfig(max_workers=1, max_retries=5, max_wait=120)

    def _safe_float(val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, list):
            nums = [v for v in val if isinstance(v, (int, float)) and v == v]
            return sum(nums) / len(nums) if nums else float("nan")
        return float("nan")

    # 샘플별 개별 평가 (RPM 15 제한 대응 — RAGAS가 내부적으로 다수 LLM 호출)
    metric_configs = [
        ("faithfulness", Faithfulness(llm=evaluator_llm), "faithfulness"),
        ("context_precision", LLMContextPrecisionWithReference(llm=evaluator_llm), "llm_context_precision_with_reference"),
    ]

    metrics_dict = {}
    for mi, (name, metric, result_key) in enumerate(metric_configs):
        print(f"\n  === {name} 평가 ({mi+1}/{len(metric_configs)}) ===")
        sample_scores = []
        for si, sample in enumerate(samples):
            if si > 0:
                print("  RPM 리셋 대기 (60초)...")
                time.sleep(60)
            print(f"    [{si+1}/{len(samples)}] 평가 중...")
            single_dataset = EvaluationDataset(samples=[sample])
            try:
                result = evaluate(dataset=single_dataset, metrics=[metric], run_config=run_config)
                val = _safe_float(result[result_key])
                sample_scores.append(val)
                print(f"    점수: {val:.3f}")
            except Exception as e:
                print(f"    실패: {type(e).__name__}: {e}")
                sample_scores.append(float("nan"))
        valid = [s for s in sample_scores if s == s]  # NaN 제외
        avg = sum(valid) / len(valid) if valid else float("nan")
        metrics_dict[name] = avg
        print(f"  {name} 평균: {avg:.3f} ({len(valid)}/{len(samples)} 성공)")

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d")
    result_path = EVAL_DIR / f"results_{timestamp}.json"

    result_dict = {
        "date": timestamp,
        "sample_count": len(qa_set),
        "model": GEMINI_MODEL,
        "metrics": metrics_dict,
        "note": "방향성 확인 초기 벤치마크 (5개 샘플). ResponseRelevancy는 embedding 호환 문제로 제외.",
    }
    result_path.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2))

    print("\n=== RAGAS 평가 결과 ===")
    for metric, value in metrics_dict.items():
        print(f"  {metric}: {value:.3f}")
    print(f"\n결과 저장: {result_path}")


if __name__ == "__main__":
    main()
