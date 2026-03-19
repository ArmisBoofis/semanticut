stepsCompleted: [1, 2]
inputDocuments: []
date: 2026-03-17
author: Armand
---

# Product Brief: semanticut

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

Semanticut is a proof‑of‑concept web application that lets users jump directly to the right moment in a video by typing a natural‑language description of a scene. Instead of scrubbing through long recordings or remembering exact quotes, users can describe what was being discussed (“the part where they argue about the contract in the office”) and immediately land on the relevant segment.

The primary goal of this POC is to showcase a clean, well‑engineered end‑to‑end pipeline built on the Mistral SDK: audio extraction, high‑quality Voxtral transcription, semantic chunking, embedding with pgvector, and fast retrieval of the best‑matching scene. Accuracy on fuzzy descriptions, contextual understanding of conversations, and solid code architecture are prioritized over large‑scale production concerns.

---

## Core Vision

### Problem Statement

When people want to rewatch a specific moment in a video—whether it is a movie scene or a personal recording—they often remember only what was being said, not the exact timestamp. Current players force them to scrub blindly through long timelines, guessing and rewinding until they stumble upon the right scene. This is frustrating, slow, and breaks the viewing experience.

### Problem Impact

For longer videos, this turns a quick “replay that moment” task into a trial‑and‑error process. Users waste time, lose focus, and sometimes give up before finding the scene they had in mind. For anyone who frequently revisits recordings (talks, calls, movies, personal videos), the friction accumulates into a persistent annoyance.

### Why Existing Solutions Fall Short

Most video players and platforms focus on time‑based navigation (progress bars, thumbnails, chapters) or require exact keyword search in manually added metadata. They generally:
- Do not understand the conversational context inside the video.
- Require users to know exact phrases or rely on manually curated timestamps.
- Provide poor support for vague, natural‑language descriptions of scenes.

As a result, they fail when the user only remembers “the part where they talk about X in Y place” rather than an exact quote.

### Proposed Solution

Semanticut provides semantic search over video speech: users type a natural‑language description of the scene they remember, and the system maps that description to the most relevant time range in the video. The pipeline is:

1. Admin uploads a video.
2. Audio is extracted and sent to Mistral’s Voxtral for transcription.
3. The transcript is chunked into context‑aware segments (not too small, to preserve conversational flow).
4. Each chunk is embedded and stored in PostgreSQL with pgvector.
5. At query time, the user enters a vague description; the system embeds it, performs vector search, and returns the best‑matching chunk and its timestamp, seeking the video player to that scene.

The POC focuses on a limited set of test videos and on speech‑only understanding, keeping the scope tight while demonstrating the full technical pipeline.

### Key Differentiators

- **Fuzzy, context‑aware search**: Optimized for vague scene descriptions and broader conversational context rather than exact quote matching, with chunk sizes tuned to capture meaningful dialogue segments.
- **End‑to‑end Mistral SDK showcase**: Uses Voxtral for transcription and Mistral embeddings in a coherent, production‑inspired pipeline.
- **Clean, inspectable architecture**: FastAPI backend, Next.js frontend, PostgreSQL + pgvector, and SQLAlchemy/Alembic, all orchestrated via Docker Compose, with emphasis on clarity, separation of concerns, and maintainable code.
- **Performance‑conscious design**: Retrieval and search flows designed so that even with LLM‑powered components, end‑to‑end query latency remains within an acceptable demo window (targeting well under 20–30 seconds from search to scene jump).
