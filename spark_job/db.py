import psycopg2
from psycopg2.extras import execute_values

from spark_job.config import (
    POSTGRES_HOST as PG_HOST,
    POSTGRES_PORT as PG_PORT,
    POSTGRES_DB as PG_DB,
    POSTGRES_USER as PG_USER,
    POSTGRES_PASSWORD as PG_PASSWORD,
)

_DIMENSIONS = {
    "date": dict(
        table="dim_date", key_col="date_key",
        natural_cols=("actual_date",),
        other_cols=("weekday_name", "month_number", "year_number", "is_weekend"),
        row_fields=("event_date", "weekday_name", "month_number", "year_number", "is_weekend"),
    ),
    "product": dict(
        table="dim_product", key_col="product_key",
        natural_cols=("product_id",), other_cols=(),
        row_fields=("product_id",),
    ),
    "location": dict(
        table="dim_location", key_col="location_key",
        natural_cols=("country_name", "region_name"), other_cols=(),
        row_fields=("country", "region"),
    ),
    "device": dict(
        table="dim_device", key_col="device_key",
        natural_cols=("browser", "os"), other_cols=(),
        row_fields=("browser", "os"),
    ),
    "referrer": dict(
        table="dim_referrer", key_col="referrer_key",
        natural_cols=("referrer_url",), other_cols=("referrer_domain",),
        row_fields=("referrer_url", "referrer_domain"),
        conflict_target="(md5(referrer_url))",
    ),
}

_FACT_COLUMNS = [
    "id", "date_key", "product_key", "location_key", "device_key", "referrer_key",
    "store_id", "ip_address", "event_hour",
]

_FACT_INSERT_SQL = f"""
INSERT INTO glamira.fact_product_view ({", ".join(_FACT_COLUMNS)})
VALUES %s
ON CONFLICT (id) DO NOTHING;
"""


def _get_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def _get_or_create_keys(cur, dim):
    rows = dim["rows"]
    if not rows:
        return {}

    natural_cols, other_cols = dim["natural_cols"], dim["other_cols"]
    all_cols = natural_cols + other_cols
    conflict_target = dim.get("conflict_target") or ", ".join(natural_cols)
    noop_update = f"{natural_cols[0]} = EXCLUDED.{natural_cols[0]}"
    sql = f"""
        INSERT INTO glamira.{dim['table']} ({", ".join(all_cols)})
        VALUES %s
        ON CONFLICT ({conflict_target}) DO UPDATE SET {noop_update}
        RETURNING {dim['key_col']}, {", ".join(natural_cols)};
    """
    returned = execute_values(cur, sql, list(rows), fetch=True)
    n = len(natural_cols)
    return {tuple(r[1:1 + n]): r[0] for r in returned}


def write_batch_to_postgres(batch_df, batch_id):
    batch_df = batch_df.dropDuplicates(["id"])
    rows = batch_df.collect()
    if not rows:
        return

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            keys_by_dim = {}
            for name, dim in _DIMENSIONS.items():
                dim = dict(dim, rows={tuple(r[f] for f in dim["row_fields"]) for r in rows})
                keys_by_dim[name] = _get_or_create_keys(cur, dim)

            fact_values = []
            for r in rows:
                fact_values.append((
                    r["id"],
                    keys_by_dim["date"][(r["event_date"],)],
                    keys_by_dim["product"][(r["product_id"],)],
                    keys_by_dim["location"][(r["country"], r["region"])],
                    keys_by_dim["device"][(r["browser"], r["os"])],
                    keys_by_dim["referrer"][(r["referrer_url"],)],
                    r["store_id"],
                    r["ip"],
                    r["event_hour"],
                ))

            execute_values(cur, _FACT_INSERT_SQL, fact_values, page_size=1000)
        conn.commit()
        print(f"[batch {batch_id}] upserted {len(fact_values)} rows into glamira.fact_product_view")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
