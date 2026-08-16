
# DevBrain

> Understand the impact before you change the code.

DevBrain is a developer tool that analyzes GitHub repositories and builds a structural view of the codebase.

It helps developers explore:

- Functions
- Classes
- Methods
- API routes
- Files
- Dependencies
- Callers and callees
- Code relationships
- Potentially affected components

The current core feature is **Impact Radar**.

## Live Demo

🌐 **Try DevBrain:**  
https://devbrain-gilt.vercel.app/

💻 **Source Code:**  
https://github.com/punithmg59/devbrain

---

## What is DevBrain?

Changing one function can affect many other parts of a codebase.

Finding those relationships manually becomes difficult as a repository grows.

DevBrain analyzes the repository structure and helps answer questions like:

> "If I change this function, what else could be affected?"

Instead of only showing code, DevBrain maps relationships between code elements and provides evidence for those relationships.

---

## Current Features

### 🔎 Repository Analysis

Connect a GitHub repository and run an analysis of its codebase.

DevBrain extracts structural information about the repository, including:

- Files
- Functions
- Classes
- Methods
- API routes
- Code relationships
- Dependencies

Analysis runs as a background job so large repositories do not block the API request.

---

### 🧭 Explore Repository

After analysis, explore the repository through:

- Functions
- Classes
- Methods
- API routes
- Repository statistics

Selecting a code element opens its available repository intelligence, including:

- Source location
- Parent class/file
- Callers
- Callees
- Dependencies
- Related files
- API relationships
- Potentially affected components
- Repository evidence

Information is shown from the repository analysis rather than generated mock data.

---

### 🎯 Impact Radar

Impact Radar is the core DevBrain feature.

Select a:

- Function
- Class
- Method
- API route

Then choose a change type:

- Modify
- Rename
- Move
- Delete

DevBrain uses the repository's dependency relationships to determine potentially affected code.

The goal is to help developers understand the consequences of a change **before modifying the code**.

---

## How It Works

```text
GitHub Repository
        │
        ▼
 Repository Analysis
        │
        ▼
 Code / AST Analysis
        │
        ▼
 Functions / Classes / Methods / API Routes
        │
        ▼
 Nodes + Relationships
        │
        ▼
 PostgreSQL
        │
        ▼
 Dependency Graph
        │
        ├───────────────┐
        ▼               ▼
 Explore Repository   Impact Radar
        │               │
        ▼               ▼
 Code Intelligence   Change Impact
