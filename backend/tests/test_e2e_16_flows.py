"""Automated End-to-End Test for the 16 Primary KHOJAI User Flows.

Explicitly validates:
Flow 1: Register
Flow 2: Login
Flow 3: Logout
Flow 4: Create conversation
Flow 5: Send message
Flow 6: Receive AI response
Flow 7: Refresh page / fetch conversation state
Flow 8: Conversation remains available with all messages
Flow 9: Upload document
Flow 10: Document processing (extract, clean, chunk, embed)
Flow 11: Search document
Flow 12: Ask question about document
Flow 13: Receive context-aware answer citing sources
Flow 14: Delete document
Flow 15: Delete conversation
Flow 16: Edit profile/settings
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_16_flow_lifecycle(client: AsyncClient):
    """Execute the full 16-step user lifecycle from registration to cleanup."""

    # -------------------------------------------------------------
    # FLOW 1: Register
    # -------------------------------------------------------------
    user_email = "aarav.explorer@example.com"
    user_password = "SecurePassword2026!"
    user_name = "Aarav Sharma"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": user_email,
            "password": user_password,
            "full_name": user_name,
        },
    )
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == user_email
    user_id = reg_data["user"]["id"]

    # -------------------------------------------------------------
    # FLOW 2: Login
    # -------------------------------------------------------------
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user_email,
            "password": user_password,
        },
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    access_token = login_data["access_token"]
    assert access_token
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # Verify session is authenticated
    me_res = await client.get("/api/v1/auth/me", headers=auth_header)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == user_email

    # -------------------------------------------------------------
    # FLOW 3: Logout
    # -------------------------------------------------------------
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers=auth_header,
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["ok"] is True

    # Re-login to continue the user session for subsequent flows
    relogin_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user_email,
            "password": user_password,
        },
    )
    assert relogin_res.status_code == 200
    access_token = relogin_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # -------------------------------------------------------------
    # FLOW 4: Create conversation
    # -------------------------------------------------------------
    create_conv_res = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_header,
        json={"title": "Hidden Himalayan Trails - Zanskar Valley"},
    )
    assert create_conv_res.status_code == 201, f"Create conv failed: {create_conv_res.text}"
    conv_data = create_conv_res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Hidden Himalayan Trails - Zanskar Valley"

    # -------------------------------------------------------------
    # FLOW 5: Send message
    # FLOW 6: Receive AI response
    # -------------------------------------------------------------
    user_prompt = "What is the best time of year to trek the Chadar frozen river route in Zanskar?"
    send_msg_res = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_header,
        json={"content": user_prompt},
    )
    assert send_msg_res.status_code == 200, f"Send message failed: {send_msg_res.text}"
    ai_msg_data = send_msg_res.json()
    assert ai_msg_data["sender_type"] == "assistant"
    assert len(ai_msg_data["content"]) > 10, "AI response content should not be empty"

    # -------------------------------------------------------------
    # FLOW 7: Refresh page (re-fetch conversation state)
    # FLOW 8: Conversation remains available
    # -------------------------------------------------------------
    # Re-fetch conversation details
    conv_refresh_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_header,
    )
    assert conv_refresh_res.status_code == 200
    refreshed_conv = conv_refresh_res.json()
    assert refreshed_conv["id"] == conv_id
    assert refreshed_conv["title"] == "Hidden Himalayan Trails - Zanskar Valley"

    # Re-fetch message history
    messages_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_header,
    )
    assert messages_res.status_code == 200
    messages = messages_res.json()
    assert len(messages) >= 2, "Both user prompt and AI response must remain persistent"
    assert any(m["sender_type"] == "user" and user_prompt in m["content"] for m in messages)
    assert any(m["sender_type"] == "assistant" for m in messages)

    # -------------------------------------------------------------
    # FLOW 9: Upload document
    # FLOW 10: Document processing
    # -------------------------------------------------------------
    doc_content = (
        "# Zanskar Valley High-Altitude Expedition Notes\n\n"
        "Padum is the administrative center of Zanskar, situated at an elevation of 3,669 meters.\n\n"
        "The Phugtal Monastery is one of the most remote Buddhist monasteries in Ladakh, "
        "built entirely around a natural cliff cave overlooking the Lungnak River gorge.\n\n"
        "Travelers must acclimatize in Leh or Kargil before attempting high passes such as Shingo La."
    )
    files = {
        "file": (
            "zanskar_field_notes.txt",
            doc_content.encode("utf-8"),
            "text/plain",
        )
    }
    data = {
        "title": "Zanskar Field Expedition Notes 2026",
        "document_type": "guide",
    }

    upload_res = await client.post(
        "/api/v1/documents?process_async=false",
        headers=auth_header,
        files=files,
        data=data,
    )
    assert upload_res.status_code == 201, f"Upload document failed: {upload_res.text}"
    doc_info = upload_res.json()
    doc_id = doc_info["id"]
    assert doc_info["status"] == "ready", "Document processing should immediately reach ready status"
    assert doc_info["chunk_count"] >= 1, "Document must have been chunked"

    # -------------------------------------------------------------
    # FLOW 11: Search document
    # -------------------------------------------------------------
    search_res = await client.get(
        "/api/v1/search/documents?q=Phugtal+Monastery+cliff+cave",
        headers=auth_header,
    )
    assert search_res.status_code == 200, f"Search document failed: {search_res.text}"
    search_data = search_res.json()
    assert search_data["total"] >= 1, "Uploaded document should match the search query"
    first_match = search_data["items"][0]
    assert "Phugtal" in first_match["content"]
    assert first_match["similarity"] > 0.1

    # -------------------------------------------------------------
    # FLOW 12: Ask question about document
    # FLOW 13: Receive context-aware answer
    # -------------------------------------------------------------
    rag_query_res = await client.post(
        "/api/v1/documents/query",
        headers=auth_header,
        json={
            "query": "Where is Phugtal Monastery located and what makes its construction unique?",
            "top_k": 3,
        },
    )
    assert rag_query_res.status_code == 200, f"RAG query failed: {rag_query_res.text}"
    rag_data = rag_query_res.json()
    assert rag_data["answer"], "Context-aware answer must not be empty"
    assert len(rag_data["sources"]) >= 1, "Must cite at least one source chunk"
    assert any("Phugtal" in src["content"] for src in rag_data["sources"]), "Sources must contain cited material"

    # -------------------------------------------------------------
    # FLOW 14: Delete document
    # -------------------------------------------------------------
    del_doc_res = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=auth_header,
    )
    assert del_doc_res.status_code == 204, f"Delete document failed: {del_doc_res.text}"

    # Verify document is no longer accessible
    verify_doc_gone = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=auth_header,
    )
    assert verify_doc_gone.status_code == 404

    # -------------------------------------------------------------
    # FLOW 15: Delete conversation
    # -------------------------------------------------------------
    del_conv_res = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_header,
    )
    assert del_conv_res.status_code == 204, f"Delete conversation failed: {del_conv_res.text}"

    # Verify conversation is no longer accessible
    verify_conv_gone = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_header,
    )
    assert verify_conv_gone.status_code == 404

    # -------------------------------------------------------------
    # FLOW 16: Edit profile/settings
    # -------------------------------------------------------------
    # 1. Update basic profile and theme
    profile_update_res = await client.patch(
        "/api/v1/users/me",
        headers=auth_header,
        json={
            "full_name": "Aarav Sharma - Himalayan Explorer",
            "bio": "Certified high-altitude mountaineer exploring unmapped passes in Ladakh.",
            "theme_preference": "dark",
        },
    )
    assert profile_update_res.status_code == 200
    updated_profile = profile_update_res.json()
    assert updated_profile["full_name"] == "Aarav Sharma - Himalayan Explorer"
    assert updated_profile["bio"] == "Certified high-altitude mountaineer exploring unmapped passes in Ladakh."
    assert updated_profile["theme_preference"] == "dark"

    # 2. Update AI travel preferences
    pref_update_res = await client.patch(
        "/api/v1/users/me/preferences",
        headers=auth_header,
        json={
            "budget": "₹45,000",
            "days": "14 days",
            "style": "High-altitude trekking",
            "interests": ["Trekking", "Monasteries", "Photography", "Remote Homestays"],
            "ai_pace": "intense",
            "ai_curiosity_level": "high",
        },
    )
    assert pref_update_res.status_code == 200
    updated_prefs = pref_update_res.json()["travel_preferences"]
    assert updated_prefs["budget"] == "₹45,000"
    assert "Trekking" in updated_prefs["interests"]
    assert updated_prefs["ai_pace"] == "intense"

    # 3. Final verification of profile state
    final_me_res = await client.get(
        "/api/v1/users/me",
        headers=auth_header,
    )
    assert final_me_res.status_code == 200
    final_profile = final_me_res.json()
    assert final_profile["full_name"] == "Aarav Sharma - Himalayan Explorer"
    assert final_profile["theme_preference"] == "dark"
    assert final_profile["travel_preferences"]["ai_curiosity_level"] == "high"
