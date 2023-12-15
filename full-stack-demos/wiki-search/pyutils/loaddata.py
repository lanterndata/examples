from datasets import load_dataset
import time
import psycopg2
import numpy as np

from oursecrets import LANTERN_PG_URI

# Postgres setup
conn = psycopg2.connect(LANTERN_PG_URI)
print("Connected to Lantern database!")
TABLE_NAME = "passages"

# Load dataset incrementally
entire_dataset = load_dataset("Cohere/wikipedia-22-12-en-embeddings", split="train", streaming=True) 
# We can skip the first N=500 rows like this:
#entire_dataset = entire_dataset.skip(500)

def normalize_vector(v):
    v = np.array(v)
    magnitude = np.linalg.norm(v)
    return (v / magnitude).tolist()

def batch_insert(rows):
    start = time.time()

    data = [(row['id'], row['title'], row['text'], row['url'], row['wiki_id'], row['views'], row['paragraph_id'], row['langs'], row['emb']) for row in rows]
    #print(data)
    cur = conn.cursor()

    query = f"INSERT INTO {TABLE_NAME} (id, title, text_content, url, wiki_id, views, paragraph_id, langs, emb) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"

    cur.executemany(query, data)
    conn.commit()

    cur.close()

    elapsed = time.time() - start
    return elapsed


# Begin inserting rows
num_rows = 1_000_000
batch_size = 1_000

batch = []
batch_n = 1

batch_start = time.time()

for i, row in enumerate(entire_dataset):
    if (i+1) > num_rows:
        break

    row['emb'] = normalize_vector(row['emb'])
    batch.append(row)

    if len(batch) == batch_size:
        batch_end = time.time()
        print(f"Batch# {batch_n} took {batch_end - batch_start}s to gather")

        print("Upserting batch...")
        elapsed = batch_insert(batch)
        print(f"Finished upserting batch! Took {elapsed}s")

        batch = []
        batch_n += 1
        batch_start = time.time()