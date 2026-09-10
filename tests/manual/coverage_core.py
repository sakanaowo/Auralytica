"""Standard-library line tracing for core/API tests, including Python threads.

Run: python tests/manual/coverage_core.py
Does not collect child processes or browser JavaScript; not total project coverage.
"""
from pathlib import Path
import sys
import sysconfig
import threading
import trace
import unittest


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root/'tests'))
    suite = unittest.defaultTestLoader.discover(str(root/'tests'))
    tracer = trace.Trace(count=True, trace=False,
                         ignoredirs=[sysconfig.get_path('stdlib'), sys.prefix, str(root/'tests')])
    threading.settrace(tracer.globaltrace)
    try:
        result = tracer.runfunc(unittest.TextTestRunner(verbosity=1).run, suite)
    finally:
        threading.settrace(None)
    output = root/'artifacts/acceptance-runs/coverage'
    output.mkdir(parents=True, exist_ok=True)
    counts = tracer.results()
    counts.counts = {key: value for key, value in counts.counts.items()
                    if Path(key[0]).is_relative_to(root/'src')}
    counts.write_results(show_missing=True, summary=True, coverdir=str(output))
    return not result.wasSuccessful()


if __name__ == '__main__':
    sys.exit(main())
