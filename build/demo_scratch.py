for name in MANDATORY:
    for k in (6, 7, 8, 10):
        sub = INSTANCES[name].subproblem(k)
        good = astar(sub)
        bad = astar(sub, key_mode="city_depth")
        nr = astar(sub, close_cycle=False)
        tr = []
        rb = good
        backs = 0
        print(name, k, "A*", good.cost, good.expanded, round(good.elapsed_seconds, 3), "| lastcity", bad.cost,
              "| noreturn path", nr.extra["path_cost"], "cycle", nr.cost,
              "| rbfs", rb.cost, rb.expanded, rb.regenerations, rb.calls, "backtracks", backs, round(rb.elapsed_seconds, 3), rb.stop_reason)
