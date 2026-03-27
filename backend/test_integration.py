"""
Integration test: full user workflow simulation.
Tests the complete end-to-end flow without AI service calls.
Run with: python3 test_integration.py
"""
import sys
import httpx

BASE = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, timeout=10.0)

passed = 0
failed = 0
results = []


def step(name: str, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        results.append(f"  ✅ {name}")
    except Exception as e:
        failed += 1
        results.append(f"  ❌ {name}: {e}")


# ═══════════════════════════════════════════════════════
# Flow 1: First-time setup → Login → Full project lifecycle
# ═══════════════════════════════════════════════════════

state = {}


def flow1_setup():
    r = client.post("/api/auth/setup", json={"username": "integ_admin", "password": "integ_pass_123"})
    assert r.status_code == 200, f"Setup failed: {r.status_code}"
    state["token"] = r.json()["access_token"]
    state["headers"] = {"Authorization": f"Bearer {state['token']}"}


step("Flow1: Admin setup", flow1_setup)


def flow1_login():
    r = client.post("/api/auth/login", json={"username": "integ_admin", "password": "integ_pass_123"})
    assert r.status_code == 200
    state["token"] = r.json()["access_token"]
    state["headers"] = {"Authorization": f"Bearer {state['token']}"}

    me = client.get("/api/auth/me", headers=state["headers"]).json()
    assert me["username"] == "integ_admin"
    assert me["is_admin"] is True


step("Flow1: Login and verify identity", flow1_login)


def flow1_configure_ai():
    h = state["headers"]
    r = client.post("/api/settings/ai", headers=h, json={
        "name": "OpenAI GPT-4",
        "provider_type": "openai",
        "api_key": "sk-test-integration-key",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4",
        "priority": 1,
    })
    assert r.status_code == 201, f"AI config create failed: {r.text}"
    state["ai_config_id"] = r.json()["id"]

    r2 = client.post("/api/settings/ai", headers=h, json={
        "name": "Backup DeepSeek",
        "provider_type": "deepseek",
        "api_key": "sk-backup-key",
        "base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-chat",
        "priority": 2,
    })
    assert r2.status_code == 201

    configs = client.get("/api/settings/ai", headers=h).json()
    assert len(configs) == 2, f"Expected 2 configs, got {len(configs)}"


step("Flow1: Configure AI providers (primary + backup)", flow1_configure_ai)


def flow1_create_project():
    h = state["headers"]
    r = client.post("/api/projects", headers=h, json={
        "title": "末世求生：觉醒之路",
        "genre": "末世",
        "target_platform": "番茄小说",
        "target_word_count": 300000,
    })
    assert r.status_code == 201, f"Create project failed: {r.text}"
    data = r.json()
    assert data["status"] == "idle"
    assert data["chapter_count"] == 0
    state["project_id"] = data["id"]

    projects = client.get("/api/projects", headers=h).json()
    assert len(projects) == 1
    assert projects[0]["title"] == "末世求生：觉醒之路"


step("Flow1: Create project", flow1_create_project)


def flow1_check_initial_state():
    h = state["headers"]
    pid = state["project_id"]

    ws = client.get(f"/api/projects/{pid}/generate/status", headers=h).json()
    assert ws["current_state"] == "idle"
    assert ws["current_chapter_no"] == 0

    chapters = client.get(f"/api/projects/{pid}/chapters", headers=h).json()
    assert chapters == []

    knowledge = client.get(f"/api/projects/{pid}/knowledge", headers=h).json()
    assert knowledge == []


step("Flow1: Verify initial state (idle, no chapters, no knowledge)", flow1_check_initial_state)


def flow1_set_outline_and_confirm():
    h = state["headers"]
    pid = state["project_id"]

    outline = """第1章 末日降临：城市崩溃，林凡在废墟中觉醒
第2章 独行者：学会在末世中生存的基本法则
第3章 同行者：遇到小队，决定合作
第4章 第一战：面对变异兽的正面交锋
第5章 秘密：发现觉醒异能的真正原因"""

    r = client.put(f"/api/projects/{pid}", headers=h, json={
        "outline": outline,
        "world_setting": "2024年，一场神秘辐射导致全球生物变异。人类城市崩溃，少数人觉醒异能。",
    })
    assert r.status_code == 200
    assert "末日降临" in r.json()["outline"]

    r = client.post(f"/api/projects/{pid}/generate/outline/confirm", headers=h, json={})
    assert r.status_code == 200
    assert r.json()["status"] == "outline_confirmed"

    project = client.get(f"/api/projects/{pid}", headers=h).json()
    assert project["status"] == "outline_confirmed"


step("Flow1: Set outline + world setting, confirm outline", flow1_set_outline_and_confirm)


def flow1_export_no_chapters():
    h = state["headers"]
    pid = state["project_id"]
    r = client.get(f"/api/projects/{pid}/generate/export/txt", headers=h)
    assert r.status_code == 400, f"Should reject export with no chapters, got {r.status_code}"


step("Flow1: Export fails when no chapters exist", flow1_export_no_chapters)


def flow1_update_project():
    h = state["headers"]
    pid = state["project_id"]
    r = client.put(f"/api/projects/{pid}", headers=h, json={
        "title": "末世觉醒：林凡传奇",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "末世觉醒：林凡传奇"
    assert "末日降临" in data["outline"]  # outline unchanged


step("Flow1: Update project title (outline preserved)", flow1_update_project)


# ═══════════════════════════════════════════════════════
# Flow 2: Multi-project management
# ═══════════════════════════════════════════════════════


def flow2_create_multiple_projects():
    h = state["headers"]
    titles = ["短篇都市", "仙侠测试", "科幻太空"]
    genres = ["都市", "仙侠", "科幻"]
    ids = []
    for title, genre in zip(titles, genres):
        r = client.post("/api/projects", headers=h, json={"title": title, "genre": genre})
        assert r.status_code == 201
        ids.append(r.json()["id"])
    state["extra_project_ids"] = ids

    projects = client.get("/api/projects", headers=h).json()
    assert len(projects) == 4  # 1 from flow1 + 3 new


step("Flow2: Create 3 additional projects", flow2_create_multiple_projects)


def flow2_delete_project():
    h = state["headers"]
    pid = state["extra_project_ids"][0]
    r = client.delete(f"/api/projects/{pid}", headers=h)
    assert r.status_code == 200

    r = client.get(f"/api/projects/{pid}", headers=h)
    assert r.status_code == 404

    projects = client.get("/api/projects", headers=h).json()
    assert len(projects) == 3


step("Flow2: Delete project and verify removal", flow2_delete_project)


# ═══════════════════════════════════════════════════════
# Flow 3: AI Config management
# ═══════════════════════════════════════════════════════


def flow3_update_ai_config():
    h = state["headers"]
    cid = state["ai_config_id"]
    r = client.put(f"/api/settings/ai/{cid}", headers=h, json={
        "temperature": 0.8,
        "max_tokens": 4000,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["temperature"] == 0.8
    assert data["max_tokens"] == 4000


step("Flow3: Update AI config parameters", flow3_update_ai_config)


def flow3_delete_ai_config():
    h = state["headers"]
    configs = client.get("/api/settings/ai", headers=h).json()
    backup = [c for c in configs if c["name"] == "Backup DeepSeek"]
    assert len(backup) == 1
    r = client.delete(f"/api/settings/ai/{backup[0]['id']}", headers=h)
    assert r.status_code == 200

    configs = client.get("/api/settings/ai", headers=h).json()
    assert len(configs) == 1


step("Flow3: Delete backup AI config", flow3_delete_ai_config)


# ═══════════════════════════════════════════════════════
# Flow 4: Security checks
# ═══════════════════════════════════════════════════════


def flow4_no_auth_access():
    pid = state["project_id"]
    endpoints = [
        ("GET", "/api/projects"),
        ("GET", f"/api/projects/{pid}"),
        ("GET", f"/api/projects/{pid}/chapters"),
        ("GET", "/api/settings/ai"),
    ]
    for method, url in endpoints:
        r = client.request(method, url)
        assert r.status_code == 403, f"{method} {url} should require auth, got {r.status_code}"


step("Flow4: All protected endpoints reject unauthenticated requests", flow4_no_auth_access)


def flow4_bad_token():
    bad = {"Authorization": "Bearer invalid.token.here"}
    r = client.get("/api/projects", headers=bad)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


step("Flow4: Invalid token rejected", flow4_bad_token)


def flow4_nonexistent_resources():
    h = state["headers"]
    r = client.get("/api/projects/fake-id-123", headers=h)
    assert r.status_code == 404

    r = client.get("/api/chapters/fake-id-123", headers=h)
    assert r.status_code == 404


step("Flow4: 404 for nonexistent resources", flow4_nonexistent_resources)


# ═══════════════════════════════════════════════════════
# Flow 5: Knowledge base empty state
# ═══════════════════════════════════════════════════════


def flow5_knowledge_empty():
    h = state["headers"]
    pid = state["project_id"]
    entities = client.get(f"/api/projects/{pid}/knowledge", headers=h).json()
    assert entities == []
    versions = client.get(f"/api/projects/{pid}/knowledge/versions", headers=h).json()
    assert versions == []


step("Flow5: Knowledge base starts empty", flow5_knowledge_empty)


# ═══════════════════════════════════════════════════════
# Cleanup: logout
# ═══════════════════════════════════════════════════════

def cleanup_logout():
    r = client.post("/api/auth/logout", headers=state["headers"])
    assert r.status_code == 200


step("Cleanup: Logout", cleanup_logout)

# ─── Results ────────────────────────────────────────────

print("\n" + "=" * 60)
print("Integration Test Results")
print("=" * 60)
for r in results:
    print(r)
print("-" * 60)
print(f"  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
