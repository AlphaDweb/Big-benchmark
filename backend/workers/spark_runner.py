import asyncio
from typing import Any, Callable, Dict


class SparkRunner:
    async def run(
        self,
        job: str,
        dataset_mb: int,
        parallelism: int,
        on_progress: Callable[[float], Any],
    ) -> Dict[str, Any]:
        if job != "wordcount":
            raise RuntimeError("Spark runner supports only 'wordcount' job")

        try:
            import os
            from pyspark.sql import SparkSession
        except Exception as e:
            raise RuntimeError("pyspark not available") from e

        # Create dataset in-memory then parallelize and process
        # Ensure Spark uses this Python (venv) for both driver and workers
        import sys
        pyexe = sys.executable
        os.environ["PYSPARK_PYTHON"] = pyexe
        os.environ["PYSPARK_DRIVER_PYTHON"] = pyexe

        from pyspark import SparkConf
        conf = (
            SparkConf()
            .setAppName("BigBenchmarkWordCount")
            .setMaster("local[*]")
            .set("spark.pyspark.python", pyexe)
            .set("spark.pyspark.driver.python", pyexe)
        )
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        sc = spark.sparkContext
        sc.setLogLevel("ERROR")

        line = "lorem ipsum dolor sit amet consectetur adipiscing elit"
        # Approximate number of lines to reach dataset_mb
        bytes_per_line = len((line + "\n").encode())
        target_bytes = dataset_mb * 1024 * 1024
        num_lines = max(1, target_bytes // bytes_per_line)

        # Create RDD
        parts = max(1, parallelism)
        rdd = sc.parallelize([line] * int(num_lines), parts)

        # Report mid progress
        on_progress(0.3)

        words = rdd.flatMap(lambda s: s.split())
        pairs = words.map(lambda w: (w, 1))
        counts = pairs.reduceByKey(lambda a, b: a + b)
        # Trigger action
        result = counts.count()

        # Finish
        on_progress(1.0)
        records = int(num_lines) * len(line.split())

        try:
            version = spark.version
        except Exception:
            version = "unknown"
        finally:
            try:
                spark.stop()
            except Exception:
                pass

        return {
            "records": records,
            "throughput_rps": None,
            "framework_version": f"Spark {version}",
        }


