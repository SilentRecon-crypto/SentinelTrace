"""
SentinelTrace — Experiment 2: Mule-Chain Identification (graph-based)

Unlike Experiment 1, the model is NEVER told which account is the mule.
It only observes a noisy transaction graph and must trace/rank candidate
accounts reachable from the victim's account.

Ground-truth fields (is_mule equivalent, ring_id, true_chain membership) are
generated here but explicitly stripped out before any model ever sees the
feature table — enforced in build_candidate_table() in experiment2_features.py,
and checked in the leakage audit at the end of run_experiment2.py.

World components:
  - legit_low / legit_high accounts        (background economy)
  - hub accounts                           (merchants/wallets: high fan-in,
                                             NOT fraud -- classic false-positive trap)
  - confusor accounts                      (legit but naturally fast pass-through
                                             behavior -- adversarial trap for any
                                             heuristic that flags "money in, money
                                             straight out" as automatically suspicious)
  - mule_pool accounts                     (some single-use, some REUSED across
                                             multiple simultaneous fraud rings)
Fraud cases:
  - 1-3 hop chains, victim -> mule_1 -> [mule_2] -> [mule_3]
  - variable pass-through delay (fast layering vs. dormant-then-move stealth)
  - decoy/background transactions on every account (mules included) so the
    graph is not "clean" -- most edges touching a mule account are irrelevant noise
"""
import numpy as np
import pandas as pd

def generate_world(seed=42, n_days=500,
                    n_legit_low=1500, n_legit_high=150, n_hub=15, n_confusor=60,
                    n_mule_pool=2200, n_complaints=500,
                    noise_level="medium", reuse_prob=0.35, obscure_amounts=False,
                    shared_pool_size=90, split_prob=0.0, missing_hop_prob=0.0,
                    adversarial_decoys=False):

    rng = np.random.default_rng(seed)
    noise_mult = {"low": 0.5, "medium": 1.0, "high": 2.2, "very_high": 4.5}[noise_level]
    # scale legit high-volume/hub/confusor populations with noise level too --
    # "very high noise" should mean a genuinely bigger, busier legitimate economy,
    # not just more random edges among the same small account set.
    n_legit_high = int(n_legit_high * max(1.0, noise_mult ** 0.6))
    n_hub = int(n_hub * max(1.0, noise_mult ** 0.5))
    n_confusor = int(n_confusor * max(1.0, noise_mult ** 0.7))
    # Realistic layering obscures the amount trail deliberately (splitting,
    # mixing with other funds, variable skims) -- default is a clean, narrow
    # decay band; obscure_amounts widens/breaks that relationship to test
    # whether performance depends on an unrealistically tidy assumption.
    hop_amount_range = (0.20, 1.55) if obscure_amounts else (0.80, 0.97)

    accounts = []
    aid = 0
    for _ in range(n_legit_low):
        accounts.append((aid, "legit_low", rng.integers(0, 200))); aid += 1
    for _ in range(n_legit_high):
        accounts.append((aid, "legit_high", rng.integers(0, 200))); aid += 1
    for _ in range(n_hub):
        accounts.append((aid, "hub", rng.integers(0, 50))); aid += 1
    for _ in range(n_confusor):
        accounts.append((aid, "confusor", rng.integers(0, 300))); aid += 1
    n_adv = 100 if adversarial_decoys else 0
    for _ in range(n_adv):
        # adversarial "bait" accounts: legit, but deliberately young + built to
        # mimic a mule's pass-through signature -- never part of any true chain
        accounts.append((aid, "adversarial_bait", rng.integers(0, 15))); aid += 1
    mule_start = aid
    for _ in range(n_mule_pool):
        accounts.append((aid, "mule", rng.integers(0, n_days))); aid += 1
    accounts = pd.DataFrame(accounts, columns=["account_id", "acc_type", "created_day"])

    legit_low_ids = accounts[accounts.acc_type == "legit_low"].account_id.values
    legit_high_ids = accounts[accounts.acc_type == "legit_high"].account_id.values
    hub_ids = accounts[accounts.acc_type == "hub"].account_id.values
    confusor_ids = accounts[accounts.acc_type == "confusor"].account_id.values
    adv_bait_ids = accounts[accounts.acc_type == "adversarial_bait"].account_id.values
    mule_ids = accounts[accounts.acc_type == "mule"].account_id.values
    all_nonmule = np.concatenate([legit_low_ids, legit_high_ids, hub_ids])

    txns = []  # (src, dst, day, hour, amount)

    # ---------------------------------------------------------------
    # 1. Background legitimate economy (noise), density scaled by noise_level
    # ---------------------------------------------------------------
    n_bg_txns = int(18000 * noise_mult)
    src_pool = np.concatenate([legit_low_ids, legit_high_ids, legit_high_ids])  # high-vol accts transact more
    for _ in range(n_bg_txns):
        src = rng.choice(src_pool)
        # hubs receive disproportionately (merchants/wallets)
        if rng.random() < 0.4:
            dst = rng.choice(hub_ids)
        else:
            dst = rng.choice(all_nonmule)
        if dst == src:
            continue
        day = rng.integers(0, n_days)
        txns.append((src, dst, day, rng.integers(0, 24), round(float(rng.lognormal(7.5, 1.1)), 2)))

    # ---------------------------------------------------------------
    # 2. Confusor accounts: legit, but naturally fast pass-through (mule lookalikes)
    # ---------------------------------------------------------------
    n_confusor_txns = int(3000 * noise_mult)
    for _ in range(n_confusor_txns):
        c = rng.choice(confusor_ids)
        day_in = rng.integers(0, n_days - 2)
        amt = round(float(rng.lognormal(8.0, 1.0)), 2)
        src = rng.choice(all_nonmule)
        txns.append((src, c, day_in, rng.integers(0, 24), amt))
        # quickly forwards most of it out, mimicking mule pass-through signature
        delay = rng.exponential(0.8)
        dst = rng.choice(all_nonmule)
        txns.append((c, dst, min(day_in + int(delay) + 1, n_days - 1), rng.integers(0, 24),
                     round(amt * rng.uniform(0.75, 0.98), 2)))

    # ---------------------------------------------------------------
    # 3. Mule pool background noise: mules ALSO do unrelated small txns sometimes
    # ---------------------------------------------------------------
    n_mule_bg = int(2500 * noise_mult)
    for _ in range(n_mule_bg):
        m = rng.choice(mule_ids)
        src, dst = (m, rng.choice(all_nonmule)) if rng.random() < 0.5 else (rng.choice(all_nonmule), m)
        day = rng.integers(0, n_days)
        txns.append((src, dst, day, rng.integers(0, 24), round(float(rng.lognormal(6.5, 1.0)), 2)))

    # ---------------------------------------------------------------
    # 4. Fraud cases: 1-3 hop chains, with reuse (shared mules / simultaneous rings)
    # ---------------------------------------------------------------
    shared_pool = rng.choice(mule_ids, size=shared_pool_size, replace=False)  # reusable subset
    decoy_mean = {"low": 1.5, "medium": 4.0, "high": 9.0, "very_high": 18.0}[noise_level]
    complaints = []
    for cid in range(n_complaints):
        day = int(rng.integers(5, n_days - 20))
        victim = int(rng.choice(legit_low_ids))
        n_hops = int(rng.choice([1, 2, 3], p=[0.28, 0.45, 0.27]))
        use_shared = rng.random() < reuse_prob
        pool = shared_pool if use_shared else mule_ids
        chain = list(rng.choice(pool, size=n_hops, replace=False))

        fraud_amount = round(float(rng.lognormal(9.5, 1.0)), 2)
        cur_day, cur_amount, cur_src = day, fraud_amount, victim
        # stealth vs rapid layering, mixed; a slow "sleeper" mode holds funds
        # for a long dwell time then moves them -- mimics a mule that never
        # trips a naive velocity/pass-through-ratio rule
        mode = rng.choice(["rapid", "stealthy", "sleeper"], p=[0.55, 0.30, 0.15])
        chain_nodes_and_times = []  # (account, time_it_becomes_active) for decoy injection
        chain_nodes_and_times.append((victim, day))
        missing_hop_idx = (rng.integers(0, n_hops) if (n_hops > 1 and rng.random() < missing_hop_prob) else -1)
        for hop_i, m in enumerate(chain):
            if mode == "sleeper":
                delay = rng.uniform(20, 45)
            elif mode == "stealthy":
                delay = rng.exponential(6.0)
            else:
                delay = rng.exponential(1.0)
            cur_day = min(int(cur_day + delay) + 1, n_days - 1)
            hop_amount = round(cur_amount * rng.uniform(*hop_amount_range), 2)  # skim/fees/mixing each hop

            if hop_i == missing_hop_idx:
                # untraceable leg (e.g. physical cash withdrawal + re-deposit):
                # DO NOT record this edge -- downstream chain becomes unreachable
                # via graph BFS from this point, a genuine real-world failure mode.
                pass
            else:
                txns.append((cur_src, m, cur_day, rng.integers(0, 24), hop_amount))

            # money splitting: with split_prob, the transfer branches into a
            # minor decoy leg (dead end) alongside the main chain continuation,
            # creating a genuine "which path is real" ambiguity at this hop
            if rng.random() < split_prob:
                minor_frac = rng.uniform(0.15, 0.40)
                minor_amt = round(hop_amount * minor_frac, 2)
                decoy_dst = rng.choice(all_nonmule)
                txns.append((cur_src, decoy_dst, cur_day, rng.integers(0, 24), minor_amt))

            chain_nodes_and_times.append((m, cur_day))
            cur_src, cur_amount = m, hop_amount

        # --- Adversarial bait: inject decoy accounts deliberately engineered to
        # mimic a mule's suspicious signature (young + fast pass-through) near
        # the true chain, without ever being part of it.
        if adversarial_decoys and len(adv_bait_ids) > 0:
            n_bait = rng.integers(1, 3)
            for _ in range(n_bait):
                bait = rng.choice(adv_bait_ids)
                src_node, t0 = chain_nodes_and_times[rng.integers(0, len(chain_nodes_and_times))]
                bait_amt = round(fraud_amount * rng.uniform(0.5, 1.1), 2)
                txns.append((src_node, bait, t0, rng.integers(0, 24), bait_amt))
                fwd_delay = rng.exponential(0.7)  # fast pass-through, mimicking a mule
                txns.append((bait, rng.choice(all_nonmule), min(t0 + int(fwd_delay) + 1, n_days - 1),
                             rng.integers(0, 24), round(bait_amt * rng.uniform(0.85, 0.98), 2)))

        # --- Decoy branching: every node along the true path ALSO has its own
        # unrelated activity within the tracing window -- this is what makes
        # forward-tracing genuinely hard, not just "follow the only edge."
        for node, t0 in chain_nodes_and_times:
            n_decoys = rng.poisson(decoy_mean)
            for _ in range(n_decoys):
                dst_pool = hub_ids if rng.random() < 0.3 else (
                    confusor_ids if rng.random() < 0.2 else all_nonmule)
                dst = rng.choice(dst_pool)
                if dst == node:
                    continue
                d = min(t0 + int(rng.integers(0, max(2, 10))), n_days - 1)
                txns.append((node, dst, d, rng.integers(0, 24),
                             round(float(rng.lognormal(6.5, 1.2)), 2)))
            # some decoys are INBOUND to the node too (other senders, unrelated)
            n_in_decoys = rng.poisson(decoy_mean * 0.6)
            for _ in range(n_in_decoys):
                src2 = rng.choice(all_nonmule)
                d = min(max(0, t0 - int(rng.integers(0, 5))), n_days - 1)
                txns.append((src2, node, d, rng.integers(0, 24),
                             round(float(rng.lognormal(6.0, 1.0)), 2)))

        complaints.append(dict(
            complaint_id=cid, victim=victim, day=day, fraud_amount=fraud_amount,
            n_hops=n_hops, chain=list(chain), used_shared_pool=use_shared,
            mode=mode, missing_hop_idx=missing_hop_idx,
        ))

    transactions = pd.DataFrame(txns, columns=["src", "dst", "day", "hour", "amount"])
    complaints = pd.DataFrame(complaints).sort_values("day").reset_index(drop=True)
    return accounts, transactions, complaints, dict(shared_pool=set(shared_pool.tolist()))


if __name__ == "__main__":
    accounts, transactions, complaints, meta = generate_world(seed=42, noise_level="medium")
    print(f"Accounts: {len(accounts)} ({(accounts.acc_type=='mule').sum()} mule pool)")
    print(f"Transactions: {len(transactions)}")
    print(f"Complaints: {len(complaints)}")
    print(complaints.n_hops.value_counts(normalize=True).round(3))
    print(f"Shared-pool usage rate: {complaints.used_shared_pool.mean():.2f}")
