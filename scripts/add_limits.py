with open(r"skelion_agent/chat_routes.py", "r", encoding="utf-8") as f:
    text = f.read()

limits_endpoints = """
@router.get("/limits/status")
def get_limits_status(
    org: Organization = Depends(get_org_from_jwt),
):
    \"\"\"Retrieve full breakdown of quotas, windows, and autofix tokens.\"\"\"
    return get_token_status(org)


@router.post("/limits/toggle-enforcement")
def toggle_limit_enforcement(
    body: Dict[str, Any],
    org: Organization = Depends(get_org_from_jwt),
    db: Session = Depends(get_db),
):
    \"\"\"Toggle sliding window limit enforcement on/off.\"\"\"
    enabled = body.get("enabled", True)
    org.limit_enforcement_enabled = enabled
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"status": "ok", "limit_enforcement_enabled": org.limit_enforcement_enabled}
"""

target = '@router.get("/conversations")'
if target in text:
    text = text.replace(target, limits_endpoints + "\n\n" + target, 1)
    with open(
        r"skelion_agent/chat_routes.py", "w", encoding="utf-8", newline="\r\n"
    ) as f:
        f.write(text)
    print("Added limits endpoints successfully!")
else:
    print("Target not found!")
