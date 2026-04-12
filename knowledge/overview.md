# EduVR: AI-Powered Collaborative Virtual Reality Learning Platform

## Project Overview
**EduVR** is a collaborative Virtual Reality (VR) learning platform designed to address the limitations of traditional 2D education by creating an immersive and interactive environment. It is particularly focused on fields requiring high spatial awareness, such as medicine and engineering.

## Terminology
- **The Pipeline**: Refers to the entire project ecosystem (API Gateway, Microservices, Frontend, Asset Processing) *excluding* the multiplayer engine.
- **The Multiplayer Engine**: Refers specifically to the standalone Rust server (`graduation-v1-multiplayer-backend`) and its associated Unity scripts.

## Key Objectives
- Allow instructors and students to join shared virtual classrooms regardless of physical location.
- Enable users to explore, dissect, and discuss high-fidelity 3D models in real-time.
- Modernize laboratory education, enhance collaboration, and improve conceptual retention.

## Current Phase Deliverables
1. **Educational Content Templates**:
   - *Anatomy Template*: Immersive environment for medical education using the open-source Z-Anatomy atlas.
   - *Mathematics Visualization Template*: Interactive environment for visualizing complex mathematical functions and geometric concepts in 3D space.

2. **Core Technical Modules**:
   - *Automated 3D Model Processor*: A robust automated pipeline for ingesting, validating, and optimizing 3D models.
   - *Asset Management System*: Centralized web interface with Role-Based Access Control (RBAC) to manage the 3D library.
   - *Collaboration Room Manager*: Subsystem for orchestrating multi-user sessions bridging the web platform and the multiplayer VR environment.

## Future Work (Phase 2)
- **Online Unity System**: Finalizing the robust multi-user networking layer.
- **AI Builder Assistant**: Tool to assist instructors in creating 3D content effortlessly.
- **RAG-Powered AI Tutor**: Connecting the AI Tutor interface to the main backend (EduVR Core) for context-aware responses based on educational material.

## Project Team (Alamein International University)
- Taher Awad (21100797)
- Ahmed Abdo (21100788)
- Ahmed Wageh (21100842)
- Ali Yasser Ali (21100801)
- Mahmoud Abdelhady (22100680)
- **Supervised by**: Dr. Mahmoud Gamal
