"""LACH detector module.

Scores a candidate document on three sub-tasks via a frontier LLM:
detection (is this a covertly transformed cover?), source-domain
classification (if cover, what original domain?), and partial inversion
(propose source-domain originals for a few cover terms).

Used by the v4 evaluation harness to compute Adv_D (detector-bounded
adversary advantage) per LACH_SPEC.md Game 2.17b.X.

Pure stdlib + urllib, matching falsecolors.py conventions. Anthropic
adapter ships first; OpenAI and Gemini adapters land in week 4.

Usage:

    from detector import score_cover
    result = score_cover(text, model="claude-opus-4-7", api="anthropic")
    # -> {"is_cover": bool, "p_cover": float, "reasoning": str,
    #     "source_domain_guess": str, "inversion_proposals": dict,
    #     "raw": str, "parse_ok": bool}

API key is read from ANTHROPIC_API_KEY (or OPENAI_API_KEY, GEMINI_API_KEY).
"""

import json
import os
import re
import urllib.request

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_API = "anthropic"

DETECTION_SCHEMA = {
    "is_cover": bool,
    "p_cover": float,
    "reasoning": str,
    "source_domain_guess": str,
    "inversion_proposals": dict,
}

VALID_DOMAIN_GUESSES = {
    "ot_ics", "political", "legal", "medical", "financial",
    "none_of_above", "unsure",
}

ZERO_SHOT_PROMPT = """You are reviewing a document to determine if it is genuine native-domain content or a covertly transformed version of a sensitive source document that was rewritten to appear as innocuous content in an unrelated domain.

A "covertly transformed document" is one where:
- The vocabulary belongs to one domain (e.g. brewing, gardening) but the underlying logical structure was originally about a different domain (e.g. industrial control systems, political analysis, legal contracts).
- The relational structure (causation, measurement, conditionals, enumeration) is preserved but the surface vocabulary is substituted.

Document to evaluate:
---
{document}
---

Respond in JSON only, with this exact schema:

{{
  "is_cover": <bool>,
  "p_cover": <float in [0, 1]>,
  "reasoning": <string, max 200 words explaining the cues you used>,
  "source_domain_guess": <one of: "ot_ics", "political", "legal", "medical", "financial", "none_of_above", "unsure">,
  "inversion_proposals": {{
    "<cover_term>": "<your guess at the source-domain original>"
  }}
}}

For inversion_proposals, list 3 to 8 cover-domain content terms that look most likely to be substitutions, and your best guess at what they were originally. If you believe this is genuine native content, return an empty object.

Output only the JSON object. Do not wrap it in markdown fences. Do not include any prose before or after."""


def build_prompt(document, mode="zero_shot"):
    """Build the detector prompt for the given document."""
    if mode != "zero_shot":
        raise NotImplementedError(f"Prompt mode {mode!r} not yet implemented")
    return ZERO_SHOT_PROMPT.format(document=document)


def _call_anthropic(prompt, model, max_tokens=1024, timeout=60):
    """Call Anthropic Messages API. Returns raw text or raises on transport
    error. Caller is responsible for parsing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    url = "https://api.anthropic.com/v1/messages"
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def _call_api(prompt, model, api, **kwargs):
    if api == "anthropic":
        return _call_anthropic(prompt, model, **kwargs)
    if api == "mock":
        return _mock_response(prompt)
    raise NotImplementedError(f"API {api!r} not yet supported")


def _mock_response(prompt):
    """Deterministic response for offline tests. Inspects the prompt to
    decide if it looks more like native or cover content using a trivial
    heuristic (presence of brewery vocabulary). Not a real detector."""
    body = prompt.split("Document to evaluate:")[1] if "Document to evaluate:" in prompt else prompt
    brewery_terms = ("fermenter", "carbonation", "brewery", "wort", "hops",
                     "mash", "lauter", "yeast", "tank", "brewmaster")
    ot_terms = ("modbus", "register", "scada", "plc", "interlock",
                "reactor", "setpoint", "rtu", "ied")
    body_l = body.lower()
    bcount = sum(t in body_l for t in brewery_terms)
    ocount = sum(t in body_l for t in ot_terms)
    if ocount > bcount:
        is_cover, p = False, 0.05
        reasoning = "OT vocabulary present; likely native source domain."
        guess = "ot_ics"
    elif bcount > 3 and ocount == 0:
        is_cover, p = True, 0.65
        reasoning = "Brewery vocabulary with structural patterns suggesting transformation."
        guess = "ot_ics"
    else:
        is_cover, p = False, 0.20
        reasoning = "Sparse signals; defaulting to native."
        guess = "none_of_above"
    return json.dumps({
        "is_cover": is_cover,
        "p_cover": p,
        "reasoning": reasoning,
        "source_domain_guess": guess,
        "inversion_proposals": {},
    })


def parse_response(raw):
    """Tolerant parser for the detector's JSON response. Strips markdown
    fences if present, finds the first balanced JSON object, validates the
    schema. Returns (parsed_dict, parse_ok). On failure, returns a
    defensive default with parse_ok=False."""
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if model added them
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)

    # Find first balanced { ... } block
    start = text.find("{")
    if start < 0:
        return _default_parse_failure(raw), False
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return _default_parse_failure(raw), False

    try:
        obj = json.loads(text[start:end])
    except json.JSONDecodeError:
        return _default_parse_failure(raw), False

    # Validate schema; coerce types where possible
    out = {
        "is_cover": bool(obj.get("is_cover", False)),
        "p_cover": float(obj.get("p_cover", 0.0)),
        "reasoning": str(obj.get("reasoning", ""))[:1000],
        "source_domain_guess": str(obj.get("source_domain_guess", "unsure")),
        "inversion_proposals": obj.get("inversion_proposals", {}) or {},
    }
    if out["source_domain_guess"] not in VALID_DOMAIN_GUESSES:
        out["source_domain_guess"] = "unsure"
    if not isinstance(out["inversion_proposals"], dict):
        out["inversion_proposals"] = {}
    # Clamp p_cover to [0, 1]
    out["p_cover"] = max(0.0, min(1.0, out["p_cover"]))
    return out, True


def _default_parse_failure(raw):
    """Returned when the detector response cannot be parsed. Signals an
    abstaining detector: no claim, no information."""
    return {
        "is_cover": False,
        "p_cover": 0.5,
        "reasoning": "[parse failure]",
        "source_domain_guess": "unsure",
        "inversion_proposals": {},
    }


def score_cover(document, model=DEFAULT_MODEL, api=DEFAULT_API,
                mode="zero_shot"):
    """Score a candidate document against the detector. Returns a dict
    with the parsed detector output plus the raw response and a parse_ok
    flag. Caller should treat parse_ok=False trials as detector
    abstentions, not as is_cover=False evidence."""
    prompt = build_prompt(document, mode=mode)
    try:
        raw = _call_api(prompt, model=model, api=api)
    except Exception as e:
        return {
            **_default_parse_failure(""),
            "raw": f"[API error: {type(e).__name__}: {e}]"[:500],
            "parse_ok": False,
            "api_error": True,
        }
    parsed, ok = parse_response(raw)
    parsed["raw"] = raw[:2000]
    parsed["parse_ok"] = ok
    parsed["api_error"] = False
    return parsed


if __name__ == "__main__":
    # Smoke test using the mock backend. Real Anthropic calls require
    # ANTHROPIC_API_KEY and use --api anthropic.
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="Path to document to score")
    p.add_argument("--api", default="mock", choices=["mock", "anthropic"])
    p.add_argument("--model", default=DEFAULT_MODEL)
    args = p.parse_args()

    text = open(args.source).read()
    result = score_cover(text, model=args.model, api=args.api)
    print(json.dumps(result, indent=2))
