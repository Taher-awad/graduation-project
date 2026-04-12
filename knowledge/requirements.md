# EduVR Requirements Listing

## Functional Requirements (FR)
| ID  | Description |
|-----|-------------|
| **FR1** | The system shall allow instructors and students to join shared virtual learning sessions. |
| **FR2** | The system shall support real-time multi-user interaction within a virtual environment. |
| **FR3** | The system shall allow instructors to control and manipulate shared 3D models. |
| **FR4** | The system shall allow students to view and interact with 3D models. |
| **FR5** | The system shall provide an AI Smart Tutor (EduVR Core) to answer user questions. |
| **FR6** | The system shall support text and voice-based interaction with the AI tutor. |

## Non-Functional Requirements (NFR)
| ID  | Category | Description |
|-----|----------|-------------|
| **NFR1** | Performance | The VR app must maintain a minimum of 72 FPS on target hardware (e.g., Meta Quest 2/3) to prevent motion sickness. |
| **NFR2** | Latency | Network latency for multi-user synchronization (movement, voice, object interaction) should not exceed 100ms. |
| **NFR3** | Scalability | The backend must support concurrent processing of uploaded 3D models without degrading active VR session performance. |
| **NFR4** | Reliability | The EduVR Core service should have 99% uptime during active learning sessions. |
| **NFR5** | Usability | The VR interface must be intuitive enough for a user to join a room and interact with an object within 2 minutes of first use. |
