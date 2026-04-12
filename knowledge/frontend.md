# Frontend Knowledge: EduVR React App

## Stack

| Library | Version | Role |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | ~5.9 | Type safety |
| Vite | 7 | Build tool + dev server |
| React Router | 7 | Client-side routing |
| TanStack Query | 5 | Server state, caching |
| Axios | 1.13 | HTTP client (via `api/client.ts`) |
| React Three Fiber | 9 | Three.js in React |
| @react-three/drei | 10 | Three.js helpers |
| Three.js | 0.182 | 3D rendering |
| Framer Motion | 12 | Animations |
| Tailwind CSS | 4 | Styling |
| Lucide React | latest | Icons |
| jwt-decode | 4 | JWT payload parsing |

## Pages

| Route | Component | Auth Required | Description |
|---|---|---|---|
| `/login` | `Login.tsx` | ❌ | Login form |
| `/register` | `Register.tsx` | ❌ | Registration form with role select |
| `/` | `Assets.tsx` | ✅ | Asset upload, list, status monitoring |
| `/rooms` | `Rooms.tsx` | ✅ | Room management, invitations |

## Context Providers

- `AuthContext` — stores JWT token, user info, login/logout
- `ThemeContext` — light/dark mode toggle

## API Client

`src/api/client.ts` — Axios instance configured with:
- Base URL from env (`VITE_API_URL` or `http://localhost:8000`)
- Auth interceptor attaches `Authorization: Bearer <token>` to every request

`src/api/rooms.ts` — typed wrappers around room API calls

## Key Patterns

### Protected Routes
```tsx
<ProtectedRoute>   // Redirects to /login if no token
  <DashboardLayout />
</ProtectedRoute>
```

### SSE for Real-time Notifications
The Assets page opens an EventSource connection to:
```
/notifications/stream/{user_id}
```
Receives processing status updates, triggers TanStack Query refetch on COMPLETED.

### Asset Upload Flow (Frontend)
1. User selects file + type + sliceable flag
2. `POST /assets/upload` (multipart) → gets `{id, status: PENDING}`
3. SSE subscription active → events stream in
4. On COMPLETED → refetch asset list → `download_url` available

## Environment Variables

```env
VITE_API_URL=http://localhost:8000
```

## Development

```bash
# Runs via docker-compose (hot reload mounted volume)
# Or locally:
cd frontend
npm install
npm run dev    # http://localhost:5173
```
