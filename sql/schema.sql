CREATE SCHEMA IF NOT EXISTS glamira;


CREATE TABLE IF NOT EXISTS glamira.dim_date (
    date_key        BIGSERIAL PRIMARY KEY,
    actual_date     DATE NOT NULL UNIQUE,
    weekday_name    VARCHAR(20) NOT NULL,
    month_number    BIGINT NOT NULL,
    year_number     BIGINT NOT NULL,
    is_weekend      BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS glamira.dim_product (
    product_key     BIGSERIAL PRIMARY KEY,
    product_id      VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS glamira.dim_location (
    location_key    BIGSERIAL PRIMARY KEY,
    country_name    VARCHAR(100) NOT NULL,
    region_name     VARCHAR(150) NOT NULL,
    UNIQUE (country_name, region_name)
);

CREATE TABLE IF NOT EXISTS glamira.dim_device (
    device_key      BIGSERIAL PRIMARY KEY,
    browser         VARCHAR(50) NOT NULL,
    os              VARCHAR(50) NOT NULL,
    UNIQUE (browser, os)
);

CREATE TABLE IF NOT EXISTS glamira.dim_referrer (
    referrer_key    BIGSERIAL PRIMARY KEY,
    referrer_url    TEXT NOT NULL,
    referrer_domain VARCHAR(100)
);

CREATE UNIQUE INDEX IF NOT EXISTS dim_referrer_referrer_url_md5_idx
    ON glamira.dim_referrer (md5(referrer_url));

INSERT INTO glamira.dim_referrer (referrer_url, referrer_domain)
VALUES ('(direct)', NULL)
ON CONFLICT ((md5(referrer_url))) DO NOTHING;

CREATE TABLE IF NOT EXISTS glamira.fact_product_view (
    product_view_key    BIGSERIAL PRIMARY KEY,
    id                   VARCHAR(64) NOT NULL UNIQUE,
    date_key             BIGINT NOT NULL REFERENCES glamira.dim_date(date_key),
    product_key          BIGINT NOT NULL REFERENCES glamira.dim_product(product_key),
    location_key         BIGINT NOT NULL REFERENCES glamira.dim_location(location_key),
    device_key           BIGINT NOT NULL REFERENCES glamira.dim_device(device_key),
    referrer_key          BIGINT NOT NULL REFERENCES glamira.dim_referrer(referrer_key),
    store_id             BIGINT NOT NULL,
    ip_address           VARCHAR(45) NOT NULL,
    event_hour           SMALLINT NOT NULL,
    created_at           TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fpv_date_key       ON glamira.fact_product_view (date_key);
CREATE INDEX IF NOT EXISTS idx_fpv_product_key     ON glamira.fact_product_view (product_key);
CREATE INDEX IF NOT EXISTS idx_fpv_location_key    ON glamira.fact_product_view (location_key);
CREATE INDEX IF NOT EXISTS idx_fpv_device_key      ON glamira.fact_product_view (device_key);
CREATE INDEX IF NOT EXISTS idx_fpv_referrer_key    ON glamira.fact_product_view (referrer_key);
CREATE INDEX IF NOT EXISTS idx_fpv_store_id        ON glamira.fact_product_view (store_id);
CREATE INDEX IF NOT EXISTS idx_fpv_date_hour       ON glamira.fact_product_view (date_key, event_hour);

-- 1) Top 10 product_id theo luot view trong ngay hien tai
CREATE OR REPLACE VIEW glamira.rpt_top10_products_today AS
SELECT p.product_id, COUNT(*) AS view_count
FROM glamira.fact_product_view f
JOIN glamira.dim_date d ON d.date_key = f.date_key
JOIN glamira.dim_product p ON p.product_key = f.product_key AND p.product_id != 'UNKNOWN'
WHERE d.actual_date = CURRENT_DATE
GROUP BY p.product_id
ORDER BY view_count DESC
LIMIT 10;

-- 2) Top 10 quoc gia theo luot view trong ngay hien tai
CREATE OR REPLACE VIEW glamira.rpt_top10_countries_today AS
SELECT l.country_name AS country, COUNT(*) AS view_count
FROM glamira.fact_product_view f
JOIN glamira.dim_date d ON d.date_key = f.date_key
JOIN glamira.dim_location l ON l.location_key = f.location_key
WHERE d.actual_date = CURRENT_DATE
GROUP BY l.country_name
ORDER BY view_count DESC
LIMIT 10;

-- 3) Top 5 referrer_url theo luot view trong ngay hien tai
CREATE OR REPLACE VIEW glamira.rpt_top5_referrers_today AS
SELECT r.referrer_url, COUNT(*) AS view_count
FROM glamira.fact_product_view f
JOIN glamira.dim_date d ON d.date_key = f.date_key
JOIN glamira.dim_referrer r ON r.referrer_key = f.referrer_key
WHERE d.actual_date = CURRENT_DATE
  AND r.referrer_url <> '(direct)'
GROUP BY r.referrer_url
ORDER BY view_count DESC
LIMIT 5;

-- 4) Voi 1 quoc gia bat ky: danh sach store_id + luot view, giam dan
CREATE OR REPLACE FUNCTION glamira.get_store_views_by_country(p_country VARCHAR)
RETURNS TABLE(store_id BIGINT, view_count BIGINT) AS $$
    SELECT f.store_id, COUNT(*) AS view_count
    FROM glamira.fact_product_view f
    JOIN glamira.dim_location l ON l.location_key = f.location_key
    WHERE l.country_name = p_country
    GROUP BY f.store_id
    ORDER BY view_count DESC;
$$ LANGUAGE sql STABLE;

-- 5) Du lieu view phan bo theo gio cua 1 product_id bat ky trong ngay
CREATE OR REPLACE FUNCTION glamira.get_hourly_views_by_product(
    p_product_id VARCHAR,
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE(event_hour SMALLINT, view_count BIGINT) AS $$
    SELECT f.event_hour, COUNT(*) AS view_count
    FROM glamira.fact_product_view f
    JOIN glamira.dim_date d ON d.date_key = f.date_key
    JOIN glamira.dim_product p ON p.product_key = f.product_key
    WHERE p.product_id = p_product_id
      AND d.actual_date = p_date
    GROUP BY f.event_hour
    ORDER BY f.event_hour;
$$ LANGUAGE sql STABLE;

-- 6) Du lieu view theo gio cua tung browser, os (ngay hien tai)
CREATE OR REPLACE VIEW glamira.rpt_hourly_views_by_browser_os_today AS
SELECT dv.browser, dv.os, f.event_hour, COUNT(*) AS view_count
FROM glamira.fact_product_view f
JOIN glamira.dim_date d ON d.date_key = f.date_key
JOIN glamira.dim_device dv ON dv.device_key = f.device_key
WHERE d.actual_date = CURRENT_DATE
GROUP BY dv.browser, dv.os, f.event_hour
ORDER BY dv.browser, dv.os, f.event_hour;
