import torch
from datasets.unity_eyes import UnityEyesDataset
from torch.utils.data import DataLoader
from models.posenet import PoseNet
import os
from torch.utils.tensorboard import SummaryWriter
from datetime import datetime
import numpy as np
import cv2
from util.preprocess import gaussian_2d
from matplotlib import pyplot as plt
from scipy.ndimage.measurements import center_of_mass

# default `log_dir` is "runs" - we'll be more specific here
timestr = datetime.now().strftime("%m-%d-Y-%H-%M-%S")
writer = SummaryWriter(f'runs/posenet')

dataset = UnityEyesDataset()


def centroid(img):
    ret, thresh = cv2.threshold(img * 255, 127, 255, 0)

    # calculate moments of binary image
    M = cv2.moments(thresh)

    # calculate x,y coordinate of center
    cX = int(M["m10"] / M["m00"])
    cY = int(M["m01"] / M["m00"])

    return (cY, cX)


def normalize_predictions(preds):
    for p in preds:
        yield (p - p.min()) / np.ptp(p)


with torch.no_grad():
    posenet = PoseNet(nstack=8, inp_dim=256, oup_dim=32)

    if os.path.exists('checkpoint'):
        checkpoint = torch.load('checkpoint')
        posenet.load_state_dict(checkpoint['model_state_dict'])

    sample = dataset[0]
    x = torch.tensor([sample['img']], dtype=torch.float32)
    y = sample['heatmaps']
    yp = posenet.forward(x)

    heatmaps = yp.numpy()[0, -1, :]
    heatmaps = [cv2.resize(x, (150, 90)) for x in heatmaps]
    heatmaps = list(normalize_predictions(heatmaps))

    centers = [centroid(x) for x in heatmaps]
    result = [gaussian_2d((90, 150), centre=tuple(int(e) for e in c), sigma=3) for c in centers]

    plt.figure(figsize=(12, 3))

    plt.subplot(141)
    plt.imshow(cv2.cvtColor(sample['full_img'], cv2.COLOR_BGR2RGB))
    plt.subplot(142)
    plt.imshow(sample['img'])
    plt.subplot(143)
    plt.imshow(np.sum(y, axis=0), cmap='gray')
    plt.subplot(144)
    plt.imshow(np.mean(result, axis=0), cmap='gray')
    plt.show()