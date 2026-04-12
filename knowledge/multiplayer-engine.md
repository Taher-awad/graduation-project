# Graduation V1 Multiplayer Backend

## Overview
This component constitutes the foundational real-time multiplayer engine tailored for the EduVR platform. It is a standalone system built using **Rust** for the backend server and natively integrated with **Unity** via customized C# client scripts.

The engine uses **WebSockets** for low-latency, bi-directional communication, employing high-performance concurrency and compact binary serialization.

---

## 🦀 Rust Backend Architecture

### 1. Technology Stack
- **Async Runtime:** `tokio` (Handles high-concurrency connections).
- **Web Server:** `axum` (Provides robust routing and WebSocket (`ws`) extraction).
- **Serialization:** `bincode` (Used over JSON for extremely compact and fast binary packet transmission) & `serde`.
- **State Management:** `dashmap` (Allows lock-free, concurrent mutation of shared application states by multiple threads without heavy Mutex blocking).

### 2. State Management (`state.rs`)
The system tracks state at the room level. The global state contains multiple isolated `rooms`.
Inside each `Room`:
- **Users**: A map of connected users, storing their Role (Teacher/Student), 3D spatial properties (`position`, `rotation`), and their WebSocket sender channel.
- **Objects**: A map of spatial objects within the room, maintaining `position`, `rotation`, `scale`, and an `owner_id` (used for grab/release mechanics and preventing concurrent physics alterations).

### 3. Protocol & Packets (`protocol.rs`)
The engine communicates via the `EduPacket` enum. Key multiplayer events include:
- `Join { user_id, role }`
- `PlayerMove { position, rotation }`
- `ObjectMove { position, rotation }`
- `Grab / Release { object_id }`
- `Slice { object_id, hit_point, normal }` - Enables the advanced 3D slicing feature required for anatomy/engineering models.
- `Spawn / Despawn { object_id }`
- `FullSync` - Dispatched when a new user joins to catch them up on the current room state.

---

## 🎮 Unity Client Integration (`unity/scripts/`)

The backend is explicitly designed to pair with custom Unity scripts contained in the `unity` directory.

### Key Scripts:
1. **`NetworkManager.cs`**: The core client-side WebSocket manager handling connection lifecycle and dispatching received packets to the relevant sub-systems.
2. **`BincodeSerializer.cs`**: A custom deserializer built in C# to decode the Rust `bincode` binary format natively within Unity. This avoids JSON string parsing overhead on the Meta Quest hardware.
3. **`PlayerSync.cs`**: Subscribes to `PlayerMove` packets to interpolate and render network avatars locally.
4. **`ObjectSync.cs`**: Handles `ObjectMove`, `Grab`, and `Release` states for interactable 3D models.
5. **`UnityMainThreadDispatcher.cs`**: Crucial utility for Unity. Since WebSocket events arrive on background threads, this enqueues them to execute on Unity's main thread (required for modifying Transforms or GameObjects).

---

## Conclusion
This isolated engine is highly performant. By substituting standard JSON-over-HTTP with **Bincode-over-WebSockets**, it directly targets the stringent NFR latency requirements (<100ms) necessary for preventing motion sickness in multi-user VR (Meta Quest 2/3).
