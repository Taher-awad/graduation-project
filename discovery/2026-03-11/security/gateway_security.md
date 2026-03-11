# API Gateway Security Strategy

## Approach: Zero-Trust Perimeter & Load Balancing

### Current Vulnerability
React communicates directly with `http://localhost:8000`. In a microservices architecture, exposing internal services directly to the public internet causes port confusion and enables direct denial-of-service (DoS) vectors on inner worker orchestration logic.

### Implementation Path
1. **Unified Perimeter (Traefik or NGINX):**
   - Place a Reverse Proxy in front of everything.
   - The React frontend targets *only* `https://api.cortex.edu/`.
   - The Gateway inspects the URL path and cleanly re-routes:
     - `/auth/*` -> `service-auth:8000`
     - `/rooms/*` -> `service-rooms:8000`
     - `/assets/*` -> `service-assets:8000`
2. **CORS Enforcement:**
   - Instead of wildcard `allow_origins=["*"]` spread across all microservices, centralize CORS policies strictly at the Gateway. Ensure only verified production VR Headset IPs and the verified origin of the Web Dashboard can pre-flight options requests.
3. **Global Rate Limiting:**
   - Establish aggressive, tier-based rate limits. For example, general API calls are capped at 100/min per IP, while `/assets/upload` is capped at 5/min per IP.
4. **DDoS Protection:**
   - Configure timeouts to drop "Slowloris" attacks (malicious clients sending 1 byte of data per minute to exhaust connection pools).
