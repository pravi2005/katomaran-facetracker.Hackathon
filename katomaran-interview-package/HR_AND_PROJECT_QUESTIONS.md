# HR and project-ownership questions

Answer in your own words; use only facts that are true for you.

**Tell me about this project.** Use the 1-minute version in `PROJECT_OVERVIEW.md`.

**What was your role / what did you build?** "I defined the requirements and architecture, reviewed and decided the key design questions (presence keyed by Face ID, seconds-based timeout, EXIT on shutdown, timestamps), used an AI coding assistant to generate and iterate the code, and I'm responsible for running, calibrating and explaining it." (Adjust to what you actually did.)

**Did you use AI? How do you know the code is right?** "Yes. I used it for planning and code generation. I validated the logic with 93 automated tests that run the real pipeline against scripted detections, I reviewed module by module, and I ran it on the real video myself to calibrate the threshold. I'm clear about what I haven't verified."

**Hardest problem?** "Making sure one visit gives exactly one ENTRY/EXIT even when detection flickers or the tracker changes IDs - solved by a state machine keyed by Face ID with a seconds-based timeout."

**A bug you found?** Fill in from your real testing. (Example of an issue found during the build: logging a misleading similarity value for the first-ever registration, now omitted when the gallery is empty.)

**What would you improve with more time?** Periodic identity re-verification, multi-embedding templates per person, Kalman/Hungarian tracking or Ultralytics BYTETracker, liveness detection, door-line ENTRY/EXIT, multi-camera support with PostgreSQL + FAISS, a dashboard, retention/consent controls.

**How did you handle privacy?** Face data stays local, git-ignored; embeddings and RTSP credentials never logged; `.env` for secrets; documented retention/consent as a requirement for real deployments.

**What did you learn?** Separation of concerns (detect/track/recognise/presence), why thresholds must be calibrated, state machines for event correctness, resilient I/O, test-friendly design with dependency injection.

**How do you handle deadlines/pressure?** Plan in phases, get the core path working first, document assumptions, mark unverified parts honestly.

**Teamwork?** Fill in honestly (this project was built individually with an AI assistant unless you worked with others).

**Why Payoda / why this role?** Personal answer - connect: end-to-end ownership, production-minded error handling, tests, documentation.
