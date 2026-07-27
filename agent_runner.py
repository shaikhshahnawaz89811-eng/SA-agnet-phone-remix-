#!/usr/bin/env python3
"""
agent_runner.py (multi-provider version)
------------------------------------------
Ab teeno provider support karta hai: Claude (Anthropic), ChatGPT
(OpenAI), Groq. Sirf `requests` package chahiye -- koi bhaari SDK
install nahi karni (Termux-friendly).

Kya karta hai (ek run = ek bug-fix cycle, pehle jaisa hi):
  1. STATE.md se agla [OPEN] bug uthata hai.
  2. Sirf relevant file(s) provider ko bhejta hai (Rule 20).
  3. Response ko temp-copy par validate karta hai, sirf clean-pass
     par asli file update hoti hai (Rule 19).
  4. Git commit + STATE.md me [FIXED] mark.

KEY / PROVIDER BADALNA (bar-bar):
  python agent_runner.py --setup
  Yeh chhota menu dikhayega -- provider chuno (claude/chatgpt/groq),
  naya key do, save ho jaayega `agent_config.json` me (isi folder
  me). Agli baar seedha `python agent_runner.py` chalane par wahi
  saved provider+key use hoga -- jab tak dobara --setup na chalao.

  Provider sirf isi run ke liye badalna ho (permanent save kiye
  bina), to:
  python agent_runner.py --provider groq --key gsk_xxx

Setup (ek baar):
  pkg install python git -y      # Termux
  pip install requests --break-system-packages
  python agent_runner.py --setup
"""
import os
import re
import sys
import json
import subprocess
import tempfile
import py_compile
from datetime import datetime

try:
    import requests
except ImportError:
    print("requests package missing. Chalao: pip install requests --break-system-packages")
    sys.exit(1)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(REPO_DIR, "STATE.md")
CONFIG_PATH = os.path.join(REPO_DIR, "agent_config.json")

DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-6",
    "chatgpt": "gpt-5.1",
    "groq": "llama-3.3-70b-versatile",
}

PROVIDER_LABELS = {"claude": "Claude (Anthropic)", "chatgpt": "ChatGPT (OpenAI)", "groq": "Groq"}


# ------------------------------------------------------------ config
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"provider": None, "keys": {}, "models": dict(DEFAULT_MODELS)}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    # Config me raw API key hoti hai -- kabhi git me commit na ho
    gitignore = os.path.join(REPO_DIR, ".gitignore")
    line = "agent_config.json\n"
    existing = ""
    if os.path.exists(gitignore):
        with open(gitignore, "r", encoding="utf-8") as f:
            existing = f.read()
    if "agent_config.json" not in existing:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write(("\n" if existing and not existing.endswith("\n") else "") + line)


def interactive_setup(cfg):
    print("\n----- Provider Setup -----")
    print("1. Claude (Anthropic)")
    print("2. ChatGPT (OpenAI)")
    print("3. Groq")
    choice = input("Kaunsa provider? (1/2/3): ").strip()
    provider = {"1": "claude", "2": "chatgpt", "3": "groq"}.get(choice)
    if not provider:
        print("Invalid choice, kuch save nahi hua.")
        return cfg
    key = input(f"{PROVIDER_LABELS[provider]} ka API key daalo: ").strip()
    if not key:
        print("Khaali key -- kuch save nahi hua.")
        return cfg
    model = input(f"Model naam (Enter = default '{DEFAULT_MODELS[provider]}'): ").strip()
    cfg["provider"] = provider
    cfg.setdefault("keys", {})[provider] = key
    cfg.setdefault("models", dict(DEFAULT_MODELS))
    cfg["models"][provider] = model or DEFAULT_MODELS[provider]
    save_config(cfg)
    print(f"Saved. Ab default provider: {PROVIDER_LABELS[provider]} (model: {cfg['models'][provider]})")
    print("Change karna ho to dobara: python agent_runner.py --setup\n")
    return cfg


def resolve_provider_and_key(cfg, args):
    """Priority: --provider/--key CLI args > saved config > env vars."""
    provider = args.get("provider") or cfg.get("provider")
    if not provider:
        return None, None, None
    key = args.get("key") or cfg.get("keys", {}).get(provider) or os.environ.get(f"{provider.upper()}_API_KEY")
    model = args.get("model") or cfg.get("models", {}).get(provider, DEFAULT_MODELS.get(provider))
    return provider, key, model


def parse_args(argv):
    args = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--setup":
            args["setup"] = True
        elif argv[i] == "--provider" and i + 1 < len(argv):
            args["provider"] = argv[i + 1]
            i += 1
        elif argv[i] == "--key" and i + 1 < len(argv):
            args["key"] = argv[i + 1]
            i += 1
        elif argv[i] == "--model" and i + 1 < len(argv):
            args["model"] = argv[i + 1]
            i += 1
        i += 1
    return args


# --------------------------------------------------------- providers
def call_claude(key, model, system_prompt, user_prompt):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 4000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def call_openai_compatible(base_url, key, model, system_prompt, user_prompt):
    """ChatGPT (OpenAI) aur Groq dono OpenAI-compatible /chat/completions
    format use karte hai -- ek hi function dono ke liye."""
    resp = requests.post(
        base_url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_ai(provider, key, model, system_prompt, user_prompt):
    if provider == "claude":
        return call_claude(key, model, system_prompt, user_prompt)
    if provider == "chatgpt":
        return call_openai_compatible("https://api.openai.com/v1/chat/completions", key, model, system_prompt, user_prompt)
    if provider == "groq":
        return call_openai_compatible("https://api.groq.com/openai/v1/chat/completions", key, model, system_prompt, user_prompt)
    raise ValueError(f"Unknown provider: {provider}")


# --------------------------------------------------------- STATE.md
def read_state():
    if not os.path.exists(STATE_PATH):
        print(f"STATE.md nahi mila yahan: {STATE_PATH}")
        sys.exit(1)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def write_state(content):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def next_open_bug(state_text):
    section = state_text.split("## 7.", 1)[-1].split("## 8.", 1)[0]
    for line in section.splitlines():
        if "[OPEN]" in line and "BUG-" in line:
            m = re.search(r"BUG-(\d+)", line)
            if m:
                return f"BUG-{m.group(1)}", line.strip()
    return None, None


def extract_bug_block(state_text, bug_id):
    lines = state_text.split("## 7.", 1)[-1].split("## 8.", 1)[0].splitlines()
    out, capture = [], False
    for line in lines:
        if bug_id in line and "**" in line:
            capture = True
        elif capture and re.match(r"^\d+\.\s+\*\*\[", line):
            break
        if capture:
            out.append(line)
    return "\n".join(out).strip()


def guess_target_files(bug_text):
    return sorted(set(re.findall(r"`(core/[a-zA-Z_]+\.py|main\.py)`", bug_text)))


def parse_file_blocks(ai_text):
    pattern = re.compile(r"### FILE:\s*(.+?)\n(.*?)### END FILE", re.DOTALL)
    out = {}
    for m in pattern.finditer(ai_text):
        rel_path = m.group(1).strip()
        content = m.group(2).strip()

        if content.startswith("```python"):
            content = content[len("```python"):].lstrip()
        elif content.startswith("```"):
            content = content[3:].lstrip()

        if content.endswith("```"):
            content = content[:-3].rstrip()

        out[rel_path] = content
    return out

def validate_and_write(rel_path, content):
    full_path = os.path.join(REPO_DIR, rel_path)
    if rel_path.endswith(".py"):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            py_compile.compile(tmp_path, doraise=True)
        except py_compile.PyCompileError as e:
            os.unlink(tmp_path)
            return False, f"Syntax error, file NOT written: {e.exc_value}"
        os.unlink(tmp_path)
    os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True, "written"


def git_commit(message):
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR)
    subprocess.run(["git", "commit", "-m", message], cwd=REPO_DIR)


def mark_bug_fixed(state_text, bug_line, bug_id, provider):
    new_line = bug_line.replace("[OPEN]", "[FIXED]")
    state_text = state_text.replace(bug_line, new_line)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_entry = f"- **[{ts}]** — {bug_id} fixed by agent_runner.py (provider: {provider}), committed to git.\n"
    marker = "## 9. Session Log (append-only, purana kabhi mat hatao)\n"
    state_text = state_text.replace(marker, marker + log_entry)
    return state_text


# --------------------------------------------------------------- main
def main():
    args = parse_args(sys.argv[1:])
    cfg = load_config()

    if args.get("setup") or not cfg.get("provider"):
        cfg = interactive_setup(cfg)
        if args.get("setup"):
            return  # --setup ka matlab sirf key/provider change karna tha, bug-fix run nahi

    provider, key, model = resolve_provider_and_key(cfg, args)
    if not provider or not key:
        print("Koi provider/key set nahi hai. Chalao: python agent_runner.py --setup")
        return

    print(f"Provider: {PROVIDER_LABELS.get(provider, provider)} (model: {model})")

    state_text = read_state()
    bug_id, bug_line = next_open_bug(state_text)
    if not bug_id:
        print("Koi [OPEN] bug nahi mila STATE.md me.")
        return

    bug_text = extract_bug_block(state_text, bug_id)
    target_files = guess_target_files(bug_text)
    if not target_files:
        print(f"{bug_id}: file-path STATE.md me clearly nahi mila.")
        return

    print(f"Fixing {bug_id} ...")
    files_content = {}
    for rel in target_files:
        p = os.path.join(REPO_DIR, rel)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                files_content[rel] = f.read()

    system_prompt = (
        "Tum SA Agent (Python/Termux CLI project) ka ek bug fix kar rahe ho. "
        "Rule 10 (correctness), Rule 19 (copy-first/no live-file risk), "
        "Rule 21 (chhota function, no extra line, no dead loop) follow karo. "
        "Sirf diye gaye bug fix karo, kuch aur unrelated mat badlo. "
        "Reply SIRF is format me, har badli hui file ke liye:\n"
        "### FILE: relative/path.py\n<poora naya file content>\n### END FILE\n"
        "Koi extra prose iske bahar mat likho."
    )
    file_blocks = "\n\n".join(f"### FILE: {p}\n{c}" for p, c in files_content.items())
    user_prompt = f"Bug to fix ({bug_id}):\n{bug_text}\n\nCurrent file(s):\n{file_blocks}"

    try:
        ai_text = call_ai(provider, key, model, system_prompt, user_prompt)
    except Exception as e:
        print(f"API call fail hui (limit/network/key ho sakta hai): {e}")
        print("Kuch likha nahi gaya -- safe hai. Provider/key badalne ke liye: python agent_runner.py --setup")
        return

    new_files = parse_file_blocks(ai_text)
    if not new_files:
        print("AI ne '### FILE:' block nahi diya -- kuch likha nahi gaya. Raw reply:")
        print(ai_text[:800])
        return

    all_ok = True
    for rel, content in new_files.items():
        ok, msg = validate_and_write(rel, content)
        print(f"  {rel}: {msg}")
        if not ok:
            all_ok = False

    if all_ok:
        git_commit(f"agent_runner ({provider}): fix {bug_id}")
        state_text = mark_bug_fixed(state_text, bug_line, bug_id, provider)
        write_state(state_text)
        print(f"{bug_id} fixed, committed, STATE.md updated.")
    else:
        print("Kuch file(s) validate fail hui -- asli file untouched, bug abhi bhi [OPEN] rahega.")


if __name__ == "__main__":
    main()

