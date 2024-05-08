# Used for Blog 15 - Wal Size Experiments
require 'sequel'
require 'json'
require 'pry'
require 'rainbow/refinement'
require_relative './wallib'
require_relative './.env'

using(Rainbow)

include WalLib

DB = Sequel.connect(ENV['DATABASE_URL'])

DB.run('CREATE EXTENSION IF NOT EXISTS pg_walinspect')
DB.run('CREATE EXTENSION IF NOT EXISTS vector')
DB.run('CREATE EXTENSION IF NOT EXISTS lantern')

VECTOR_DIM = 1536

def r
  load __FILE__
  DB.run('rollback;DROP TABLE IF EXISTS a ,embeddings1, embeddings2, papers CASCADE')
  DB.run('rollback;DROP TABLE IF EXISTS a,b,c')
  DB.run('DROP TABLE IF EXISTS wal_records, experiment_results CASCADE')
  setup
  'Reloaded'
end

def setup
  DB.create_table(:experiment_results) do
    primary_key :id
    String :name
    Integer :num_rows
    Integer :total_wal_movement
    Integer :total_time_ms
  end

  # {:resource_manager=>"Generic", :record_type=>"Generic", :count=>131, :total_record_length=>964338, :total_main_data_length=>0, :total_fpi_length=>957912}
  # {:resource_manager=>"Btree", :record_type=>"INSERT_LEAF", :count=>11, :total_record_length=>744, :total_main_data_length=>22, :total_fpi_length=>0}
  # {:resource_manager=>"Heap2", :record_type=>"NEW_CID", :count=>5, :total_record_length=>300, :total_main_data_length=>170, :total_fpi_length=>0}
  # {:resource_manager=>"Heap2", :record_type=>"MULTI_INSERT", :count=>3, :total_record_length=>350, :total_main_data_length=>18, :total_fpi_length=>0}
  # {:resource_manager=>"Heap", :record_type=>"INSERT", :count=>2, :total_record_length=>441, :total_main_data_length=>6, :total_fpi_length=>0}
  # {:resource_manager=>"Heap", :record_type=>"INPLACE", :count=>2, :total_record_length=>417, :total_main_data_length=>4, :total_fpi_length=>0}
  # {:resource_manager=>"Transaction", :record_type=>"INVALIDATION", :count=>2, :total_record_length=>284, :total_main_data_length=>232, :total_fpi_length=>0}
  # {:resource_manager=>"Storage", :record_type=>"CREATE", :count=>1, :total_record_length=>42, :total_main_data_length=>16, :total_fpi_length=>0}
  # {:resource_manager=>"Standby", :record_type=>"LOCK", :count=>1, :total_record_length=>42, :total_main_data_length=>16, :total_fpi_length=>0}
  # table for the data above
  DB.create_table(:wal_records) do
    primary_key :id
    foreign_key :experiment_result_id, :experiment_results
    String :resource_manager
    String :record_type
    Integer :count
    Integer :total_record_length
    Integer :total_main_data_length
    Integer :total_fpi_length
  end
end

setup unless DB.table_exists?(:experiment_results) || DB.table_exists?(:wal_records)

class ExperimentResult < Sequel::Model
  one_to_many :wal_records
end

class WalRecord < Sequel::Model
  many_to_one :experiment_result
end

def experiments
  puts 'Experiments'
  puts 'Note that txid_current allocated a transaction ID even when one is not needed'
  wal_movement('CREATE TABLE a(i bigint)', flush: true)
  wal_movement('BEGIN; CREATE TABLE b(i bigint); COMMIT')
  wal_movement('BEGIN; CREATE TABLE c(i bigint); SELECT txid_current(); COMMIT')
  wal_movement('SELECT pg_current_xact_id_if_assigned();')
  wal_movement('SELECT pg_current_xact_id();', flush: true)
  wal_movement('BEGIN;SELECT pg_current_xact_id();SELECT pg_current_xact_id();SELECT pg_current_xact_id();COMMIT;',
               flush: true)
  wal_movement('SELECT pg_current_xact_id();SELECT pg_current_xact_id();SELECT pg_current_xact_id();', flush: true)
  DB.run('DROP TABLE a,b,c')
  DB.run('DROP TABLE IF EXISTS a,b,c')
  DB.transaction do
  end
end

def aborted
  puts 'Aborted transactions still generate WAL'
  wal_movement(flush: true, wal_info: true) do
    DB.transaction do
      DB.rollback_on_exit
      DB.run('CREATE TABLE a(i bigint)')
    end
  end
end

def populate_table(table_name, count: 1_000, add_vectors: false)
  if add_vectors
    DB.run("INSERT INTO #{table_name}(i, t, v) SELECT RANDOM() * 1000 * 1000, md5(random()::text), array_agg(random()) FROM generate_series(1, #{count}) a cross join generate_series(1, #{VECTOR_DIM}) group by a;")
  else
    DB.run("INSERT INTO #{table_name}(i) SELECT RANDOM() * 1000 * 1000 FROM generate_series(1, #{count})")
  end
end

def temporary_table_tx(run_at_create: true, count: 1000)
  wal_movement(flush: true) do
    DB.transaction do
      DB.rollback_on_exit
      DB.run("CREATE TABLE a(i bigint, t text, v real[#{VECTOR_DIM}])")
      yield if block_given? && run_at_create
      populate_table('a', add_vectors: true, count:)
      yield if block_given? && !run_at_create
    end
  end
end

def create_index_experiment(name, count, run_at_create, create_index_query)
  title "Experiment #{name} [#{count} rows]"
  start = Time.now
  movement, info = temporary_table_tx(run_at_create:, count:) do
    DB.run(create_index_query)
  end
  total_time_ms = (Time.now - start)
  res = ExperimentResult.create({ name:, num_rows: count, total_time_ms:, total_wal_movement: movement })
  info.each do |r|
    res.add_wal_record(r)
  end
end

def tt
  DB.run('VACUUM')
  title 'table creation experiments [in explicit transaction]'
  temporary_table_tx
  title 'table creation experiments [no explicit transaction]'
  wal_movement do
    # DB.rollback_on_exit
    DB.run('CREATE TABLE b(i bigint)')
    populate_table('b')
  end

  [1000, 2000, 3000, 5000, 10_000].each do |count|
    create_index_experiment('NO INDEX', count, false,
                            'SELECT 1')
    [false, true].each do |run_at_create|
      run_at_create_str = run_at_create ? 'before' : 'after'

      create_index_experiment("create btee index #{run_at_create_str} insert", count, run_at_create,
                              'CREATE INDEX i_a ON a(i)')
      create_index_experiment("create hash index #{run_at_create_str} insert", count, run_at_create,
                              'CREATE INDEX ih_a ON a using hash(i)')

      create_index_experiment("create btee index ON TEXT #{run_at_create_str} insert", count, run_at_create,
                              'CREATE INDEX i_a ON a(t)')
      create_index_experiment("create hash index ON TEXT #{run_at_create_str} insert", count, run_at_create,
                              'CREATE INDEX ih_a ON a using hash(t)')
      create_index_experiment("create pgvector index #{run_at_create_str} insert", count, run_at_create,
                              "CREATE INDEX v_a ON a using hnsw((v::vector(#{VECTOR_DIM})) vector_cosine_ops) WITH (M=16, ef_construction = 100)")
      # puts 'index size: ' + DB.fetch('SELECT pg_size_pretty(pg_relation_size(\'v_a\'))').first[:pg_size_pretty]
      create_index_experiment("create lantern index #{run_at_create_str} insert", count, run_at_create,
                              "CREATE INDEX vl_a ON a using lantern_hnsw(v dist_cos_ops) WITH (dim=#{VECTOR_DIM}, M=16, ef_construction = 100)")
    end
  end

  DB.run('DROP TABLE IF EXISTS a,b,c')
  results = ExperimentResult.select(:name, :num_rows,
                                    :total_wal_movement)
                            # .where(resource_manager: 'Generic')
                            .to_hash_groups(:name)
                            .transform_values do |v|
                              {
                                num_rows: v.map { |r| r[:num_rows] },
                                total_wal_movement: v.map do |r|
                                                      r[:total_wal_movement]
                                                    end
                              }
                            end

  results = { labels: results.values[0][:num_rows], datasets: results.map do |k, v|
                                                                { label: k, data: v[:total_wal_movement] }
                                                              end }

  q = DB[<<~SQL].to_hash_groups(:name)
    SELECT name,
           resource_manager || '_' || record_type as label,
           array_agg(total_record_length) as total_record_length,
           array_agg(num_rows) FROM wal_records
    JOIN experiment_results b
    ON b.id = experiment_result_id
    GROUP BY name,
            resource_manager || '_' || record_type
  SQL

  wal_results = q.transform_values { |v| v.map { |r| { label: r[:label], data: r[:total_record_length] } } }

  results_json = JSON.pretty_generate(results)
  File.open('index_type_movement.jsonl', 'w') { |f| f.write(results_json) }

  wal_results_json = JSON.pretty_generate(wal_results)
  File.open('wal_record_types.jsonl', 'w') { |f| f.write(wal_results_json) }
end
