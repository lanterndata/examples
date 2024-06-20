import pandas as pd
from pyarrow import dataset as ds
from pgpq import ArrowToPostgresBinaryEncoder
import os
import psycopg
from psycopg.rows import namedtuple_row
import json
import numpy as np
from pprint import pprint



def get_yfcc_data(queries=False, dataset="100K"):
    # size: 100K or 10M
    
    # make sure to authenticate with gcloud before running this
    # ./google-cloud-sdk/bin/gcloud auth application-default login
    # yfcc_data = pd.read_parquet("gs://pinecone-datasets-dev/yfcc-10M-filter-euclidean-formatted/queries/part-0.parquet")
    queries_str = "queries" if queries else "passages"
    yfcc_data = pd.read_parquet(
        f"gs://pinecone-datasets-dev/yfcc-{dataset}-filter-euclidean-formatted/{queries_str}/part-0.parquet"
    )
    return yfcc_data

class GlobalConnManager:
    def __init__(self, conn_string):
        self.conn_string = conn_string
        self.global_conn = psycopg.connect(self.conn_string)

    def __enter__(self):
        return self.global_conn

    def __exit__(self, exc_type, exc_value, traceback):
        pass

global_conn_manager = None



def get_conn(conn_string, reuse_conn):
    global global_conn_manager

    if not reuse_conn:
         return psycopg.connect(conn_string)
    else:
        if global_conn_manager is None:
            global_conn_manager = GlobalConnManager(conn_string)
        return global_conn_manager
        
        
def recreate_table(conn_string, queries=False):
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            if queries:
                additional_fields = """
                top_k integer,
                filter jsonb
                """
            else:
                additional_fields = """
                metadata jsonb
                """
            table_name = "yfcc_queries" if queries else "yfcc_passages"
            cur.execute(
                f"""
            DROP TABLE IF EXISTS {table_name};
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                vector real[],
                {additional_fields},
                blob jsonb
            )
            """
            )
        conn.commit()


def recreate_tables(conn_string):
    recreate_table(conn_string, queries=True)
    recreate_table(conn_string, queries=False)


def custom_serializer(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError("Object of type '{}' is not JSON serializable".format(type(obj)))


def _transform_metadata(conn_string, queries=False):
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cursor:

            print("Transforming metadata")
            # transfrm for queries into array mode
            if queries:
                cursor.execute(
                    """
                ALTER TABLE yfcc_queries ADD COLUMN filter_tags INTEGER[];
                UPDATE yfcc_queries SET filter_tags =
                  CASE 
                    WHEN filter::jsonb ? 'tags' THEN ARRAY[filter->>'tags']::INTEGER[]
                    WHEN filter::jsonb ? '$and' THEN ARRAY(SELECT jsonb_array_elements_text(filter::jsonb -> '$and')::jsonb ->> 'tags')::INTEGER[]
                    ELSE ARRAY[]::INTEGER[]
                  END ;

                ALTER TABLE yfcc_queries DROP COLUMN filter;
                        """
                )
            else:
                cursor.execute(
                    """
                ALTER TABLE yfcc_passages ADD COLUMN metadata_tags INTEGER[];
                UPDATE yfcc_passages SET metadata_tags = (SELECT array_agg(v::INTEGER) FROM jsonb_array_elements_text(metadata->'tags') as v);
                CREATE INDEX ON yfcc_passages USING GIN (metadata_tags gin__int_ops);
                ALTER TABLE yfcc_passages DROP COLUMN metadata;
                        """
                )

        conn.commit()
        with conn.cursor() as cursor:
            conn.autocommit = True
            cursor.execute("VACUUM (FULL, ANALYZE) yfcc_queries;")
            cursor.execute("VACUUM (FULL, ANALYZE) yfcc_passages;")


def df2pg(conn_string, df, queries=False):
    # ndarray to json dumps
    df_copy = df.copy()
    df_copy["blob2"] = df_copy["blob"].apply(
        lambda x: json.dumps(x, default=custom_serializer)
    )
    yfcc_data_mapped = df_copy.drop(columns=["blob"], inplace=False)
    yfcc_data_mapped.rename(columns={"blob2": "blob"}, inplace=True)
    # drop column called sparse values if it exists
    if "sparse_values" in yfcc_data_mapped.columns:
        yfcc_data_mapped.drop(columns=["sparse_values"], inplace=True)
    yfcc_data_mapped_take = yfcc_data_mapped  # .take(range(10000))
    yfcc_data_mapped_take.to_parquet("yfcc_data.parquet")
    yfcc_data_mapped_take_arrow = ds.dataset("yfcc_data.parquet")
    schema = yfcc_data_mapped_take_arrow.schema
    encoder = ArrowToPostgresBinaryEncoder(schema)
    pg_schema = encoder.schema()

    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            cols = [
                f'"{col_name}" {col.data_type.ddl()}'
                for col_name, col in pg_schema.columns
            ]
            ddl = (
                f"DROP TABLE IF EXISTS data; CREATE TEMP TABLE data ({','.join(cols)})"
            )
            conn.commit()
            cursor.execute(ddl)
            with cursor.copy("COPY data FROM STDIN WITH (FORMAT BINARY)") as copy:
                copy.write(encoder.write_header())
                for batch in yfcc_data_mapped_take_arrow.to_batches():
                    copy.write(encoder.write_batch(batch))
                    print(f"Writing batch of {len(batch)} rows")
                copy.write(encoder.finish())
            print(cursor.execute("SELECT count(*) FROM data").fetchall())

            if queries:
                cursor.execute(
                    """
    INSERT INTO yfcc_queries (id, top_k, vector, filter, blob)
    SELECT substring(id from 2)::integer, -- id has 'q' prefix in the dataset, we remove it here
           top_k, values::float[], filter::jsonb, blob::jsonb
    FROM data
                """
                )
            else:
                cursor.execute(
                    """
    INSERT INTO yfcc_passages (id, vector, metadata, blob)
    SELECT id::integer, values::float[], metadata::jsonb, blob::jsonb 
    FROM data
                """
                )
    _transform_metadata(conn_string, queries)


def create_extensions(conn_string):
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """CREATE EXTENSION iF NOT EXISTS intarray;
                   CREATE EXTENSION iF NOT EXISTS lantern;"""
            )


def create_index(conn_string):
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "create extension if not exists lantern;CREATE INDEX on yfcc_passages USING lantern_hnsw(vector)"
            )


def pg_stat_reset(conn_string):
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_stat_reset();")


def pg_stat_show(conn_string):
    # select the following columns: indexrelname, idx_scan, idx_scan, idx_tup_read, idx_tup_fetch
    # return with named tuple factory
    with psycopg.connect(conn_string) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                "SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes;"
            )
            return cur.fetchall()


def vector_search(
    conn_string,
    k=10,
    tags=None,
    q_vector_id=None,
    materialize_first=False,
    return_recall=False,
    explain=False,
    reuse_conn=False,
):
    # df = pd.read_sql("""""", con=engine)
    with get_conn(conn_string, reuse_conn) as conn:
        with conn.cursor() as cur:
            if q_vector_id is not None:
                assert tags is None
                q_vector = f"(SELECT vector from yfcc_queries where id = {q_vector_id})"
            else:
                q_vector = "(SELECT vector from yfcc_queries order by id limit 1)"

            if tags is None:
                assert q_vector_id is not None
                tags_query = (
                    f"(SELECT filter_tags from yfcc_queries where id = {q_vector_id})"
                )
            elif isinstance(tags, int):
                tags_query = "ARRAY[{}]".format(tags)
            else:
                assert False, "get back and fix me"
                tags_query = " AND ".join(
                    ["metadata_tags @> ARRAY[{}]".format(tag) for tag in tags]
                )

            if materialize_first:
                q_vector = "ARRAY%s" % (cur.execute(q_vector).fetchone())
                tags_query = "ARRAY%s" % (cur.execute(tags_query).fetchone())

            query = f"""
    SELECT id, 
        vector <-> {q_vector} as dist
    FROM yfcc_passages 
    WHERE 
        metadata_tags @> {tags_query}
    ORDER BY dist
    LIMIT {k}"""

            if explain:
                pprint(
                    cur.execute(
                        f"EXPLAIN (ANALYZE, BUFFERS, TIMING) {query}"
                    ).fetchall()
                )
            else:
                res = cur.execute(query)
                res = res.fetchall()
                if return_recall:
                    assert q_vector_id is not None and tags is None
                    near_ids = [r[0] for r in res]
                    # NULLIF makes sure division does not become division by zero. it leverages the fact that NULL/0 = NULL
                    return_recall_q = f"NULLIF(CARDINALITY(ARRAY(SELECT jsonb_array_elements_text(q.blob->'neighbors'))::INTEGER[] & ARRAY{near_ids}::integer[])::float, 0) / LEAST({k}, (q.blob->'selectivity')::INTEGER) as recall"
                    recall = cur.execute(
                        f"SELECT {return_recall_q} FROM yfcc_queries q WHERE id = {q_vector_id}"
                    ).fetchone()[0]
                    if recall is None:
                        recall = 1
                    return res, recall
                else:
                    return res


def bulk_vector_search(
    conn_string, query_count=10, k=10, filter=True, return_recall=False, explain=False
):
    if k > 10:
        raise ValueError("Ground truth is only available for up to 10 neighbors")

    filter_q = ""
    return_recall_q = "'not selected'"
    if filter:
        filter_q = "WHERE metadata_tags @> filter_tags"

    explain_q = ""
    if explain:
        explain_q = "EXPLAIN"  # (ANALYZE, BUFFERS, TIMING)"

    if return_recall:
        return_recall_q = f"CARDINALITY(ARRAY(SELECT jsonb_array_elements_text(q.blob->'neighbors'))::INTEGER[] & near_ids)::float / LEAST({k}, (q.blob->'selectivity')::INTEGER) as recall"

    with psycopg.connect(conn_string) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            distance_calc_q = "vector <-> q.q_vector"
            distance_calc_q = "l2sq_dist(vector, q.q_vector)"
            query = f"""

             {explain_q} WITH q_vectors AS (SELECT id, blob, filter_tags, vector as q_vector from yfcc_queries order by id limit {query_count})
            -- write necessary lateral join query
            SELECT q.id, near_ids, near_dists, {return_recall_q}
            FROM q_vectors q
            JOIN LATERAL (
                SELECT 
                    array_agg(id ORDER BY rnum) as near_ids, 
                    array_agg(dist ORDER BY rnum) as near_dists
                FROM
                (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY {distance_calc_q}) as rnum, {distance_calc_q} as dist
                    FROM yfcc_passages
                    {filter_q}
                    ORDER BY dist
                    LIMIT {k}
                ) as _unused_name
            ) nearest_neighbor_per_id ON true -- GROUP BY q.id
                """
            # ORDER BY {distance_calc_q}
            print(query)
            res = cur.execute(query)
            return res.fetchall()
