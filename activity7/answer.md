To complete this activity, execute your script and answer these 4 questions in your workspace submission markdown:

Which chunking strategy returned the most relevant text for your query? Look closely at the exact string fragment returned—did it capture the entire sentence context or was it cut off?
- Paragraph chunking typically yields the best match for this query. The sentence containing "overlap" is frequently sliced mid-though or mid-sentence depending on where the character index falls
What happened to the text structure in Fixed-Size Chunk #2 vs. Paragraph Chunk #2? Identify how boundaries changed word availability.
- This strategy uses a regex pattern to split text only when natural double-line break
Hypothetical Application: Imagine you are building a production AI system for a company's internal HR manual handbook. Why might relying exclusively on Fixed-Size character chunking create bad answers for employees?
- An AI or LLM retrieving only the first chunk would confidently tell an employee they get 4 weeks of paid leave, completely missing the crucial eligibility constraint in the next chunk.
The Metadata Payload: Why do we spend computing effort storing things like chunk_index and strategy inside the database alongside raw vectors? Why can't we just store the text string alone?
- If an LLM needs more context to answer a question, the application can use the chunk_index to fetch chunk_index - 1 and chunk_index + 1 from the database to reconstruct the surrounding text. 
- In production, AI systems must cite their sources. Storing the source payload allows the UI to show the user exactly which document (e.g., hr_policy_2026.pdf) the answer came from.
- Storing the strategy allows developers to filter, evaluate, and compare how different chunking strategies perform in production, making it easy to identify which pipeline configuration is yielding bad data.