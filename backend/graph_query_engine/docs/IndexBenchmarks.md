# Index Benchmark Suite Documentation

## Purpose
`IndexBenchmarkSuite` measures construction throughput, cold vs warm build latency, memory footprint, and lookup complexity across index layers.

---

## Metrics Captured
- **Total Build Duration**: Construction time in seconds over a given `GraphView`.
- **Estimated Total Memory**: RAM footprint calculation across lookup maps, CSR slices, and semantic indexes.
- **Lookup Complexity**: Algorithmic complexity guarantee (O(1) Hash / CSR-slice).
