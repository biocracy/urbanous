---
trigger: always_on
description: "Project-specific rules for Urbanous"
---

# Deployment Rules

1. **Version Increment**:
   - WHENEVER you push code to Github, you MUST increment the application version number by `0.001`.
   - The version is displayed in the lower right corner of the UI.
   - Example: `v0.1` -> `v0.101` -> `v0.102`.
   - **Stop Condition**: If the version reaches `v0.999`, STOP and notify the user (do not increment to 1.0 automatically without approval).


2. Upload to Github at most once per prompt, when the thought process and debugging has finished. Do not upload and then start thinking again!


3. whenever a propmpt start with the word "question", don't change any code, just answer the what was asked in that prompt.