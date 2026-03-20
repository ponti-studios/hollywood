# Phase 2: The Agentic Loop — Teaching a Model to Look Things Up

## The Core Idea

Imagine hiring a brand-new employee who is sharp, logical, and hardworking — but who has been living off-grid for the past five years and missed a lot of world events. You wouldn't fire them. You'd give them a computer and an internet connection.

Phase 2 does exactly that for our 3B model. Instead of relying on whatever facts happened to be baked into the model during training, we give it the ability to search the web and retrieve relevant documents in real time. This transforms the model from a closed book into an open-book exam taker.

The technical term for this setup is an **agentic loop** — a cycle where the model doesn't just generate one answer and stop, but instead decides what information it needs, goes to get it, reads what it finds, and *then* generates an answer.

---

## What "Agentic" Actually Means

A standard language model works like this:

```
  You ask a question
        │
        ▼
  Model searches its memory (its weights)
        │
        ▼
  Model outputs an answer
        │
        ▼
  Done. No going back.
```

An agentic model works like this:

```
  You ask a question
        │
        ▼
  Model thinks: "Do I know this, or should I look it up?"
        │
     ┌──▼──────────────────────────────────┐
     │  I know this → Generate answer      │
     └─────────────────────────────────────┘
        │
     ┌──▼──────────────────────────────────┐
     │  I don't know → Pick a tool         │
     │                                     │
     │   WebSearchTool: search the web     │
     │   DocRetrievalTool: search docs     │
     └──────────────┬──────────────────────┘
                    │
                    ▼
          Tool runs and returns results
                    │
                    ▼
          Model reads the results
                    │
                    ▼
          Model generates a grounded answer
```

The critical skill here — the one we're testing — is whether a 3B model can reliably *decide when to use a tool*. A model that searches everything wastes time. A model that never searches will hallucinate facts. We want a model that knows what it knows and knows what it doesn't.

---

## The Two Tools

### WebSearchTool

Queries a search engine (or a local search index for offline runs) and returns the top snippets from search results. The model is given a window of ~512 tokens from the most relevant results.

```
Model Input:   "What year did Burkina Faso gain independence?"

Tool Call:     WebSearchTool("Burkina Faso independence year")

Tool Returns:  "Burkina Faso gained independence from France on
                August 5, 1960. The country was formerly known as
                Upper Volta. Independence Day is a national holiday..."

Model Output:  "Burkina Faso gained independence on August 5, 1960."
```

The model doesn't just get the raw search results — it gets a formatted snippet with a source label, so it can learn to cite where information came from (which also helps catch hallucinations).

### DocRetrievalTool (RAG)

RAG stands for Retrieval-Augmented Generation. Instead of searching the open web, this tool searches a private, curated library of documents — things like Python documentation, API references, research papers, or any corpus we load in advance.

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Library                         │
│                                                             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│   │  Python     │  │  HuggingFace│  │  Research       │   │
│   │  Docs       │  │  Docs       │  │  Papers         │   │
│   │  (chunked)  │  │  (chunked)  │  │  (chunked)      │   │
│   └─────────────┘  └─────────────┘  └─────────────────┘   │
│            │                │                │             │
│            └────────────────┼────────────────┘             │
│                             │                              │
│                    ┌────────▼─────────┐                    │
│                    │  Vector Index    │                    │
│                    │  (ChromaDB)      │                    │
│                    └────────┬─────────┘                    │
└─────────────────────────────┼───────────────────────────── ┘
                              │
           Query: "How do I use LoRA with PEFT?"
                              │
                    ┌─────────▼─────────┐
                    │  Similarity Search │
                    │  Top 3 chunks     │
                    └─────────┬─────────┘
                              │
                    Returns relevant documentation
```

The documents are split into small chunks (~300 words each), converted into numerical vectors (embeddings), and stored in a vector database (ChromaDB). When the model needs something, it converts its query into a vector too, and the database finds the most similar chunks — like a hyper-precise keyword search.

---

## The Full Agentic Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENTIC LOOP                               │
│                                                                 │
│   Question arrives                                              │
│        │                                                        │
│        ▼                                                        │
│   ┌──────────────────────────────────────────────────────┐     │
│   │  3B Model — Step 1: Plan                             │     │
│   │                                                      │     │
│   │  "I need to answer X. Do I know this?                │     │
│   │   No → I'll use WebSearchTool with query Y"          │     │
│   └──────────────────────┬───────────────────────────────┘     │
│                          │ Tool call                           │
│                          ▼                                      │
│   ┌──────────────────────────────────────────────────────┐     │
│   │  Tool Executor                                       │     │
│   │                                                      │     │
│   │  Receives: { tool: "WebSearch", query: "Y" }         │     │
│   │  Runs: actual HTTP request / vector search           │     │
│   │  Returns: text snippets + source labels              │     │
│   └──────────────────────┬───────────────────────────────┘     │
│                          │ Results                             │
│                          ▼                                      │
│   ┌──────────────────────────────────────────────────────┐     │
│   │  3B Model — Step 2: Read & Synthesize                │     │
│   │                                                      │     │
│   │  Context now includes: [original question]           │     │
│   │                        [search results]              │     │
│   │                                                      │     │
│   │  "Based on the search results, the answer is..."     │     │
│   └──────────────────────┬───────────────────────────────┘     │
│                          │ Final answer                        │
│                          ▼                                      │
│                    Scored vs ground truth                       │
└─────────────────────────────────────────────────────────────────┘
```

The model can call tools multiple times if it needs to refine its search. There's a cap of 3 tool calls per question to prevent runaway loops — after 3 calls, the model must commit to an answer with whatever information it has.

---

## What We're Testing

We re-run the same TriviaQA and MMLU samples from Phase 1, but now the 3B model has access to its tools. The comparison is:

| Test | 3B (no tools) | 3B (with tools) | 70B (no tools) |
|------|--------------|-----------------|----------------|
| TriviaQA | ~38% | Target: 65%+ | ~81% |
| MMLU | ~44% | Target: 60%+ | ~76% |

If the tool-equipped 3B significantly closes the gap with the 70B on knowledge tasks, we've proven the central claim: **storage can be outsourced to search**.

We also track:
- **Tool call rate** — what percentage of questions trigger a search?
- **Search precision** — when the model does search, does it get useful results back?
- **Hallucination rate** — does having tool access actually reduce made-up answers?

---

## The Tricky Part: Teaching the Model When to Search

This is the hardest part of Phase 2. A model trained purely on text has no built-in concept of "I should use a tool here." We use a structured prompting technique where the model is shown examples of the decision-making process:

```
System prompt (simplified):
  You are a careful assistant. When asked a question,
  first decide if you need to look something up.

  If you need to search, output:
    [SEARCH: your query here]

  If you can answer from reasoning alone, output:
    [ANSWER: your answer here]

  After a search result is returned, you may search
  again or commit to a final answer.
```

This structured format makes the model's decision-making *visible* and *scorable* — we can see exactly when it chose to search and whether that choice was correct.

---

## What Comes Next

Phase 2 proves that knowledge can be fetched on demand. But fetching the right fact is only half the battle. What if the model reasons *about* that fact incorrectly? What if it writes code based on the retrieved documentation but makes a logical error in the process?

Phase 3 addresses exactly that — building in a structured self-review step where the model checks its own work before submitting a final answer.
