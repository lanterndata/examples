# Used for Blog 15 - Wal Size Experiments
require 'sequel'
require 'json'
require 'pry'
require 'rainbow/refinement'
require_relative './wallib'
require_relative './.env'

using(Rainbow)

DB = Sequel.connect(ENV['DATABASE_URL'])

DB.run('CREATE EXTENSION IF NOT EXISTS pg_walinspect')
DB.run('CREATE EXTENSION IF NOT EXISTS vector')
DB.run('CREATE EXTENSION IF NOT EXISTS lantern')
def r
  DB.run('rollback;DROP TABLE IF EXISTS a ,embeddings1, embeddings2, papers CASCADE')
  DB.run('rollback;DROP TABLE IF EXISTS a,b,c')
  DB.run('DROP TABLE IF EXISTS experiment_results, wal_records CASCADE')
  load __FILE__
  'Reloaded'
end

VECTOR_DIM = 1536

TEXT_SIZE = 150
ROW_COUNT = 10_000

def hot_info
  DB.fetch(<<~SQL).all
      SELECT
        relname AS table_name,
        seq_scan AS sequential_scans,
        idx_scan AS index_scans,
        n_tup_ins AS inserts,
        n_tup_upd AS updates,
        n_tup_hot_upd AS hot_updates
    FROM
        pg_stat_user_tables
    ORDER BY
        hot_updates DESC;
  SQL
end

def insert_text_data
  DB.run("INSERT INTO papers(t1) SELECT get_random_string(#{TEXT_SIZE}) FROM generate_series(1, #{ROW_COUNT}) a cross join generate_series(1, #{VECTOR_DIM}) group by a;")
end

def hot
  include WalLib

  DB.run('DROP TABLE IF EXISTS embeddings1, embeddings2, papers CASCADE')
  DB.run(<<~SQL)
      CREATE OR REPLACE FUNCTION get_random_string(
            IN string_length INTEGER,
            IN possible_chars TEXT
            DEFAULT '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        ) RETURNS text
        LANGUAGE plpgsql
        AS $$
    DECLARE
        output TEXT = '';
        i INT4;
        pos INT4;
    BEGIN
        FOR i IN 1..string_length LOOP
            pos := 1 + CAST( random() * ( LENGTH(possible_chars) - 1) AS INT4 );
            output := output || substr(possible_chars, pos, 1);
        END LOOP;
        RETURN output;
    END;
    $$;
  SQL

  start = Time.now
  movement, = wal_movement(flush: true) do
    title 'scenario 1: vector column part of main table'
    DB.transaction do
      # DB.rollback_on_exit
      # create table
      DB.run("CREATE TABLE papers(id bigserial PRIMARY KEY, t1 text, t2 text, v1 real[#{VECTOR_DIM}], v2 real[#{VECTOR_DIM}])")
      # create vector index on the table
      DB.run("CREATE INDEX v1_papers ON papers using hnsw((v1::vector(#{VECTOR_DIM})) vector_cosine_ops) WITH (M=16, ef_construction = 100)")
      DB.run("CREATE INDEX v2_papers ON papers using hnsw((v2::vector(#{VECTOR_DIM})) vector_cosine_ops) WITH (M=16, ef_construction = 100)")
      # DB.run('CREATE INDEX t_gin ON a using gin(to_tsvector(\'english\', t))')
      # insert row text data into the table
      insert_text_data
      # asynchronously generate and upsert embeddings
      num_updated = 0
      %w[v1 v2].each do |vi|
        num_updated += DB.fetch(<<~SQL).all.map(&:values).flatten.sum
          INSERT INTO papers(id, #{vi})
          SELECT seq.i, array_agg(random() ORDER BY gs) AS random_v
          FROM generate_series(1, #{ROW_COUNT}) AS seq(i)
          CROSS JOIN LATERAL generate_series(1, #{VECTOR_DIM}) AS gs
          GROUP BY seq.i
          ON CONFLICT (id) DO UPDATE SET #{vi} = EXCLUDED.#{vi} RETURNING 1 as num_updated;
        SQL
      end
      puts "updated #{num_updated} rows"
    end
  end
  puts movement, 'time', Time.now - start, hot_info
  DB.run('DROP TABLE IF EXISTS papers')
  start = Time.now
  movement, = wal_movement(flush: true) do
    title 'scenario 2: vector column part of separate table'
    DB.transaction do
      # DB.rollback_on_exit
      # create table
      DB.run('CREATE TABLE papers(id bigserial PRIMARY KEY, t1 text, t2 text)')
      # DB.run('CREATE INDEX t_gin ON a using gin(to_tsvector(\'english\', t))')
      DB.run("CREATE TABLE embeddings1(papers_id bigint PRIMARY KEY REFERENCES papers(id), v real[#{VECTOR_DIM}])")
      DB.run("CREATE TABLE embeddings2(papers_id bigint PRIMARY KEY REFERENCES papers(id), v real[#{VECTOR_DIM}])")
      # create vector index on the table
      DB.run("CREATE INDEX embeddings1_v ON embeddings1 using hnsw((v::vector(#{VECTOR_DIM})) vector_cosine_ops) WITH (M=16, ef_construction = 100)")
      DB.run("CREATE INDEX embeddings2_v ON embeddings2 using hnsw((v::vector(#{VECTOR_DIM})) vector_cosine_ops) WITH (M=16, ef_construction = 100)")
      # insert row text data into the table
      insert_text_data
      # asynchronously generate and insert embeddings
      num_updated = 0
      %w[embeddings1 embeddings2].each do |embeddingsi|
        num_updated += DB.fetch(<<~SQL).all.map(&:values).flatten.sum
          WITH new_embeddings AS (
              SELECT id as papers_id
              FROM papers
          )
          INSERT INTO #{embeddingsi} (papers_id, v)
          SELECT n.papers_id, array_agg(random() ORDER BY gs)
          FROM new_embeddings n
          CROSS JOIN LATERAL generate_series(1, #{VECTOR_DIM}) AS gs(gs)
          GROUP BY n.papers_id
          ON CONFLICT (papers_id) DO UPDATE SET v = EXCLUDED.v RETURNING 1 AS num_updated;
        SQL
      end
      puts "updated #{num_updated} rows"
    end
  end
  puts movement, 'time', Time.now - start, hot_info
end
