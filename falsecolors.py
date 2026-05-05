#!/usr/bin/env python3
# Eris FALSECOLORS
# Copyright (C) 2026 River Caudle
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Commercial use requires a separate commercial license.

"""
Eris FALSECOLORS - Standalone Proof of Concept
Noncryptographic Semantic Transformation for Deniable Document Protection

The best protection doesn't look like protection.

ENCRYPT:
  python falsecolors.py encrypt \\
    --source finding.txt \\
    --passphrase "my secret" \\
    --topic brewery \\
    --output cover.txt

DECRYPT:
  python falsecolors.py decrypt \\
    --source cover.txt \\
    --passphrase "my secret" \\
    --output recovered.txt

PROXY (interactive LLM chat with transparent domain shift):
  python falsecolors.py proxy \\
    --passphrase "my secret" \\
    --api anthropic

DEMO:
  python falsecolors.py demo

Zero external dependencies. Python 3.8+ standard library only.
For LLM backend (--backend llm) and proxy mode, requires Ollama
or compatible local model server.
"""

import json
import re
import sys
import os
import math
import argparse
import hashlib
import base64
import struct
import random
from collections import OrderedDict
from pathlib import Path


# Minimum fraction of sampled mapping entries that must appear in the cover.
# If the LLM backend produces a ratio below this, a warning is printed to
# stderr. Set to 0.0 to disable. Overridden to a hard error by --strict.
MAPPING_VERIFY_THRESHOLD = 0.8
MAPPING_VERIFY_SAMPLES = 5


# ================================================================
# STREAM CIPHER (passphrase-based, standard library only)
# ================================================================

class Cipher:
    """Passphrase-derived stream cipher. PBKDF2-SHA256 key derivation,
    counter-mode keystream XOR. No external crypto dependencies."""

    @staticmethod
    def _derive_key(passphrase, salt, iterations=100_000):
        key = passphrase.encode()
        for _ in range(iterations):
            key = hashlib.sha256(salt + key).digest()
        return key

    @classmethod
    def encrypt(cls, plaintext, passphrase):
        salt = os.urandom(16)
        key = cls._derive_key(passphrase, salt)
        stream = cls._keystream(key, len(plaintext))
        return salt + bytes(a ^ b for a, b in zip(plaintext, stream))

    @classmethod
    def decrypt(cls, data, passphrase):
        salt, ct = data[:16], data[16:]
        key = cls._derive_key(passphrase, salt)
        stream = cls._keystream(key, len(ct))
        return bytes(a ^ b for a, b in zip(ct, stream))

    @staticmethod
    def _keystream(key, length):
        out, ctr = b"", 0
        while len(out) < length:
            out += hashlib.sha256(key + struct.pack(">Q", ctr)).digest()
            ctr += 1
        return out[:length]


# ================================================================
# IDENTIFIER ENCODER
# ================================================================

class IdentEncoder:
    """Replace technical identifiers (IPs, registers, protocols, CVEs,
    measurements, standards, firmware) with innocuous placeholders.
    Separates sensitive parameters from operational context."""

    PATTERNS = OrderedDict([
        ("ipv4", re.compile(
            r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
            r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b')),
        ("cve", re.compile(r'\bCVE-\d{4}-\d{4,}\b')),
        ("port", re.compile(r'\b(?:port|tcp|udp)[/ ]\d{1,5}\b', re.I)),
        ("register", re.compile(r'\b[1-4]0\d{3,4}\b')),
        ("standard", re.compile(
            r'\b(?:IEC|ISO|NIST|IEEE|ISA|NERC)\s+\d[\d.\-]*\b')),
        ("measurement", re.compile(
            r'\b\d+(?:\.\d+)?\s*(?:PSI|psi|bar|kPa|MPa|mA|VDC|VAC|Hz'
            r'|kHz|MHz|GHz|Mbps|Gbps|rpm|CFM|GPM|LPM)\b')),
        ("firmware", re.compile(r'\b[vV]\d+\.\d+(?:\.\d+)*\b')),
        ("protocol", re.compile(
            r'\b(?:Modbus TCP|Modbus RTU|Modbus|EtherNet/IP|OPC\s*UA|'
            r'DNP3|PROFINET|PROFIBUS|BACnet|HART|WirelessHART|'
            r'S7comm|IEC\s*104|GOOSE|MMS|Foundation\s*Fieldbus)\b')),
    ])

    POOL = [
        "alpha", "baker", "charlie", "delta", "echo",
        "foxtrot", "golf", "hotel", "india", "juliet",
        "kilo", "lima", "mike", "november", "oscar",
        "papa", "quebec", "romeo", "sierra", "tango",
        "uniform", "victor", "whiskey", "xray", "yankee",
        "zulu", "amber", "bronze", "coral", "dusk",
        "ember", "frost", "granite", "harbor", "ivory",
        "jasper", "kelp", "linden", "marble", "nectar",
    ]

    def __init__(self):
        self._idx = 0
        self._seen = {}

    def _placeholder(self, original):
        if original in self._seen:
            return self._seen[original]
        base = self.POOL[self._idx % len(self.POOL)]
        cycle = self._idx // len(self.POOL)
        p = base if cycle == 0 else f"{base}{cycle + 1}"
        self._idx += 1
        self._seen[original] = p
        return p

    def encode(self, text, extra_terms=None):
        matches = []
        for ptype, pat in self.PATTERNS.items():
            for m in pat.finditer(text):
                if not any(m.start() < x["end"] and m.end() > x["start"]
                           for x in matches):
                    matches.append({"start": m.start(), "end": m.end(),
                                    "original": m.group(), "type": ptype})
        if extra_terms:
            for term in extra_terms:
                for m in re.finditer(re.escape(term), text):
                    if not any(m.start() < x["end"] and m.end() > x["start"]
                               for x in matches):
                        matches.append({"start": m.start(), "end": m.end(),
                                        "original": m.group(), "type": "manual"})

        matches.sort(key=lambda x: x["start"], reverse=True)
        ident_map = {}
        result = text
        for match in matches:
            p = self._placeholder(match["original"])
            ident_map[p] = match["original"]
            repl = p.upper() if match["original"].isupper() else (
                p.capitalize() if match["original"][0].isupper() else p)
            result = result[:match["start"]] + repl + result[match["end"]:]
        return result, ident_map

    @staticmethod
    def decode(text, ident_map):
        result = text
        for p, orig in sorted(ident_map.items(), key=lambda x: len(x[0]),
                               reverse=True):
            for variant in [p, p.upper(), p.capitalize(), p.lower()]:
                if variant in result:
                    result = result.replace(variant, orig)
        return result


# ================================================================
# DOMAIN MAPPING ENGINE
# ================================================================

def apply_mapping(text, mapping):
    """Longest-match-first substitution with word boundaries."""
    sorted_map = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
    replacements, used = [], set()
    for src, tgt in sorted_map:
        if src == tgt:
            continue
        for m in re.finditer(r'(?<!\w)' + re.escape(src) + r'(?!\w)', text):
            s, e = m.start(), m.end()
            if set(range(s, e)) & used:
                continue
            replacements.append((s, e, tgt))
            used |= set(range(s, e))
    replacements.sort(key=lambda x: x[0], reverse=True)
    for s, e, tgt in replacements:
        text = text[:s] + tgt + text[e:]
    return text


def invert_mapping(mapping):
    return OrderedDict((v, k) for k, v in mapping.items() if k != v)


# ================================================================
# MAPPING EMBEDDING
# ================================================================

EMBED_MARKER = "\n\n---\nDocument Tracking: "


def embed_key(cover, key_data, passphrase):
    """Encrypt key_data and embed as base64 footer."""
    import zlib
    raw = json.dumps(key_data, separators=(',', ':')).encode()
    compressed = zlib.compress(raw)
    encrypted = Cipher.encrypt(compressed, passphrase)
    encoded = base64.b64encode(encrypted).decode()
    lines = [encoded[i:i+76] for i in range(0, len(encoded), 76)]
    return cover + EMBED_MARKER + "\n".join(lines) + "\n"


def extract_key(text, passphrase):
    """Extract and decrypt embedded key."""
    import zlib
    if EMBED_MARKER not in text:
        raise ValueError("No embedded key found.")
    cover, block = text.split(EMBED_MARKER, 1)
    encrypted = base64.b64decode(block.strip().replace("\n", ""))
    try:
        compressed = Cipher.decrypt(encrypted, passphrase)
        raw = zlib.decompress(compressed)
        return cover, json.loads(raw.decode())
    except Exception:
        raise ValueError("Wrong passphrase.")


# ================================================================
# BUILT-IN DOMAIN MAPPINGS
# ================================================================

DOMAINS = {
    "brewery": OrderedDict([
        # Document framing
        ("CONFIDENTIAL - ENGAGEMENT FINDINGS", "INTERNAL - QUALITY AUDIT NOTES"),
        ("Client: [Redacted Chemical Manufacturing]", "Client: [Redacted Craft Brewery]"),
        # Systems
        ("Safety Instrumented System", "Quality Control System"),
        ("safety instrumented system", "quality control system"),
        ("safety system", "quality system"),
        ("Safety PLC", "Quality Controller"),
        ("safety controller", "quality controller"),
        ("emergency shutdown valve", "batch rejection gate"),
        ("emergency shutdown", "batch rejection"),
        # Process
        ("high-pressure interlock setpoints", "carbonation quality checkpoint thresholds"),
        ("interlock threshold", "quality checkpoint threshold"),
        ("interlock setpoints", "checkpoint thresholds"),
        ("interlock", "quality checkpoint"),
        ("overpressure event", "over-carbonation event"),
        ("overpressure condition", "over-carbonation condition"),
        ("overpressure", "over-carbonation"),
        ("reactor vessel", "fermentation vessel"),
        ("reactor control", "fermenter control"),
        ("reactor", "fermenter"),
        ("ethylene oxide", "imperial stout"),
        ("control loop", "production loop"),
        ("control network", "production network"),
        ("holding registers", "recipe parameters"),
        ("register writes", "parameter writes"),
        ("register", "parameter"),
        # Network
        ("Level 1 control network", "production floor network"),
        ("Level 1 boundary", "production floor boundary"),
        ("Level 1", "production floor"),
        ("network access", "system access"),
        ("network architecture", "system architecture"),
        ("SIS setpoint registers", "QCS threshold parameters"),
        ("SIS network", "QCS system"),
        ("SIS", "QCS"),
        # Interface
        ("operator HMI", "brewmaster dashboard"),
        ("HMI", "dashboard"),
        ("console", "terminal"),
        # Consequence
        ("pressure to exceed the vessel's rated capacity",
         "carbonation to exceed the vessel's rated tolerance"),
        ("immediate risk to human life and facility integrity",
         "immediate risk to product safety and brand integrity"),
        ("human life", "product safety"),
        ("facility integrity", "brand integrity"),
        # People
        ("plant manager", "head brewer"),
        ("assessor", "auditor"),
        ("Assessor", "Auditor"),
        ("attacker", "unauthorized user"),
        ("An attacker", "An unauthorized user"),
        # Actions
        ("exploitation", "misuse"),
        ("setpoint value", "threshold value"),
        ("setpoint changes", "threshold changes"),
        ("engineered setpoint", "engineered threshold"),
        ("setpoint of", "threshold of"),
        ("setpoint", "threshold"),
        ("alarm or audit log", "notification or activity log"),
        ("alarm", "notification"),
        ("audit log", "activity log"),
        ("change detection", "modification tracking"),
        ("change history", "modification history"),
        ("firewall rules", "access control rules"),
        ("write access", "edit access"),
        # Standards (handled by ident encoder, but catch remnants)
        ("penetration test", "quality audit"),
        ("pentest", "audit"),
        ("vulnerability", "deficiency"),
        ("vulnerabilities", "deficiencies"),
        # Response-side vocabulary (terms LLMs generate in brewery domain)
        ("brewmaster", "plant operator"),
        ("brewmasters", "plant operators"),
        ("fermentation", "reaction"),
        ("carbonation levels", "pressure levels"),
        ("carbonation monitoring", "pressure monitoring"),
        ("carbonation", "pressure"),
        ("Carbonation", "Pressure"),
        ("recipe management", "configuration management"),
        ("recipe parameter", "control parameter"),
        ("recipe parameters", "control parameters"),
        ("recipe database", "configuration database"),
        ("recipe", "configuration"),
        ("batch record", "process record"),
        ("batch records", "process records"),
        ("batch rejection", "emergency shutdown"),
        ("batch", "process run"),
        ("production floor network", "Level 1 control network"),
        ("production floor boundary", "Level 1 boundary"),
        ("production floor", "Level 1"),
        ("production loop", "control loop"),
        ("quality checkpoint threshold", "interlock threshold"),
        ("quality checkpoint", "interlock"),
        ("quality controller", "safety controller"),
        ("Quality Controller", "Safety PLC"),
        ("Quality Control System", "Safety Instrumented System"),
        ("quality control", "safety"),
        ("quality system", "safety system"),
        ("product safety", "human life"),
        ("brand integrity", "facility integrity"),
        ("over-carbonation event", "overpressure event"),
        ("over-carbonation condition", "overpressure condition"),
        ("over-carbonation", "overpressure"),
        ("fermentation vessel", "reactor vessel"),
        ("fermenter control", "reactor control"),
        ("fermenter", "reactor"),
        ("imperial stout", "ethylene oxide"),
        ("head brewer", "plant manager"),
        ("unauthorized user", "attacker"),
        ("An unauthorized user", "An attacker"),
        ("notification or activity log", "alarm or audit log"),
        ("notification", "alarm"),
        ("activity log", "audit log"),
        ("modification tracking", "change detection"),
        ("modification history", "change history"),
        ("access control rules", "firewall rules"),
        ("edit access", "write access"),
        ("threshold value", "setpoint value"),
        ("threshold changes", "setpoint changes"),
        ("engineered threshold", "engineered setpoint"),
        ("threshold of", "setpoint of"),
        ("misuse", "exploitation"),
        ("deficiency", "vulnerability"),
        ("deficiencies", "vulnerabilities"),
        ("system access", "network access"),
        ("system architecture", "network architecture"),
        ("QCS threshold parameters", "SIS setpoint registers"),
        ("QCS system", "SIS network"),
        ("QCS", "SIS"),
        ("brewmaster dashboard", "operator HMI"),
        ("dashboard", "HMI"),
        ("terminal", "console"),
        ("ISO 22000", "IEC 61511"),
        ("HACCP", "IEC 61511 Annex"),
        ("food safety", "process safety"),
    ]),
}


# ================================================================
# LLM BACKEND
# ================================================================

LLM_TWO_STEP = True


def _parse_mapping_response(raw):
    """Tolerant parser for a model's mapping JSON. Accepts either a single
    flat object {"src": "tgt", ...} or a list-of-pairs shape
    [{"original": "x", "replacement": "y"}, ...] (with or without array
    brackets), and returns a flat dict. Returns {} on any parse failure."""
    if not raw:
        return {}
    s = raw.strip().strip('`')
    if s.startswith('json'):
        s = s[4:].strip()

    obj_start = s.find('{')
    obj_end = s.rfind('}')
    if obj_start == -1 or obj_end == -1:
        return {}
    body = s[obj_start:obj_end + 1]

    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict) and all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in parsed.items()):
            return parsed
    except json.JSONDecodeError:
        pass

    try:
        wrapped = '[' + body + ']'
        parsed = json.loads(wrapped)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, list):
        return {}
    out = {}
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        if 'original' in entry and 'replacement' in entry:
            k, v = entry['original'], entry['replacement']
        elif len(entry) == 1:
            (k, v), = entry.items()
        else:
            continue
        if isinstance(k, str) and isinstance(v, str) and k:
            out[k] = v
    return out


def llm_translate(text, topic, direction="encode", model="llama3.2:3b"):
    """Use local LLM for domain translation. Returns (text, mapping).

    Encode direction uses a two-step call when LLM_TWO_STEP is True:
      Call 1: model proposes the term mapping as a JSON object only.
      Call 2: model rewrites the source using the fixed mapping.
    This eliminates the bimodal failure mode observed when a single prompt
    asks the model to simultaneously commit to prose and a mapping.

    OLLAMA_TIMEOUT (seconds, default 120) controls the request timeout.
    OLLAMA_PROMPT_PREFIX is prepended to every prompt and is intended for
    model-specific directives like qwen3's /no_think."""
    import urllib.request

    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    timeout = float(os.environ.get("OLLAMA_TIMEOUT", "120"))
    prompt_prefix = os.environ.get("OLLAMA_PROMPT_PREFIX", "")

    def _call(prompt):
        if prompt_prefix:
            prompt_with_prefix = prompt_prefix + prompt
        else:
            prompt_with_prefix = prompt
        body = json.dumps({"model": model, "prompt": prompt_with_prefix,
                           "stream": False,
                           "options": {"temperature": 0.1}}).encode()
        req = urllib.request.Request(
            f"{base}/api/generate", data=body,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())["response"]

    try:
        if direction == "encode" and LLM_TWO_STEP:
            prompt1 = (
                f"You are a domain translation engine. Identify every "
                f"domain-specific term in the SOURCE text below that should "
                f"be replaced with a {topic}-domain equivalent. Output a "
                f"single flat JSON object whose keys are the original terms "
                f"and whose values are their {topic} replacements.\n\n"
                f"Example for an OT-to-brewery rewrite (illustrative, not "
                f"the source you are working on):\n"
                f"{{\"reactor\": \"fermenter\", \"Modbus TCP\": \"Brewery "
                f"Protocol\", \"holding register\": \"recipe parameter\"}}\n\n"
                f"Output ONLY the single JSON object. No prose, no markdown, "
                f"no commentary, no array wrapper, no per-entry objects.\n\n"
                f"SOURCE:\n{text}"
            )
            raw1 = _call(prompt1)
            mapping = _parse_mapping_response(raw1)

            prompt2 = (
                f"You are a domain translation engine. Rewrite the SOURCE "
                f"text below as a document about: {topic}\n\n"
                f"Apply these substitutions exactly. Do not introduce other "
                f"substitutions. Preserve every logical relationship.\n\n"
                f"MAPPING:\n{json.dumps(mapping)}\n\n"
                f"SOURCE:\n{text}\n\n"
                f"Output ONLY the rewritten text. No JSON, no commentary."
            )
            cover = _call(prompt2).strip()
            return cover, mapping

        elif direction == "encode":
            prompt = (
                f"You are a domain translation engine. Rewrite the following "
                f"text so it reads as a document about: {topic}\n\n"
                f"Replace every domain-specific term with an equivalent from "
                f"the target topic. Preserve every logical relationship.\n\n"
                f"After the rewritten text, output ONLY a JSON object on a "
                f"new line mapping every substitution: "
                f'{{\"original\": \"replacement\", ...}}\n\n'
                f"SOURCE:\n{text}"
            )
            response = _call(prompt)
            json_start = response.rfind('\n{')
            if json_start == -1:
                json_start = response.rfind('{')
            if json_start != -1:
                cover = response[:json_start].strip()
                mapping_str = response[json_start:].strip().strip('`')
                if mapping_str.startswith('json'):
                    mapping_str = mapping_str[4:].strip()
                mapping = json.loads(mapping_str)
            else:
                cover = response.strip()
                mapping = {}
            return cover, mapping

        else:
            prompt = (
                f"Reverse the following domain substitutions in this text. "
                f"Apply these mappings:\n{json.dumps(text[1])}\n\n"
                f"TEXT:\n{text[0]}"
            )
            response = _call(prompt)
            return response.strip(), {}

    except ConnectionRefusedError:
        print(f"[!] Cannot connect to Ollama at {base}")
        print(f"    Install: curl -fsSL https://ollama.com/install.sh | sh")
        print(f"    Pull:    ollama pull {model}")
        sys.exit(1)


# ================================================================
# GRAPH-SHIFT METHOD (Method 5)
# ================================================================
#
# Two-pass pipeline that decouples cover generation from source text:
#
#   Pass 1 (extract): source text -> relational graph (entities,
#                     relations, claims, identifiers, source_vocab).
#                     The LLM invents entity ids, types, and predicates
#                     per document. No fixed schema, no curated mapping.
#   Pass 2 (cover):   graph (without source_vocab) + topic -> cover
#                     document + cover_vocab. Pass 2 cannot see the
#                     source text, so source vocabulary cannot leak.
#
# Recovery is mechanical: cover_vocab inverts the cover into entity
# ids, then source_vocab maps ids back to source terms. The
# IdentEncoder layer handles IPs, CVEs, and other technical
# identifiers as in the other methods.
#
# Tradeoff: round-trip preserves semantic content (entities,
# relations, claims, identifiers) but not the source's exact
# rhetorical framing or document genre. For pentest findings and
# situation reports this is acceptable; for documents where exact
# wording is load-bearing (legal contracts, signed instruments),
# Method 1 with a curated mapping is the appropriate choice.


def _extract_first_json_object(text):
    """Pull the first balanced { ... } block out of a string and parse it.
    Tolerant of leading prose, markdown fences, and trailing prose. Returns
    (parsed_dict, ok). Raises ValueError on hard failure."""
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s)
    start = s.find("{")
    if start < 0:
        raise ValueError("no JSON object in response")
    depth = 0
    end = -1
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise ValueError("unbalanced JSON braces")
    return json.loads(s[start:end])


GRAPH_EXTRACT_PROMPT = """Extract the document below as a JSON graph. Use generic ids like e1, e2, e3 (not source phrases). Output JSON only, no markdown.

Schema:
{"entities":[{"id":"e1","type":"asset"}],"relations":[{"from":"e1","verb":"protects","to":"e2"}],"facts":["e1 protects e2"],"numbers":{"e3":"185"},"vocab":{"e1":"the exact source phrase","e2":"another source phrase"}}

Rules:
- ids must be e1, e2, e3, ... (NEVER source phrases as ids)
- vocab MUST have an entry for every entity, mapping id -> exact source phrase
- entities, relations, facts, numbers MUST NOT contain any source phrase, only ids and generic words

DOCUMENT:
"""


GRAPH_COVER_PROMPT_TEMPLATE = """Write a short {topic} document. Use only {topic} vocabulary. Output JSON only.

Schema:
{{"cover":"...full document text...","names":{{"e1":"a {topic} word","e2":"another {topic} word"}}}}

For each entity id in the graph, invent a {topic} word and put it in names. Use those words in the cover text. Never write e1, e2, e3 in the cover text. Never use cybersecurity, security audit, OT, ICS, intelligence, military, legal, or political vocabulary in the cover text or names. Keep numbers from the graph's "numbers" dict exactly as-is.

GRAPH:
{graph_json}
"""


def _llm_call(prompt, model, backend, timeout):
    """Backend-agnostic LLM call. Supports backend in {ollama, groq,
    anthropic}. Returns raw text response."""
    import urllib.request
    if backend == "ollama":
        base = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0.1}}).encode()
        req = urllib.request.Request(
            f"{base}/api/generate", data=body,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())["response"]
    if backend == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set for backend=groq")
        body = json.dumps({"model": model,
                           "messages": [{"role": "user", "content": prompt}],
                           "temperature": 0.1, "max_tokens": 4096}).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}",
                     "User-Agent": "eris-falsecolors-graph/0.1"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())["choices"][0]["message"]["content"]
    if backend == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set for backend=anthropic")
        body = json.dumps({"model": model, "max_tokens": 4096,
                           "messages": [{"role": "user", "content": prompt}]
                           }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body,
            headers={"Content-Type": "application/json",
                     "x-api-key": api_key,
                     "anthropic-version": "2023-06-01"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        for block in data.get("content", []) or []:
            if block.get("type") == "text" and block.get("text"):
                return block["text"]
        return f"[empty content, stop_reason={data.get('stop_reason','?')}]"
    raise ValueError(f"unknown backend {backend!r}")


def llm_extract_graph(text, model, timeout=None, backend="ollama"):
    """Pass 1: source text -> relational graph dict."""
    if timeout is None:
        timeout = float(os.environ.get("OLLAMA_TIMEOUT", "300"))
    prefix = os.environ.get("OLLAMA_PROMPT_PREFIX", "")
    prompt = prefix + GRAPH_EXTRACT_PROMPT + text
    raw = _llm_call(prompt, model, backend, timeout)
    graph = _extract_first_json_object(raw)
    # Normalize to canonical field names used by encode_via_graph and
    # decode_via_graph. Pass 1 prompts may use either the long-form schema
    # (source_vocab, claims, identifiers) or the short-form schema (vocab,
    # facts, numbers). Both are accepted.
    if "vocab" in graph and "source_vocab" not in graph:
        graph["source_vocab"] = graph.pop("vocab")
    if "facts" in graph and "claims" not in graph:
        graph["claims"] = graph.pop("facts")
    if "numbers" in graph and "identifiers" not in graph:
        graph["identifiers"] = graph.pop("numbers")
    # Sanity check the shape
    for k in ("entities", "relations", "claims", "source_vocab"):
        if k not in graph:
            graph[k] = []
    if not isinstance(graph.get("identifiers"), dict):
        graph["identifiers"] = {}
    if not isinstance(graph.get("source_vocab"), dict):
        graph["source_vocab"] = {}
    return graph


def llm_generate_cover_from_graph(graph, topic, model, timeout=None,
                                    backend="ollama"):
    """Pass 2: graph (with source_vocab REMOVED) + topic -> (cover_text,
    cover_vocab dict)."""
    if timeout is None:
        timeout = float(os.environ.get("OLLAMA_TIMEOUT", "300"))
    prefix = os.environ.get("OLLAMA_PROMPT_PREFIX", "")
    safe_graph = {k: v for k, v in graph.items() if k != "source_vocab"}
    prompt = prefix + GRAPH_COVER_PROMPT_TEMPLATE.format(
        topic=topic, graph_json=json.dumps(safe_graph, indent=2))
    raw = _llm_call(prompt, model, backend, timeout)
    obj = _extract_first_json_object(raw)
    cover = obj.get("cover", "")
    # Accept either "cover_vocab" (long-form) or "names" (short-form)
    cover_vocab = obj.get("cover_vocab") or obj.get("names") or {}
    if not isinstance(cover_vocab, dict):
        cover_vocab = {}
    return cover.strip(), cover_vocab


def _strip_entity_id_parentheticals(cover, entity_ids):
    """Pass 2 sometimes surfaces entity ids in parens like 'fermenter
    (asset_1)'. Strip these patterns so the cover reads natively and the
    decoder doesn't have to handle stray entity-id artifacts."""
    if not entity_ids:
        return cover
    # Match (asset_1) or ( asset_1 ) etc., with optional surrounding space
    pattern = (r"\s*\(\s*(?:" + "|".join(re.escape(e) for e in entity_ids) +
               r")\s*\)")
    return re.sub(pattern, "", cover)


def _entity_id_variants(eid):
    """Generate likely surface forms a Pass 2 model might emit for an
    entity id like 'system_1': 'System 1', 'system 1', 'System1',
    'SYSTEM 1', etc. The strip step matches all of these."""
    parts = eid.split("_")
    if len(parts) != 2:
        return [eid]
    head, tail = parts
    forms = [
        eid,                                # system_1
        f"{head} {tail}",                   # system 1
        f"{head.capitalize()} {tail}",      # System 1
        f"{head.upper()} {tail}",           # SYSTEM 1
        f"{head}{tail}",                    # system1
        f"{head.capitalize()}{tail}",       # System1
    ]
    # Deduplicate while preserving order
    seen = set()
    return [f for f in forms if not (f in seen or seen.add(f))]


def _strip_raw_entity_ids(cover, entity_ids, cover_vocab):
    """Pass 2 sometimes leaks raw entity ids ('role_1', 'System 1',
    'Protocol 1') into the cover prose. Replace each variant with the
    cover_vocab term if available; otherwise drop it."""
    if not entity_ids:
        return cover
    # Build a map from variant string -> replacement
    variant_pairs = []
    for eid in sorted(entity_ids, key=len, reverse=True):
        replacement = cover_vocab.get(eid, "")
        if isinstance(replacement, str) and replacement.strip() and \
                replacement.strip().lower() != eid.lower():
            sub = replacement
        else:
            sub = "the relevant component"
        for variant in _entity_id_variants(eid):
            variant_pairs.append((variant, sub))
    # Apply longest-variant-first so 'System 1' matches before 'System'
    variant_pairs.sort(key=lambda x: -len(x[0]))
    for variant, sub in variant_pairs:
        cover = re.sub(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", sub,
                        cover, flags=re.IGNORECASE)
    return cover


# Source-domain vocabulary that should never appear in a cover. If Pass 2
# selected one of these as a cover_vocab value, the cover is broken;
# warn at encode time so the operator can regenerate.
SOURCE_LEAK_VOCAB = {
    "ot_ics": {
        "modbus", "scada", "plc", "rtu", "ied", "interlock", "setpoint",
        "holding register", "holding registers", "register", "registers",
        "safety instrumented system", "sis", "emergency shutdown",
        "shutdown valve", "control loop", "control system", "process bus",
        "engineering workstation", "audit log", "iec 61850", "iec 61511",
        "iec 62443", "nerc cip", "level 1", "level 2", "level 3",
        "firmware", "patch level", "cve", "goose", "hmi",
    },
    "political": {
        "election", "parliament", "ruling party", "opposition", "coalition",
        "ballot", "polling station", "voter turnout", "general strike",
        "approval rating", "interior minister", "embassy", "foreign minister",
    },
    "legal": {
        "plaintiff", "defendant", "court", "deposition", "subpoena",
        "indictment", "tort", "statute", "litigation",
    },
}


def _check_cover_vocab_leaks(cover_vocab, source_kind="ot_ics"):
    """Return list of (entity_id, value) pairs whose cover_vocab value
    contains source-domain vocabulary."""
    leaks = []
    forbidden = SOURCE_LEAK_VOCAB.get(source_kind, set())
    for eid, term in cover_vocab.items():
        if not isinstance(term, str):
            continue
        tlow = term.lower()
        for bad in forbidden:
            if bad in tlow:
                leaks.append((eid, term, bad))
                break
    return leaks


def encode_via_graph(text, passphrase, topic, model="gemma3:4b",
                     extra_ident_terms=None):
    """Method 5 (Graph Shift) encode. Returns the cover document with the
    encrypted recovery key embedded as the existing footer format.

    Unlike Methods 1 and 4, this path does NOT run IdentEncoder before
    Pass 1. The NATO-word placeholders that IdentEncoder emits ('charlie',
    'baker-alpha') leak through the graph and are flagged by frontier
    detectors as phonetic-alphabet artifacts characteristic of industrial
    or military naming. The graph schema's identifiers dict and the
    cover_vocab together cover the same ground without producing
    out-of-domain placeholder words in the cover."""
    ident_map = {}
    graph = llm_extract_graph(text, model)

    # Verify source_vocab covers every entity. If Pass 1 missed entities,
    # warn (the round-trip will be partial) but proceed.
    entity_ids = [e["id"] for e in graph.get("entities", [])
                  if isinstance(e, dict) and "id" in e]
    sv = graph.get("source_vocab", {}) or {}
    missing = [eid for eid in entity_ids if eid not in sv]
    if missing:
        print(f"[!] Graph extraction did not include source_vocab for "
              f"{len(missing)} of {len(entity_ids)} entities: "
              f"{', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}",
              file=sys.stderr)
        print(f"[!] Round-trip recovery will be partial for these entities.",
              file=sys.stderr)

    cover, cover_vocab = llm_generate_cover_from_graph(graph, topic, model)

    # Detect Pass 2 cover_vocab entries that did not actually invent a
    # cover-domain term (e.g. cover_vocab["role_1"] = "role_1"). Warn and
    # exclude these from the round-trip mapping; they will fail to decode
    # but at least the cover does not contain a misleading mapping.
    bad = [eid for eid, term in cover_vocab.items()
           if isinstance(term, str) and term.strip().lower() == eid.lower()]
    if bad:
        print(f"[!] Pass 2 produced placeholder cover_vocab for "
              f"{len(bad)} entities: {', '.join(bad[:5])}",
              file=sys.stderr)

    leaks = _check_cover_vocab_leaks(cover_vocab, source_kind="ot_ics")
    if leaks:
        print(f"[!] Pass 2 cover_vocab leaks source-domain vocabulary: "
              f"{', '.join(f'{e}={v!r}({m})' for e,v,m in leaks[:3])}",
              file=sys.stderr)
        print(f"[!] Cover is likely to be detected. Consider regenerating "
              f"or trying a stronger Pass 2 model.", file=sys.stderr)

    # Strip stray entity-id parentheticals AND raw entity-id mentions
    # that Pass 2 may have emitted despite the prompt instruction.
    cover = _strip_entity_id_parentheticals(cover, entity_ids)
    cover = _strip_raw_entity_ids(cover, entity_ids, cover_vocab)

    key_data = {
        "v": "fc-graph-1.0",
        "ident": ident_map,
        "topic": topic,
        "graph": {k: v for k, v in graph.items() if k != "source_vocab"},
        "source_vocab": graph.get("source_vocab", {}),
        "cover_vocab": cover_vocab,
    }
    return embed_key(cover, key_data, passphrase)


def decode_via_graph(text_with_key, passphrase):
    """Method 5 (Graph Shift) decode. Reverses cover_vocab to entity ids,
    then forward-applies source_vocab to recover source-domain terms."""
    cover, key_data = extract_key(text_with_key, passphrase)
    cover_vocab = key_data.get("cover_vocab", {}) or {}
    source_vocab = key_data.get("source_vocab", {}) or {}
    ident_map = key_data.get("ident", {}) or {}

    # Stage 1: cover-domain term -> entity id placeholder. Sort by descending
    # cover-term length so longer multi-word phrases bind before shorter
    # substrings.
    pairs = sorted(((eid, term) for eid, term in cover_vocab.items()
                    if isinstance(term, str) and term),
                   key=lambda x: -len(x[1]))
    text = cover
    for entity_id, cover_term in pairs:
        pattern = r"(?<!\w)" + re.escape(cover_term) + r"(?!\w)"
        text = re.sub(pattern, f"__{entity_id}__", text,
                       flags=re.IGNORECASE)

    # Stage 2: entity id -> source-domain term
    for entity_id, source_term in source_vocab.items():
        text = text.replace(f"__{entity_id}__", source_term)

    # Stage 3: identifier restore (graph mode skips IdentEncoder so this
    # is a no-op for fc-graph-1.0 keys; kept for forward compatibility
    # in case future variants reintroduce a placeholder pre-pass)
    if ident_map:
        text = IdentEncoder.decode(text, ident_map)
    return text


# ================================================================
# MAPPING VERIFICATION
# ================================================================

def verify_mapping_support(domain_map, cover_text, k=MAPPING_VERIFY_SAMPLES):
    """Spot-check up to k random (src, tgt) pairs from domain_map against
    cover_text. An entry is supported when tgt appears as a substring in the
    lowercased cover. Returns (supported, sampled). sampled == 0 when there
    are no non-identity entries to check."""
    items = [(s, t) for s, t in domain_map.items()
             if isinstance(s, str) and isinstance(t, str) and t and s != t]
    if not items:
        return 0, 0
    sample = random.sample(items, min(k, len(items)))
    cover_lower = cover_text.lower()
    supported = sum(1 for _, t in sample if t.lower() in cover_lower)
    return supported, len(sample)


# ================================================================
# LLM POLISH
# ================================================================

def polish_cover(cover_text, mapping, topic, model):
    """Ask the LLM to rewrite the cover for naturalness while preserving
    every cover-domain term in the mapping. Returns polished text or None
    on any failure. Temperature 0.3 permits stylistic variation without
    hallucinating domain substitutions."""
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    timeout = float(os.environ.get("OLLAMA_TIMEOUT", "120"))
    prompt_prefix = os.environ.get("OLLAMA_PROMPT_PREFIX", "")

    terms = ", ".join(str(v) for v in mapping.values() if v)
    prompt = (f"You are an editor. Rewrite the following text to read more "
              f"naturally as a document about: {topic}\n\n"
              f"Preserve every term from this list exactly as written, "
              f"do not paraphrase or remove them:\n{terms}\n\n"
              f"TEXT:\n{cover_text}\n\n"
              f"Output ONLY the rewritten text. No commentary.")

    if prompt_prefix:
        prompt = prompt_prefix + prompt

    import urllib.request
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                        "options": {"temperature": 0.3}}).encode()
    try:
        req = urllib.request.Request(f"{base}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read())["response"].strip()
        return result if result else None
    except Exception:
        return None


def _polish_with_fallback(cover, mapping, topic, model):
    """Polish cover text and verify mapping integrity. Falls back to the
    original cover if polish fails or drops more than 20% of sampled
    mapping targets."""
    polished = polish_cover(cover, mapping, topic, model)
    if polished is None:
        return cover

    pairs = [(src, tgt) for src, tgt in mapping.items() if src != tgt and tgt]
    if pairs:
        sample = random.sample(pairs, min(5, len(pairs)))
        hits = sum(1 for _, tgt in sample if tgt.lower() in polished.lower())
        if hits < len(sample) * 0.8:
            print("[!] Polish degraded mapping coverage; using unpolished cover.",
                  file=sys.stderr)
            return cover

    return polished


# ================================================================
# CORE PIPELINE
# ================================================================

def encode_document(text, passphrase, topic, backend="static",
                     model="llama3.2:3b", extra_ident_terms=None,
                     polish=False, strict=False, method="domain_shift"):
    """Full encode: ident strip -> domain shift -> embed key.

    method="domain_shift" (default): Methods 1/4 vocabulary substitution.
    method="graph": Method 5 (Graph Shift). Two-pass pipeline that
        decouples cover generation from source text. Backend is forced
        to llm; topic is the cover-domain directive."""
    if method == "graph":
        return encode_via_graph(text, passphrase, topic, model=model,
                                 extra_ident_terms=extra_ident_terms)

    # Stage 1: Strip identifiers
    encoder = IdentEncoder()
    processed, ident_map = encoder.encode(text, extra_ident_terms)

    # Stage 2: Domain shift
    if backend == "llm":
        cover, domain_map = llm_translate(processed, topic, "encode", model)
        if polish:
            cover = _polish_with_fallback(cover, domain_map, topic, model)
        supported, sampled = verify_mapping_support(domain_map, cover)
        if sampled > 0:
            ratio = supported / sampled
            if ratio < MAPPING_VERIFY_THRESHOLD:
                msg = (
                    f"[!] WARNING: mapping verification failed "
                    f"({supported}/{sampled} entries supported in cover).\n"
                    f"[!] The model may have emitted a mapping that does not "
                    f"match the substitutions in the cover.\n"
                    f"[!] Round-trip recovery is likely to fail. "
                    f"Inspect the output file before relying on it."
                )
                print(msg, file=sys.stderr)
                if strict:
                    sys.exit(1)
    else:
        if topic not in DOMAINS:
            print(f"[!] No built-in mapping for '{topic}'. Using 'brewery'.")
            print(f"    For arbitrary topics, use --backend llm")
            topic = "brewery"
        # For static, we only apply the forward half of the mapping
        fwd = OrderedDict(list(DOMAINS[topic].items())[:len(DOMAINS[topic])//2])
        cover = apply_mapping(processed, fwd)
        domain_map = dict(fwd)

    # Stage 3: Build key and embed
    key_data = {
        "v": "fc-1.0",
        "ident": ident_map,
        "domain": domain_map,
        "topic": topic,
    }
    return embed_key(cover, key_data, passphrase)


def decode_document(text_with_key, passphrase, backend="static",
                     model="llama3.2:3b"):
    """Full decode: extract key -> inverse shift -> restore idents.

    Auto-dispatches Method 5 (Graph Shift) when key version is
    fc-graph-1.0; otherwise uses the standard inverse-mapping path."""
    # Peek at the key version without consuming the result so we can
    # dispatch. extract_key handles decryption; if version is graph,
    # delegate to decode_via_graph which re-extracts internally.
    _, key_data_peek = extract_key(text_with_key, passphrase)
    if key_data_peek.get("v") == "fc-graph-1.0":
        return decode_via_graph(text_with_key, passphrase)

    cover, key_data = extract_key(text_with_key, passphrase)
    domain_map = key_data.get("domain", {})
    ident_map = key_data.get("ident", {})

    # Stage 1: Inverse domain shift
    inv = invert_mapping(OrderedDict(domain_map))
    recovered = apply_mapping(cover, inv)

    # Stage 2: Restore identifiers
    recovered = IdentEncoder.decode(recovered, ident_map)

    return recovered


# ================================================================
# SANITIZE MODE
# ================================================================

class Sanitizer:
    """Parameterized abstraction for LLM analysis. No domain shift, no
    readability requirement. Every content token becomes an opaque but
    consistent label. Numeric values shift by a constant derived from
    hash(input_text + timestamp_salt). Math is preserved. Identities
    are gone.

    The LLM sees ASSET_003, PARAM_007, SYS_012. It can reason about
    relationships between them. It can't identify the physical system."""

    CATEGORIES = {
        "system": "SYS",
        "asset": "ASSET",
        "param": "PARAM",
        "zone": "ZONE",
        "role": "ROLE",
        "action": "ACT",
        "std": "STD",
        "alert": "ALERT",
        "log": "LOG",
        "misc": "TOKEN",
    }

    TOKEN_CLASSES = OrderedDict([
        ("system", [
            "Modbus", "Modbus TCP", "Modbus RTU", "EtherNet/IP", "OPC UA",
            "DNP3", "PROFINET", "PROFIBUS", "BACnet", "HART", "WirelessHART",
            "S7comm", "GOOSE", "MMS", "Foundation Fieldbus", "SCADA", "DCS",
            "PLC", "RTU", "IED",
        ]),
        ("asset", [
            "reactor", "boiler", "turbine", "compressor", "pump", "valve",
            "motor", "furnace", "vessel", "tank", "pipeline", "conveyor",
            "generator", "transformer", "breaker", "switch", "relay",
            "controller", "actuator", "sensor", "transmitter",
        ]),
        ("param", [
            "pressure", "temperature", "flow", "level", "speed", "voltage",
            "current", "frequency", "power", "torque", "vibration",
            "humidity", "pH", "conductivity", "viscosity", "density",
            "setpoint", "threshold", "interlock", "limit", "range",
            "register", "registers", "coil", "coils", "holding register",
        ]),
        ("zone", [
            "Level 0", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5",
            "DMZ", "perimeter", "zone", "conduit", "segment", "network",
            "firewall", "gateway", "data diode", "jump host",
        ]),
        ("role", [
            "operator", "engineer", "technician", "manager", "attacker",
            "assessor", "auditor", "administrator", "vendor", "contractor",
            "plant manager", "control engineer",
        ]),
        ("std", [
            "IEC 62443", "IEC 61511", "IEC 61850", "ISO 27001", "ISO 22000",
            "NIST 800-82", "NIST 800-53", "NERC CIP", "ISA 84", "ISA 99",
            "ISA 62443",
        ]),
        ("alert", [
            "alarm", "alert", "notification", "event", "trip", "fault",
            "warning", "emergency", "shutdown",
        ]),
        ("log", [
            "audit log", "event log", "change log", "history", "record",
            "audit trail",
        ]),
    ])

    def __init__(self):
        self._label_counter = {}
        self._token_map = {}
        self._token_map_inv = {}

    def _classify(self, token):
        token_lower = token.lower()
        for category, terms in self.TOKEN_CLASSES.items():
            for term in terms:
                if token_lower == term.lower():
                    return category
        return "misc"

    def _get_label(self, token):
        # Case-sensitive: 'assessor' and 'Assessor' get different labels
        # so round-trip recovery preserves casing exactly.
        if token in self._token_map:
            return self._token_map[token]
        category = self._classify(token)
        prefix = self.CATEGORIES[category]
        self._label_counter[prefix] = self._label_counter.get(prefix, 0) + 1
        label = f"{prefix}_{self._label_counter[prefix]:03d}"
        self._token_map[token] = label
        self._token_map_inv[label] = token
        return label

    @staticmethod
    def _derive_offset(text, salt):
        h = hashlib.sha256(text.encode() + salt.encode()).digest()
        raw = struct.unpack(">I", h[:4])[0]
        return (raw % 9900) + 100

    def sanitize(self, text, salt=None):
        """Replace domain tokens with opaque labels and shift numerics
        by a content-derived offset. Returns (sanitized_text, key_data)."""
        import time
        if salt is None:
            salt = f"fc-{int(time.time() * 1000000)}"
        offset = self._derive_offset(text, salt)

        ident_enc = IdentEncoder()
        processed, ident_map = ident_enc.encode(text)

        all_terms = []
        for terms in self.TOKEN_CLASSES.values():
            all_terms.extend(terms)
        all_terms.sort(key=len, reverse=True)

        result = processed
        used_positions = set()
        replacements = []
        for term in all_terms:
            pattern = r'(?<!\w)' + re.escape(term) + r'(?!\w)'
            for m in re.finditer(pattern, result, re.IGNORECASE):
                s, e = m.start(), m.end()
                if set(range(s, e)) & used_positions:
                    continue
                label = self._get_label(m.group())
                replacements.append((s, e, label))
                used_positions |= set(range(s, e))
        replacements.sort(key=lambda x: x[0], reverse=True)
        for s, e, label in replacements:
            result = result[:s] + label + result[e:]

        def shift_number(match):
            original = match.group()
            try:
                if '.' in original:
                    val = float(original)
                    return f"{val + offset:.{len(original.split('.')[1])}f}"
                return str(int(original) + offset)
            except ValueError:
                return original

        result = re.sub(r'(?<![A-Z_a-z])\b\d+(?:\.\d+)?\b(?!_\d)',
                        shift_number, result)

        key_data = {
            "v": "fc-sanitize-1.0",
            "salt": salt,
            "offset": offset,
            "ident_map": ident_map,
            "token_map": self._token_map_inv,
            "stats": {
                "tokens_replaced": len(self._token_map),
                "identifiers_replaced": len(ident_map),
                "numeric_offset": offset,
            },
        }
        return result, key_data

    @staticmethod
    def desanitize(text, key_data):
        """Recover original text from sanitized version + key."""
        offset = key_data["offset"]
        token_map_inv = key_data["token_map"]
        ident_map = key_data["ident_map"]

        # Unshift numerics first so numbers inside restored compound
        # terms (e.g. "Level 1") are never touched by the unshift.
        def unshift_number(match):
            s = match.group()
            try:
                if '.' in s:
                    val = float(s)
                    return f"{val - offset:.{len(s.split('.')[1])}f}"
                return str(int(s) - offset)
            except ValueError:
                return s

        result = re.sub(r'(?<![A-Z_a-z])\b\d+(?:\.\d+)?\b(?!_\d)',
                        unshift_number, text)

        for label, original in sorted(token_map_inv.items(),
                                       key=lambda x: len(x[0]), reverse=True):
            result = result.replace(label, original)

        result = IdentEncoder.decode(result, ident_map)
        return result


def sanitize_document(text, passphrase):
    """Sanitize a document for LLM analysis. Returns embedded output."""
    sanitized, key_data = Sanitizer().sanitize(text)
    return embed_key(sanitized, key_data, passphrase)


def desanitize_document(text_with_key, passphrase):
    """Recover original from sanitized document."""
    sanitized, key_data = extract_key(text_with_key, passphrase)
    return Sanitizer.desanitize(sanitized, key_data)


# ================================================================
# PROXY MODE
# ================================================================

COVER_SYSTEM_PROMPTS = {
    "brewery": (
        "You are a quality assurance consultant specializing in craft "
        "brewery operations. You help breweries identify and remediate "
        "quality control issues in their fermentation processes, recipe "
        "management systems, and production floor monitoring infrastructure. "
        "Be thorough, technically precise, and focused on product safety "
        "and regulatory compliance (ISO 22000)."
    ),
}


def proxy_chat(passphrase, topic="brewery", api="mock", model=None):
    """Interactive proxy chat. User speaks OT. LLM sees brewery."""
    if topic not in DOMAINS:
        print(f"[!] Static proxy requires built-in domain. Using 'brewery'.")
        topic = "brewery"

    fwd = OrderedDict(list(DOMAINS[topic].items())[:len(DOMAINS[topic])//2])
    inv = invert_mapping(fwd)
    sys_prompt = COVER_SYSTEM_PROMPTS.get(topic, "You are a helpful consultant.")
    cover_history = []
    show_wire = False

    print("=" * 60)
    print("Eris FALSECOLORS Proxy")
    print(f"Cover domain: {topic} | API: {api}")
    print("=" * 60)
    print("Type in your native domain. The LLM sees only the cover.")
    print("Commands: /wire  /quit")
    print("-" * 60)

    while True:
        try:
            msg = input("\n[you] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg == "/quit":
            break
        if msg == "/wire":
            show_wire = not show_wire
            print(f"[wire: {'ON' if show_wire else 'OFF'}]")
            continue

        # Encode
        enc = IdentEncoder()
        processed, ident_map = enc.encode(msg)
        shifted = apply_mapping(processed, fwd)

        # Call LLM
        cover_history.append({"role": "user", "content": shifted})
        response = _call_api(api, model or "claude-sonnet-4-20250514",
                              sys_prompt, cover_history)
        cover_history.append({"role": "assistant", "content": response})

        # Decode
        unshifted = apply_mapping(response, inv)
        restored = IdentEncoder.decode(unshifted, ident_map)

        if show_wire:
            print(f"\n  [WIRE OUT] {shifted[:200]}...")
            print(f"  [WIRE IN]  {response[:200]}...")

        print(f"\n[assistant] > {restored}")


def _call_api(provider, model, system, history):
    """Call LLM API."""
    import urllib.request

    if provider == "mock":
        return _mock_response(history[-1]["content"])

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        body = json.dumps({"model": model, "max_tokens": 2048,
                            "system": system, "messages": history}).encode()
        headers = {"Content-Type": "application/json",
                    "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                    "anthropic-version": "2023-06-01"}
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            data = json.loads(urllib.request.urlopen(req).read())
            return data["content"][0]["text"]
        except Exception as e:
            return f"[API error: {e}]"

    if provider == "openai":
        url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        msgs = [{"role": "system", "content": system}] + history
        body = json.dumps({"model": model, "messages": msgs}).encode()
        headers = {"Content-Type": "application/json",
                    "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"}
        try:
            req = urllib.request.Request(f"{url}/chat/completions",
                                         data=body, headers=headers)
            data = json.loads(urllib.request.urlopen(req).read())
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[API error: {e}]"

    if provider == "ollama":
        url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        msgs = [{"role": "system", "content": system}] + history
        body = json.dumps({"model": model, "messages": msgs,
                            "stream": False}).encode()
        try:
            req = urllib.request.Request(f"{url}/api/chat", data=body,
                                         headers={"Content-Type": "application/json"})
            data = json.loads(urllib.request.urlopen(req).read())
            return data["message"]["content"]
        except Exception as e:
            return f"[LLM error: {e}]"

    return "[Unknown provider]"


def _mock_response(msg):
    m = msg.lower()
    if "quality control" in m or "checkpoint" in m or "deficien" in m:
        return ("The quality checkpoint configuration you described represents "
                "a significant product safety risk. Allowing unauthenticated "
                "parameter writes to the quality controller means any user on "
                "the production floor network could modify carbonation "
                "thresholds without accountability. I recommend implementing "
                "database access authentication immediately, restricting edit "
                "access to authorized personnel, and enabling modification "
                "tracking on all threshold parameters.")
    if "remediat" in m or "correct" in m or "fix" in m or "recommend" in m:
        return ("For remediation I recommend a phased approach. Phase 1: "
                "implement access control rules on the production floor "
                "boundary to restrict unauthorized system access to the "
                "quality controller. Phase 2: enable modification tracking "
                "and activity logging on all recipe parameter changes. "
                "Phase 3: conduct a full system architecture review against "
                "ISO 22000 requirements. The batch rejection gate should be "
                "validated independently of the quality controller.")
    return ("Based on the details provided about the fermentation monitoring "
            "system, there are several areas of concern. The production floor "
            "access controls need strengthening, and the quality controller "
            "threshold management should include authentication and audit "
            "trails.")


# ================================================================
# CAUDLE DISTANCE (SCD)
# ================================================================
# Definition 2.15.2: SCD(D, X) = D_KL( TAD(D) || TAD(X) ).
# TAD is the distribution of cos(e(t_i), e(t_{i+1})) over adjacent
# content tokens, where e is a token embedding. The corpus serves as
# both the embedding space (PPMI co-occurrence vectors) and the
# reference distribution. Pure stdlib, no external models required.

STOPWORDS = frozenset((
    "a an the and or but if then so of to in on at by for with from as is "
    "are was were be been being this that these those it its he she they "
    "we you i me my our your their not no nor do does did have has had "
    "will would should could may might can must about into over under "
    "between than them him her us also such only just very more most some"
).split())

_TOKEN_RE = re.compile(r"[a-z][a-z0-9]+")


def _tokenize_content(text):
    return [t for t in _TOKEN_RE.findall(text.lower())
            if t not in STOPWORDS and len(t) > 1]


def _build_ppmi(tokens, window=2):
    """Sparse PPMI vectors: token -> {context_token: ppmi}."""
    cooc, total = {}, 0
    n = len(tokens)
    for i, w in enumerate(tokens):
        lo, hi = max(0, i - window), min(n, i + window + 1)
        for j in range(lo, hi):
            if j == i:
                continue
            c = tokens[j]
            row = cooc.setdefault(w, {})
            row[c] = row.get(c, 0) + 1
            total += 1
    if total == 0:
        return {}
    margin = {w: sum(row.values()) for w, row in cooc.items()}
    ppmi = {}
    for w, row in cooc.items():
        wm = margin[w]
        out = {}
        for c, n_wc in row.items():
            cm = margin.get(c, 0)
            if cm == 0 or wm == 0:
                continue
            pmi = math.log((n_wc * total) / (wm * cm))
            if pmi > 0:
                out[c] = pmi
        if out:
            ppmi[w] = out
    return ppmi


def _cosine(va, vb):
    if not va or not vb:
        return 0.0
    common = set(va).intersection(vb)
    if not common:
        return 0.0
    dot = sum(va[k] * vb[k] for k in common)
    na = math.sqrt(sum(x * x for x in va.values()))
    nb = math.sqrt(sum(x * x for x in vb.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _adjacent_cosines(tokens, embeddings):
    out = []
    for a, b in zip(tokens, tokens[1:]):
        if a in embeddings and b in embeddings:
            out.append(_cosine(embeddings[a], embeddings[b]))
    return out


def _histogram(values, bins=50, lo=0.0, hi=1.0):
    counts = [0] * bins
    width = (hi - lo) / bins
    for v in values:
        if v < lo:
            v = lo
        elif v >= hi:
            v = hi - 1e-12
        counts[int((v - lo) / width)] += 1
    return counts


def _kl_smoothed(p_counts, q_counts, alpha=1.0):
    k = len(p_counts)
    pt = sum(p_counts) + alpha * k
    qt = sum(q_counts) + alpha * k
    s = 0.0
    for pc, qc in zip(p_counts, q_counts):
        p = (pc + alpha) / pt
        q = (qc + alpha) / qt
        s += p * math.log(p / q)
    return s


def caudle_distance(document_text, corpus_text, bins=50, window=2):
    """Compute SCD(D, X) per Definition 2.15.2.

    Cosine similarities are computed over PPMI vectors built from the
    corpus. Histograms of adjacent-pair cosines are KL-compared with
    Laplace smoothing.
    """
    corpus_tokens = _tokenize_content(corpus_text)
    doc_tokens = _tokenize_content(document_text)
    embeddings = _build_ppmi(corpus_tokens, window=window)

    doc_cos = _adjacent_cosines(doc_tokens, embeddings)
    cor_cos = _adjacent_cosines(corpus_tokens, embeddings)

    result = {
        "doc_tokens": len(doc_tokens),
        "corpus_tokens": len(corpus_tokens),
        "vocab": len(embeddings),
        "doc_pairs": len(doc_cos),
        "corpus_pairs": len(cor_cos),
        "bins": bins,
        "window": window,
    }
    if not doc_cos or not cor_cos:
        result["scd"] = float("inf")
        result["note"] = ("insufficient overlap between document and "
                          "corpus vocabulary; expand the corpus")
        return result

    p = _histogram(doc_cos, bins=bins)
    q = _histogram(cor_cos, bins=bins)
    result["scd"] = _kl_smoothed(p, q)
    result["doc_mean_cos"] = sum(doc_cos) / len(doc_cos)
    result["corpus_mean_cos"] = sum(cor_cos) / len(cor_cos)
    return result


# ================================================================
# DEMO
# ================================================================

def demo():
    SENSITIVE = """CONFIDENTIAL - ENGAGEMENT FINDINGS
Client: [Redacted Chemical Manufacturing]
Assessor: River Caudle, Riverman Enterprises
Date: April 2026

CRITICAL FINDING: Safety Instrumented System Bypass via Modbus TCP

During the assessment of the client's ethylene oxide reactor control loop, the assessor identified that the Safety Instrumented System protecting the reactor overpressure condition accepts unauthenticated Modbus TCP writes to holding registers 40001 through 40016. These registers control the high-pressure interlock setpoints for the emergency shutdown valve on the reactor vessel.

An attacker with network access to the Level 1 control network can modify the interlock threshold from the engineered setpoint of 185 PSI to an arbitrary value without triggering any alarm or audit log entry. The Safety PLC does not validate the source of register writes and does not maintain a change history.

The reactor control system is accessible at 10.10.1.50 on port 502. The SIS network architecture does not comply with IEC 61511 requirements.

This finding has not been disclosed to any party other than the client's plant manager and the assessor's legal counsel."""

    PASSPHRASE = "privateer-2026"

    w = 65
    print()
    print("=" * w)
    print("  Eris FALSECOLORS - Proof of Concept")
    print("  Noncryptographic Semantic Transformation")
    print("=" * w)

    # --- Step 1: Show the sensitive document ---
    print()
    print("[ORIGINAL DOCUMENT - SENSITIVE]")
    print("-" * w)
    print(SENSITIVE)

    # --- Step 2: Encrypt ---
    print()
    print("=" * w)
    print(f"  ENCRYPTING")
    print(f"  Passphrase: '{PASSPHRASE}'")
    print(f"  Topic: 'brewery'")
    print("=" * w)

    output = encode_document(SENSITIVE, PASSPHRASE, "brewery")

    cover_part = output.split(EMBED_MARKER)[0]
    footer_lines = output.split(EMBED_MARKER)[1].strip().split("\n")

    print()
    print("[COVER DOCUMENT - WHAT ANYONE SEES]")
    print("-" * w)
    print(cover_part)
    print()
    print(f"[EMBEDDED KEY - {len(footer_lines)} lines of encrypted base64]")
    print(f"  {footer_lines[0][:60]}...")
    print(f"  (looks like a document tracking reference)")

    # --- Step 3: Decrypt ---
    print()
    print("=" * w)
    print("  DECRYPTING")
    print("=" * w)

    recovered = decode_document(output, PASSPHRASE)

    print()
    print("[RECOVERED DOCUMENT]")
    print("-" * w)
    print(recovered)

    # --- Step 4: Verify ---
    print()
    print("=" * w)
    print("  VERIFICATION")
    print("=" * w)
    if SENSITIVE.strip() == recovered.strip():
        print("  [+] PERFECT RECOVERY")
    else:
        import difflib
        diffs = [l for l in difflib.unified_diff(
            SENSITIVE.splitlines(), recovered.splitlines(), n=0)
            if l.startswith("@@")]
        print(f"  [~] {len(diffs)} minor differences (mapping coverage)")

    # --- Step 5: Wrong passphrase ---
    print()
    try:
        decode_document(output, "wrong-password")
        print("  [!] Should have rejected wrong passphrase")
    except ValueError:
        print("  [+] Wrong passphrase correctly rejected")

    # --- Step 6: Summary ---
    print()
    print("=" * w)
    print("  WHAT AN ADVERSARY SEES")
    print("=" * w)
    print()
    print("  A craft brewery quality audit.")
    print("  Carbonation thresholds. Recipe parameters.")
    print("  A routine quality assurance document.")
    print()
    print("  Nothing about reactors. Nothing about Modbus.")
    print("  Nothing about safety interlocks.")
    print("  Nothing worth investigating.")
    print()
    print("=" * w)
    print("  USAGE")
    print("=" * w)
    print("""
  # Encrypt
  python falsecolors.py encrypt \\
    --source finding.txt \\
    --passphrase "secret" \\
    --topic brewery \\
    --output cover.txt

  # Decrypt
  python falsecolors.py decrypt \\
    --source cover.txt \\
    --passphrase "secret" \\
    --output original.txt

  # Interactive proxy (LLM sees only brewery)
  python falsecolors.py proxy \\
    --passphrase "secret" \\
    --api anthropic

  # Use local LLM for any topic
  python falsecolors.py encrypt \\
    --source finding.txt \\
    --passphrase "secret" \\
    --topic "bumblebee colony management" \\
    --backend llm \\
    --output cover.txt
""")
    print("  The best protection doesn't look like protection.")
    print()


# ================================================================
# CLI
# ================================================================

def main():
    p = argparse.ArgumentParser(
        prog="falsecolors",
        description="Eris FALSECOLORS - Noncryptographic Semantic "
                    "Transformation for Deniable Document Protection",
        epilog="The best protection doesn't look like protection.")

    sub = p.add_subparsers(dest="cmd")

    # encrypt
    e = sub.add_parser("encrypt", help="Encrypt a document")
    e.add_argument("--source", required=True, help="Input file")
    e.add_argument("--passphrase", required=True)
    e.add_argument("--topic", required=True,
                    help="Cover topic (e.g., 'brewery', or any topic with --backend llm)")
    e.add_argument("--output", required=True, help="Output file")
    e.add_argument("--backend", default="static", choices=["static", "llm"])
    e.add_argument("--model", default="llama3.2:3b")
    e.add_argument("--polish", action="store_true",
                    help="Run a naturalness polish pass after LLM translation "
                         "(requires --backend llm; default off)")
    e.add_argument("--strict", action="store_true",
                    help="Treat mapping verification failure as a hard error "
                         "(non-zero exit). Only relevant with --backend llm.")
    e.add_argument("--method", default="domain_shift",
                    choices=["domain_shift", "graph"],
                    help="Encoding method. 'domain_shift' (default) is the "
                         "Method 1/4 vocabulary substitution path. 'graph' is "
                         "Method 5 (Graph Shift): a two-pass pipeline that "
                         "extracts the source as a relational graph then "
                         "generates a native cover-domain document from the "
                         "graph alone. Implies --backend llm.")

    # decrypt
    d = sub.add_parser("decrypt", help="Decrypt a cover document")
    d.add_argument("--source", required=True)
    d.add_argument("--passphrase", required=True)
    d.add_argument("--output", required=True)

    # proxy
    x = sub.add_parser("proxy", help="Interactive LLM proxy")
    x.add_argument("--passphrase", required=True)
    x.add_argument("--topic", default="brewery")
    x.add_argument("--api", default="mock",
                    choices=["anthropic", "openai", "ollama", "mock"])
    x.add_argument("--model", default=None)

    # sanitize
    s = sub.add_parser("sanitize",
        help="Strip identities, preserve math, for LLM analysis")
    s.add_argument("--source", required=True)
    s.add_argument("--passphrase", required=True)
    s.add_argument("--output", required=True)

    # desanitize
    ds = sub.add_parser("desanitize", help="Recover from sanitized document")
    ds.add_argument("--source", required=True)
    ds.add_argument("--passphrase", required=True)
    ds.add_argument("--output", required=True)

    # measure
    m = sub.add_parser("measure",
                        help="Compute Caudle Distance (SCD) of a cover "
                             "document against a native cover-domain corpus")
    m.add_argument("--source", required=True, help="Cover document file")
    m.add_argument("--corpus", required=True,
                    help="Native cover-domain corpus file (plain text)")
    m.add_argument("--bins", type=int, default=50,
                    help="Histogram bins for the cosine TAD")
    m.add_argument("--window", type=int, default=2,
                    help="Context window for PPMI co-occurrence")

    # demo
    sub.add_parser("demo", help="Run full demonstration")

    args = p.parse_args()

    if args.cmd == "encrypt":
        text = Path(args.source).read_text()
        backend = args.backend
        if args.method == "graph":
            backend = "llm"
        out = encode_document(text, args.passphrase, args.topic,
                               backend, args.model,
                               polish=args.polish, strict=args.strict,
                               method=args.method)
        Path(args.output).write_text(out)
        print(f"[+] Encrypted: {args.source} -> {args.output}")
        print(f"    Recipient needs only the file + passphrase.")

    elif args.cmd == "decrypt":
        text = Path(args.source).read_text()
        out = decode_document(text, args.passphrase)
        Path(args.output).write_text(out)
        print(f"[+] Decrypted: {args.source} -> {args.output}")

    elif args.cmd == "proxy":
        proxy_chat(args.passphrase, args.topic, args.api, args.model)

    elif args.cmd == "sanitize":
        text = Path(args.source).read_text()
        out = sanitize_document(text, args.passphrase)
        Path(args.output).write_text(out)
        print(f"[+] Sanitized: {args.source} -> {args.output}")
        print(f"    Safe for LLM analysis. Math preserved. Identities gone.")

    elif args.cmd == "desanitize":
        text = Path(args.source).read_text()
        out = desanitize_document(text, args.passphrase)
        Path(args.output).write_text(out)
        print(f"[+] Desanitized: {args.source} -> {args.output}")

    elif args.cmd == "measure":
        doc = Path(args.source).read_text()
        corpus = Path(args.corpus).read_text()
        r = caudle_distance(doc, corpus, bins=args.bins, window=args.window)
        scd = r["scd"]
        scd_str = "inf" if scd == float("inf") else f"{scd:.4f}"
        print(f"Caudle Distance (SCD): {scd_str} nats")
        print(f"  document tokens: {r['doc_tokens']}, "
              f"adjacent pairs scored: {r['doc_pairs']}")
        print(f"  corpus tokens:   {r['corpus_tokens']}, "
              f"adjacent pairs scored: {r['corpus_pairs']}")
        print(f"  shared embedding vocab: {r['vocab']}")
        if "doc_mean_cos" in r:
            print(f"  mean adjacent cosine: doc={r['doc_mean_cos']:.3f} "
                  f"corpus={r['corpus_mean_cos']:.3f}")
        if "note" in r:
            print(f"  note: {r['note']}")

    elif args.cmd == "demo":
        demo()

    else:
        p.print_help()


if __name__ == "__main__":
    main()
