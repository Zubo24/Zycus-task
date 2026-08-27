# Design Note

Building this pipeline on a 1B local model (`gemma3:1b`) was a really interesting challenge. Without a massive frontier model to lean on, I had to be much more intentional about the system architecture. Here's how I approached the hard constraints and what I learned along the way.

## 1. What broke and how I fixed it

During development, the pipeline failed in a few really illuminating ways:

- **The Stale Date Bug:** Originally, I was filtering tickets using `datetime.now()` for the 90-day window. Because the mock dataset is from 2025, running this on my machine today returned exactly zero recent tickets for every account. I caught this when Task 2 returned blank outputs. To fix it, I anchored the "current date" dynamically to the `max(created_at)` across the entire dataset. It's much more robust this way.
- **The "Nested Schema" Collapse:** Small models like `gemma3:1b` just flat-out refuse to output complex, nested JSON arrays reliably. When I asked it to extract multiple verbatim quotes into a Pydantic list of objects, it crashed or hallucinated completely new text. I fixed this by splitting the process: first, a dead-simple text prompt just asking for a bulleted list of quotes, and then a second LLM call to build the JSON brief using those quotes. I also added a hard, rule-based post-check (`is_verified`) that aggressively checks if the exact string exists in the source text. I don't trust the LLM at all here!
- **The Empty-Data Hallucination:** I noticed some test cases (like `ACC-7893`) had zero recent tickets and empty escalation notes. However, because the LLM was still being asked to "extract risks", it felt forced to invent them, confidently hallucinating JSON keys as if they were quotes. You can't prompt-engineer your way out of that on a 1B model. Instead, I added a hard code-level input guard: if the ticket and note data are both empty, we skip the LLM call entirely and just return a templated "Account appears stable" brief. 

## 2. Latency vs. Quality

Because I was constrained to a local 1B model (zero API budget), I traded away instruction-following capabilities for zero network latency and zero cost. 

To make this small model work, I had to build a lot of application-level scaffolding: multi-step extractions, schema retries, and strict deterministic validation checks. If latency were my primary constraint (e.g. for a real-time agentic chat), I would migrate to a hosted frontier model. A stronger model would let me collapse the two-step extraction into a single prompt, remove the recursive retry logic, and potentially parallelize the triage and retrieval steps, which would drastically speed up the response time.

## 3. Data Privacy & PII

The biggest win of this Ollama architecture is privacy. Ticket bodies and customer data never leave my local machine. This is a massively stronger privacy guarantee than sending PII to Anthropic or OpenAI.

That being said, if we were deploying this to production, we couldn't just rely on "it's local." We would still need a dedicated redaction layer (like Presidio) to scrub PII *before* it gets written to application logs, and we'd need strict access controls on the inference server's request history.

## 4. Scaling up

Right now, running `gemma3:1b` sequentially on my CPU takes about 15-30 seconds per request. If we scaled this to 10x the ticket volume, the queue would instantly bottleneck.

To handle scale, we'd have to move to GPU-accelerated infrastructure or a hosted API that supports massive batch concurrency. But doing that just reintroduces the exact cost, latency, and data privacy trade-offs I mentioned above. It's all about picking the right constraint for the business!
