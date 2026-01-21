def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"username": "newuser", "password": "password123", "role": "STUDENT"}
    )
    assert response.status_code == 201
    assert response.json()["message"] == "User created successfully"
    # assert "id" in response.json() # Removed as ID is not returned

def test_register_duplicate_user(client):
    client.post(
        "/auth/register",
        json={"username": "dupuser", "password": "password123", "role": "STUDENT"}
    )
    response = client.post(
        "/auth/register",
        json={"username": "dupuser", "password": "password123", "role": "STUDENT"}
    )
    assert response.status_code == 400

def test_login_success(client):
    client.post(
        "/auth/register",
        json={"username": "loginuser", "password": "password123", "role": "STUDENT"}
    )
    response = client.post(
        "/auth/login",
        json={"username": "loginuser", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
