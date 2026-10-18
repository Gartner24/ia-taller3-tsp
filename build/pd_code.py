#%% code
def astar(inst, budget=EXACT_BUDGET, h_kind="mst", start=0, use_cache=False, close_cycle=True,
          key_mode="state", trace=None):
    """A* over partial routes. key_mode 'last_city' and 'city_depth' are wrong merge rules, kept for the demo."""
    W, n = inst.W, inst.n
    meter = Meter(**budget)
    H = MSTHeuristic(W, start, h_kind, close_cycle, use_cache)
    key = {"state": state_key,
           "last_city": lambda nd: (nd.last, nd.closed),
           "city_depth": lambda nd: (nd.last, nd.depth, nd.closed)}[key_mode]
    root = root_node(n, start)
    tie = itertools.count()
    open_heap = [(H(root), 0, next(tie), root)]
    best_g = {key(root): 0}
    expanded = generated = stale = 0
    frontier_peak = 1
    goal, reason = None, "EXHAUSTED"
    try:
        while open_heap:
            meter.check_search(expanded)
            f, _, _, node = heapq.heappop(open_heap)
            if node.g > best_g[key(node)]:
                stale += 1
                continue
            if node.closed or (not close_cycle and node.remaining == 0):
                goal, reason = node, "GOAL"
                break
            expanded += 1
            children = successors(W, node, start, close_cycle)
            if trace is not None:
                trace.append({"step": expanded, "expanded": reconstruct(node), "g": node.g, "f": f,
                              "frontier_before": len(open_heap) + 1})
            for child in children:
                generated += 1
                k = key(child)
                if child.g < best_g.get(k, INF):
                    best_g[k] = child.g
                    heapq.heappush(open_heap, (child.g + H(child), -child.depth, next(tie), child))
            frontier_peak = max(frontier_peak, len(open_heap))
    except Interrupted as stop:
        reason = stop.reason
    elapsed, peak = meter.finish()
    tour = reconstruct(goal) if goal is not None else None
    cost = tour_cost(W, tour) if tour is not None else None
    exact = reason == "GOAL" and key_mode == "state" and close_cycle
    return RunResult(inst.name, inst.subset, "A* + MST" if h_kind == "mst" else "A* (h=0)", None,
                     dict(h=h_kind, start=start, cache=use_cache, key=key_mode, close_cycle=close_cycle),
                     tour, cost, gap_percent(cost, inst.optimum), elapsed, peak, reason,
                     "OPTIMAL" if exact else ("NO_TOUR" if tour is None else "NOT_CERTIFIED"),
                     expanded=expanded, generated=generated, mst_calls=H.mst_calls, frontier_peak=frontier_peak,
                     stale=stale, extra=dict(cache_hits=H.cache_hits, path_cost=goal.g if goal else None))
#%% code
def rbfs(inst, budget=EXACT_BUDGET, h_kind="mst", start=0, audit=False, trace=None):
    """Recursive best-first search with backed-up f values (section 8). audit=True counts regenerations."""
    W, n = inst.W, inst.n
    meter = Meter(**budget)
    H = MSTHeuristic(W, start, h_kind)
    st = dict(expanded=0, generated=0, calls=0, max_depth=0, retained=1, retained_peak=1, regenerations=0)
    seen = set() if audit else None    # external audit record; it costs memory, so it is off when measuring

    def search(node, f_node, limit):
        st["calls"] += 1
        st["max_depth"] = max(st["max_depth"], node.depth)
        meter.check_search(st["expanded"])
        if node.closed:
            return node, f_node
        children = successors(W, node, start)
        st["expanded"] += 1
        st["generated"] += len(children)
        if audit:
            k = state_key(node)
            if k in seen:
                st["regenerations"] += 1
            else:
                seen.add(k)
        if not children:
            return None, INF
        entries = [[max(c.g + H(c), f_node), c] for c in children]
        st["retained"] += len(entries)
        st["retained_peak"] = max(st["retained_peak"], st["retained"])
        try:
            while True:
                entries.sort(key=lambda e: e[0])          # stable: ties keep successor order
                best = entries[0]
                if best[0] == INF or best[0] > limit:
                    return None, best[0]
                alternative = entries[1][0] if len(entries) > 1 else INF
                if trace is not None:
                    trace.append({"call": st["calls"], "node": reconstruct(node), "limit": limit,
                                  "best": reconstruct(best[1]), "best_f": best[0], "alternative": alternative})
                result, best[0] = search(best[1], best[0], min(limit, alternative))
                if result is not None:
                    return result, best[0]
        finally:
            st["retained"] -= len(entries)

    root = root_node(n, start)
    goal, reason = None, "EXHAUSTED"
    try:
        goal, _ = search(root, H(root), INF)
        reason = "GOAL" if goal is not None else "EXHAUSTED"
    except Interrupted as stop:
        reason = stop.reason
    except RecursionError:
        reason = "RECURSION"
    elapsed, peak = meter.finish()
    tour = reconstruct(goal) if goal is not None else None
    cost = tour_cost(W, tour) if tour is not None else None
    return RunResult(inst.name, inst.subset, "RBFS + MST" if h_kind == "mst" else "RBFS (h=0)", None,
                     dict(h=h_kind, start=start, audit=audit), tour, cost, gap_percent(cost, inst.optimum),
                     elapsed, peak, reason, "OPTIMAL" if reason == "GOAL" else "NO_TOUR",
                     expanded=st["expanded"], generated=st["generated"], mst_calls=H.mst_calls,
                     frontier_peak=st["retained_peak"], regenerations=st["regenerations"] if audit else None,
                     calls=st["calls"], max_depth=st["max_depth"])
