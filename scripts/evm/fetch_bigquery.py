#!/usr/bin/env python3
"""BigQuery goog 官方公共数据集薄采集器——备用/出错复核通道(v3.12.1 定位,用户 2026-07-21 拍板)。

定位(与采集主力的分工):
  - 采集主力=fetch_hypersync_v2.py(HyperSync Starter);本件**不用于常态采集**。
  - 用途:①HyperSync 结果可疑/对账挂了之后的独立复核源 ②HyperSync 平台级故障的备用通道。
  - 仅 ETH 主网(goog 数据集只有 ethereum_mainnet;BSC/Base 无 BigQuery 公共表)。
  - AWS 公共数据湖(方案 D)已验证等价但用户 pass(宽带整分区下载太慢),不做采集器;
    需要第三独立源时手工走 raw parquet(方法见 data-pipeline-evm §11)。

准入实证(2026-07-21,ASTEROID 5 代表日 132,471 行):与 HyperSync 逐行字节级等价;
定向查询按日期分区限定只扫 12 GiB(免费 1 TiB/月 ≈ 85 次复核)。

前置(一次性,已完成可跳过):
  pip3 install google-cloud-bigquery pydata-google-auth
  首跑会弹浏览器 OAuth(之后凭据缓存 ~/.cache/pydata_google_auth/ 不再弹);
  GCP 项目须已建且账号已接受 ToS(现役项目见 ~/.claude/api-keys.md 第 17 节「Google Cloud / BigQuery」)。

用法:
  python3 fetch_bigquery.py --config config.json --from-date 2026-04-01 --to-date 2026-04-30
  python3 fetch_bigquery.py --config config.json --dates 2024-09-10,2026-04-19
  日期=UTC 块时间戳日;输出标准 8 列 CSV(与 fetch_sqd_evm 同款),对账走 transfers_lib merge。

config.json 增节:
  "bigquery": {"project": "<GCP项目ID>", "max_scan_gib": 200, "out": "data/bq_recheck.csv"}
"""
import argparse, csv, json, os, sys

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TABLE = "bigquery-public-data.goog_blockchain_ethereum_mainnet_us.logs"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--from-date", help="UTC 起始日 YYYY-MM-DD(与 --to-date 成对)")
    ap.add_argument("--to-date", help="UTC 截止日(含)")
    ap.add_argument("--dates", help="离散日期列表,逗号分隔(与 from/to 二选一)")
    ap.add_argument("--out", help="输出 CSV(默认取 config bigquery.out)")
    a = ap.parse_args()

    c = json.load(open(a.config))
    token = c["token"].lower()
    bq_cfg = c.get("bigquery", {})
    project = bq_cfg.get("project") or ""
    if not project:
        sys.exit("config.json 缺 bigquery.project(GCP 项目 ID,登记在 ~/.claude/api-keys.md 第 17 节「Google Cloud / BigQuery」)")
    max_gib = float(bq_cfg.get("max_scan_gib", 200))
    out = a.out or bq_cfg.get("out") or "bq_recheck.csv"

    if a.dates:
        where_date = "DATE(block_timestamp) IN ({})".format(
            ",".join(f"'{d.strip()}'" for d in a.dates.split(",")))
    elif a.from_date and a.to_date:
        where_date = f"DATE(block_timestamp) BETWEEN '{a.from_date}' AND '{a.to_date}'"
    else:
        sys.exit("必须给 --dates 或 --from-date/--to-date(禁止无日期全史扫——扫描量失控)")

    import pydata_google_auth
    from google.cloud import bigquery
    creds = pydata_google_auth.get_user_credentials(SCOPES, auth_local_webserver=True)
    client = bigquery.Client(project=project, credentials=creds)

    sql = f"""
    SELECT block_number, block_hash, transaction_hash, log_index,
           topics[SAFE_OFFSET(1)] AS t1, topics[SAFE_OFFSET(2)] AS t2, data,
           FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%S', block_timestamp) AS ts
    FROM `{TABLE}`
    WHERE {where_date} AND address = @token AND topics[SAFE_OFFSET(0)] = @transfer
    ORDER BY block_number, log_index
    """
    params = [
        bigquery.ScalarQueryParameter("token", "STRING", token),
        bigquery.ScalarQueryParameter("transfer", "STRING", TRANSFER),
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=params)

    dry = bigquery.QueryJobConfig(query_parameters=params, dry_run=True)
    job = client.query(sql, job_config=dry, location="US")
    gib = job.total_bytes_processed / 1024**3
    print(f"dry run 扫描量 {gib:.1f} GiB(免费 1024 GiB/月;熔断线 {max_gib:.0f})")
    if gib > max_gib:
        sys.exit(2)

    job_config.maximum_bytes_billed = int(max_gib * 1024**3)
    job = client.query(sql, job_config=job_config, location="US")
    n = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"])
        for row in job.result(page_size=50000):
            t1, t2 = row["t1"] or "", row["t2"] or ""
            data = row["data"] or "0x0"
            val = int(data, 16) if data not in ("0x", "") else 0
            w.writerow([
                int(row["block_number"]),
                row["ts"],
                row["transaction_hash"].lower(),
                int(row["log_index"]),
                "0x" + t1.lower()[-40:] if t1 else "",
                "0x" + t2.lower()[-40:] if t2 else "",
                val,
                row["block_hash"].lower(),
            ])
            n += 1
    print(f"完成 {n} 行 → {out}(计费扫描 {job.total_bytes_billed / 1024**3:.1f} GiB)")
    print("对账: python3 transfers_lib.py merge <主通道文件> " + out)


if __name__ == "__main__":
    main()
