import unittest

from backend.multilingual import (
    apply_multilingual_sentiment_guard,
    detect_language,
    normalize_multilingual_text,
)


class MultilingualTests(unittest.TestCase):
    def test_detect_language_marks_plain_english_reviews_as_english(self):
        language, confidence = detect_language(
            "Worst delivery and customer care. The app is slow and support is poor."
        )

        self.assertEqual(language, "en")
        self.assertGreater(confidence, 0.5)

    def test_detect_language_keeps_romanized_hindi_when_distinct_hints_exist(self):
        language, confidence = detect_language("bahut accha refund nahi mila")

        self.assertEqual(language, "hi")
        self.assertGreater(confidence, 0.5)

    def test_detect_language_marks_romanized_telugu_negative_word_as_telugu(self):
        language, confidence = detect_language("baledhu")

        self.assertEqual(language, "te")
        self.assertGreater(confidence, 0.5)

    def test_detect_language_marks_romanized_telugu_neutral_word_as_telugu(self):
        language, confidence = detect_language("parledhu")

        self.assertEqual(language, "te")
        self.assertGreater(confidence, 0.5)

    def test_normalize_multilingual_text_returns_english_label_for_english_text(self):
        payload = normalize_multilingual_text("Good quality and speed service")

        self.assertEqual(payload["detected_language"], "en")
        self.assertEqual(payload["detected_language_label"], "English")

    def test_normalize_multilingual_text_canonicalizes_negated_english_sentiment(self):
        payload = normalize_multilingual_text("Product is not good and support was not working")

        self.assertEqual(payload["normalized_text"], "product is very bad and support was failed broken")

    def test_normalize_multilingual_text_strengthens_translated_negative_phrases(self):
        payload = normalize_multilingual_text("refund nahi mila aur jawab nahi diya")

        self.assertEqual(payload["normalized_text"], "refund missing and response failed")

    def test_normalize_multilingual_text_maps_hindi_negated_good_phrase_to_negative(self):
        payload = normalize_multilingual_text("acha nahi")

        self.assertEqual(payload["detected_language"], "hi")
        self.assertEqual(payload["normalized_text"], "very bad")

    def test_normalize_multilingual_text_maps_hindi_strong_negated_good_phrase_to_negative(self):
        payload = normalize_multilingual_text("bahut acha nahi")

        self.assertEqual(payload["detected_language"], "hi")
        self.assertEqual(payload["normalized_text"], "very bad")

    def test_normalize_multilingual_text_maps_romanized_telugu_negative_word(self):
        payload = normalize_multilingual_text("baledhu")

        self.assertEqual(payload["detected_language"], "te")
        self.assertEqual(payload["normalized_text"], "bad")

    def test_normalize_multilingual_text_maps_romanized_telugu_neutral_word(self):
        payload = normalize_multilingual_text("parledhu")

        self.assertEqual(payload["detected_language"], "te")
        self.assertEqual(payload["normalized_text"], "okay")

    def test_normalize_multilingual_text_maps_okish_to_okay(self):
        payload = normalize_multilingual_text("okish")

        self.assertEqual(payload["detected_language"], "en")
        self.assertEqual(payload["normalized_text"], "okay")

    def test_normalize_multilingual_text_maps_not_okish_to_negative(self):
        payload = normalize_multilingual_text("not okish")

        self.assertEqual(payload["detected_language"], "en")
        self.assertEqual(payload["normalized_text"], "very bad")

    def test_apply_multilingual_sentiment_guard_marks_okay_as_neutral(self):
        sentiment, reason = apply_multilingual_sentiment_guard(
            "okay",
            "Positive",
            {"Negative": 0.12, "Neutral": 0.18, "Positive": 0.70},
        )

        self.assertEqual(sentiment, "Neutral")
        self.assertEqual(reason, "multilingual_neutral_guard")

    def test_normalize_multilingual_text_maps_tamil_negated_good_phrase_to_negative(self):
        payload = normalize_multilingual_text("nalla ille")

        self.assertEqual(payload["detected_language"], "ta")
        self.assertEqual(payload["normalized_text"], "very bad")


if __name__ == "__main__":
    unittest.main()
