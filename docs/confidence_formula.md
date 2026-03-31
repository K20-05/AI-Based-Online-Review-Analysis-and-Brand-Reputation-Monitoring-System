# Confidence Formula

This file explains how confidence is calculated in the project.

Primary implementation:
- [backend/predict.py](c:/Users/ADMIN/OneDrive/AI_BrandReview_Analysis/backend/predict.py#L23)
- [backend/predict.py](c:/Users/ADMIN/OneDrive/AI_BrandReview_Analysis/backend/predict.py#L84)

## 1. Raw Model Confidence

The model predicts probabilities for each class:

- `P(Positive)`
- `P(Negative)`
- `P(Neutral)`

The initial raw confidence is:

```text
raw_model_confidence = max(P(Positive), P(Negative), P(Neutral))
```

## 2. Decision Confidence

By default:

```text
decision_confidence = raw_model_confidence
```

But the value changes in these cases.

### Case A: Low confidence

Condition:

```text
best_prob < 0.55
```

Formula:

```text
severity = (0.55 - best_prob) / 0.55
decision_confidence = 0.52 + (0.16 * severity)
```

### Case B: Positive and Negative are too close

Condition:

```text
abs(P(Positive) - P(Negative)) < 0.15
```

Formula:

```text
closeness = 1 - (abs(P(Positive) - P(Negative)) / 0.15)
decision_confidence = max(P(Neutral), 0.56 + (0.18 * closeness))
```

### Case C: Neutral probability guard

Condition:

```text
P(Neutral) >= 0.35 and best_prob < 0.65
```

Formula:

```text
strength = (P(Neutral) - 0.35) / 0.30
decision_confidence = max(P(Neutral), 0.58 + (0.18 * strength))
```

After this, the value is clamped:

```text
decision_confidence = clamp(decision_confidence, 0.0, 0.995)
```

## 3. Final Confidence

This happens inside `calibrate_prediction_confidence()`.

Start with:

```text
confidence = decision_confidence
```

Token count:

```text
cleaned_token_count = len(cleaned_review.split())
normalized_token_count = len(normalized_review.split())
token_count = max(cleaned_token_count, normalized_token_count)
```

### Translation adjustment

If translation was applied and `language_confidence` exists:

```text
model_weight = 0.78 if token_count >= 2 else 0.72
confidence = (confidence * model_weight) + (language_confidence * (1 - model_weight))
```

### Short text penalty

If:

```text
token_count <= 1
```

Then:

```text
confidence -= 0.12   if translation_applied
confidence -= 0.08   otherwise
```

If:

```text
token_count == 2
```

Then:

```text
confidence -= 0.06   if translation_applied
confidence -= 0.03   otherwise
```

### Sentiment-adjustment cap

If a multilingual sentiment guard changed the sentiment:

```text
confidence = max(confidence, 0.60)
confidence = min(confidence, 0.78 if translation_applied else 0.82)
```

### Final returned value

```text
final_confidence = round(clamp(confidence, 0.0, 0.995), 4)
```

## 4. Displayed Percentage

Frontend display converts the decimal value into percent:

```text
shown_confidence = final_confidence * 100
```

So:

```text
0.8234 -> 82.34%
```

## 5. Average Confidence in Batch View

The batch dashboard card averages all `prediction_confidence` values from the batch response.

Source:
- [frontend/app.js](c:/Users/ADMIN/OneDrive/AI_BrandReview_Analysis/frontend/app.js#L3615)

Formula:

```text
average_confidence = sum(prediction_confidence values) / number_of_valid_rows
displayed_average = average_confidence * 100
```

## 6. Short Viva Answer

```text
Confidence starts from the model probability, then it is adjusted using neutral-guard rules,
multilingual translation confidence, short-text penalties, and sentiment-guard caps.
The final value is clamped to 0.0-0.995 and shown as a percentage in the UI.
```
