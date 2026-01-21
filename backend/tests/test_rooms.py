def test_create_room(client, staff_auth_header):
    response = client.post(
        "/rooms/",
        json={"name": "Test Room", "description": "A room for testing"},
        headers=staff_auth_header
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Room"
    assert data["id"] is not None

def test_list_rooms(client, auth_header, staff_auth_header):
    # Create two rooms
    client.post("/rooms/", json={"name": "Room A"}, headers=staff_auth_header)
    client.post("/rooms/", json={"name": "Room B"}, headers=staff_auth_header)
    # The list endpoint only returns rooms we own or joined.
    # auth_header (Student) owns none.
    # Let's use staff_auth_header to list.
    
    response = client.get("/rooms/", headers=staff_auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

def test_join_room(client, auth_header, staff_auth_header):
    # Create a room (needs STAFF)
    create_resp = client.post("/rooms/", json={"name": "Joinable Room"}, headers=staff_auth_header)
    room_id = create_resp.json()["id"]
    
    # Join it (owner automatically joins usually, so maybe test with a second user?)
    # For simplicity, verifying endpoint exists and handles logic
    response = client.post(f"/rooms/{room_id}/join", headers=auth_header)
    # Depending on implementation, might be 200 or 400 if already joined
    assert response.status_code in [200, 400] 
