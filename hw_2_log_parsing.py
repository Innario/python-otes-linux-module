#!/usr/bin/python

import argparse
import json
import pathlib
import subprocess

import yaml

METHODS = ["GET", "POST", "HEAD", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"]
N_REQUESTS = "total number of requests"
N_REQUESTS_BY_METHODS = "total number of requests by method"
N_REQUESTS_BY_IPS = "top ip adresses by number of requests"
REQUESTS_BY_DURATION = "top requests by duration"


def run(*args):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE)
    return result.stdout


def scan_file(file_path):
    print(f"[{file_path}] Counting number of requests...")
    n_requests = int(run("wc", "-l", file_path).split(" ")[0])

    print(f"[{file_path}] Counting number of requests for each method...")
    n_method_requests = {}
    for method in METHODS:
        n_method_requests[method] = int(run("grep", "-c", f"\"{method} ", file_path))
    assert n_requests == sum(n_method_requests.values())
    sorted_methods = sorted(n_method_requests.keys(), key=lambda method: -n_method_requests[method])
    n_method_requests_report = [f"\t{method:10}: {n_method_requests[method]:,} entries" for method in sorted_methods]
    n_method_requests_report = "\n".join(n_method_requests_report)

    print(f"[{file_path}] Looking for top ip's in requests...")
    top_unique_ips = run("bash", "-c", "grep -E -o \"([0-9]{1,3}[\.]){3}[0-9]{1,3}\" " + file_path + " | uniq -c | sort | tail")
    top_unique_ips = dict([_.split()[::-1] for _ in top_unique_ips.split("\n") if _])
    top_unique_ips = {ip: int(count) for ip, count in top_unique_ips.items()}
    top_unique_ips_str = [f"\t{ip:15}: {int(count)} entries" for ip, count in top_unique_ips.items()]
    top_unique_ips_str = "\n".join(top_unique_ips_str)

    print(f"[{file_path}] Looking for top longest requests...")
    top_long_request = run("bash", "-c", "grep -E -o -n \" [0-9]+$\" " + file_path + " | sort -nr -k 2 | head -n 3")
    top_long_request_line = [int(line.split(": ")[0]) for line in top_long_request.split("\n") if line]
    top_long_request_info = [run("bash", "-c", f"sed '{line}q;d' {file_path}") for line in top_long_request_line]
    top_long_request_dict = {(file_path, line, request.strip()): int(request.split()[-1]) for line, request in zip(top_long_request_line, top_long_request_info)}
    top_long_request_str = [f"\t request {line:<10} took {duration} sec: {request}" for (file_path, line, request), duration in top_long_request_dict.items()]
    top_long_request_str = "\n".join(top_long_request_str)

    print(f"""
    Summary on '{file_path}' log file:
    - {N_REQUESTS}: {n_requests:,}
    - {N_REQUESTS_BY_METHODS}: \n{n_method_requests_report}
    - {N_REQUESTS_BY_IPS}: \n{top_unique_ips_str}
    - {REQUESTS_BY_DURATION}: \n{top_long_request_str}
    """)

    report = {
        N_REQUESTS: n_requests,
        N_REQUESTS_BY_METHODS: {method: n_method_requests[method] for method in sorted_methods},
        N_REQUESTS_BY_IPS: top_unique_ips,
        REQUESTS_BY_DURATION: top_long_request_dict,
    }

    return report


def scan_for_logs(paths):
    log_files = []
    for path_str in paths:
        path = pathlib.Path(path_str)
        if path.is_file() and path.suffix == ".log":
            log_files.append(str(path.absolute()))
        elif path.is_dir():
            for log_path in path.rglob("*.log"):
                if log_path.is_file():
                    log_files.append(str(log_path.absolute()))
    return sorted(log_files)


def merge_reports(reports):
    final = {
        N_REQUESTS: 0,
        N_REQUESTS_BY_METHODS: {method: 0 for method in METHODS},
        N_REQUESTS_BY_IPS: {},
        REQUESTS_BY_DURATION: {}
    }
    for rep in reports:
        final[N_REQUESTS] += rep[N_REQUESTS]
        for method, count in rep[N_REQUESTS_BY_METHODS].items():
            final[N_REQUESTS_BY_METHODS][method] += count
        for ip, count in rep[N_REQUESTS_BY_IPS].items():
            if ip not in final[N_REQUESTS_BY_IPS]:
                final[N_REQUESTS_BY_IPS][ip] = 0
            final[N_REQUESTS_BY_IPS][ip] += count
        sorted_keys = sorted(final[N_REQUESTS_BY_IPS].keys(), key=lambda ip: -final[N_REQUESTS_BY_IPS][ip])
        final[N_REQUESTS_BY_IPS] = {key: final[N_REQUESTS_BY_IPS][key] for key in sorted_keys[:3]}
        for (file_path, line, request), duration in rep[REQUESTS_BY_DURATION].items():
            final[REQUESTS_BY_DURATION][f"{file_path}:{line} took {duration} sec"] = request
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs=argparse.REMAINDER)
    paths = parser.parse_args().paths
    log_files = scan_for_logs(paths)
    paths_str = "\n".join([f" -{_}" for _ in log_files])

    print(f"Paths for logs parsing: \n{paths_str}")
    reports = []
    for lof_file in log_files:
        reports.append(scan_file(lof_file))
    final_report = merge_reports(reports)

    paths_str = ", ".join(paths)
    print(f"FINAL REPORT FOR PATHS {paths_str}")
    print(yaml.dump(final_report, indent=4, sort_keys=False, width=1000))
    with open("report.json", "w") as file:
        json.dump(final_report, file, indent=4)
