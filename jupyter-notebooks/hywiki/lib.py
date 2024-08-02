import psycopg2

conn_string = "postgresql://postgres:postgres@localhost:6666"

def add_tsvector_column(table_name, column_name, suffix='_simple', tsvector_strategy='simple'):
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""
    alter table {table_name} add column {column_name}{suffix} text;
    UPDATE {table_name}
    SET {column_name}{suffix} = ts_vector_to_ordered_string(to_tsvector('simple', {column_name}));
    -- WHERE id < 1000;                       
""")

            
def calculate_term_frequency(table_name, column_name, id_column = 'id', limit = None):
    limit_q = ""
    if limit:
        limit_q = f"LIMIT {limit}"
        
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""
    DROP TABLE IF EXISTS term_frequency;
    CREATE TABLE term_frequency AS
    SELECT
    {id_column},
    word,
    COUNT(*) AS frequency
FROM
    (SELECT * FROM {table_name} {limit_q}) a,
    UNNEST(string_to_array(lower(regexp_replace({column_name}, '\\W+', ' ', 'g')), ' ')) AS word
GROUP BY
    {id_column}, word;
    """)
            
            
def total_words(table_name, column_name, id_column = 'id', limit = None):
    limit_q = f"LIMIT {limit}" if limit else ""
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""
    -- Calculate the total number of words in each document
    DROP TABLE IF EXISTS total_words;
    CREATE TABLE total_words AS
    SELECT
        {id_column},
        cardinality(string_to_array(lower(regexp_replace({column_name}, '\\W+', ' ', 'g')), ' '))
    FROM
        (SELECT * FROM {table_name} {limit_q}) a;
    """)



def inverted_frequency(table_name, column_name, id_column = 'id', limit = None):
    limit_q = f"LIMIT {limit}" if limit else ""
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""
    DROP TABLE IF EXISTS unique_terms;
    CREATE TABLE unique_terms AS
    SELECT
        {id_column},
        UNNEST(string_to_array(lower(regexp_replace({column_name}, '\\W+', ' ', 'g')), ' ')) AS word
    FROM
        (SELECT * FROM {table_name} {limit_q}) a
    GROUP BY
        {id_column}, word;
    DROP TABLE IF EXISTS inverted_frequency;
    CREATE TABLE inverted_frequency AS
    SELECT
        word,
        COUNT(DISTINCT {id_column}) AS document_frequency
    FROM
        unique_terms
    GROUP BY
        word;



DROP TABLE IF EXISTS doc_frequency;
CREATE TABLE doc_frequency AS
SELECT
    word,
    COUNT(DISTINCT {id_column}) AS doc_count
FROM
    unique_terms
GROUP BY
    word;
    """)
 

 
def bm25_query(query, table_name, column_name, id_column = 'id', limit = None):
    limit_q = f"LIMIT {limit}" if limit else ""
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""   
WITH res AS (

    SELECT
        (array_agg(corpus.{column_name}))[1],
        array_agg(tf.word),
        array_agg(tf.frequency),
        array_agg(df.doc_count),
        array_agg(cardinality(string_to_array(lower(regexp_replace({column_name}, '\\W+', ' ', 'g')), ' '))),
        SUM(tf.frequency::decimal / cardinality(string_to_array(lower(regexp_replace({column_name}, '\\W+', ' ', 'g')), ' '))
        * LOG((SELECT COUNT(*) AS count FROM {table_name}) / df.doc_count)) AS tf_idf
        
        
    FROM
        (SELECT * FROM {table_name} {limit_q}) corpus
    JOIN term_frequency tf ON corpus.{id_column} = tf.{id_column}
    JOIN doc_frequency df ON tf.word = df.word
    WHERE
        tf.word = ANY(string_to_array('{query}', ' '))
    GROUP BY
        tf.{id_column}
    ) SELECT * from res order by tf_idf desc;
    """)
            return cursor.fetchall()