import json
import time
import asyncio
import os
from typing import List, Dict, Any
from collections import Counter
from datetime import datetime

# Import the extraction function directly to bypass FastAPI overhead for local testing
# or we can call the API if it's running. Calling function directly is easier for a script.
try:
    from inference_openrouter import extract_criteria, OpenRouterExtractorError
except ImportError:
    print("Error: inference_openrouter.py not found or dependencies missing.")
    exit(1)

DATASET_FILE = "synthetic_dataset.json"
REPORT_FILE = "inference_report.json"
SUMMARY_FILE = "inference_summary.txt"

# Number of concurrent requests to avoid hitting rate limits too hard or waiting forever
CONCURRENCY_LIMIT = 10

def normalize_json(obj):
    """
    Recursively sort keys and lists to make JSON comparable.
    But strict equality might be too harsh for some float comparisons or nulls.
    """
    return json.dumps(obj, sort_keys=True)

import unicodedata

def normalize_string(s: str) -> str:
    """
    Normalize string for loose comparison:
    - NFD decomposition to split accents
    - Remove combining characters (accents)
    - Lowercase
    - Strip whitespace
    - Remove punctuation/parentheses for cleaner comparison
    """
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize('NFD', s)
    s = "".join(c for c in s if unicodedata.category(c) != 'Mn')
    # Remove non-alphanumeric (except spaces)
    s = "".join(c for c in s if c.isalnum() or c.isspace())
    return s.lower().strip()

def compare_results(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare expected and actual results field by field.
    Returns a dict summarizing matches/mismatches.
    """
    comparison = {
        "match": True,
        "mismatches": []
    }
    
    # Top level keys
    for key in expected:
        if key not in actual:
            comparison["match"] = False
            comparison["mismatches"].append(f"Missing key: {key}")
            continue
            
        exp_val = expected[key]
        act_val = actual[key]
        
        # Deep compare for sub-dictionaries (localisation, activite, etc.)
        if isinstance(exp_val, dict) and isinstance(act_val, dict):
            for sub_key in exp_val:
                if sub_key not in act_val:
                    comparison["match"] = False
                    comparison["mismatches"].append(f"Missing sub-key: {key}.{sub_key}")
                    continue
                
                e_v = exp_val[sub_key]
                a_v = act_val[sub_key]
                
                # Handle float comparison with tolerance
                if isinstance(e_v, (int, float)) and isinstance(a_v, (int, float)) and not isinstance(e_v, bool):
                    if abs(e_v - a_v) > 0.1:
                         comparison["match"] = False
                         comparison["mismatches"].append(f"Value mismatch {key}.{sub_key}: expected {e_v}, got {a_v}")
                # Handle string comparison with normalization
                elif isinstance(e_v, str) and isinstance(a_v, str):
                    if normalize_string(e_v) != normalize_string(a_v):
                        comparison["match"] = False
                        comparison["mismatches"].append(f"Value mismatch {key}.{sub_key}: expected {e_v}, got {a_v}")
                elif e_v != a_v:
                    comparison["match"] = False
                    comparison["mismatches"].append(f"Value mismatch {key}.{sub_key}: expected {e_v}, got {a_v}")
        else:
            if exp_val != act_val:
                comparison["match"] = False
                comparison["mismatches"].append(f"Value mismatch {key}: expected {exp_val}, got {act_val}")
                
    return comparison

async def process_sample(semaphore, sample: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Run a single sample through the extractor.
    """
    async with semaphore:
        query = sample["input"]
        expected = sample["expected_output"]
        
        start_time = time.time()
        result = {
            "index": index,
            "input": query,
            "expected": expected,
            "actual": None,
            "error": None,
            "latency": 0.0,
            "match": False,
            "details": []
        }
        
        try:
            # We run the synchronous function in a thread to not block the event loop
            actual = await asyncio.to_thread(extract_criteria, query)
            latency = time.time() - start_time
            
            comparison = compare_results(expected, actual)
            
            result["actual"] = actual
            result["latency"] = latency
            result["match"] = comparison["match"]
            result["details"] = comparison["mismatches"]
            
        except Exception as e:
            result["error"] = str(e)
            result["latency"] = time.time() - start_time
            
        return result

async def run_test_suite(dataset: List[Dict[str, Any]]):
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []
    
    print(f"Starting inference on {len(dataset)} samples with concurrency {CONCURRENCY_LIMIT}...")
    
    for i, sample in enumerate(dataset):
        tasks.append(process_sample(semaphore, sample, i))
        
    results = []
    # Use asyncio.as_completed to show progress
    total = len(tasks)
    completed = 0
    
    for future in asyncio.as_completed(tasks):
        res = await future
        results.append(res)
        completed += 1
        if completed % 10 == 0 or completed == total:
            print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)", end="\r")
            
    print("\nInference complete.")
    return sorted(results, key=lambda x: x["index"])

def generate_report(results: List[Dict[str, Any]]):
    total = len(results)
    if total == 0:
        print("No results to report.")
        return

    success_count = sum(1 for r in results if r["match"])
    error_count = sum(1 for r in results if r["error"])
    mismatch_count = total - success_count - error_count
    
    latencies = [r["latency"] for r in results if not r["error"]]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    
    # Analyze specific field failures
    field_errors = Counter()
    for r in results:
        if not r["match"] and not r["error"]:
            for mismatch in r["details"]:
                # Extract field name from mismatch string "Value mismatch localization.region: ..."
                parts = mismatch.split(":")
                if len(parts) > 1:
                    field_info = parts[0].replace("Value mismatch ", "").replace("Missing sub-key: ", "")
                    field_errors[field_info] += 1

    report_text = []
    report_text.append(f"--- Inference Test Report ---")
    report_text.append(f"Date: {datetime.now().isoformat()}")
    report_text.append(f"Total Samples: {total}")
    report_text.append(f"Success (Exact Match): {success_count} ({success_count/total*100:.2f}%)")
    report_text.append(f"Errors (Exceptions): {error_count} ({error_count/total*100:.2f}%)")
    report_text.append(f"Mismatches: {mismatch_count} ({mismatch_count/total*100:.2f}%)")
    report_text.append(f"")
    report_text.append(f"Latency (s): Avg={avg_latency:.3f}, Max={max_latency:.3f}")
    report_text.append(f"")
    report_text.append(f"--- Top Mismatch Fields ---")
    for field, count in field_errors.most_common(10):
        report_text.append(f"{field}: {count} failures")
        
    # Save summary
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_text))
        
    # Save full details
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("\n".join(report_text))
    print(f"\nFull JSON report saved to {REPORT_FILE}")
    print(f"Summary text saved to {SUMMARY_FILE}")

def main():
    if not os.path.exists(DATASET_FILE):
        print(f"Dataset file {DATASET_FILE} not found. Run generate_synthetic_data.py first.")
        return

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    # Optional: Limit for quick testing if needed
    # dataset = dataset[:50] 

    results = asyncio.run(run_test_suite(dataset))
    generate_report(results)

if __name__ == "__main__":
    main()

