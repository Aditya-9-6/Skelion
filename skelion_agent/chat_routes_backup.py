with open("skelion_agent/chat_routes.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

old_sug = """    # Query only unresolved incidents for the active org or default org
    incidents = db.exec(
        select(Incident)
        .where(
            ((Incident.org_id == org.id) | (Incident.org_id == "org_default") | (Incident.org_id == None)),
            Incident.status != "resolved"
        )
        .order_by(Incident.last_seen_at.desc())
        .limit(10)
    ).all()"""

new_sug = """    # Query only unresolved incidents for the active org or default org
    incidents = db.exec(
        select(Incident)
        .where(
            ((Incident.org_id == org.id) | (Incident.org_id == "org_default") | (Incident.org_id == None)),
            Incident.status != "resolved"
        )
        .order_by(Incident.last_seen_at.desc())
        .limit(10)
    ).all()
    if not incidents:
        # Fallback to any active unresolved edge crash in database
        incidents = db.exec(
            select(Incident)
            .where(Incident.status != "resolved")
            .order_by(Incident.last_seen_at.desc())
            .limit(10)
        ).all()"""

assert old_sug in text, "old_sug not found!"
text = text.replace(old_sug, new_sug, 1)

with open("skelion_agent/chat_routes.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated fallback in get_autofix_suggestions!")
