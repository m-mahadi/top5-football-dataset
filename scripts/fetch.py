"""Shared parallel fetch helper. Network-bound pulls are I/O blocked, so a small
thread pool gives a near-linear speedup. Kept modest (8 workers) to stay polite
to the public endpoints we rely on.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import tls_requests

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}


def get_json(url, tries=4, timeout=25):
    for i in range(tries):
        try:
            r = tls_requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(1.2 * (i + 1))
    return None


def get_text(url, tries=3, timeout=40):
    for i in range(tries):
        try:
            r = tls_requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(1.2 * (i + 1))
    return None


def pmap(fn, items, workers=8, label='', every=200, on_batch=None):
    """Run fn over items in a thread pool. Returns results in completion order,
    skipping None. Calls on_batch(results) periodically so callers can
    checkpoint partial progress to disk."""
    out, done = [], 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): it for it in items}
        for f in as_completed(futs):
            done += 1
            try:
                r = f.result()
            except Exception:
                r = None
            if r is not None:
                out.append(r) if not isinstance(r, list) else out.extend(r)
            if every and done % every == 0:
                print(f'  {label} {done}/{len(items)} ({len(out)} rows)', flush=True)
                if on_batch:
                    on_batch(out)
    return out
