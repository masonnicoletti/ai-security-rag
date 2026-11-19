# Index benchmark: minilm:struct-v1

- vectors: 2307 x 384d; queries: 439 document titles; k=10
- HNSW build (M=32, efConstruction=200): 0.195s (mean of 3)
- single-threaded, one query at a time, best of 3 runs; query embedding time excluded

| index | efSearch | recall@10 vs exact | QPS | ms/query |
|---|---|---|---|---|
| exact (numpy) | - | 1.000 | 22,027 | 0.045 |
| HNSW | 4 | 0.778 | 86,308 | 0.012 |
| HNSW | 8 | 0.889 | 76,160 | 0.013 |
| HNSW | 16 | 0.949 | 60,025 | 0.017 |
| HNSW | 32 | 0.979 | 40,652 | 0.025 |
| HNSW | 64 | 0.991 | 24,525 | 0.041 |
| HNSW | 128 | 0.998 | 13,736 | 0.073 |
| HNSW | 256 | 0.999 | 6,922 | 0.144 |

Query embedding alone: 3.2 ms/query (mean of 100), which dominates end-to-end latency at this corpus size.
