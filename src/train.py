import os
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms

from PIL import Image
from tqdm import tqdm
import numpy as np

# from utils.save_model import save_model
from dataset import LLIDataset
from model import AutoEncoder


def train(model, optimizer, criterion, n_epoch,
          data_loaders: dict, device, lr_scheduler=None
          ):
    train_losses = np.zeros(n_epoch)
    val_losses = np.zeros(n_epoch)

    model.to(device)

    since = time.time()

    for epoch in range(n_epoch):
        train_loss = 0.0
        model.train()
        for inputs, targets in tqdm(data_loaders['train'], desc=f'Training... Epoch: {epoch + 1}/{EPOCHS}'):

            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()

            outputs = model(inputs)
            loss = criterion(outputs, targets)
            train_loss += loss.item()

            loss.backward()
            optimizer.step()

        train_loss = train_loss / len(data_loaders['train'].dataset)

        with torch.no_grad():
            val_loss = 0.0
            model.eval()
            for inputs, targets in tqdm(data_loaders['validation'], desc=f'Validating... Epoch: {epoch + 1}/{EPOCHS}'):
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad()

                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss += loss.item()
                
                # Save output images every 10 ephoch
                if (epoch + 1) % 10 == 0:
                    for i, output_image in enumerate(outputs):
                        output_image = output_image.detach().cpu().permute(1, 2, 0).numpy()
                        output_image = (output_image * 255).astype(np.uint8)
                        output_image = Image.fromarray(output_image)
                        os.makedirs('output_images', exist_ok=True)
                        output_path = os.path.join('output_images', f'output_{epoch + 1}_{i + 1}.png')
                        output_image.save(output_path)
                

            val_loss = val_loss / len(data_loaders['validation'].dataset)


        # save epoch losses
        train_losses[epoch] = train_loss
        val_losses[epoch] = val_loss

        print(f"Epoch {epoch+1}/{n_epoch}:")
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Validation Loss: {val_loss:.4f}")
        print('-'*20)

    time_elapsed = time.time() - since
    print('Training completed in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    # save_model(model, 'new_model.pt')


if __name__ == '__main__':
    INPUT_SIZE = 256
    DATASET_DIR_ROOT = "/Users/hossshakiba/Desktop/LLIE Paper/LOLdataset"
    BATCH_SIZE = 32
    EPOCHS = 30

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda:0"
    elif torch.backends.mps.is_available():
        device = "mps"

    train_transforms = transforms.Compose([
        transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
        transforms.ToTensor(),
    ])

    test_transforms = transforms.Compose([
        transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
        transforms.ToTensor(),
    ])

    train_dataset = LLIDataset(os.path.join(DATASET_DIR_ROOT, "train", "low"), os.path.join(DATASET_DIR_ROOT, "train", "high"), train_transforms, train_transforms)
    test_dataset = LLIDataset(os.path.join(DATASET_DIR_ROOT, "test", "low"), os.path.join(DATASET_DIR_ROOT, "test", "high"), test_transforms, test_transforms)

    data_loaders = {
        "train": DataLoader(
            train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=5
        ),
        "validation": DataLoader(
            test_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=5
        )
    }

    model = AutoEncoder().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    train(model, optimizer, criterion, EPOCHS, data_loaders, device)