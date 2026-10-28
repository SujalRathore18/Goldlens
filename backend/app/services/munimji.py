import os
from typing import Any


def _default_context_summary(context: dict[str, Any]) -> str:
    route = context.get("route") or "desk"
    page = context.get("page") or "Desk"
    dataset = context.get("dataset_name") or "sample dataset"
    pair = context.get("pair") or "selected pair"
    verdict = context.get("verdict") or "pending"
    reason = context.get("reason_code") or "no reason yet"
    return (
        f"Current page: {page}. Route: {route}. "
        f"Dataset: {dataset}. Pair: {pair}. Verdict: {verdict}. "
        f"Reason: {reason}."
    )


def render_munimji_reply(question: str, language: str = "en", context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    summary = _default_context_summary(context)
    question_lower = question.lower()
    if language == "hi":
        if "basis" in question_lower:
            reply = (
                "बेसिस वह अंतर है जो दो कॉन्ट्रैक्ट्स के बीच मूल्य अंतर को बताता है। "
                f"{summary} इस उदाहरण में, Goldlens केवल सत्यापित डेटा, लागत और जीवन-चक्र बाधाओं के आधार पर निर्णय देता है।"
            )
        elif "cost" in question_lower or "लागत" in question_lower:
            reply = (
                "लागत के हिसाब में ब्रोकरेज, एक्सचेंज शुल्क, स्लिपेज, और राउंड-ट्रिप कॉस्ट शामिल होती है। "
                f"{summary} अगर लागत आधार से अधिक है, तो परिणाम 'Gap eaten by costs' के रूप में दर्शाया जाता है।"
            )
        elif "why" in question_lower or "क्यों" in question_lower:
            reply = (
                "Goldlens सत्यापित डेटा, पर्याप्त सबूत, और जीवन-चक्र बाधाओं के आधार पर केवल तभी निष्कर्ष देता है जब सभी आवश्यक गेट्स पास हों। "
                f"{summary} अगर डेटा कम है या पैयर असंगत है, तो परिणाम 'Cannot establish a comparison' दिया जाता है।"
            )
        else:
            reply = (
                "मैं Goldlens का डिटerminिस्टिक सहायक हूँ। मैं वास्तविक गणना को दोहराता हूँ, आँकड़ों को कल्पना नहीं करता, और केवल डेटा-आधारित व्याख्या देता हूँ। "
                f"{summary} कृपया अपने प्रश्न को सरल रूप में पूछें जैसे: 'इस परिणाम को समझाइए' या 'लागत कैसे गणना हुई?'"
            )
        provider = "deterministic" if not os.getenv("GEMINI_API_KEY") else "gemini"
        return {"reply": reply, "language": "hi", "provider": provider, "source": "deterministic" if provider == "deterministic" else "server-side"}

    if "basis" in question_lower:
        reply = (
            "Basis is the gap between the two contracts. "
            f"{summary} In Goldlens, the engine only uses validated observations, cost gates, and lifecycle constraints before it creates a verdict."
        )
    elif "cost" in question_lower:
        reply = (
            "Costs include brokerage, exchange charges, slippage and the round-trip estimate. "
            f"{summary} If the gap is smaller than the cost floor, the engine reports the opportunity as gap eaten by costs."
        )
    elif "why" in question_lower:
        reply = (
            "The verdict is based on whether the data is sufficient, the date is valid, the pair is compatible, and the cost gate clears. "
            f"{summary} When evidence is weak or the pair is misaligned, Goldlens reports that the comparison cannot be established."
        )
    else:
        reply = (
            "I am the deterministic Munimji guide for Goldlens. I explain the actual engine output and do not invent new market data. "
            f"{summary} Ask for a simple explanation, cost logic, basis, expiry meaning, or why a result is inconclusive."
        )
    provider = "deterministic" if not os.getenv("GEMINI_API_KEY") else "gemini"
    return {"reply": reply, "language": "en", "provider": provider, "source": "deterministic" if provider == "deterministic" else "server-side"}
