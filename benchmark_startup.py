#!/usr/bin/env python3
"""Benchmark script to measure Wyrm startup times with cached vs fresh runs.

This script measures the startup time of Wyrm with different configurations:
1. Fresh run (no cached structure) - measures full parsing time
2. Cached run (using existing structure) - measures optimized startup time
3. Forced fresh run with cache - measures forced re-parsing time

The script logs detailed timing information and calculates performance improvements.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

# Configuration
BENCHMARK_CONFIG = "config.yaml"
STRUCTURE_CACHE_PATH = Path("logs/sidebar_structure.json")
BENCHMARK_RUNS = 3  # Number of runs for averaging
TEST_TIMEOUT = 300  # 5 minutes timeout for each test


def log_benchmark(message: str, level: str = "INFO") -> None:
    """Log benchmark messages with timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def clear_cache() -> None:
    """Remove cached structure file to force fresh parsing."""
    if STRUCTURE_CACHE_PATH.exists():
        STRUCTURE_CACHE_PATH.unlink()
        log_benchmark(f"Cleared cache: {STRUCTURE_CACHE_PATH}")
    else:
        log_benchmark("No cache file found to clear")


def ensure_cache_exists() -> bool:
    """Check if cache file exists."""
    exists = STRUCTURE_CACHE_PATH.exists()
    if exists:
        log_benchmark(f"Cache file exists: {STRUCTURE_CACHE_PATH}")
        # Get cache file info
        stat = STRUCTURE_CACHE_PATH.stat()
        size_kb = stat.st_size / 1024
        mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
        log_benchmark(f"Cache size: {size_kb:.1f} KB, modified: {mod_time}")
    else:
        log_benchmark("Cache file does not exist")
    return exists


def run_wyrm_benchmark(test_name: str, cmd_args: List[str]) -> Tuple[float, bool, str]:
    """Run Wyrm with given arguments and measure execution time.

    Args:
        test_name: Name of the test for logging
        cmd_args: Command line arguments to pass to main.py

    Returns:
        Tuple of (execution_time, success, output_summary)
    """
    log_benchmark(f"Starting {test_name}")

    # Build command
    cmd = ["python3", "main.py"] + cmd_args
    log_benchmark(f"Command: {' '.join(cmd)}")

    start_time = time.time()

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT,
            cwd=Path.cwd()
        )

        end_time = time.time()
        execution_time = end_time - start_time

        success = result.returncode == 0

        # Extract key information from output
        output_lines = result.stdout.split('\n') + result.stderr.split('\n')
        output_summary = extract_output_summary(output_lines)

        log_benchmark(
            f"{test_name} completed in {execution_time:.2f}s "
            f"(Success: {success})"
        )

        if not success:
            log_benchmark(f"Error output: {result.stderr[:200]}...", "ERROR")

        return execution_time, success, output_summary

    except subprocess.TimeoutExpired:
        end_time = time.time()
        execution_time = end_time - start_time
        log_benchmark(f"{test_name} timed out after {execution_time:.2f}s", "ERROR")
        return execution_time, False, "TIMEOUT"

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        log_benchmark(f"{test_name} failed with exception: {e}", "ERROR")
        return execution_time, False, f"EXCEPTION: {str(e)}"


def extract_output_summary(output_lines: List[str]) -> str:
    """Extract key metrics from Wyrm output."""
    summary_items = []

    for line in output_lines:
        line = line.strip()
        if not line:
            continue

        # Look for key performance indicators
        if "Processing items" in line:
            summary_items.append(line)
        elif ("structure" in line and
              ("cache" in line.lower() or "load" in line.lower())):
            summary_items.append(line)
        elif "Navigating to target URL" in line:
            summary_items.append(line)
        elif "Menu expansion completed" in line:
            summary_items.append(line)
        elif "items processed" in line.lower():
            summary_items.append(line)

    return " | ".join(summary_items[-5:])  # Last 5 relevant lines


def run_benchmark_suite() -> Dict:
    """Run complete benchmark suite and return results."""
    log_benchmark("=== Wyrm Startup Time Benchmark Suite ===")
    results = {
        "fresh_runs": [],
        "cached_runs": [],
        "forced_fresh_runs": [],
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config_file": BENCHMARK_CONFIG,
            "runs_per_test": BENCHMARK_RUNS,
            "timeout_seconds": TEST_TIMEOUT
        }
    }

    # Test 1: Fresh runs (no cache) - measures full parsing performance
    log_benchmark("\n=== TEST 1: Fresh Runs (No Cache) ===")
    for run in range(BENCHMARK_RUNS):
        clear_cache()  # Ensure clean state

        # Use resume-info to avoid actual processing, just measure
        # structure loading/parsing
        cmd_args = ["--config", BENCHMARK_CONFIG, "--resume-info", "--max-items", "1"]

        exec_time, success, summary = run_wyrm_benchmark(
            f"Fresh Run {run + 1}/{BENCHMARK_RUNS}",
            cmd_args
        )

        results["fresh_runs"].append({
            "run": run + 1,
            "time": exec_time,
            "success": success,
            "summary": summary
        })

        # Brief pause between runs
        time.sleep(2)

    # Ensure we have a cached structure for next tests
    log_benchmark("\n=== Creating Cache for Subsequent Tests ===")
    clear_cache()
    cmd_args = ["--config", BENCHMARK_CONFIG, "--resume-info", "--max-items", "1"]
    run_wyrm_benchmark("Cache Creation Run", cmd_args)

    if not ensure_cache_exists():
        log_benchmark("Failed to create cache file - cached tests will fail", "ERROR")
        return results

    # Test 2: Cached runs - measures optimized performance
    log_benchmark("\n=== TEST 2: Cached Runs (Using Existing Structure) ===")
    for run in range(BENCHMARK_RUNS):
        # Verify cache exists before each run
        if not ensure_cache_exists():
            log_benchmark(f"Cache missing for run {run + 1}, skipping", "ERROR")
            continue

        cmd_args = ["--config", BENCHMARK_CONFIG, "--resume-info", "--max-items", "1"]

        exec_time, success, summary = run_wyrm_benchmark(
            f"Cached Run {run + 1}/{BENCHMARK_RUNS}",
            cmd_args
        )

        results["cached_runs"].append({
            "run": run + 1,
            "time": exec_time,
            "success": success,
            "summary": summary
        })

        time.sleep(2)

    # Test 3: Forced fresh runs (with cache present) - measures forced re-parsing
    log_benchmark("\n=== TEST 3: Forced Fresh Runs (Cache Bypass) ===")
    for run in range(BENCHMARK_RUNS):
        ensure_cache_exists()  # Make sure cache is present

        # Use --force-full-expansion flag to force re-parsing even when cache exists
        cmd_args = [
            "--config", BENCHMARK_CONFIG,
            "--resume-info",
            "--max-items", "1",
            "--force-full-expansion"
        ]

        exec_time, success, summary = run_wyrm_benchmark(
            f"Forced Fresh Run {run + 1}/{BENCHMARK_RUNS}",
            cmd_args
        )

        results["forced_fresh_runs"].append({
            "run": run + 1,
            "time": exec_time,
            "success": success,
            "summary": summary
        })

        time.sleep(2)

    return results


def analyze_results(results: Dict) -> None:
    """Analyze and display benchmark results."""
    log_benchmark("\n=== BENCHMARK ANALYSIS ===")

    # Calculate statistics for each test type
    test_types = ["fresh_runs", "cached_runs", "forced_fresh_runs"]
    stats = {}

    for test_type in test_types:
        runs = results[test_type]
        successful_runs = [r for r in runs if r["success"]]

        if not successful_runs:
            log_benchmark(f"No successful {test_type}, skipping analysis", "WARNING")
            continue

        times = [r["time"] for r in successful_runs]

        stats[test_type] = {
            "successful_runs": len(successful_runs),
            "total_runs": len(runs),
            "min_time": min(times),
            "max_time": max(times),
            "avg_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0
        }

        log_benchmark(f"\n{test_type.replace('_', ' ').title()} Statistics:")
        log_benchmark(f"  Successful runs: {len(successful_runs)}/{len(runs)}")
        log_benchmark(f"  Average time: {stats[test_type]['avg_time']:.2f}s")
        log_benchmark(f"  Median time: {stats[test_type]['median_time']:.2f}s")
        log_benchmark(f"  Min time: {stats[test_type]['min_time']:.2f}s")
        log_benchmark(f"  Max time: {stats[test_type]['max_time']:.2f}s")
        if stats[test_type]['stdev'] > 0:
            log_benchmark(f"  Std deviation: {stats[test_type]['stdev']:.2f}s")

    # Performance comparisons
    if "fresh_runs" in stats and "cached_runs" in stats:
        fresh_avg = stats["fresh_runs"]["avg_time"]
        cached_avg = stats["cached_runs"]["avg_time"]
        improvement = ((fresh_avg - cached_avg) / fresh_avg) * 100
        speedup = fresh_avg / cached_avg if cached_avg > 0 else 0

        log_benchmark("\n=== CACHE PERFORMANCE IMPACT ===")
        log_benchmark(f"Fresh run average: {fresh_avg:.2f}s")
        log_benchmark(f"Cached run average: {cached_avg:.2f}s")
        log_benchmark(f"Time saved: {fresh_avg - cached_avg:.2f}s")
        log_benchmark(f"Performance improvement: {improvement:.1f}%")
        log_benchmark(f"Speedup factor: {speedup:.1f}x")

    # Save detailed results
    results_file = Path("benchmark_results.json")
    results["analysis"] = stats

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    log_benchmark(f"\nDetailed results saved to: {results_file}")


def main():
    """Main benchmark execution."""
    log_benchmark("Starting Wyrm startup time benchmark")

    # Check that main.py exists
    if not Path("main.py").exists():
        log_benchmark("main.py not found in current directory", "ERROR")
        return 1

    # Check that config file exists
    if not Path(BENCHMARK_CONFIG).exists():
        log_benchmark(f"Config file {BENCHMARK_CONFIG} not found", "ERROR")
        return 1

    try:
        results = run_benchmark_suite()
        analyze_results(results)
        log_benchmark("Benchmark completed successfully")
        return 0

    except KeyboardInterrupt:
        log_benchmark("Benchmark interrupted by user", "WARNING")
        return 1
    except Exception as e:
        log_benchmark(f"Benchmark failed with error: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    exit(main())
