import gradio as gr
import time
from PIL import Image

import torch
import clip

import os

import psycopg2

# Initialize CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# Prepare postgres
conn = psycopg2.connect(
    dbname="dog_images",
    user="postgres",
    password="password",
    host="localhost",
    port="5432" 
)
TABLE_NAME = "images"

# Performs a vector search using lantern
def single_search(vec):
    cursor = conn.cursor()

    cursor.execute(f"SELECT path, cos_dist(vector, ARRAY{vec}) AS dist FROM {TABLE_NAME} ORDER BY vector <-> ARRAY{vec} LIMIT 9;")
    results = cursor.fetchall()
    
    cursor.close()
    return results


def process_image(uploaded_image):
    start_time = time.time()

    image = preprocess(uploaded_image).unsqueeze(0).to(device)

    # Get vector embedding of the query
    with torch.no_grad():
        image_features = model.encode_image(image)

    query_embedding = image_features.tolist()

    # Perform the vector search
    search_results = single_search(query_embedding)

    gallery_items = [(path, f"Distance: {dist:.4f}") for path, dist in search_results]

    end_time = time.time()
    operation_time = end_time - start_time

    return gallery_items, f"Total time for the search: {operation_time:.2f} seconds"


# Define your Gradio interface
with gr.Blocks() as app:
    gr.Markdown("# WoofSearch: Reverse Image Search For Dogs")

    with gr.Row():
        # Input image
        with gr.Column():

            image_input = gr.Image(type="pil", label="Upload Input Image", width=512, height=512)

        # Gallery for output images
        with gr.Column():
            output_image = gr.Gallery(columns=3, label="Results", show_label=True)

    gr.Markdown("## Examples")

    example_images = [
        "gradio_example_images/0.webp",
        "gradio_example_images/1.jpeg",
        "gradio_example_images/2.jpeg",
        "gradio_example_images/3.webp",
        "gradio_example_images/4.webp",
    ]

    gr.Examples(
        examples=example_images,
        inputs=image_input,
    )

    generate_button = gr.Button("Search")
    output_text = gr.Textbox(label="Operation Time")

    generate_button.click(
        fn=process_image,
        inputs=image_input,
        outputs=[output_image, output_text]
    )


# Run the Gradio app
app.launch()

