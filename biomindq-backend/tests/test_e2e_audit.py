import pytest
import httpx
import uuid

BASE_URL = "http://localhost:3001"

@pytest.mark.asyncio
async def test_e2e_full_application_suite():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. Health Check
        r_health = await client.get("/api/health")
        assert r_health.status_code == 200
        health_data = r_health.json()
        assert "mongo" in health_data
        assert "groq" in health_data

        # 2. Registration & Authentication
        unique_email = f"e2e_tester_{uuid.uuid4().hex[:6]}@biomindq.ai"
        pwd = "TestPassword123!"

        r_reg = await client.post("/auth/register", json={"email": unique_email, "password": pwd})
        assert r_reg.status_code == 200
        reg_data = r_reg.json()
        assert "access_token" in reg_data
        user_id = reg_data["user"]["id"]
        token = reg_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. GET /auth/me
        r_me = await client.get("/auth/me", headers=headers)
        assert r_me.status_code == 200
        assert r_me.json()["email"] == unique_email

        # 4. Anonymous Trial Gate Test
        anon_client = httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)
        # Query 1 (Anonymous) - Allowed
        r_q1 = await anon_client.post("/api/query", json={"question": "What is known about metformin's interaction with AMPK?"})
        assert r_q1.status_code in [200, 500] # pipeline response or mock

        # Query 2 (Anonymous) - Must be blocked by trial gate
        r_q2 = await anon_client.post("/api/query", json={"question": "Does ibuprofen interact with lisinopril?"})
        assert r_q2.status_code == 403
        q2_err = r_q2.json()
        assert q2_err.get("detail", {}).get("trial_limit_reached") is True
        await anon_client.aclose()

        # 5. Authenticated Query Execution (User is never blocked)
        r_auth_q1 = await client.post("/api/query", json={"question": "What is known about metformin's interaction with AMPK?"}, headers=headers)
        assert r_auth_q1.status_code == 200
        data1 = r_auth_q1.json()
        assert "final_answer" in data1
        assert "verifier_output" in data1
        assert "consensus" in data1
        assert "latency_ms" in data1

        # Second query for same authenticated user
        r_auth_q2 = await client.post("/api/query", json={"question": "How does GLP-1 activation synergize with metformin in type 2 diabetes?"}, headers=headers)
        assert r_auth_q2.status_code == 200

        # 6. Sessions API Test
        r_sess = await client.get("/api/sessions", headers=headers)
        assert r_sess.status_code == 200
        sess_data = r_sess.json()
        assert "sessions" in sess_data
        assert len(sess_data["sessions"]) >= 2
        first_session_id = sess_data["sessions"][0]["id"]

        r_sess_detail = await client.get(f"/api/sessions/{first_session_id}", headers=headers)
        assert r_sess_detail.status_code == 200
        assert r_sess_detail.json()["id"] == first_session_id

        # 7. Research Knowledge Graph API Test
        r_graph = await client.get("/api/graph/user", headers=headers)
        assert r_graph.status_code == 200
        graph_data = r_graph.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        
        # Verify node types
        node_types = set([n["type"] for n in graph_data["nodes"]])
        assert "Researcher" in node_types
        assert "Session" in node_types
        assert "Topic" in node_types

        # Verify topic deduplication (e.g. 'metformin' appears in 2 queries, should only have 1 Topic node for metformin)
        metformin_nodes = [n for n in graph_data["nodes"] if n["type"] == "Topic" and n.get("normalized_name") == "metformin"]
        assert len(metformin_nodes) <= 1

        # 8. User Session Isolation Test (User B cannot see User A's sessions)
        user2_email = f"user2_{uuid.uuid4().hex[:6]}@biomindq.ai"
        r_reg2 = await client.post("/auth/register", json={"email": user2_email, "password": pwd})
        token2 = r_reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        r_user2_sess = await client.get("/api/sessions", headers=headers2)
        assert r_user2_sess.status_code == 200
        # User B should have 0 sessions or only their own
        user2_session_ids = [s["id"] for s in r_user2_sess.json()["sessions"]]
        assert first_session_id not in user2_session_ids
