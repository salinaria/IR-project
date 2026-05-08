# Error Analysis (auto-generated)

## Case 1
- Query ID: `Q016`
- Query: `Counseling Services`
- Query type: `navigational`
- Expected relevant documents: The user is trying to get to the couneling services page
- Top-ranked non-relevant results: N/A
- Failure reason: BM25 lexical mismatch; ES retrieves alternative term variants that BM25 misses.
- Evidence: BM25 nDCG@10=0.5956, BM25 P@5=0.8000, Recall@10=0.2273; ES nDCG@10=0.9113 (delta=+0.3157)
- Proposed fix (do not implement): Add synonym expansion and domain vocabulary normalization before retrieval.

## Case 2
- Query ID: `Q098`
- Query: `how many credits do you need to graduate with a bachelor degree at Temple`
- Query type: `informational`
- Expected relevant documents: student planning their schedule wants to know the total credit hour requirement for a bachelor's degree
- Top-ranked non-relevant results: N/A
- Failure reason: Length/term-frequency bias in alternate ranking introduces off-target but term-heavy pages.
- Evidence: BM25 nDCG@10=0.6826, BM25 P@5=1.0000, Recall@10=0.3214; ES nDCG@10=0.2381 (delta=-0.4445)
- Proposed fix (do not implement): Tune field-length normalization and add a reranker with relevance features.

## Case 3
- Query ID: `Q051`
- Query: `Montgomery garage parking rate student`
- Query type: `informational`
- Expected relevant documents: The user wants to know the parking prices or rates for Montgomery Garage
- Top-ranked non-relevant results: N/A
- Failure reason: BM25 lexical mismatch; ES retrieves alternative term variants that BM25 misses.
- Evidence: BM25 nDCG@10=0.7393, BM25 P@5=0.8000, Recall@10=0.5000; ES nDCG@10=0.8421 (delta=+0.1027)
- Proposed fix (do not implement): Add synonym expansion and domain vocabulary normalization before retrieval.

## Case 4
- Query ID: `Q064`
- Query: `temple university main campus map pdf`
- Query type: `navigational`
- Expected relevant documents: Find a pdf document that contains a map of the temple university main capus
- Top-ranked non-relevant results: N/A
- Failure reason: Length/term-frequency bias in alternate ranking introduces off-target but term-heavy pages.
- Evidence: BM25 nDCG@10=0.7595, BM25 P@5=1.0000, Recall@10=0.2963; ES nDCG@10=0.5389 (delta=-0.2206)
- Proposed fix (do not implement): Tune field-length normalization and add a reranker with relevance features.

## Case 5
- Query ID: `Q084`
- Query: `temple university campus map pdf`
- Query type: `navigational`
- Expected relevant documents: Find and download a PDF map of the Temple University campus
- Top-ranked non-relevant results: N/A
- Failure reason: Length/term-frequency bias in alternate ranking introduces off-target but term-heavy pages.
- Evidence: BM25 nDCG@10=0.7595, BM25 P@5=1.0000, Recall@10=0.2963; ES nDCG@10=0.5389 (delta=-0.2206)
- Proposed fix (do not implement): Tune field-length normalization and add a reranker with relevance features.
