import os
import sys

sys.path.insert(0, os.path.abspath("."))

import json
import time
import httpx

BASE_URL = "http://127.0.0.1:8003"
HEADERS = {"Authorization": "Bearer dev", "Content-Type": "application/json"}

results = []

def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    results.append({"name": name, "passed": passed, "detail": detail})

def run_tests():
    print("=" * 65)
    print("      SKELION / HELIOS COMPREHENSIVE DEEP SYSTEM AUDIT")
    print("=" * 65)

    with httpx.Client(timeout=35.0) as client:
        # 1. Health & Limits Status
        try:
            r = client.get(f"{BASE_URL}/v1/limits/status", headers=HEADERS)
            data = r.json()
            ok = r.status_code == 200 and "coding_tokens" in data and "autofix_tokens" in data
            record("1. Limits Status Endpoint", ok, f"Plan={data.get('plan')}, AutofixTokens={data.get('autofix_tokens', {}).get('remaining')}")
        except Exception as e:
            record("1. Limits Status Endpoint", False, str(e))

        # 2. Model Pacing & Deduct Token Multipliers
        for test_model in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "free-tier-agent", "unknown-fallback-model"]:
            try:
                r = client.post(
                    f"{BASE_URL}/v1/chat",
                    headers=HEADERS,
                    json={"messages": [{"role": "user", "content": "ping"}], "model": test_model}
                )
                record(f"2. Model Acceptance: {test_model}", r.status_code == 200, f"HTTP {r.status_code}")
            except Exception as e:
                record(f"2. Model Acceptance: {test_model}", False, str(e))

        # 3. Chat Streaming & Reasoning (SSE)
        try:
            events_seen = set()
            text_received = []
            with client.stream(
                "POST",
                f"{BASE_URL}/v1/chat",
                headers=HEADERS,
                json={"messages": [{"role": "user", "content": "Explain what 1+1 equals in one short sentence."}], "model": "openai/gpt-oss-120b"}
            ) as stream:
                for line in stream.iter_lines():
                    if line.startswith("event: "):
                        events_seen.add(line.replace("event: ", "").strip())
                    elif line.startswith("data: "):
                        try:
                            d = json.loads(line.replace("data: ", ""))
                            if "text" in d:
                                text_received.append(d["text"])
                        except:
                            pass
            full_text = "".join(text_received).strip()
            ok = ("start" in events_seen or "thinking" in events_seen) and len(full_text) > 0
            record("3. Streaming SSE with Reasoning", ok, f"Events={list(events_seen)}, TextLen={len(full_text)}")
        except Exception as e:
            record("3. Streaming SSE with Reasoning", False, str(e))

        # 4. Autonomous File Creation on Disk
        target_file = "scratch/test_deep_tool.py"
        if os.path.exists(target_file):
            os.remove(target_file)
        try:
            r = client.post(
                f"{BASE_URL}/v1/chat",
                headers=HEADERS,
                json={
                    "messages": [{"role": "user", "content": f"Please write a python module {target_file} that defines greet(name) returning 'Hello ' + name."}],
                    "model": "openai/gpt-oss-120b"
                }
            )
            time.sleep(1)
            file_exists = os.path.exists(target_file)
            content = ""
            if file_exists:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()
            ok = file_exists and "def greet" in content
            record("4. Autonomous File Materialization", ok, f"File={target_file}, Exists={file_exists}, HasGreet={'def greet' in content}")
        except Exception as e:
            record("4. Autonomous File Materialization", False, str(e))

        # 5. Tool Call Verification (edit_file)
        try:
            emitted_tools = []
            with client.stream(
                "POST",
                f"{BASE_URL}/v1/chat",
                headers=HEADERS,
                json={
                    "messages": [{"role": "user", "content": f"Create a helper in scratch/math_sub.py that subtracts numbers."}],
                    "model": "openai/gpt-oss-120b"
                }
            ) as stream:
                for line in stream.iter_lines():
                    if line.startswith("data: "):
                        try:
                            d = json.loads(line.replace("data: ", ""))
                            if d.get("name") in ["edit_file", "create_file"]:
                                emitted_tools.append(d)
                        except:
                            pass
            ok = len(emitted_tools) > 0 and "scratch/math_sub.py" in emitted_tools[0].get("args", {}).get("path", "")
            record("5. Tool Call Generation (edit_file)", ok, f"ToolCalls={len(emitted_tools)}, Path={emitted_tools[0].get('args', {}).get('path') if emitted_tools else None}")
        except Exception as e:
            record("5. Tool Call Generation (edit_file)", False, str(e))

        # 6. Autonomous GitHub Bot PR Generation
        try:
            r = client.post(
                f"{BASE_URL}/v1/github/create-autofix-pr",
                headers=HEADERS,
                json={
                    "incident_id": "deep_test_incident",
                    "repo": "adity/helios",
                    "target_path": "src/controllers/checkout.js",
                    "pr_title": "Automated Deep Test Fix PR"
                }
            )
            data = r.json()
            ok = r.status_code == 200 and data.get("status") == "success" and "pull" in data.get("pr_url", "")
            record("6. GitHub PR Bot Creation", ok, f"PR={data.get('pr_url')}, Branch={data.get('branch')}")
        except Exception as e:
            record("6. GitHub PR Bot Creation", False, str(e))

        # 7. Incidents Retrieval
        try:
            r = client.get(f"{BASE_URL}/v1/incidents", headers=HEADERS)
            data = r.json()
            incidents = data.get("incidents", [])
            ok = r.status_code == 200 and isinstance(incidents, list)
            record("7. Incidents Feed API", ok, f"TotalIncidents={len(incidents)}")
        except Exception as e:
            record("7. Incidents Feed API", False, str(e))

        # 8. Autofix Suggestions Feed
        try:
            r = client.get(f"{BASE_URL}/v1/autofix/suggestions", headers=HEADERS)
            data = r.json()
            suggestions = data.get("suggestions", [])
            ok = r.status_code == 200 and "autofix_tokens_remaining" in data
            record("8. Autofix Suggestions Feed", ok, f"SuggestionsCount={len(suggestions)}, Tokens={data.get('autofix_tokens_remaining')}")
        except Exception as e:
            record("8. Autofix Suggestions Feed", False, str(e))

        # 9. Apply Autofix Patch
        try:
            # First create or find an incident to apply
            inc_id = "inc_test_apply_fix"
            from sqlmodel import Session
            from skelion_agent.database import get_engine
            from skelion_agent.models import Incident
            with Session(get_engine()) as db:
                existing = db.get(Incident, inc_id)
                if not existing:
                    new_inc = Incident(
                        id=inc_id,
                        org_id="org_default",
                        route_path="/api/test_apply",
                        http_method="POST",
                        status_code=500,
                        error_summary="Test error for autofix",
                        fingerprint="fp_apply_test_123",
                        status="analyzing"
                    )
                    db.add(new_inc)
                    db.commit()

            r = client.post(
                f"{BASE_URL}/v1/autofix/apply",
                headers=HEADERS,
                json={"incident_id": inc_id}
            )
            data = r.json()
            ok = r.status_code == 200 and data.get("status") == "applied"
            record("9. Apply Autofix Patch", ok, f"Status={data.get('status')}, RemainingTokens={data.get('autofix_tokens_remaining')}")
        except Exception as e:
            record("9. Apply Autofix Patch", False, str(e))

        # 10. Conversation Lifecycle (Create -> List -> Get -> Delete)
        try:
            # Create conversation via chat
            r = client.post(
                f"{BASE_URL}/v1/chat",
                headers=HEADERS,
                json={"messages": [{"role": "user", "content": "Lifecycle test conversation"}], "model": "free-tier-agent"}
            )
            conv_id = None
            for line in r.iter_lines():
                if "conversation_id" in line:
                    try:
                        d = json.loads(line.replace("data: ", ""))
                        conv_id = d.get("conversation_id")
                        if conv_id:
                            break
                    except:
                        pass

            if not conv_id:
                # Get first conversation
                r_list = client.get(f"{BASE_URL}/v1/conversations", headers=HEADERS)
                convs = r_list.json()
                if convs:
                    conv_id = convs[0]["id"]

            r_msgs = client.get(f"{BASE_URL}/v1/conversations/{conv_id}/messages", headers=HEADERS)
            msgs_ok = r_msgs.status_code == 200 and len(r_msgs.json()) > 0

            r_del = client.delete(f"{BASE_URL}/v1/conversations/{conv_id}", headers=HEADERS)
            del_ok = r_del.status_code == 200

            record("10. Conversation Lifecycle & Delete", msgs_ok and del_ok, f"ConvID={conv_id}, MsgsRetrieved={len(r_msgs.json())}, Deleted={del_ok}")
        except Exception as e:
            record("10. Conversation Lifecycle & Delete", False, str(e))

    # 11. VS Code Extension Bundle Verification
    ext_src = "skelion_vscode_extension/out/extension.js"
    ext_installed = os.path.expanduser("~/.vscode/extensions/adity.skelion-vscode-0.1.0/out/extension.js")
    
    ok_src = os.path.exists(ext_src) and os.path.getsize(ext_src) > 100000
    ok_inst = os.path.exists(ext_installed) and os.path.getsize(ext_installed) > 100000
    record("11. VS Code Compiled Extension Bundle", ok_src, f"Path={ext_src}, Size={os.path.getsize(ext_src) if ok_src else 0} bytes")
    record("12. VS Code Installed Extension Deploy", ok_inst, f"Path={ext_installed}, Size={os.path.getsize(ext_installed) if ok_inst else 0} bytes")

    # 12. Check extension event handlers in bundle
    with open(ext_src, "r", encoding="utf-8") as f:
        bundle_content = f.read()

    required_actions = [
        "sendPrompt", "applyDiff", "applyAutofix", "deleteConversation",
        "fetchIncidents", "fetchSuggestions", "createGitHubPR", "openExternalPR"
    ]
    missing = [a for a in required_actions if a not in bundle_content]
    record("13. Webview Actions & Event Handlers", len(missing) == 0, f"All {len(required_actions)} Present: {len(missing) == 0}")

    print("=" * 65)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    print(f"DEEP AUDIT RESULTS: {passed_count}/{total_count} PASSED ({(passed_count/total_count)*100:.1f}%)")
    print("=" * 65)

    if passed_count < total_count:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
