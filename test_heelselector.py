import cv2
import numpy as np
import torch
import matplotlib.pyplot as py
from torch.utils.data import DataLoader, Dataset, TensorDataset
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.autograd import Variable
import numpy as np
import torchvision
import test_dl_utils


def selectHeel(filename, frame):
    cap = cv2.VideoCapture(filename)
    cap.set(1, frame)
    ret, img = cap.read()
    cv2.namedWindow("Bild")
    if ret:

        roi = cv2.selectROI("Bild", img)
        cv2.destroyAllWindows()
        cv2.normalize(img, img)
        x, y, w, h = roi
        height, width, _ = img.shape
        mask = np.zeros([height, width])
        mask[y:y + h, x:x + w] = 1

        heelArray = []
        for i in range(x - 15, x + w - 15):
            for k in range(y - 15, y + h - 15):
                heelArray.append(img[k:k + 32, i:i + 32])

        falseArray = []
        for i in range(x - 32, x + w):
            falseArray.append(img[y - 32:y, i:i + 32])
            falseArray.append(img[y + h:y + h + 32, i:i + 32])
        for i in range(y - 32, y + h):
            falseArray.append(img[i:i + 32, x - 32:x])
            falseArray.append(img[i:i + 32, x + w:x + w + 32])
        return mask, np.array(heelArray), np.array(falseArray)
    else:
        return False


def separateDatasets(imageArray, falseArray, ratio=0.6):
    numOfTrainImages = int(np.floor(len(imageArray) * ratio + len(falseArray) * ratio) - 1)
    numOfValImages = int(np.floor(len(imageArray) * (1 - ratio) + len(falseArray) * (1 - ratio)))
    _, width, height, _ = imageArray.shape

    trainImages = np.zeros([numOfTrainImages, width, height, 3])
    trainLabels = np.zeros([numOfTrainImages], dtype="int")
    valImages = np.zeros([numOfValImages, width, height, 3])
    valLabels = np.zeros([numOfValImages], dtype="int")

    for ind, image in enumerate(imageArray[0:int(len(imageArray)*ratio)-1]):
        trainImages[ind] = image
        trainLabels[ind] = 1

    for ind, image in enumerate(falseArray[0:int(len(falseArray) * ratio)-1]):
        trainImages[ind] = image
        trainLabels[ind] = 0

    for ind, image in enumerate(imageArray[int(len(imageArray)*ratio):]):
        valImages[ind] = image
        valLabels[ind] = 1

    for ind, image in enumerate(falseArray[int(len(falseArray)*ratio):]):
        valImages[ind] = image
        valLabels[ind] = 0

    trainTensor = torch.from_numpy(trainImages.reshape(-1,32,32,3))
    trainInts = torch.from_numpy(trainLabels)
    valTensor = torch.from_numpy(valImages)
    valInts =  torch.from_numpy(valLabels)


    return {'train': TensorDataset(trainTensor.float(), trainInts),
            'val': TensorDataset(valTensor.float(), valInts)}


mask, iA, fA = selectHeel("input-videos/4farger.mp4", 120)

footDataset = separateDatasets(iA, fA)

dataloaders = {x: torch.utils.data.DataLoader(footDataset[x], batch_size=1,
                                             shuffle=True, num_workers=1)
               for x in ['train', 'val']}

vgg19 = torchvision.models.vgg19(pretrained=True)
for params in vgg19.parameters():
    params.require_grad = False

vgg19.features = torch.nn.Sequential(*[vgg19.features[i] for i in range(8)])
fc1 = torch.nn.Linear(32768, 100)
fc2 = torch.nn.Linear(100,2)
vgg19.classifier = torch.nn.Sequential(fc1,fc2)

criterion = torch.nn.CrossEntropyLoss()
optimizer_conv = optim.SGD(vgg19.classifier.parameters(), lr=0.01, momentum=0.9)
exp_lr_scheduler = lr_scheduler.StepLR(optimizer_conv, step_size=1, gamma=0.1)
epoch = 10

test_dl_utils.train_model(vgg19, criterion, optimizer_conv, exp_lr_scheduler, dataloaders, epoch)

'''for phase in ['train', 'val']:
    for data in dataloaders[phase]:
        image, label = data
        print(image.shape)
        print(label.shape)'''
