"""Apache Sedona (PySpark) job: 500 m catchments around stores joined to GPS pings.

Counts unique devices per store per hour without collecting data to the driver, so it
scales to millions of pings.

Usage:
    python spatial/spatial_join.py --pings data/raw/pings.csv --stores data/stores.csv \
        --output data/processed/hourly_footfall
Needs Java 11+ and internet access on first run to fetch the Sedona jars.
"""
import argparse
from pyspark.sql import functions as F
from sedona.spark import SedonaContext

RADIUS_M = 500


def build_session():
    config = (
        SedonaContext.builder()
        .appName("geopulse-spatial-join")
        .config("spark.jars.packages",
                "org.apache.sedona:sedona-spark-shaded-3.5_2.12:1.7.1,"
                "org.datasyslab:geotools-wrapper:1.7.1-28.5")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
        .getOrCreate()
    )
    return SedonaContext.create(config)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pings", default="data/raw/pings.csv")
    ap.add_argument("--stores", default="data/stores.csv")
    ap.add_argument("--output", default="data/processed/hourly_footfall")
    ap.add_argument("--radius", type=float, default=RADIUS_M)
    a = ap.parse_args()

    sedona = build_session()

    pings = (sedona.read.option("header", True).option("inferSchema", True).csv(a.pings)
             .withColumn("ts", F.to_timestamp("ts"))
             .withColumn("geom", F.expr("ST_Point(CAST(lon AS DOUBLE), CAST(lat AS DOUBLE))")))
    stores = (sedona.read.option("header", True).option("inferSchema", True).csv(a.stores)
              .withColumn("geom", F.expr("ST_Point(CAST(lon AS DOUBLE), CAST(lat AS DOUBLE))")))

    # Stores are few: broadcast them. ST_DistanceSphere returns metres on the earth's surface.
    joined = pings.alias("p").join(
        F.broadcast(stores.alias("s")),
        F.expr(f"ST_DistanceSphere(p.geom, s.geom) <= {a.radius}"),
    )

    hourly = (joined
              .withColumn("hour", F.date_trunc("hour", F.col("p.ts")))
              .groupBy("s.store_id", "hour")
              .agg(F.countDistinct("p.device_id").alias("unique_visitors"))
              .orderBy("store_id", "hour"))

    hourly.write.mode("overwrite").option("header", True).csv(a.output)
    print(f"Wrote hourly unique visitors to {a.output}")
    sedona.stop()


if __name__ == "__main__":
    main()
