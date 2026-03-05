from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, ForeignKey,
    ARRAY, DateTime, JSON, Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ── 버스 정류장 ─────────────────────────────────────────────────────
class BusStop(Base):
    __tablename__ = "bus_stops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ars_id = Column(String(10), nullable=False, index=True)
    node_id = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    lng = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    routes = Column(ARRAY(String), nullable=True)
    use_ym = Column(String(6), nullable=False)
    total_ride = Column(Integer, default=0)
    total_alight = Column(Integer, default=0)
    total = Column(Integer, default=0)

    hourly = relationship("BusStopHourly", back_populates="stop", cascade="all, delete-orphan")


class BusStopHourly(Base):
    __tablename__ = "bus_stop_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stop_id = Column(Integer, ForeignKey("bus_stops.id", ondelete="CASCADE"), nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    ride = Column(Integer, default=0)
    alight = Column(Integer, default=0)

    stop = relationship("BusStop", back_populates="hourly")


# ── 실시간 교통속도 이력 (TOPIS 5분 주기) ──────────────────────────
class TrafficRealtimeLog(Base):
    __tablename__ = "traffic_realtime_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    link_id = Column(String(20), nullable=False)
    speed = Column(Float, nullable=False)
    travel_time = Column(Float, nullable=False, default=0)


# ── 지하철역 (Silver: subway_stations_hourly.json) ──────────────────
class SubwayStation(Base):
    __tablename__ = "subway_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    lng = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    sub_sta_sn = Column(Integer, nullable=True, index=True)
    use_date = Column(String(8), nullable=True)

    hourly = relationship("SubwayStationHourly", back_populates="station", cascade="all, delete-orphan")


class SubwayStationHourly(Base):
    __tablename__ = "subway_station_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("subway_stations.id", ondelete="CASCADE"), nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    ride = Column(Integer, default=0)
    alight = Column(Integer, default=0)

    station = relationship("SubwayStation", back_populates="hourly")


# ── 도로 교통속도 세그먼트 (Silver: traffic_seongsu.json) ─────────────
class TrafficSegment(Base):
    __tablename__ = "traffic_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link_id = Column(String(30), nullable=False, unique=True, index=True)
    road_name = Column(String(100), nullable=True)
    direction = Column(String(10), nullable=True)
    distance = Column(Integer, nullable=True)
    lanes = Column(Integer, nullable=True)
    road_type = Column(String(50), nullable=True)
    area_type = Column(String(20), nullable=True)
    coordinates = Column(JSON, nullable=True)
    speeds = Column(ARRAY(Float), nullable=True)
    use_date = Column(String(8), nullable=True)


# ── 상가 (Silver: stores_seongsu.json) ──────────────────────────────
class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String(30), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    road_address = Column(Text, nullable=True)
    category_bg = Column(String(20), nullable=True, index=True)
    category_mi = Column(String(100), nullable=True)
    category_sl = Column(String(100), nullable=True)
    lng = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    peco_total = Column(BigInteger, default=0)
    peco_individual = Column(BigInteger, default=0)
    peco_corporate = Column(BigInteger, default=0)
    peco_foreign = Column(BigInteger, default=0)
    times = Column(JSON, nullable=True)
    weekday = Column(JSON, nullable=True)
    gender_f = Column(JSON, nullable=True)
    gender_m = Column(JSON, nullable=True)


# ── 사업장 근로자·임금 (Silver: salary_seongsu.json) ─────────────────
class SalaryWorkplace(Base):
    __tablename__ = "salary_workplaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=True)
    industry = Column(String(200), nullable=True, index=True)
    employees = Column(Integer, default=0)
    monthly_salary = Column(Float, default=0)
    lng = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)


# ── 보행 유동인구 링크 (Silver: foottraffic_seongsu.json) ─────────────
class FoottrafficLink(Base):
    __tablename__ = "foottraffic_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    road_link_id = Column(String(30), nullable=False, unique=True, index=True)
    coordinates = Column(JSON, nullable=True)
    centroid_lng = Column(Float, nullable=True)
    centroid_lat = Column(Float, nullable=True)
    data = Column(JSON, nullable=True)
