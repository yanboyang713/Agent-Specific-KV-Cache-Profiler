# KVFlow Workflow

Baseline KVFlow / PEER-style workflow used by the profiler MVP.

Topology:

```text
planner -> executor -> expresser -> reviewer -> planner or END
```

The implementation lives in `workflows.kvflow.workflow`. The historical import
path `kv_cache_profiler.workflow` remains as a compatibility wrapper for the
CLI and existing downstream users.
