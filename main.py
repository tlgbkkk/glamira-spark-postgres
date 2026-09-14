from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, udf, to_timestamp, to_date, hour, coalesce, lit,
    date_format, dayofweek, month, year, when,
)
from pyspark.sql.types import StringType, StructType, StructField

from spark_job.config import kafka_read_options, CHECKPOINT_DIR, TRIGGER_INTERVAL
from spark_job.schema import product_view_schema
from spark_job.utils import extract_domain, map_country, parse_browser, parse_os
from spark_job.geoip import lookup_geo
from spark_job.db import write_batch_to_postgres


def build_spark():
    return SparkSession.builder.appName("glamira-product-view-to-postgres").getOrCreate()

def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    extract_domain_udf = udf(extract_domain, StringType())
    map_country_udf = udf(map_country, StringType())
    parse_browser_udf = udf(parse_browser, StringType())
    parse_os_udf = udf(parse_os, StringType())

    geo_schema = StructType(
        [
            StructField("geo_country", StringType(), True),
            StructField("geo_region", StringType(), True),
        ]
    )
    lookup_geo_udf = udf(lookup_geo, geo_schema)

    reader = spark.readStream.format("kafka")
    for key, value in kafka_read_options().items():
        reader = reader.option(key, value)
    raw = reader.load()

    parsed = (
        raw.selectExpr("CAST(value AS STRING) AS json_value")
        .select(from_json(col("json_value"), product_view_schema).alias("data"))
        .select("data.*")
    )

    enriched = (
        parsed
        .withColumn("local_time", to_timestamp(col("local_time"), "yyyy-MM-dd HH:mm:ss"))
        .withColumn("event_date", to_date(col("local_time")))
        .withColumn("event_hour", hour(col("local_time")))
        .withColumn("weekday_name", date_format(col("event_date"), "EEEE"))
        .withColumn("month_number", month(col("event_date")))
        .withColumn("year_number", year(col("event_date")))
        .withColumn("is_weekend", dayofweek(col("event_date")).isin(1, 7))

        .withColumn("domain", extract_domain_udf(col("current_url")))
        .withColumn(
            "referrer_url",
            when((col("referrer_url").isNull()) | (col("referrer_url") == ""), lit("(direct)"))
            .otherwise(col("referrer_url")),
        )
        .withColumn("referrer_domain", extract_domain_udf(col("referrer_url")))

        .withColumn("_geo", lookup_geo_udf(col("ip")))
        .withColumn("country", coalesce(col("_geo.geo_country"), map_country_udf(col("domain")), lit("Unknown")))
        .withColumn("region", coalesce(col("_geo.geo_region"), lit("Unknown")))
        .drop("_geo")

        .withColumn("browser", parse_browser_udf(col("user_agent")))
        .withColumn("os", parse_os_udf(col("user_agent")))

        .withColumn("product_id", coalesce(col("product_id"), lit("UNKNOWN")))
        .withColumn("store_id", coalesce(col("store_id").cast("long"), lit(0)))

        .drop("option", "email", "current_url", "user_agent", "api_version", "collection", "time_stamp")
    )

    query = (
        enriched.writeStream
        .foreachBatch(write_batch_to_postgres)
        .option("checkpointLocation", CHECKPOINT_DIR)
        .trigger(processingTime=TRIGGER_INTERVAL)
        .outputMode("append")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
