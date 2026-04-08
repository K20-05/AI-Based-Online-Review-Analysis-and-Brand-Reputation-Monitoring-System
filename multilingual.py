from __future__ import annotations

import re
import unicodedata


LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "unknown": "Unknown",
}

SCRIPT_RANGES = {
    "hi": [(0x0900, 0x097F)],
    "ta": [(0x0B80, 0x0BFF)],
    "te": [(0x0C00, 0x0C7F)],
    "kn": [(0x0C80, 0x0CFF)],
    "ml": [(0x0D00, 0x0D7F)],
}

LANGUAGE_HINTS = {
    "hi": {
        "bahut", "accha", "acha", "achha", "sahi", "kharab", "bekar", "dhokha", "nakli",
        "wapas", "paise", "dhima", "tez", "nahi", "mila", "jawab",
    },
    "ta": {
        "romba", "migavum", "nalla", "nallathu", "mosam", "poli", "thaamatham", "thaamasa", "methuva",
        "aadharavu", "rathu", "sariseiyavillai", "velai", "kidaikkavillai", "illa", "ille", "illai", "alla",
    },
    "te": {
        "chala", "bagundi", "manchidi", "chedu", "nakili", "alasyam", "maddatu", "raddu",
        "pani", "cheyadu", "raledu", "baledu", "baaledu", "baledhu", "baaledhu", "bale", "asalu",
        "parledu", "parledhu", "parvaledu", "parvaledhu", "paravaaledu", "paravaaledhu",
    },
    "ml": {
        "valare", "nalla", "nallathu", "mosham", "vyaja", "vaiki", "sahayam", "raddakki",
        "pravarthikkunnilla", "kittiyilla", "illa", "ille",
    },
    "kn": {
        "tumba", "chennagide", "olledu", "ketta", "nakali", "tada", "bembala", "raddu",
        "kelasa", "madalla", "sigalilla",
    },
}

ENGLISH_HINTS = {
    "the", "and", "is", "was", "are", "very", "good", "great", "bad", "worst", "poor",
    "service", "customer", "delivery", "product", "screen", "button", "app", "quality",
    "shopping", "safe", "secure", "support", "platform", "slow", "fast", "late", "click",
    "package", "seller", "resolved", "guidance", "review", "reviews",
}

SENTIMENT_CANONICAL_RULES = (
    (re.compile(r"\brefund\s+not\s+received\b"), "refund missing"),
    (re.compile(r"\bnot\s+received\b"), "missing"),
    (re.compile(r"\bno\s+support\b"), "support failed"),
    (re.compile(r"\bno\s+response\b"), "response failed"),
    (re.compile(r"\bnot\s+ok(?:ay)?(?:[\s-]*ish)?\b"), "very bad"),
    (re.compile(r"\bvery\s+good\s+(?:not|nahi)\b"), "very bad"),
    (re.compile(r"\bgood\s+(?:not|nahi)\b"), "very bad"),
    (re.compile(r"\bdoes\s+not\s+work\b"), "failed broken"),
    (re.compile(r"\bdid\s+not\s+work\b"), "failed broken"),
    (re.compile(r"\bnot\s+working\b"), "failed broken"),
    (re.compile(r"\bnot\s+good\b"), "very bad"),
    (re.compile(r"\bnot\s+great\b"), "very bad"),
    (re.compile(r"\bok(?:ay)?[\s-]*ish\b"), "okay"),
    (re.compile(r"\bok\b"), "okay"),
    (re.compile(r"\bso[\s-]+so\b"), "okay"),
    (re.compile(r"\bvery\s+late\b"), "late delayed"),
    (re.compile(r"\bfake\s+product\b"), "fake scam"),
)

PHRASE_MAP = {
    "bahut accha": "very good",
    "bahut acha": "very good",
    "bahut kharab": "very bad",
    "bahut late": "very late",
    "refund nahi mila": "refund not received",
    "jawab nahi diya": "no response",
    "support nahi mila": "no support",
    "nakli product": "fake product",
    "\u092c\u0939\u0941\u0924 \u0905\u091a\u094d\u091b\u093e": "very good",
    "\u092c\u0939\u0941\u0924 \u0916\u0930\u093e\u092c": "very bad",
    "\u092c\u0939\u0941\u0924 \u0932\u0947\u091f": "very late",
    "\u0930\u093f\u092b\u0902\u0921 \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u093e": "refund not received",
    "\u091c\u0935\u093e\u092c \u0928\u0939\u0940\u0902 \u0926\u093f\u092f\u093e": "no response",
    "\u0938\u092a\u094b\u0930\u094d\u091f \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u093e": "no support",
    "\u0928\u0915\u0932\u0940 \u092a\u094d\u0930\u0949\u0921\u0915\u094d\u091f": "fake product",
    "migavum nallathu": "very good",
    "migavum mosam": "very bad",
    "nalla ille": "very bad",
    "nalla illa": "very bad",
    "nalla illai": "very bad",
    "nallathu ille": "very bad",
    "nallathu illa": "very bad",
    "nallathu illai": "very bad",
    "nalla alla": "very bad",
    "velai seyyavillai": "not working",
    "refund kidaikkavillai": "refund not received",
    "migavum thaamatham": "very late",
    "\u0bae\u0bbf\u0b95\u0bb5\u0bc1\u0bae\u0bcd \u0ba8\u0bb2\u0bcd\u0bb2\u0ba4\u0bc1": "very good",
    "\u0bae\u0bbf\u0b95\u0bb5\u0bc1\u0bae\u0bcd \u0bae\u0bcb\u0b9a\u0bae\u0bcd": "very bad",
    "\u0bb5\u0bc7\u0bb2\u0bc8 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8": "not working",
    "\u0bb0\u0bbf\u0b83\u0baa\u0ba3\u0bcd\u0b9f\u0bcd \u0b95\u0bbf\u0b9f\u0bc8\u0b95\u0bcd\u0b95\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8": "refund not received",
    "\u0bae\u0bbf\u0b95\u0bb5\u0bc1\u0bae\u0bcd \u0ba4\u0bbe\u0bae\u0ba4\u0bae\u0bcd": "very late",
    "\u0baa\u0bcb\u0bb2\u0bbf \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bcd": "fake product",
    "chala bagundi": "very good",
    "chala chedu": "very bad",
    "pani cheyadu": "not working",
    "refund raledu": "refund not received",
    "chala alasya": "very late",
    "parledu": "okay",
    "parledhu": "okay",
    "parvaledu": "okay",
    "parvaledhu": "okay",
    "paravaaledu": "okay",
    "paravaaledhu": "okay",
    "\u0c1a\u0c3e\u0c32\u0c3e \u0c2c\u0c3e\u0c17\u0c41\u0c02\u0c26\u0c3f": "very good",
    "\u0c1a\u0c3e\u0c32\u0c3e \u0c1a\u0c46\u0c21\u0c41": "very bad",
    "\u0c2a\u0c28\u0c3f \u0c1a\u0c47\u0c2f\u0c26\u0c41": "not working",
    "\u0c30\u0c3f\u0c2b\u0c02\u0c21\u0c4d \u0c30\u0c3e\u0c32\u0c47\u0c26\u0c41": "refund not received",
    "\u0c1a\u0c3e\u0c32\u0c3e \u0c06\u0c32\u0c38\u0c4d\u0c2f\u0c02": "very late",
    "\u0c28\u0c15\u0c3f\u0c32\u0c40 \u0c09\u0c24\u0c4d\u0c2a\u0c24\u0c4d\u0c24\u0c3f": "fake product",
    "valare nallathu": "very good",
    "valare mosham": "very bad",
    "nalla ille": "very bad",
    "nalla illa": "very bad",
    "pravarthikkunnilla": "not working",
    "refund kittiyilla": "refund not received",
    "valare vaiki": "very late",
    "\u0d35\u0d33\u0d30\u0d46 \u0d28\u0d32\u0d4d\u0d32\u0d24\u0d4d": "very good",
    "\u0d35\u0d33\u0d30\u0d46 \u0d2e\u0d4b\u0d36\u0d02": "very bad",
    "\u0d2a\u0d4d\u0d30\u0d35\u0d7c\u0d24\u0d4d\u0d24\u0d3f\u0d15\u0d4d\u0d15\u0d41\u0d28\u0d4d\u0d28\u0d3f\u0d32\u0d4d\u0d32": "not working",
    "\u0d31\u0d3f\u0d2b\u0d23\u0d4d\u0d1f\u0d4d \u0d15\u0d3f\u0d1f\u0d4d\u0d1f\u0d3f\u0d2f\u0d3f\u0d32\u0d4d\u0d32": "refund not received",
    "\u0d35\u0d33\u0d30\u0d46 \u0d35\u0d48\u0d15\u0d3f": "very late",
    "\u0d35\u0d4d\u0d2f\u0d3e\u0d1c \u0d09\u0d7d\u0d2a\u0d4d\u0d2a\u0d28\u0d4d\u0d28\u0d02": "fake product",
    "tumba chennagide": "very good",
    "tumba ketta": "very bad",
    "kelasa maduvudilla": "not working",
    "marupavati sigalilla": "refund not received",
    "tumba tada": "very late",
    "\u0ca4\u0cc1\u0c82\u0cac\u0cbe \u0c9a\u0cc6\u0ca8\u0ccd\u0ca8\u0cbe\u0c97\u0cbf\u0ca6\u0cc6": "very good",
    "\u0ca4\u0cc1\u0c82\u0cac\u0cbe \u0c95\u0cc6\u0c9f\u0ccd\u0c9f": "very bad",
    "\u0c95\u0cc6\u0cb2\u0cb8 \u0cae\u0cbe\u0ca1\u0cc1\u0cb5\u0cc1\u0ca6\u0cbf\u0cb2\u0ccd\u0cb2": "not working",
    "\u0cae\u0cb0\u0cc1\u0caa\u0cbe\u0cb5\u0ca4\u0cbf \u0cb8\u0cbf\u0c97\u0cb2\u0cbf\u0cb2\u0ccd\u0cb2": "refund not received",
    "\u0ca4\u0cc1\u0c82\u0cac\u0cbe \u0ca4\u0ca1": "very late",
    "\u0ca8\u0c95\u0cb2\u0cbf \u0c89\u0ca4\u0ccd\u0caa\u0ca8\u0ccd\u0ca8": "fake product",
}

TOKEN_MAP = {
    "bahut": "very",
    "accha": "good",
    "acha": "good",
    "achha": "good",
    "sahi": "good",
    "kharab": "bad",
    "bekar": "bad",
    "dhokha": "scam",
    "nakli": "fake",
    "paisa": "money",
    "paise": "money",
    "wapas": "return",
    "refund": "refund",
    "delivery": "delivery",
    "late": "late",
    "dhima": "slow",
    "tez": "fast",
    "aur": "and",
    "support": "support",
    "package": "package",
    "product": "product",
    "bahut": "very",
    "\u092c\u0939\u0941\u0924": "very",
    "\u092f\u0939": "this",
    "\u0914\u0930": "and",
    "\u0928\u0939\u0940\u0902": "not",
    "\u092e\u093f\u0932\u093e": "received",
    "\u0905\u091a\u094d\u091b\u093e": "good",
    "\u0916\u0930\u093e\u092c": "bad",
    "\u092c\u0947\u0915\u093e\u0930": "bad",
    "\u0927\u0940\u092e\u093e": "slow",
    "\u0924\u0947\u091c": "fast",
    "\u0921\u093f\u0932\u0940\u0935\u0930\u0940": "delivery",
    "\u0932\u0947\u091f": "late",
    "\u0927\u094b\u0916\u093e": "scam",
    "\u0928\u0915\u0932\u0940": "fake",
    "\u0938\u0930\u094d\u0935\u093f\u0938": "service",
    "\u092d\u0941\u0917\u0924\u093e\u0928": "payment",
    "\u0935\u093e\u092a\u0938": "return",
    "\u0930\u093f\u092b\u0902\u0921": "refund",
    "\u0911\u0930\u094d\u0921\u0930": "order",
    "\u092a\u0948\u0915\u0947\u091c": "package",
    "\u0921\u0948\u092e\u0947\u091c": "damaged",
    "\u0926\u0947\u0930": "delay",
    "\u0915\u0948\u0902\u0938\u0932": "cancel",
    "\u091c\u0935\u093e\u092c": "response",
    "romba": "very",
    "migavum": "very",
    "nalla": "good",
    "nallathu": "good",
    "mosam": "bad",
    "poli": "fake",
    "thaamatham": "delay",
    "methuva": "slow",
    "refund": "refund",
    "aadharavu": "support",
    "\u0ba8\u0bb2\u0bcd\u0bb2": "good",
    "\u0ba8\u0bb2\u0bcd\u0bb2\u0ba4\u0bc1": "good",
    "\u0bae\u0bcb\u0b9a\u0bae\u0bcd": "bad",
    "\u0baa\u0bcb\u0bb2\u0bbf": "fake",
    "\u0bae\u0bc6\u0ba4\u0bc1\u0bb5\u0bbe\u0b95": "slow",
    "\u0ba4\u0bbe\u0bae\u0ba4\u0bae\u0bcd": "delay",
    "\u0ba4\u0bbe\u0bae\u0ba4\u0bae\u0bbe\u0ba9": "late",
    "\u0b9f\u0bc6\u0bb2\u0bbf\u0bb5\u0bb0\u0bbf": "delivery",
    "\u0baa\u0bc7\u0b95\u0bcd\u0b95\u0bc7\u0b9c\u0bcd": "package",
    "\u0b9a\u0bc7\u0ba4\u0bae\u0bcd": "damaged",
    "\u0b89\u0b9f\u0bc8\u0ba8\u0bcd\u0ba4\u0ba4\u0bc1": "broken",
    "\u0b86\u0ba4\u0bb0\u0bb5\u0bc1": "support",
    "\u0bb0\u0ba4\u0bcd\u0ba4\u0bc1": "cancel",
    "\u0baa\u0ba3\u0bae\u0bcd": "money",
    "\u0ba4\u0bbf\u0bb0\u0bc1\u0bae\u0bcd\u0baa": "return",
    "\u0bb0\u0bbf\u0b83\u0baa\u0ba3\u0bcd\u0b9f\u0bcd": "refund",
    "\u0b86\u0bb0\u0bcd\u0b9f\u0bb0\u0bcd": "order",
    "\u0baa\u0ba4\u0bbf\u0bb2\u0bcd": "response",
    "chala": "very",
    "bagundi": "good",
    "manchidi": "good",
    "baledu": "bad",
    "baaledu": "bad",
    "baledhu": "bad",
    "baaledhu": "bad",
    "parledu": "okay",
    "parledhu": "okay",
    "parvaledu": "okay",
    "parvaledhu": "okay",
    "paravaaledu": "okay",
    "paravaaledhu": "okay",
    "chedu": "bad",
    "nakili": "fake",
    "alasya": "delay",
    "maddatu": "support",
    "raddu": "cancel",
    "\u0c2e\u0c02\u0c1a\u0c3f": "good",
    "\u0c2c\u0c3e\u0c17\u0c41\u0c02\u0c26\u0c3f": "good",
    "\u0c1a\u0c46\u0c21\u0c41": "bad",
    "\u0c28\u0c15\u0c3f\u0c32\u0c40": "fake",
    "\u0c28\u0c46\u0c2e\u0c4d\u0c2e\u0c26\u0c3f\u0c17\u0c3e": "slow",
    "\u0c35\u0c47\u0c17\u0c02": "fast",
    "\u0c06\u0c32\u0c38\u0c4d\u0c2f\u0c02": "delay",
    "\u0c06\u0c32\u0c38\u0c4d\u0c2f\u0c02\u0c17\u0c3e": "late",
    "\u0c21\u0c46\u0c32\u0c3f\u0c35\u0c30\u0c40": "delivery",
    "\u0c2a\u0c4d\u0c2f\u0c3e\u0c15\u0c47\u0c1c\u0c4d": "package",
    "\u0c26\u0c46\u0c2c\u0c4d\u0c2c\u0c24\u0c3f\u0c02\u0c26\u0c3f": "damaged",
    "\u0c35\u0c3f\u0c30\u0c3f\u0c17\u0c3f\u0c02\u0c26\u0c3f": "broken",
    "\u0c2e\u0c26\u0c4d\u0c26\u0c24\u0c41": "support",
    "\u0c30\u0c26\u0c4d\u0c26\u0c41": "cancel",
    "\u0c21\u0c2c\u0c4d\u0c2c\u0c41": "money",
    "\u0c30\u0c3f\u0c2b\u0c02\u0c21\u0c4d": "refund",
    "\u0c06\u0c30\u0c4d\u0c21\u0c30\u0c4d": "order",
    "\u0c38\u0c2e\u0c3e\u0c27\u0c3e\u0c28\u0c02": "response",
    "valare": "very",
    "nalla": "good",
    "mosham": "bad",
    "vyaja": "fake",
    "vaiki": "late",
    "sahayam": "support",
    "\u0d28\u0d32\u0d4d\u0d32": "good",
    "\u0d2e\u0d4b\u0d36\u0d02": "bad",
    "\u0d35\u0d4d\u0d2f\u0d3e\u0d1c": "fake",
    "\u0d2e\u0d28\u0d4d\u0d26\u0d02": "slow",
    "\u0d35\u0d47\u0d17\u0d02": "fast",
    "\u0d35\u0d48\u0d15\u0d3f": "late",
    "\u0d21\u0d46\u0d32\u0d3f\u0d35\u0d31\u0d3f": "delivery",
    "\u0d2a\u0d3e\u0d15\u0d4d\u0d15\u0d47\u0d1c\u0d4d": "package",
    "\u0d15\u0d47\u0d1f\u0d3e\u0d2f\u0d3f": "damaged",
    "\u0d24\u0d15\u0d7c\u0d28\u0d4d\u0d28\u0d41": "broken",
    "\u0d38\u0d39\u0d3e\u0d2f\u0d02": "support",
    "\u0d31\u0d26\u0d4d\u0d26\u0d3e\u0d15\u0d4d\u0d15\u0d3f": "cancelled",
    "\u0d2a\u0d23\u0d02": "money",
    "\u0d31\u0d3f\u0d2b\u0d23\u0d4d\u0d1f\u0d4d": "refund",
    "\u0d13\u0d7c\u0d21\u0d7c": "order",
    "\u0d2e\u0d31\u0d41\u0d2a\u0d1f\u0d3f": "response",
    "tumba": "very",
    "chennagide": "good",
    "olledu": "good",
    "ketta": "bad",
    "nakali": "fake",
    "tada": "late",
    "bembala": "support",
    "\u0c9a\u0cc6\u0ca8\u0ccd\u0ca8\u0cbe\u0c97\u0cbf\u0ca6\u0cc6": "good",
    "\u0c92\u0cb3\u0ccd\u0cb3\u0cc6\u0caf\u0ca6\u0cc1": "good",
    "\u0c95\u0cc6\u0c9f\u0ccd\u0c9f": "bad",
    "\u0ca8\u0c95\u0cb2\u0cbf": "fake",
    "\u0ca8\u0cbf\u0ca7\u0cbe\u0ca8": "slow",
    "\u0cb5\u0cc7\u0c97": "fast",
    "\u0ca4\u0ca1": "late",
    "\u0ca1\u0cc6\u0cb2\u0cbf\u0cb5\u0cb0\u0cbf": "delivery",
    "\u0caa\u0ccd\u0caf\u0cbe\u0c95\u0cc7\u0c9c\u0ccd": "package",
    "\u0cb9\u0cbe\u0ca8\u0cbf": "damaged",
    "\u0cae\u0cc1\u0cb0\u0cbf\u0ca6\u0cbf\u0ca6\u0cc6": "broken",
    "\u0cac\u0cc6\u0c82\u0cac\u0cb2": "support",
    "\u0cb0\u0ca6\u0ccd\u0ca6\u0cc1": "cancel",
    "\u0cb9\u0ca3": "money",
    "\u0cae\u0cb0\u0cc1\u0caa\u0cbe\u0cb5\u0ca4\u0cbf": "refund",
    "\u0c86\u0cb0\u0ccd\u0ca1\u0cb0\u0ccd": "order",
    "\u0c89\u0ca4\u0ccd\u0ca4\u0cb0": "response",
}

NEGATIVE_CUE_TOKENS = {
    "bad",
    "late",
    "delay",
    "delayed",
    "damaged",
    "broken",
    "fake",
    "scam",
    "failed",
    "cancel",
    "cancelled",
    "defective",
    "useless",
    "slow",
    "missing",
}

POSITIVE_CUE_TOKENS = {
    "good",
    "great",
    "excellent",
    "fast",
    "genuine",
    "better",
}

NEUTRAL_CUE_TOKENS = {
    "okay",
}

NEGATIVE_CUE_PHRASES = {
    "very bad",
    "not working",
    "refund not received",
    "refund missing",
    "fake product",
    "no response",
    "no support",
    "support failed",
    "response failed",
}

POSITIVE_CUE_PHRASES = {
    "very good",
}

NEUTRAL_CUE_PHRASES = set()


# Broaden the built-in lexicon with additional Indian-language coverage.
# This keeps the bridge maintainable while letting us expand vocabulary
# without rewriting the core normalization flow.
LANGUAGE_LABELS.update(
    {
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "pa": "Punjabi",
        "ur": "Urdu",
    }
)

SCRIPT_RANGES.update(
    {
        "bn": [(0x0980, 0x09FF)],
        "pa": [(0x0A00, 0x0A7F)],
        "gu": [(0x0A80, 0x0AFF)],
        "ur": [(0x0600, 0x06FF), (0x0750, 0x077F)],
    }
)

for language, hints in {
    "bn": {"khub", "bhalo", "kharap", "nokol", "deri", "kaj", "korena", "refund", "paini", "uttor"},
    "mr": {"khup", "changla", "changli", "changle", "vait", "ushir", "banavat", "paratava", "milala", "kam", "karat"},
    "gu": {"khub", "saru", "saras", "kharab", "nakli", "modu", "nathi", "kam", "kartu", "refund", "malyo"},
    "pa": {"vadhiya", "bahut", "kharab", "nakli", "der", "kam", "karda", "refund", "milya"},
    "ur": {"bohat", "acha", "bura", "naqli", "dair", "kaam", "nahin", "refund", "mila", "jawab", "madad"},
}.items():
    LANGUAGE_HINTS.setdefault(language, set()).update(hints)

PHRASE_MAP.update(
    {
        "khub bhalo": "very good",
        "khub kharap": "very bad",
        "kaj kore na": "not working",
        "kaj korena": "not working",
        "refund paini": "refund not received",
        "refund pai ni": "refund not received",
        "khub deri": "very late",
        "nokol product": "fake product",
        "khup changla": "very good",
        "khup changli": "very good",
        "khup changle": "very good",
        "khup vait": "very bad",
        "kam karat nahi": "not working",
        "refund milala nahi": "refund not received",
        "khup ushir": "very late",
        "banavat product": "fake product",
        "khub saru": "very good",
        "khub saras": "very good",
        "kam kartu nathi": "not working",
        "refund malyo nathi": "refund not received",
        "khub modu": "very late",
        "bahut vadhiya": "very good",
        "bahut kharab": "very bad",
        "kam nahi karda": "not working",
        "refund nahi milya": "refund not received",
        "bahut der": "very late",
        "nakli saman": "fake product",
        "bohat acha": "very good",
        "bohat bura": "very bad",
        "kaam nahin karta": "not working",
        "refund nahin mila": "refund not received",
        "bohat dair": "very late",
        "naqli product": "fake product",
    }
)

TOKEN_MAP.update(
    {
        "khub": "very",
        "khup": "very",
        "bhalo": "good",
        "kharap": "bad",
        "nokol": "fake",
        "deri": "late",
        "nahi": "not",
        "nahin": "not",
        "nathi": "not",
        "mila": "received",
        "milala": "received",
        "malyo": "received",
        "milya": "received",
        "changla": "good",
        "changli": "good",
        "changle": "good",
        "vait": "bad",
        "ushir": "late",
        "banavat": "fake",
        "saru": "good",
        "saras": "good",
        "modu": "late",
        "vadhiya": "good",
        "der": "late",
        "bohat": "very",
        "bura": "bad",
        "naqli": "fake",
        "dair": "late",
    }
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_surface_text(text: str) -> str:
    normalized = _strip_accents(text.lower()).replace("’", "'")
    normalized = normalized.replace("can't", "can not")
    normalized = normalized.replace("won't", "will not")
    normalized = re.sub(r"n['’]t\b", " not", normalized)
    return normalized


def _tokenize_unicode(text: str) -> list[str]:
    sanitized = re.sub(
        r"[^\w\s\u0600-\u06FF\u0750-\u077F\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]+",
        " ",
        text.lower(),
        flags=re.UNICODE,
    )
    return [token for token in sanitized.split() if token]


def _detect_from_script(text: str) -> str | None:
    for char in text:
        code_point = ord(char)
        for language, ranges in SCRIPT_RANGES.items():
            if any(start <= code_point <= end for start, end in ranges):
                return language
    return None


def _map_token(token: str) -> str:
    return TOKEN_MAP.get(token, token)


def _language_score_map(tokens: list[str]) -> dict[str, int]:
    return {
        language: sum(1 for token in tokens if token in hints)
        for language, hints in LANGUAGE_HINTS.items()
    }


def _canonicalize_sentiment_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    if not normalized:
        return ""
    for pattern, replacement in SENTIMENT_CANONICAL_RULES:
        normalized = pattern.sub(replacement, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def detect_language(text: str) -> tuple[str, float]:
    value = str(text or "").strip()
    if not value:
        return "unknown", 0.0

    tokens = _tokenize_unicode(_strip_accents(value))
    if not tokens:
        by_script = _detect_from_script(value)
        return (by_script, 0.98) if by_script else ("unknown", 0.0)

    by_script = _detect_from_script(value)
    english_score = sum(1 for token in tokens if token in ENGLISH_HINTS)
    scores = _language_score_map(tokens)
    best_language = max(scores, key=scores.get)
    best_score = scores[best_language]

    ascii_only = all(token.isascii() for token in tokens)
    if ascii_only and english_score >= max(2, best_score + 1):
        confidence = min(0.94, 0.5 + (english_score * 0.08))
        return "en", confidence

    if best_score > 0:
        confidence = min(0.95, 0.45 + (best_score * 0.12))
        if by_script and best_language == by_script:
            confidence = min(0.98, confidence + 0.08)
        return best_language, confidence

    if by_script:
        return by_script, 0.98

    return ("en", 0.56) if ascii_only else ("unknown", 0.2)


def normalize_multilingual_text(text: str) -> dict:
    raw_text = str(text or "").strip()
    normalized_text = _normalize_surface_text(raw_text)
    detected_language, confidence = detect_language(raw_text)

    mapped_text = normalized_text
    for source, target in PHRASE_MAP.items():
        mapped_text = mapped_text.replace(_strip_accents(source.lower()), target)
    mapped_text = _canonicalize_sentiment_text(mapped_text)

    tokens = _tokenize_unicode(mapped_text)
    translated_tokens = [_map_token(token) for token in tokens]
    translated_text = _canonicalize_sentiment_text(" ".join(translated_tokens).strip())
    translation_applied = translated_text != normalized_text

    if translation_applied:
        strategy = "lexicon_bridge"
    elif detected_language != "unknown":
        strategy = "language_detected_no_mapping"
    else:
        strategy = "fallback"

    return {
        "raw_text": raw_text,
        "normalized_text": translated_text or " ".join(tokens).strip(),
        "detected_language": detected_language,
        "detected_language_label": LANGUAGE_LABELS.get(detected_language, "Unknown"),
        "language_confidence": round(float(confidence), 3),
        "translation_applied": translation_applied,
        "strategy": strategy,
    }


def _rating_sentiment_hint(rating) -> str | None:
    try:
        value = float(rating)
    except (TypeError, ValueError):
        return None
    if value <= 2:
        return "Negative"
    if value == 3:
        return "Neutral"
    return "Positive"


def multilingual_sentiment_cues(normalized_text: str) -> dict:
    text = str(normalized_text or "").strip().lower()
    tokens = set(_tokenize_unicode(text))
    negative_tokens = sorted(token for token in tokens if token in NEGATIVE_CUE_TOKENS)
    positive_tokens = sorted(token for token in tokens if token in POSITIVE_CUE_TOKENS)
    neutral_tokens = sorted(token for token in tokens if token in NEUTRAL_CUE_TOKENS)
    negative_phrases = sorted(phrase for phrase in NEGATIVE_CUE_PHRASES if phrase in text)
    positive_phrases = sorted(phrase for phrase in POSITIVE_CUE_PHRASES if phrase in text)
    neutral_phrases = sorted(phrase for phrase in NEUTRAL_CUE_PHRASES if phrase in text)
    return {
        "negative_tokens": negative_tokens,
        "positive_tokens": positive_tokens,
        "neutral_tokens": neutral_tokens,
        "negative_phrases": negative_phrases,
        "positive_phrases": positive_phrases,
        "neutral_phrases": neutral_phrases,
        "negative_score": len(negative_tokens) + (2 * len(negative_phrases)),
        "positive_score": len(positive_tokens) + (2 * len(positive_phrases)),
        "neutral_score": len(neutral_tokens) + (2 * len(neutral_phrases)),
    }


def apply_multilingual_sentiment_guard(
    normalized_text: str,
    predicted_sentiment: str,
    class_probabilities: dict[str, float] | None = None,
    rating=None,
) -> tuple[str, str | None]:
    sentiment = str(predicted_sentiment or "").strip() or "Neutral"
    probability_map = class_probabilities or {}
    confidence = float(probability_map.get(sentiment, 0.0))
    rating_hint = _rating_sentiment_hint(rating)
    cues = multilingual_sentiment_cues(normalized_text)

    strong_negative = cues["negative_score"] >= 2 and cues["positive_score"] == 0
    strong_positive = cues["positive_score"] >= 2 and cues["negative_score"] == 0
    strong_neutral = (
        cues["neutral_score"] >= 1
        and cues["positive_score"] == 0
        and cues["negative_score"] == 0
    )

    if strong_negative and sentiment != "Negative" and (confidence < 0.75 or rating_hint == "Negative"):
        return "Negative", "multilingual_negative_guard"
    if strong_positive and sentiment != "Positive" and (confidence < 0.75 or rating_hint == "Positive"):
        return "Positive", "multilingual_positive_guard"
    if (
        strong_neutral
        and sentiment != "Neutral"
        and rating_hint not in {"Positive", "Negative"}
        and probability_map
        and confidence <= 0.85
    ):
        return "Neutral", "multilingual_neutral_guard"
    return sentiment, None
