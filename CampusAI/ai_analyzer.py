"""AI analysis of complaints.

Uses Claude if ANTHROPIC_API_KEY is set, otherwise a built-in keyword analyzer.
Returns: {"priority": "High|Medium|Low", "summary": str, "tags": [str], "suggested_category": str}
"""

import json
import re
import urllib.request

import config

HIGH = ["fire", "short circuit", "sparking", "electric shock", "ragging", "harass", "fight",
        "violence", "weapon", "drug", "smoking", "leak", "flood", "collapse", "crack", "broken glass",
        "injury", "unsafe", "danger", "urgent", "emergency", "no water", "sewage", "overflow"]
MEDIUM = ["broken", "not working", "damaged", "dirty", "smell", "garbage", "dustbin", "toilet",
          "washroom", "late", "misbehave", "noise", "cheating", "fan", "light", "projector", "bench",
          "door", "window", "ac ", "wifi", "water"]

KEYWORDS = {
    "Discipline": ["ragging", "fight", "cheating", "late", "misbehave", "smoking", "drug", "harass",
                   "noise", "bunk", "abuse", "bully", "uniform", "attendance", "teacher", "violence"],
    "Cleanliness": ["dirty", "garbage", "dustbin", "toilet", "washroom", "smell", "clean", "sweep",
                    "waste", "litter", "mess", "dust", "stink", "drain", "cobweb"],
    "Infrastructure": ["broken", "repair", "renovation", "leak", "crack", "fan", "light", "projector",
                       "bench", "door", "window", "wall", "ceiling", "roof", "wifi", "ac ", "pipe",
                       "electric", "paint", "lab", "building", "furniture", "tap"],
}


def _rule_based(category, description, location):
    text = f" {description} {location} ".lower()
    if any(k in text for k in HIGH):
        priority = "High"
    elif any(k in text for k in MEDIUM):
        priority = "Medium"
    else:
        priority = "Low"

    scores = {c: sum(1 for k in kws if k in text) for c, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    suggested = best if scores[best] > 0 else category

    tags = sorted({k.strip() for kws in KEYWORDS.values() for k in kws if k in text})[:5]
    clean = re.sub(r"\s+", " ", description).strip()
    summary = clean if len(clean) <= 110 else clean[:107] + "..."
    summary = f"{category} issue at {location or 'unspecified location'}: {summary}"
    return {"priority": priority, "summary": summary, "tags": tags, "suggested_category": suggested}


def _claude(category, description, location):
    prompt = (
        "You triage campus complaints. Reply ONLY with JSON: "
        '{"priority":"High|Medium|Low","summary":"max 20 words","tags":["..."],'
        '"suggested_category":"Discipline|Cleanliness|Infrastructure"}\n'
        f"Selected category: {category}\nLocation: {location}\nDescription: {description}"
    )
    body = json.dumps({
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    text = data["content"][0]["text"]
    result = json.loads(text[text.index("{"): text.rindex("}") + 1])
    if result.get("priority") not in ("High", "Medium", "Low"):
        raise ValueError("bad priority")
    if result.get("suggested_category") not in config.CATEGORIES:
        result["suggested_category"] = category
    result["tags"] = list(result.get("tags", []))[:5]
    return result


def analyze(category, description, location):
    if config.ANTHROPIC_API_KEY:
        try:
            return _claude(category, description, location)
        except Exception as e:  # fall back silently to offline analyzer
            print("Claude analysis failed, using fallback:", e)
    return _rule_based(category, description, location)
