# Section 1: Non-Functional Requirements

The following table outlines the key quality attributes and performance constraints for the VR Learning Platform.

| ID   | Category    | Requirement Description                                                                                                        |
| :--- | :---------- | :----------------------------------------------------------------------------------------------------------------------------- |
| NFR1 | Performance | The VR application must maintain a minimum of 72 FPS on target hardware (e.g., Meta Quest 2/3) to prevent motion sickness.     |
| NFR2 | Latency     | Network latency for multi-user synchronization (movement, voice, object interaction) should not exceed 100ms.                  |
| NFR3 | Scalability | The backend must support concurrent processing of uploaded 3D models without degrading the performance of active VR sessions.  |
| NFR4 | Reliability | The AI Smart Tutor service should have 99% uptime during active learning sessions.                                             |
| NFR5 | Usability   | The VR interface must be intuitive enough for a user to join a room and interact with an object within 2 minutes of first use. |
