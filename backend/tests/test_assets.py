from unittest.mock import patch

def test_list_assets_empty(client, auth_header):
    response = client.get("/assets/", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == []

@patch("routers.assets.s3")
@patch("routers.assets.process_asset")
def test_upload_asset(mock_task, mock_s3, client, auth_header):
    # Mock return values
    # mock_s3.upload_fileobj is called. We don't need return value usually.
    
    # Create dummy file
    files = {'file': ('test.glb', b'dummy content', 'model/gltf-binary')}
    
    response = client.post(
        "/assets/upload",
        files=files,
        data={"is_sliceable": "false", "asset_type": "MODEL"},
        headers=auth_header
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "PENDING"
    assert data["type"] == "MODEL"
