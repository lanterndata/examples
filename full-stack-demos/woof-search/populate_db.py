import pickle
import psycopg2

# Load the embeddings and paths from the .pkl file
with open('embeddings_paths_pairs.pkl', 'rb') as f:
    loaded_embeddings_paths_pairs = pickle.load(f)


# We use the dbname, user, and password that we specified above
conn = psycopg2.connect(
    dbname="dog_images",
    user="postgres",
    password="password",
    host="localhost",
    port="5432" # default port for Postgres
)

# how we created the table in psql:
#CREATE TABLE images (id SERIAL PRIMARY KEY, path text, vector real[]);

TABLE_NAME = "images"

# Get a new cursor
cursor = conn.cursor()


for embedding, path in loaded_embeddings_paths_pairs:
   cursor.execute(f"INSERT INTO {TABLE_NAME}(path, vector) VALUES (%s, %s);", (path, embedding))
    

conn.commit()
cursor.close()

# index creation command:
# CREATE INDEX on images USING hnsw (vector dist_cos_ops);