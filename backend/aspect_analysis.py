from __future__ import annotations

import re


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


ASPECT_DEFINITIONS = (
    {
        "key": "delivery",
        "label": "Delivery",
        "keywords": {
            "delivery", "deliver", "delivered", "arrived", "arrival", "shipping", "shipment",
            "courier", "dispatch", "package", "packed", "packing", "order",
        },
        "positive_terms": {"fast", "quick", "prompt", "timely", "on", "smooth", "speedy"},
        "negative_terms": {"late", "delay", "delayed", "slow", "missing", "lost", "damaged", "stuck"},
        "positive_phrases": {"on time", "arrived early", "fast delivery", "quick delivery"},
        "negative_phrases": {"very late", "late delayed", "delivery late", "delivery delay", "not received"},
    },
    {
        "key": "product_quality",
        "label": "Product Quality",
        "keywords": {
            "product", "quality", "item", "material", "fabric", "size", "fit", "screen",
            "battery", "button", "packaging", "broken", "damaged", "defective", "fake", "genuine",
        },
        "positive_terms": {"good", "great", "excellent", "genuine", "durable", "perfect", "premium", "better"},
        "negative_terms": {"bad", "poor", "broken", "damaged", "defective", "fake", "scam", "worst", "useless"},
        "positive_phrases": {"very good", "good quality", "best quality", "genuine product"},
        "negative_phrases": {"very bad", "fake product", "failed broken", "not working"},
    },
    {
        "key": "pricing_value",
        "label": "Pricing & Value",
        "keywords": {
            "price", "pricing", "cost", "money", "value", "worth", "cheap", "expensive",
            "offer", "discount", "refund", "return", "payment", "charge",
        },
        "positive_terms": {"worth", "cheap", "affordable", "fair", "good", "better", "refund", "value"},
        "negative_terms": {"expensive", "overpriced", "missing", "pending", "scam", "charge", "bad"},
        "positive_phrases": {"worth money", "good value", "refund received"},
        "negative_phrases": {"refund missing", "refund not received", "extra charge"},
    },
    {
        "key": "customer_support",
        "label": "Customer Support",
        "keywords": {
            "support", "service", "customer", "seller", "response", "help", "staff", "agent", "team",
        },
        "positive_terms": {"helpful", "resolved", "quick", "prompt", "good", "fast", "support"},
        "negative_terms": {"poor", "worst", "slow", "ignored", "rude", "missing", "failed", "bad"},
        "positive_phrases": {"quick response", "helpful support", "issue resolved"},
        "negative_phrases": {"no support", "support failed", "no response", "response failed"},
    },
    {
        "key": "app_experience",
        "label": "App Experience",
        "keywords": {
            "app", "website", "ui", "interface", "login", "checkout", "search", "payment",
            "bug", "crash", "screen", "button", "platform",
        },
        "positive_terms": {"smooth", "easy", "fast", "good", "promising", "safe", "secure"},
        "negative_terms": {"crash", "bug", "slow", "failed", "broken", "issue", "error", "bad"},
        "positive_phrases": {"easy to use", "works well", "safe secure"},
        "negative_phrases": {"not working", "does not work", "did not work"},
    },
)

NEUTRAL_TERMS = {"okay", "average", "fine", "decent"}


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(str(text or "").lower())


def _window_scores(tokens: list[str], index: int, aspect: dict) -> tuple[int, set[str], bool]:
    start = max(0, index - 4)
    stop = min(len(tokens), index + 5)
    window = tokens[start:stop]
    evidence: set[str] = set()
    score = 0
    neutral_hit = False

    for token in window:
        if token in aspect["positive_terms"]:
            score += 1
            evidence.add(token)
        if token in aspect["negative_terms"]:
            score -= 1
            evidence.add(token)
        if token in NEUTRAL_TERMS:
            neutral_hit = True
            evidence.add(token)

    return score, evidence, neutral_hit


def _phrase_scores(text: str, aspect: dict) -> tuple[int, set[str], bool]:
    score = 0
    evidence: set[str] = set()
    neutral_hit = False

    for phrase in aspect["positive_phrases"]:
        if phrase in text:
            score += 2
            evidence.add(phrase)
    for phrase in aspect["negative_phrases"]:
        if phrase in text:
            score -= 2
            evidence.add(phrase)
    if "okay" in text:
        neutral_hit = True
        evidence.add("okay")

    return score, evidence, neutral_hit


def analyze_review_aspects(
    review_text: str,
    predicted_sentiment: str,
    normalized_review: str | None = None,
) -> dict:
    source_text = str(normalized_review or review_text or "").strip().lower()
    tokens = _tokenize(source_text)
    if not tokens:
        return {
            "aspect_sentiments": [],
            "aspect_summary": "",
            "primary_aspect": None,
            "primary_aspect_sentiment": None,
        }

    aspect_rows = []
    for aspect in ASPECT_DEFINITIONS:
        indices = [index for index, token in enumerate(tokens) if token in aspect["keywords"]]
        phrase_score, phrase_evidence, phrase_neutral = _phrase_scores(source_text, aspect)
        if not indices and not phrase_evidence:
            continue

        mention_terms = {tokens[index] for index in indices}
        score = phrase_score
        evidence = set(phrase_evidence)
        neutral_hit = phrase_neutral

        for index in indices:
            window_score, window_evidence, window_neutral = _window_scores(tokens, index, aspect)
            score += window_score
            evidence.update(window_evidence)
            neutral_hit = neutral_hit or window_neutral

        if score > 0:
            sentiment = "Positive"
        elif score < 0:
            sentiment = "Negative"
        elif neutral_hit:
            sentiment = "Neutral"
        elif indices:
            sentiment = str(predicted_sentiment or "Neutral")
        else:
            sentiment = "Neutral"

        aspect_rows.append(
            {
                "aspect": aspect["label"],
                "sentiment": sentiment,
                "score": int(score),
                "mentions": len(indices) + len(phrase_evidence),
                "evidence": sorted({*mention_terms, *evidence})[:8],
            }
        )

    aspect_rows.sort(
        key=lambda item: (
            abs(int(item["score"])),
            int(item["mentions"]),
            1 if item["sentiment"] == "Negative" else 0,
        ),
        reverse=True,
    )

    primary = aspect_rows[0] if aspect_rows else None
    return {
        "aspect_sentiments": aspect_rows,
        "aspect_summary": "; ".join(f'{row["aspect"]}: {row["sentiment"]}' for row in aspect_rows),
        "primary_aspect": primary["aspect"] if primary else None,
        "primary_aspect_sentiment": primary["sentiment"] if primary else None,
    }


def summarize_batch_aspects(results: list[dict]) -> list[dict]:
    summary: dict[str, dict] = {}
    for row in results:
        for item in row.get("aspect_sentiments", []) or []:
            key = str(item.get("aspect", "")).strip()
            if not key:
                continue
            bucket = summary.setdefault(
                key,
                {"aspect": key, "mentions": 0, "Positive": 0, "Neutral": 0, "Negative": 0},
            )
            sentiment = str(item.get("sentiment", "Neutral"))
            if sentiment not in {"Positive", "Neutral", "Negative"}:
                sentiment = "Neutral"
            bucket["mentions"] += 1
            bucket[sentiment] += 1

    rows = []
    for item in summary.values():
        dominant = max(("Negative", "Neutral", "Positive"), key=lambda name: (item[name], item["mentions"]))
        rows.append(
            {
                "aspect": item["aspect"],
                "mentions": item["mentions"],
                "positive": item["Positive"],
                "neutral": item["Neutral"],
                "negative": item["Negative"],
                "dominant_sentiment": dominant,
            }
        )

    rows.sort(key=lambda item: (item["negative"], item["mentions"], item["positive"]), reverse=True)
    return rows
