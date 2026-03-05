-- ── 버스 정류장 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bus_stops (
    id SERIAL PRIMARY KEY,
    ars_id VARCHAR(10) NOT NULL,
    node_id VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    routes TEXT[],
    use_ym VARCHAR(6) NOT NULL,
    total_ride INTEGER DEFAULT 0,
    total_alight INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_bus_stops_ars_id ON bus_stops (ars_id);
CREATE INDEX IF NOT EXISTS idx_bus_stops_node_id ON bus_stops (node_id);

CREATE TABLE IF NOT EXISTS bus_stop_hourly (
    id SERIAL PRIMARY KEY,
    stop_id INTEGER NOT NULL REFERENCES bus_stops(id) ON DELETE CASCADE,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    ride INTEGER DEFAULT 0,
    alight INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_bus_stop_hourly_stop_id ON bus_stop_hourly (stop_id);
CREATE INDEX IF NOT EXISTS idx_bus_stop_hourly_hour ON bus_stop_hourly (hour);

-- ── 실시간 교통속도 이력 (TOPIS 5분 주기) ────────────────────────────
CREATE TABLE IF NOT EXISTS traffic_realtime_log (
    id BIGSERIAL PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    link_id VARCHAR(20) NOT NULL,
    speed REAL NOT NULL,
    travel_time REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_trl_fetched_at ON traffic_realtime_log (fetched_at);
CREATE INDEX IF NOT EXISTS idx_trl_link_fetched ON traffic_realtime_log (link_id, fetched_at);

-- ── 지하철역 ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subway_stations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    sub_sta_sn INTEGER,
    use_date VARCHAR(8)
);

CREATE INDEX IF NOT EXISTS idx_subway_stations_sub_sta_sn ON subway_stations (sub_sta_sn);

CREATE TABLE IF NOT EXISTS subway_station_hourly (
    id SERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES subway_stations(id) ON DELETE CASCADE,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    ride INTEGER DEFAULT 0,
    alight INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_subway_station_hourly_station_id ON subway_station_hourly (station_id);

-- ── 도로 교통속도 세그먼트 ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS traffic_segments (
    id SERIAL PRIMARY KEY,
    link_id VARCHAR(30) NOT NULL UNIQUE,
    road_name VARCHAR(100),
    direction VARCHAR(10),
    distance INTEGER,
    lanes INTEGER,
    road_type VARCHAR(50),
    area_type VARCHAR(20),
    coordinates JSONB,
    speeds REAL[],
    use_date VARCHAR(8)
);

CREATE INDEX IF NOT EXISTS idx_traffic_segments_link_id ON traffic_segments (link_id);

-- ── 상가 ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stores (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    road_address TEXT,
    category_bg VARCHAR(20),
    category_mi VARCHAR(100),
    category_sl VARCHAR(100),
    lng DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    peco_total BIGINT DEFAULT 0,
    peco_individual BIGINT DEFAULT 0,
    peco_corporate BIGINT DEFAULT 0,
    peco_foreign BIGINT DEFAULT 0,
    times JSONB,
    weekday JSONB,
    gender_f JSONB,
    gender_m JSONB
);

CREATE INDEX IF NOT EXISTS idx_stores_category_bg ON stores (category_bg);

-- ── 사업장 근로자·임금 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS salary_workplaces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    industry VARCHAR(200),
    employees INTEGER DEFAULT 0,
    monthly_salary REAL DEFAULT 0,
    lng DOUBLE PRECISION,
    lat DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_salary_workplaces_industry ON salary_workplaces (industry);

-- ── 보행 유동인구 링크 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foottraffic_links (
    id SERIAL PRIMARY KEY,
    road_link_id VARCHAR(30) NOT NULL UNIQUE,
    coordinates JSONB,
    centroid_lng DOUBLE PRECISION,
    centroid_lat DOUBLE PRECISION,
    data JSONB
);

CREATE INDEX IF NOT EXISTS idx_foottraffic_links_road_link_id ON foottraffic_links (road_link_id);
