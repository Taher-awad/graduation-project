# Unity Integration Guide — EduVR Cortex AI

This document contains **everything Unity needs** to integrate with the Cortex AI backend:
- Login system
- Asset list (preview)
- Asset download & import (GLB at runtime)

> **Base URL**: `http://localhost:8000`  
> Replace with production URL when deployed.

---

## Unity Package Requirements

Install these packages via Unity Package Manager before starting:

| Package | Purpose |
|---|---|
| `com.unity.nuget.newtonsoft-json` | JSON serialization/deserialization |
| `GLTFUtility` (Siccity) _or_ `UnityGLTF` (KhronosGroup) | Runtime GLB/GLTF loading |

> **Recommended**: [Siccity GLTFUtility](https://github.com/Siccity/GLTFUtility) — simpler API for runtime loading.  
> Or [KhronosGroup UnityGLTF](https://github.com/KhronosGroup/UnityGLTF) — official, more features.

---

## Part 1: Login System

### 1.1 — What the API Expects

```
POST http://localhost:8000/auth/login
Content-Type: application/json

{
  "username": "taher",
  "password": "123"
}
```

> ⚠️ The `role` field is **NOT needed** for login — only for registration.

### 1.2 — What the API Returns

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "TEACHER"
}
```

| Field | Type | What to do with it |
|---|---|---|
| `access_token` | `string` | Store this. Send it in every subsequent request |
| `token_type` | `string` | Always `"bearer"` — used to build the Auth header |
| `role` | `string` | `"TEACHER"` / `"TA"` / `"STUDENT"` — use to control what UI shows |

### 1.3 — JWT Token Details

- **Algorithm**: HS256  
- **Expires**: 15 minutes from login  
- **Payload contains**: `{ "sub": "username", "role": "TEACHER", "exp": 1234567890 }`  
- **How to send**: `Authorization: Bearer <access_token>` header on every request

> ⚠️ After 15 min the token expires. You get a `401 Unauthorized`. You must ask the user to log in again (or implement auto-refresh by calling login again silently with stored credentials).

### 1.4 — C# Data Classes

```csharp
// Request body
[System.Serializable]
public class LoginRequest
{
    public string username;
    public string password;
}

// Response body
[System.Serializable]
public class LoginResponse
{
    public string access_token;
    public string token_type;
    public string role;
}
```

### 1.5 — C# Login Implementation

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class AuthManager : MonoBehaviour
{
    private const string BASE_URL = "http://localhost:8000";

    // Store token globally (use DontDestroyOnLoad or singleton)
    public static string AccessToken { get; private set; }
    public static string UserRole { get; private set; }

    public IEnumerator Login(string username, string password, 
                              System.Action onSuccess, System.Action<string> onError)
    {
        var requestBody = new LoginRequest { username = username, password = password };
        string json = JsonUtility.ToJson(requestBody);

        using var request = new UnityWebRequest($"{BASE_URL}/auth/login", "POST");
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            var response = JsonUtility.FromJson<LoginResponse>(request.downloadHandler.text);
            AccessToken = response.access_token;
            UserRole = response.role;
            Debug.Log($"Login OK — Role: {UserRole}");
            onSuccess?.Invoke();
        }
        else
        {
            string error = request.downloadHandler.text; // e.g. {"detail":"Incorrect username or password"}
            Debug.LogError($"Login Failed: {error}");
            onError?.Invoke(error);
        }
    }
}
```

### 1.6 — Error Handling

| HTTP Status | Response Body | Meaning |
|---|---|---|
| `200 OK` | `{access_token, token_type, role}` | Success |
| `401 Unauthorized` | `{"detail": "Incorrect username or password"}` | Wrong credentials |
| `422 Unprocessable Entity` | `{"detail": [...]}` | Missing field in request body |

---

## Part 2: Asset Preview System (List Assets)

### 2.1 — What the API Expects

```
GET http://localhost:8000/assets/
Authorization: Bearer <access_token>

# Optional filter by type:
GET http://localhost:8000/assets/?asset_type=MODEL
```

| Query Param | Values | Optional |
|---|---|---|
| `asset_type` | `MODEL`, `VIDEO`, `SLIDE`, `IMAGE` | ✅ Yes |

### 2.2 — What the API Returns

An **array** of asset objects:

```json
[
  {
    "id": "f7c3e2b1-4a5d-48ce-9200-123456789abc",
    "filename": "human_heart.glb",
    "asset_type": "MODEL",
    "status": "COMPLETED",
    "is_sliceable": true,
    "download_url": "http://localhost:9000/assets/processed/f7c3e2b1...?X-Amz-Signature=...&X-Amz-Expires=3600",
    "metadata_json": {
      "interaction_type": "sliceable",
      "original_file": "human_heart.glb"
    }
  },
  {
    "id": "c9d1a2b3-...",
    "filename": "lecture_slides.pdf",
    "asset_type": "SLIDE",
    "status": "COMPLETED",
    "is_sliceable": false,
    "download_url": "http://localhost:9000/assets/raw/c9d1a2b3...?...",
    "metadata_json": null
  },
  {
    "id": "a1b2c3d4-...",
    "filename": "engine_model.fbx",
    "asset_type": "MODEL",
    "status": "PROCESSING",
    "is_sliceable": false,
    "download_url": null,
    "metadata_json": null
  }
]
```

### 2.3 — Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | `string (UUID)` | Unique asset ID — use this to fetch/load a specific asset |
| `filename` | `string` | Original uploaded filename (for display) |
| `asset_type` | `string` | `"MODEL"` / `"VIDEO"` / `"SLIDE"` / `"IMAGE"` |
| `status` | `string` | See status table below |
| `is_sliceable` | `bool` | If `true`, model supports cross-section slicing in VR |
| `download_url` | `string` or `null` | **Pre-signed URL** to download the file. Only valid when `status == "COMPLETED"`. **Expires in 1 hour.** |
| `metadata_json` | `object` or `null` | Processing info (`interaction_type`: `"sliceable"` / `"static"`) |

### 2.4 — Asset Status Values

| Status | Meaning | Has `download_url`? |
|---|---|---|
| `"PENDING"` | Upload received, waiting for worker | ❌ null |
| `"PROCESSING"` | Blender is converting the model | ❌ null |
| `"COMPLETED"` | Model ready, GLB available | ✅ Valid presigned URL |
| `"FAILED"` | Conversion failed | ❌ null |

> Only `COMPLETED` assets are worth showing download buttons for in Unity.

### 2.5 — C# Data Classes

```csharp
[System.Serializable]
public class AssetItem
{
    public string id;
    public string filename;
    public string asset_type;   // "MODEL", "VIDEO", "SLIDE", "IMAGE"
    public string status;       // "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    public bool is_sliceable;
    public string download_url; // null if not COMPLETED
    // metadata_json omitted — not needed for Unity basic flow
}

[System.Serializable]
public class AssetListWrapper
{
    public AssetItem[] items;   // Use this for JsonUtility array trick
}
```

> ⚠️ **Unity's `JsonUtility` cannot deserialize root JSON arrays directly.**  
> Use this helper:
> ```csharp
> string wrappedJson = "{\"items\":" + rawJson + "}";
> var wrapper = JsonUtility.FromJson<AssetListWrapper>(wrappedJson);
> AssetItem[] assets = wrapper.items;
> ```
> Or use `Newtonsoft.Json` (JsonConvert) if you installed it — it handles arrays natively:
> ```csharp
> using Newtonsoft.Json;
> AssetItem[] assets = JsonConvert.DeserializeObject<AssetItem[]>(rawJson);
> ```

### 2.6 — C# Fetch Asset List Implementation

```csharp
public IEnumerator FetchAssets(string assetType,
                                System.Action<AssetItem[]> onSuccess,
                                System.Action<string> onError)
{
    // assetType can be "" (all), "MODEL", "VIDEO", "SLIDE", "IMAGE"
    string url = $"{BASE_URL}/assets/";
    if (!string.IsNullOrEmpty(assetType))
        url += $"?asset_type={assetType}";

    using var request = UnityWebRequest.Get(url);
    request.SetRequestHeader("Authorization", $"Bearer {AuthManager.AccessToken}");

    yield return request.SendWebRequest();

    if (request.result == UnityWebRequest.Result.Success)
    {
        string rawJson = request.downloadHandler.text;

        // JsonUtility array workaround
        string wrapped = "{\"items\":" + rawJson + "}";
        var wrapper = JsonUtility.FromJson<AssetListWrapper>(wrapped);

        onSuccess?.Invoke(wrapper.items);
    }
    else
    {
        onError?.Invoke(request.downloadHandler.text);
    }
}

// Usage:
// StartCoroutine(FetchAssets("MODEL", OnAssetsLoaded, OnError));
```

### 2.7 — Fetch Single Asset

```csharp
public IEnumerator FetchAsset(string assetId,
                               System.Action<AssetItem> onSuccess,
                               System.Action<string> onError)
{
    using var request = UnityWebRequest.Get($"{BASE_URL}/assets/{assetId}");
    request.SetRequestHeader("Authorization", $"Bearer {AuthManager.AccessToken}");

    yield return request.SendWebRequest();

    if (request.result == UnityWebRequest.Result.Success)
    {
        var asset = JsonUtility.FromJson<AssetItem>(request.downloadHandler.text);
        onSuccess?.Invoke(asset);
    }
    else
    {
        onError?.Invoke(request.downloadHandler.text);
    }
}
```

---

## Part 3: Import Assets into Unity (Runtime GLB Loading)

The `download_url` from the asset list is a **pre-signed HTTP URL** pointing directly to the processed `.glb` file in MinIO. Unity can download and load it at runtime.

### 3.1 — The GLB File Details

| Property | Value |
|---|---|
| Format | `.glb` (binary GLTF 2.0) |
| Coordinate system | Y-up, centered at origin |
| Scale | Normalized to unit cube (max dimension = 1.0) |
| Metadata embedded | Custom `id` and `interaction_type` properties on root node |
| Textures | Embedded inside the GLB (baked by Blender) |
| URL expiry | **1 hour** from when `GET /assets/` was called |

> ⚠️ The URL expires in 1 hour. If you cache it too long, re-call `GET /assets/{id}` to get a fresh presigned URL before downloading.

### 3.2 — Download the GLB Binary

```csharp
public IEnumerator DownloadGLB(string downloadUrl,
                                System.Action<byte[]> onSuccess,
                                System.Action<string> onError)
{
    using var request = UnityWebRequest.Get(downloadUrl);
    // NOTE: Do NOT add Authorization header here!
    // The presigned URL already contains auth credentials in the query string.
    // Adding Bearer token breaks the MinIO signature.

    yield return request.SendWebRequest();

    if (request.result == UnityWebRequest.Result.Success)
    {
        onSuccess?.Invoke(request.downloadHandler.data);
    }
    else
    {
        onError?.Invoke(request.error);
    }
}
```

> ⚠️ **Do NOT add `Authorization` header to the MinIO download URL.** The URL already contains `X-Amz-Signature` in the query string. Adding a Bearer header will break the request.

### 3.3 — Load GLB into Scene (GLTFUtility)

Using **Siccity GLTFUtility**:

```csharp
using Siccity.GLTFUtility;

public class AssetImporter : MonoBehaviour
{
    // Spawn a loaded GLB model into the scene
    public IEnumerator ImportModelFromUrl(string downloadUrl, Vector3 spawnPosition)
    {
        // Step 1: Download the GLB bytes
        byte[] glbData = null;
        bool downloadDone = false;
        bool downloadFailed = false;

        yield return StartCoroutine(DownloadGLB(downloadUrl,
            data => { glbData = data; downloadDone = true; },
            err  => { Debug.LogError($"Download failed: {err}"); downloadFailed = true; }
        ));

        if (downloadFailed || glbData == null) yield break;

        // Step 2: Load GLB from bytes (GLTFUtility)
        GameObject loadedModel = null;
        bool loadDone = false;

        Importer.ImportGLBAsync(glbData, new ImportSettings(), result =>
        {
            loadedModel = result;
            loadDone = true;
        });

        // Wait for async load to complete
        while (!loadDone) yield return null;

        if (loadedModel == null)
        {
            Debug.LogError("GLB load returned null");
            yield break;
        }

        // Step 3: Place in scene
        loadedModel.transform.position = spawnPosition;
        loadedModel.transform.rotation = Quaternion.identity;

        Debug.Log($"Model loaded: {loadedModel.name}");
    }

    // Helper to download raw bytes
    private IEnumerator DownloadGLB(string url,
                                     System.Action<byte[]> onSuccess,
                                     System.Action<string> onError)
    {
        using var request = UnityWebRequest.Get(url);
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
            onSuccess?.Invoke(request.downloadHandler.data);
        else
            onError?.Invoke(request.error);
    }
}
```

### 3.4 — Alternative: Using UnityGLTF (KhronosGroup)

```csharp
using UnityGLTF;

// Path-based (if saved to disk first):
var loader = new GLTFSceneImporter(filePath, null);
await loader.LoadSceneAsync();
GameObject model = loader.LastLoadedScene;

// Or use GLTFComponent on a GameObject and set StreamingAssets path.
```

### 3.5 — Save to Disk First (Optional, more reliable)

```csharp
using System.IO;

public IEnumerator DownloadAndSaveGLB(string downloadUrl, string assetId,
                                       System.Action<string> onFilePath,
                                       System.Action<string> onError)
{
    string savePath = Path.Combine(Application.persistentDataPath, $"{assetId}.glb");

    // Skip download if already cached
    if (File.Exists(savePath))
    {
        onFilePath?.Invoke(savePath);
        yield break;
    }

    using var request = UnityWebRequest.Get(downloadUrl);
    yield return request.SendWebRequest();

    if (request.result == UnityWebRequest.Result.Success)
    {
        File.WriteAllBytes(savePath, request.downloadHandler.data);
        Debug.Log($"GLB saved to: {savePath}");
        onFilePath?.Invoke(savePath);
    }
    else
    {
        onError?.Invoke(request.error);
    }
}
```

---

## Part 4: Complete Flow — Login → List → Import

```csharp
public class EduVRController : MonoBehaviour
{
    private AuthManager authManager;
    private AssetImporter assetImporter;

    void Start()
    {
        authManager = GetComponent<AuthManager>();
        assetImporter = GetComponent<AssetImporter>();
    }

    // Call this from your login button:
    public void OnLoginPressed(string username, string password)
    {
        StartCoroutine(authManager.Login(username, password,
            onSuccess: () =>
            {
                Debug.Log($"Logged in as {AuthManager.UserRole}");
                // Load asset browser UI
                StartCoroutine(LoadModelAssets());
            },
            onError: (err) =>
            {
                // Show error to user
                Debug.LogError(err);
            }
        ));
    }

    // Call this to populate your asset list UI:
    public IEnumerator LoadModelAssets()
    {
        yield return StartCoroutine(authManager.FetchAssets("MODEL",
            onSuccess: (assets) =>
            {
                foreach (var asset in assets)
                {
                    Debug.Log($"{asset.filename} — {asset.status}");
                    if (asset.status == "COMPLETED")
                    {
                        // Populate your UI panel with this asset
                        // ShowAssetCard(asset);
                    }
                }
            },
            onError: (err) => Debug.LogError(err)
        ));
    }

    // Call this when user taps "Load" on an asset card:
    public void OnLoadAssetPressed(AssetItem asset)
    {
        if (asset.status != "COMPLETED" || string.IsNullOrEmpty(asset.download_url))
        {
            Debug.LogWarning("Asset not ready yet");
            return;
        }

        Vector3 spawnPos = Vector3.zero; // Or wherever you want it in VR
        StartCoroutine(assetImporter.ImportModelFromUrl(asset.download_url, spawnPos));
    }
}
```

---

## Part 5: Key Gotchas & Rules

| Rule | Why |
|---|---|
| Always send `Content-Type: application/json` with POST/PUT | FastAPI rejects without it |
| Never add `Authorization` header to MinIO download URLs | Breaks presigned signature |
| JWT expires in **15 minutes** | Catch 401 responses and re-login |
| `download_url` is only non-null when `status == "COMPLETED"` | Always check before using |
| `download_url` expires after **1 hour** | Re-fetch `GET /assets/{id}` if stale |
| `GET /assets/` returns only **the logged-in user's assets** | Each user sees their own library |
| Do NOT add `role` field to login request | Only register needs it |

---

## Part 6: Error Response Format

All API errors return JSON like this:
```json
{ "detail": "Incorrect username or password" }
```

In C#:
```csharp
[System.Serializable]
public class ErrorResponse
{
    public string detail;
}

// Parse:
var err = JsonUtility.FromJson<ErrorResponse>(request.downloadHandler.text);
Debug.LogError(err.detail);
```

---

## Part 7: Summary Checklist for Unity Dev

### Login System
- [ ] `POST /auth/login` with `{username, password}` as JSON
- [ ] Store `access_token` and `role` from response
- [ ] Attach `Authorization: Bearer <token>` to every subsequent request
- [ ] Handle `401` → redirect to login screen
- [ ] Show/hide UI elements based on `role` (TEACHER vs STUDENT)

### Asset Preview (List)
- [ ] `GET /assets/?asset_type=MODEL` with Bearer token
- [ ] Parse array response (use Newtonsoft or wrap JSON trick)
- [ ] Display cards: `filename`, `status`, `is_sliceable`
- [ ] Only enable "Load" button when `status == "COMPLETED"`
- [ ] Show `"Processing..."` indicator for PENDING/PROCESSING assets

### Asset Import (Load GLB)
- [ ] Get `download_url` from the asset object
- [ ] `GET <download_url>` — NO authorization header
- [ ] Pass raw bytes to GLTFUtility `ImportGLBAsync`
- [ ] Place `GameObject` at desired VR scene position
- [ ] (Optional) Cache GLB bytes to `Application.persistentDataPath` by `asset_id`
- [ ] (Optional) Re-fetch `GET /assets/{id}` if URL may have expired (> 1 hour old)
