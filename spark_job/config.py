import os

from dotenv import load_dotenv

load_dotenv()

# Local Kafka
LOCAL_KAFKA_BOOTSTRAP_SERVERS = os.getenv("LOCAL_KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
LOCAL_KAFKA_SECURITY_PROTOCOL = os.getenv("LOCAL_KAFKA_SECURITY_PROTOCOL", "SASL_PLAINTEXT")
LOCAL_KAFKA_SASL_MECHANISM = os.getenv("LOCAL_KAFKA_SASL_MECHANISM", "PLAIN")
LOCAL_KAFKA_USERNAME = os.getenv("LOCAL_KAFKA_USERNAME", "")
LOCAL_KAFKA_PASSWORD = os.getenv("LOCAL_KAFKA_PASSWORD", "")
LOCAL_KAFKA_TOPIC = os.getenv("LOCAL_KAFKA_TOPIC", "product_view_local")

CONSUMER_GROUP_ID = os.getenv("CONSUMER_GROUP_ID", "product_view_spark_group")
AUTO_OFFSET_RESET = os.getenv("AUTO_OFFSET_RESET", "latest")

# Streaming job
CHECKPOINT_DIR = os.getenv("CHECKPOINT_DIR", "/data/checkpoints/product_view")
TRIGGER_INTERVAL = os.getenv("TRIGGER_INTERVAL", "30 seconds")

# Postgres
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "glamira")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# P2Location (IP -> country & region)
IP2LOCATION_BIN_PATH = os.getenv("IP2LOCATION_BIN_PATH", "/data/geoip/IP-COUNTRY-REGION-CITY.BIN")
IP2LOCATION_MODE = os.getenv("IP2LOCATION_MODE", "SHARED_MEMORY")


def kafka_read_options():
    offset = AUTO_OFFSET_RESET if AUTO_OFFSET_RESET in ("earliest", "latest") else "latest"
    opts = {
        "kafka.bootstrap.servers": LOCAL_KAFKA_BOOTSTRAP_SERVERS,
        "subscribe": LOCAL_KAFKA_TOPIC,
        "startingOffsets": offset,
        "failOnDataLoss": "false",
    }
    if LOCAL_KAFKA_SECURITY_PROTOCOL and LOCAL_KAFKA_SECURITY_PROTOCOL.upper() != "PLAINTEXT":
        jaas = (
            "org.apache.kafka.common.security.plain.PlainLoginModule required "
            f'username="{LOCAL_KAFKA_USERNAME}" password="{LOCAL_KAFKA_PASSWORD}";'
        )
        opts.update(
            {
                "kafka.security.protocol": LOCAL_KAFKA_SECURITY_PROTOCOL,
                "kafka.sasl.mechanism": LOCAL_KAFKA_SASL_MECHANISM,
                "kafka.sasl.jaas.config": jaas,
            }
        )
    return opts
