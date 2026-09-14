import threading

from spark_job.config import IP2LOCATION_BIN_PATH, IP2LOCATION_MODE

_lock = threading.Lock()
_db = None

_NO_DATA_VALUES = {"-", "", "INVALID IP ADDRESS", None}


def _get_db():
    global _db

    if _db is None:
        with _lock:
            if _db is None:
                import IP2Location

                print(
                    f"[IP2LOCATION] Loading BIN: "
                    f"{IP2LOCATION_BIN_PATH}"
                )
                print(
                    f"[IP2LOCATION] Mode: "
                    f"{IP2LOCATION_MODE}"
                )

                _db = IP2Location.IP2Location(
                    IP2LOCATION_BIN_PATH,
                    IP2LOCATION_MODE
                )

                print("[IP2LOCATION] BIN loaded successfully")

    return _db


def lookup_geo(ip):
    if not ip:
        return (None, None)

    try:
        db = _get_db()
        rec = db.get_all(str(ip))

        country = rec.country_long
        region = rec.region

        if country in _NO_DATA_VALUES:
            country = None

        if region in _NO_DATA_VALUES:
            region = None

        return (
            str(country) if country is not None else None,
            str(region) if region is not None else None,
        )

    except Exception as e:
        print(
            f"[IP2LOCATION ERROR] "
            f"ip={ip!r}, error={type(e).__name__}: {e}"
        )
        return (None, None)