import argparse
import json
import os
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import request, error


def rand_suffix(n=6):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def http_json(method, url, payload=None, headers=None, timeout=10):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return e.code, body
    except Exception as e:
        return "EXCEPTION", str(e)


def http_raw(method, url, raw_bytes, headers=None, timeout=10):
    req = request.Request(url, data=raw_bytes, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return e.code, body
    except Exception as e:
        return "EXCEPTION", str(e)


def run(base_url):
    results = []
    def log(name, status, body):
        results.append((name, status, body[:500]))

    # 1) Invalid JSON
    log(
        "invalid_json_posts",
        *http_raw("POST", f"{base_url}/api/posts", b"{bad json", {"Content-Type": "application/json"}),
    )

    def log_err(name, status_body):
        status, body = status_body
        log(name, status, body)

    # 2) Institution with empty name
    log("institution_empty", *http_json("POST", f"{base_url}/api/institutions", {"institution_name": "   "}))

    # 3) Platform whitespace
    log("platform_whitespace", *http_json("POST", f"{base_url}/api/platforms", {"platform_name": "  "}))

    # 4) Overlong username
    long_username = "u" * 41
    log(
        "account_long_username",
        *http_json(
            "POST",
            f"{base_url}/api/accounts",
            {"username": long_username, "platform_name": "EdgeNet"},
        ),
    )

    # 5) Project invalid dates
    proj_name = f"EdgeProject_{rand_suffix()}"
    log(
        "project_bad_dates",
        *http_json(
            "POST",
            f"{base_url}/api/projects",
            {
                "project_name": proj_name,
                "institution_name": "InstEdge",
                "start_date": "2026-05-05",
                "end_date": "2026-05-01",
            },
        ),
    )

    # 1b) Wrong content-type with JSON
    log(
        "wrong_content_type",
        *http_raw("POST", f"{base_url}/api/posts", json.dumps({"foo": "bar"}).encode("utf-8"), {"Content-Type": "text/plain"}),
    )

    # 1c) Empty body
    log(
        "empty_body",
        *http_raw("POST", f"{base_url}/api/posts", b"", {"Content-Type": "application/json"}),
    )

    # 6) Project with duplicate/blank fields
    proj_name_ok = f"EdgeProject_{rand_suffix()}"
    log(
        "project_fields_dup_blank",
        *http_json(
            "POST",
            f"{base_url}/api/projects",
            {
                "project_name": proj_name_ok,
                "institution_name": "InstEdge",
                "fields": ["toxicity", "toxicity", "  ", "sentiment"],
            },
        ),
    )

    # 7) Post with invalid datetime
    log(
        "post_invalid_datetime",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": "edge_user",
                "platform_name": "EdgeNet",
                "text": "bad time",
                "time": "2026-99-99 99:99:99",
            },
        ),
    )

    # 7b) Post with invalid datetime format
    log(
        "post_invalid_datetime_format",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": "edge_user",
                "platform_name": "EdgeNet",
                "text": "bad time",
                "time": "05/03/2026 10:00",
            },
        ),
    )

    # 8) Post with huge text payload (100KB)
    huge_text = "A" * 100_000
    log(
        "post_huge_text",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": huge_text,
                "time": "2026-05-03 10:00:00",
            },
            timeout=30,
        ),
    )

    # 9) Post with emoji + RTL + SQL-like text
    weird_text = "😈 RTL:  ; DROP TABLE Post; --"
    log(
        "post_weird_text",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": weird_text,
                "time": "2026-05-03 10:01:00",
            },
        ),
    )

    # 9b) Post with zero-width + combining characters
    weird_text2 = "Z\u200dW\u200dJ + comb: a\u0301\u0301"
    log(
        "post_weird_text_unicode",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": weird_text2,
                "time": "2026-05-03 10:01:30",
            },
        ),
    )

    # 10) Duplicate post at same timestamp (unique constraint)
    dup_username = f"dup_user_{rand_suffix()}"
    dup_payload = {
        "username": dup_username,
        "platform_name": "EdgeNet",
        "text": "first",
        "time": "2026-05-03 10:02:00",
    }
    log("post_dup_first", *http_json("POST", f"{base_url}/api/posts", dup_payload))
    log("post_dup_second", *http_json("POST", f"{base_url}/api/posts", dup_payload))

    # 11) Analysis with missing post_id
    log(
        "analysis_missing_post_id",
        *http_json(
            "POST",
            f"{base_url}/api/analysis",
            {"project_name": proj_name_ok, "results": [{"field_name": "toxicity", "field_value": "0.9"}]},
        ),
    )

    # 11b) Analysis with invalid post_id type
    log(
        "analysis_post_id_string",
        *http_json(
            "POST",
            f"{base_url}/api/analysis",
            {"project_name": proj_name_ok, "post_id": "abc", "results": [{"field_name": "toxicity", "field_value": "0.9"}]},
        ),
    )

    # 11c) Analysis with non-existent project
    log(
        "analysis_unknown_project",
        *http_json(
            "POST",
            f"{base_url}/api/analysis",
            {"project_name": f"NoProj_{rand_suffix()}", "post_id": 1, "results": [{"field_name": "toxicity", "field_value": "0.9"}]},
        ),
    )

    # 12) Person link with invalid accounts payload
    log(
        "person_link_empty",
        *http_json(
            "POST",
            f"{base_url}/api/persons/link",
            {"accounts": []},
        ),
    )

    # 13) Create account with age overflow
    log(
        "account_age_overflow",
        *http_json(
            "POST",
            f"{base_url}/api/accounts",
            {
                "username": f"age_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "age": 1000,
            },
        ),
    )

    # 13b) Create account with non-numeric age
    log(
        "account_age_non_numeric",
        *http_json(
            "POST",
            f"{base_url}/api/accounts",
            {"username": f"age_user_{rand_suffix()}", "platform_name": "EdgeNet", "age": "old"},
        ),
    )

    # 13c) Create account with missing platform
    log(
        "account_missing_platform",
        *http_json(
            "POST",
            f"{base_url}/api/accounts",
            {"username": f"no_platform_{rand_suffix()}"},
        ),
    )

    # 14) Invalid contains_multimedia values
    log(
        "post_invalid_multimedia",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": "multimedia",
                "time": "2026-05-03 10:04:00",
                "contains_multimedia": "maybe",
            },
        ),
    )

    # 15) Repost of non-existent post
    log(
        "post_repost_invalid",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": "repost",
                "time": "2026-05-03 10:05:00",
                "repost_of": 999999,
            },
        ),
    )

    # 16) Link accounts with bad entries
    log(
        "person_link_bad_entries",
        *http_json(
            "POST",
            f"{base_url}/api/persons/link",
            {
                "accounts": [
                    {"username": "", "platform_name": "EdgeNet"},
                    {"username": "good_user", "platform_name": ""},
                    {"username": "good_user", "platform_name": "EdgeNet"},
                ]
            },
        ),
    )

    # 17) Query posts with invalid filters
    log(
        "query_posts_invalid_date_from",
        *http_json("GET", f"{base_url}/api/posts?from=not-a-date", None),
    )

    # 18) Query posts with extreme date range
    log(
        "query_posts_extreme_range",
        *http_json("GET", f"{base_url}/api/posts?from=1900-01-01%2000:00:00&to=3000-01-01%2000:00:00", None),
    )

    # 19) Create project with very long names
    long_name = "P" * 250
    log(
        "project_long_name",
        *http_json(
            "POST",
            f"{base_url}/api/projects",
            {"project_name": long_name, "institution_name": "InstEdge"},
        ),
    )

    # 20) Duplicate project name
    dup_project = f"DupProject_{rand_suffix()}"
    log(
        "project_dup_first",
        *http_json("POST", f"{base_url}/api/projects", {"project_name": dup_project, "institution_name": "InstEdge"}),
    )
    log(
        "project_dup_second",
        *http_json("POST", f"{base_url}/api/projects", {"project_name": dup_project, "institution_name": "InstEdge"}),
    )

    # 21) Add field to non-existent project
    log(
        "add_field_missing_project",
        *http_json("POST", f"{base_url}/api/projects/NoSuchProject/fields", {"field_name": "sentiment"}),
    )

    # 22) Add field with long name
    log(
        "add_field_long_name",
        *http_json("POST", f"{base_url}/api/projects/{dup_project}/fields", {"field_name": "f" * 300}),
    )

    # 23) Account with extreme values / invalid types
    log(
        "account_invalid_gender_type",
        *http_json(
            "POST",
            f"{base_url}/api/accounts",
            {"username": f"gender_user_{rand_suffix()}", "platform_name": "EdgeNet", "gender": {"bad": "type"}},
        ),
    )

    # 24) Post with negative likes/dislikes
    log(
        "post_negative_likes",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": "neg likes",
                "time": "2026-05-03 10:06:00",
                "num_likes": -5,
                "num_dislikes": -1,
            },
        ),
    )

    # 25) Post with huge num_likes (overflow check)
    log(
        "post_huge_likes",
        *http_json(
            "POST",
            f"{base_url}/api/posts",
            {
                "username": f"edge_user_{rand_suffix()}",
                "platform_name": "EdgeNet",
                "text": "huge likes",
                "time": "2026-05-03 10:06:30",
                "num_likes": 2**63,
            },
        ),
    )

    # 26) SQL injection-like strings in various fields
    inj = "' OR 1=1; DROP TABLE UserAccount; --"
    log(
        "platform_sql_injection_string",
        *http_json("POST", f"{base_url}/api/platforms", {"platform_name": inj}),
    )
    log(
        "account_sql_injection_string",
        *http_json("POST", f"{base_url}/api/accounts", {"username": inj, "platform_name": "EdgeNet"}),
    )

    # 27) Analysis with duplicate field entries in one request
    log(
        "analysis_duplicate_fields",
        *http_json(
            "POST",
            f"{base_url}/api/analysis",
            {
                "project_name": dup_project,
                "post_id": 1,
                "results": [
                    {"field_name": "toxicity", "field_value": "0.1"},
                    {"field_name": "toxicity", "field_value": "0.9"},
                ],
            },
        ),
    )

    # 28) Experiments query for missing project
    log(
        "experiments_missing_project",
        *http_json("GET", f"{base_url}/api/experiments/NoSuchProject", None),
    )

    # 29) Person link with duplicate accounts
    log(
        "person_link_duplicates",
        *http_json(
            "POST",
            f"{base_url}/api/persons/link",
            {"accounts": [{"username": "dup_user", "platform_name": "EdgeNet"}, {"username": "dup_user", "platform_name": "EdgeNet"}]},
        ),
    )

    # 30) Large batch of platforms (stress insert)
    for i in range(20):
        log(
            f"platform_bulk_{i}",
            *http_json("POST", f"{base_url}/api/platforms", {"platform_name": f"BulkPlat_{rand_suffix()}_{i}"}),
        )

    # 14) Concurrency: 10 same-time posts
    conc_username = f"race_user_{rand_suffix()}"
    conc_payload = {
        "username": conc_username,
        "platform_name": "EdgeNet",
        "text": "race",
        "time": "2026-05-03 10:03:00",
    }
    def send_one(i):
        return http_json("POST", f"{base_url}/api/posts", conc_payload)

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(send_one, i) for i in range(10)]
        for idx, fut in enumerate(as_completed(futures), 1):
            status, body = fut.result()
            log(f"post_race_{idx}", status, body)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:5001"))
    args = parser.parse_args()

    results = run(args.base_url)
    for name, status, body in results:
        print(f"{name}: {status}")
        if body:
            print(body)
        print("-" * 60)


if __name__ == "__main__":
    main()
