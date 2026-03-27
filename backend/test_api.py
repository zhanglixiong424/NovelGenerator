"""
Comprehensive API integration test.
Run with: python3 test_api.py
"""
import json
import sys
import httpx

BASE = "http://127.0.0.1:8000"

passed = 0
failed = 0
results = []

def test(name: str, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        results.append(f"  ✅ {name}")
    except Exception as e:
        failed += 1
        results.append(f"  ❌ {name}: {e}")

client = httpx.Client(base_url=BASE, timeout=10.0)
token = ""
project_id = ""
chapter_id = ""

# ─── 1. Health ──────────────────────────────────────────

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200, f"status={r.status_code}"
    assert r.json()["status"] == "ok"

test("GET /api/health", test_health)

# ─── 2. Auth Setup ─────────────────────────────────────

def test_setup():
    global token
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "testpass123"})
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    data = r.json()
    assert "access_token" in data
    token = data["access_token"]

test("POST /api/auth/setup (create admin)", test_setup)

def test_setup_duplicate():
    r = client.post("/api/auth/setup", json={"username": "admin2", "password": "testpass123"})
    assert r.status_code == 400, f"should fail with 400, got {r.status_code}"

test("POST /api/auth/setup (duplicate should fail)", test_setup_duplicate)

# ─── 3. Auth Login ─────────────────────────────────────

def test_login():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert r.status_code == 200, f"status={r.status_code}"
    assert "access_token" in r.json()

test("POST /api/auth/login", test_login)

def test_login_bad_password():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert r.status_code == 401, f"should be 401, got {r.status_code}"

test("POST /api/auth/login (bad password)", test_login_bad_password)

# ─── 4. Auth Me ────────────────────────────────────────

def test_me():
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"status={r.status_code}"
    data = r.json()
    assert data["username"] == "admin"
    assert data["is_admin"] is True

test("GET /api/auth/me", test_me)

def test_me_no_token():
    r = client.get("/api/auth/me")
    assert r.status_code == 403, f"should be 403, got {r.status_code}"

test("GET /api/auth/me (no token)", test_me_no_token)

# ─── 5. AI Config ──────────────────────────────────────

headers = {}

def test_ai_config_create():
    global headers
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/settings/ai", headers=headers, json={
        "name": "Test Provider",
        "provider_type": "openai",
        "api_key": "sk-test-key-12345678",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4",
        "priority": 1,
    })
    assert r.status_code == 201, f"status={r.status_code} body={r.text}"
    data = r.json()
    assert data["name"] == "Test Provider"
    assert "***" in data["api_key_masked"] or "*" in data["api_key_masked"]

test("POST /api/settings/ai (create)", test_ai_config_create)

def test_ai_config_list():
    r = client.get("/api/settings/ai", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["model_name"] == "gpt-4"

test("GET /api/settings/ai (list)", test_ai_config_list)

def test_ai_config_update():
    configs = client.get("/api/settings/ai", headers=headers).json()
    cid = configs[0]["id"]
    r = client.put(f"/api/settings/ai/{cid}", headers=headers, json={
        "name": "Updated Provider",
        "temperature": 0.5,
    })
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Provider"
    assert r.json()["temperature"] == 0.5

test("PUT /api/settings/ai/:id (update)", test_ai_config_update)

# ─── 6. Projects CRUD ──────────────────────────────────

def test_project_create():
    global project_id
    r = client.post("/api/projects", headers=headers, json={
        "title": "测试玄幻小说",
        "genre": "玄幻",
        "target_platform": "番茄小说",
        "target_word_count": 200000,
    })
    assert r.status_code == 201, f"status={r.status_code} body={r.text}"
    data = r.json()
    assert data["title"] == "测试玄幻小说"
    assert data["status"] == "idle"
    assert data["chapter_count"] == 0
    project_id = data["id"]

test("POST /api/projects (create)", test_project_create)

def test_project_list():
    r = client.get("/api/projects", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["title"] == "测试玄幻小说"

test("GET /api/projects (list)", test_project_list)

def test_project_get():
    r = client.get(f"/api/projects/{project_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == project_id

test("GET /api/projects/:id", test_project_get)

def test_project_update():
    r = client.put(f"/api/projects/{project_id}", headers=headers, json={
        "title": "修改后的书名",
        "outline": "这是大纲内容\n第1章 开始：主角出场\n第2章 修炼：主角开始修炼",
    })
    assert r.status_code == 200
    assert r.json()["title"] == "修改后的书名"
    assert "大纲" in r.json()["outline"]

test("PUT /api/projects/:id (update)", test_project_update)

# ─── 7. Chapters ───────────────────────────────────────

def test_chapters_list():
    r = client.get(f"/api/projects/{project_id}/chapters", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

test("GET /api/projects/:id/chapters (empty list)", test_chapters_list)

# ─── 8. Generate Status ────────────────────────────────

def test_generate_status():
    r = client.get(f"/api/projects/{project_id}/generate/status", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["current_state"] == "idle"
    assert data["current_chapter_no"] == 0

test("GET /api/projects/:id/generate/status", test_generate_status)

# ─── 9. Knowledge Base (empty) ─────────────────────────

def test_knowledge_list():
    r = client.get(f"/api/projects/{project_id}/knowledge", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

test("GET /api/projects/:id/knowledge (empty)", test_knowledge_list)

def test_knowledge_versions():
    r = client.get(f"/api/projects/{project_id}/knowledge/versions", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

test("GET /api/projects/:id/knowledge/versions (empty)", test_knowledge_versions)

# ─── 10. Outline Confirm ───────────────────────────────

def test_outline_confirm():
    outline = """第1章 觉醒：林凡在末世中觉醒异能
第2章 求生：林凡加入小队
第3章 战斗：第一次正面交锋"""
    # First set outline on project
    client.put(f"/api/projects/{project_id}", headers=headers, json={"outline": outline})
    r = client.post(f"/api/projects/{project_id}/generate/outline/confirm", headers=headers, json={})
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    assert r.json()["status"] == "outline_confirmed"

    # Verify project status changed
    p = client.get(f"/api/projects/{project_id}", headers=headers).json()
    assert p["status"] == "outline_confirmed"

test("POST /api/projects/:id/generate/outline/confirm", test_outline_confirm)

# ─── 11. Export (no chapters) ──────────────────────────

def test_export_no_chapters():
    r = client.get(f"/api/projects/{project_id}/generate/export/txt", headers=headers)
    assert r.status_code == 400, f"should 400, got {r.status_code}"

test("GET /api/projects/:id/generate/export/txt (empty)", test_export_no_chapters)

# ─── 12. Validation tests ──────────────────────────────

def test_create_project_validation():
    r = client.post("/api/projects", headers=headers, json={
        "title": "",
        "genre": "玄幻",
    })
    assert r.status_code == 422, f"should 422, got {r.status_code}"

test("POST /api/projects validation (empty title)", test_create_project_validation)

def test_login_validation():
    r = client.post("/api/auth/login", json={"username": "a", "password": "12345"})
    assert r.status_code == 422, f"should 422, got {r.status_code}"

test("POST /api/auth/login validation (short password)", test_login_validation)

# ─── 13. 404 tests ─────────────────────────────────────

def test_project_not_found():
    r = client.get("/api/projects/nonexistent-id", headers=headers)
    assert r.status_code == 404

test("GET /api/projects/:id (not found)", test_project_not_found)

def test_chapter_not_found():
    r = client.get("/api/chapters/nonexistent-id", headers=headers)
    assert r.status_code == 404

test("GET /api/chapters/:id (not found)", test_chapter_not_found)

# ─── 14. Delete test ───────────────────────────────────

def test_create_and_delete_project():
    r = client.post("/api/projects", headers=headers, json={
        "title": "待删除项目",
        "genre": "末世",
    })
    pid = r.json()["id"]
    r = client.delete(f"/api/projects/{pid}", headers=headers)
    assert r.status_code == 200

    r = client.get(f"/api/projects/{pid}", headers=headers)
    assert r.status_code == 404

test("DELETE /api/projects/:id", test_create_and_delete_project)

# ─── 15. Auth logout ─────────────────────────────────

def test_logout():
    r = client.post("/api/auth/logout", headers=headers)
    assert r.status_code == 200

test("POST /api/auth/logout", test_logout)

# ─── Results ────────────────────────────────────────────

print("\n" + "=" * 60)
print("API Test Results")
print("=" * 60)
for r in results:
    print(r)
print("-" * 60)
print(f"  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
