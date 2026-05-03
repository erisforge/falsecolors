#!/usr/bin/env python3
# Eris FALSECOLORS
# Copyright (C) 2026 River Caudle, Riverman Enterprises
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
# Commercial use requires a separate license from Riverman Enterprises.

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
from collections import OrderedDict
from pathlib import Path


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

def llm_translate(text, topic, direction="encode", model="llama3.2:3b"):
    """Use local LLM for domain translation. Returns (text, mapping)."""
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    if direction == "encode":
        prompt = (f"You are a domain translation engine. Rewrite the following "
                  f"text so it reads as a document about: {topic}\n\n"
                  f"Replace every domain-specific term with an equivalent from "
                  f"the target topic. Preserve every logical relationship.\n\n"
                  f"After the rewritten text, output ONLY a JSON object on a "
                  f"new line mapping every substitution: "
                  f'{{\"original\": \"replacement\", ...}}\n\n'
                  f"SOURCE:\n{text}")
    else:
        prompt = (f"Reverse the following domain substitutions in this text. "
                  f"Apply these mappings:\n{json.dumps(text[1])}\n\n"
                  f"TEXT:\n{text[0]}")

    import urllib.request
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                        "options": {"temperature": 0.1}}).encode()
    try:
        req = urllib.request.Request(f"{base}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=120)
        response = json.loads(resp.read())["response"]

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
    except ConnectionRefusedError:
        print(f"[!] Cannot connect to Ollama at {base}")
        print(f"    Install: curl -fsSL https://ollama.com/install.sh | sh")
        print(f"    Pull:    ollama pull {model}")
        sys.exit(1)


# ================================================================
# CORE PIPELINE
# ================================================================

def encode_document(text, passphrase, topic, backend="static",
                     model="llama3.2:3b", extra_ident_terms=None):
    """Full encode: ident strip -> domain shift -> embed key."""
    # Stage 1: Strip identifiers
    encoder = IdentEncoder()
    processed, ident_map = encoder.encode(text, extra_ident_terms)

    # Stage 2: Domain shift
    if backend == "llm":
        cover, domain_map = llm_translate(processed, topic, "encode", model)
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
    """Full decode: extract key -> inverse shift -> restore idents."""
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
        out = encode_document(text, args.passphrase, args.topic,
                               args.backend, args.model)
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
