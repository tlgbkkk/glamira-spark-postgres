from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    ArrayType,
)

option_schema = StructType(
    [
        StructField("option_id", StringType(), True),
        StructField("option_label", StringType(), True),
    ]
)

product_view_schema = StructType(
    [
        StructField("id", StringType(), True),
        StructField("api_version", StringType(), True),
        StructField("collection", StringType(), True),
        StructField("current_url", StringType(), True),
        StructField("device_id", StringType(), True),
        StructField("email", StringType(), True),
        StructField("ip", StringType(), True),
        StructField("local_time", StringType(), True),
        StructField("option", ArrayType(option_schema), True),
        StructField("product_id", StringType(), True),
        StructField("referrer_url", StringType(), True),
        StructField("store_id", StringType(), True),
        StructField("time_stamp", LongType(), True),
        StructField("user_agent", StringType(), True),
    ]
)
