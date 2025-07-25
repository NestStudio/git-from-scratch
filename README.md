# Build Your Own Git

Recreate a simplified version of Git from scratch to deepen your understanding of version control internals: object storage, commits, branches, and cloning.

---

## 🎯 Purpose

This project is educational—not production-grade. It encourages you to build Git-like features by hand, empowering you to internalize how version control truly works. Inspired by the CodeCrafters approach, it guides you through staged exercises with tests that validate each step.

---

### 🛠️ What You'll Learn

- How to initialize a `.git` repository
- Creating and reading Git objects (blobs, trees, commits)
- Content-addressable storage using hashes
- Simple branch management and references
- Logic to reconstruct directory states from stored objects
- A basic implementation of cloning a public repository

---

### 🚧 Why Build Git from Scratch?

You’ll get hands-on experience with:

- Designing and working with low-level data structures
- Hash-based content lookup
- Versioning logic behind branching and commit history
- CLI-style command flows (e.g. `init`, `add`, `commit`, `log`, `checkout`)

This approach demystifies Git's plumbing and clarifies what happens beneath typical high-level Git commands.

---

### ⚡ How It Works

1. **Stage-based Progression**  
   The project is divided into clear stages. Each stage has tests (initially failing) that define the next task. Push your solution when ready. This TDD-like workflow encourages focused, test-driven learning.

2. **Language Flexibility**  
   You can choose any supported language (e.g. Python, Go, Rust, TypeScript, Java, C++, C#). You’re free to switch as you go.

3. **Testing & Submission**  
   Solutions are typically verified via Git pushes to a dedicated testing repo. Optionally, you can mirror progress to GitHub for visibility and documentation.

---
