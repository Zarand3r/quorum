"""
market.legacy — pre-refinement code preserved for reference.

The modules under here implement the original 10-dimension sentiment-vector
pipeline from before the project was refined to the news-impact market state
estimator (see ``PLAN.md``). They are NOT on the path for Slice 0 or any
milestone M1–M6.

Why kept: the JSON-extraction and rate-limiting plumbing are reusable for
the event-extraction stage of PLAN.md section 4.4 once Slice 0 lands.

Do not extend code in this subpackage. Build new functionality under
``market/`` directly.
"""
