from pathlib import Path
import torch
import clip
from PIL import Image
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
import pickle

# Directory where your images are stored
root_dir = 'Images'

# CLIP requires a specific preprocessing pipeline
preprocess = Compose([
    Resize(256, interpolation=3),
    CenterCrop(224),
    ToTensor(),
    Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
])

# Use CUDA if available
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# A custom dataset to read images from a list of files
class ImageDataset(Dataset):
    def __init__(self, file_paths, transform=None):
        self.file_paths = [str(path) for path in file_paths]
        self.transform = transform

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        image_path = self.file_paths[idx]
        image = Image.open(image_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, image_path

# Function to get all image paths
def get_image_paths(directory):
    return list(Path(directory).rglob('*.jpg')) + list(Path(directory).rglob('*.jpeg'))

# Batch size for embedding
batch_size = 32  # You can adjust this according to your GPU memory

# Get all image file paths
image_paths = get_image_paths(root_dir)
print(image_paths)
image_dataset = ImageDataset(image_paths, transform=preprocess)
image_dataloader = DataLoader(image_dataset, batch_size=batch_size, shuffle=False)

def process_and_embed_images(dataloader, model):
    model.eval()  # Put the model in evaluation mode
    embeddings = []
    paths = []

    with torch.no_grad():  # No need to track gradients
        # Initialize the tqdm progress bar
        progress_bar = tqdm(dataloader, desc="Processing Images", mininterval=1)
        for images, image_paths in progress_bar:
            images = images.to(device)
            # Get the embeddings for this batch
            batch_embeddings = model.encode_image(images)
            
            embeddings.append(batch_embeddings.cpu())
            paths.extend(image_paths)
            
            # Manually update the progress bar
            progress_bar.update()
            progress_bar.refresh()  # Force refresh the stdout
            #sys.stdout.flush() 

    # Concatenate all the embeddings from each batch into a single Tensor
    embeddings = torch.cat(embeddings, dim=0)
    return embeddings, paths


# Process the images and get their embeddings
embeddings, paths = process_and_embed_images(image_dataloader, model)

embeddings_list = embeddings.tolist()
paths_list = [str(path) for path in paths]

# Pair each embedding with its corresponding path
embeddings_paths_pairs = list(zip(embeddings_list, paths_list))

print(embeddings_paths_pairs)

# Serialize with pickle and save to a file
with open('embeddings_paths_pairs.pkl', 'wb') as f:
    pickle.dump(embeddings_paths_pairs, f)


# At this point, `embeddings` is a Tensor containing all the image embeddings,
# and `paths` is a list of image paths corresponding to these embeddings.
