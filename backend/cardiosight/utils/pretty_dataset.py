from torch.utils.data import Dataset
import pandas as pd
import os
from utils.sig_transform import Resample, RandomCrop, HighpassFilter, LowpassFilter, Standardize
from torchvision import transforms
import wfdb
from PIL import Image
import numpy as np
import torch

'''
PTB-XL super_class, sub_class, form, rhythm class norm filtering setting
'''

class ECGDataset(Dataset):
    def __init__(
        self, csv_dir, ptbxl_class, split, root_dir
    ):
        # root file
        self.csv_file = pd.read_csv(
            os.path.join(
                csv_dir, 'ptbxl', ptbxl_class, f'ptbxl_{ptbxl_class}_{split}.csv'
            )
        )
        
        # norm filtering
        if ptbxl_class in ['super_class','sub_class']:
            gt_cols = self.csv_file.columns[6:]
            
            only_norm = (self.csv_file['NORM'] == 1) & (self.csv_file[gt_cols.difference(['NORM'])].sum(axis=1) == 0)
            non_norm = self.csv_file['NORM'] == 0
            keep_mask = only_norm | non_norm
            
            self.csv_file = self.csv_file[keep_mask].reset_index(drop= True)
        
        # signal, image file list
        self.sig_list, self.img_list = [], []
        for file_dir in self.csv_file.filename_hr:
            # signal
            self.sig_list.append(
                os.path.join(
                    root_dir, file_dir.replace('records500/', '')
                )
            )
            # image
            self.img_list.append(
                os.path.join(
                    root_dir, file_dir.split('/')[1], file_dir.split('/')[2]+'-0.png'
                )
            )
        
        # signal preprocessing
        self.resample = Resample(target_fs= 250)
        self.random_crop = RandomCrop(crop_length= 2250)
        self.h_filter = HighpassFilter(fs= 250, cutoff= 0.67)
        self.l_filter = LowpassFilter(fs= 250, cutoff= 40)
        self.standardize = Standardize(axis= [-1,-2])
        
        # image transform
        self.crop_area = (0, 530, 2200, 1700-70)
        self.transform = transforms.Compose([
            transforms.Resize((224,224)),
            transforms.ToTensor(),
            # transforms.Normalize((0.485,0.456,0.406),(0.229, 0.224, 0.225))
        ])
    
    def __len__(self):
        return len(self.csv_file)
    
    def __getitem__(self, idx):
        # signal data
        sig, _ = wfdb.rdsamp(self.sig_list[idx])
        # signal preprocessing
        sig = sig.T
        sig = self.resample(sig, 500)
        sig = self.random_crop(sig)
        sig = self.h_filter(sig)
        sig = self.l_filter(sig)
        sig = self.standardize([sig])[0]
        sig = torch.tensor(sig, dtype= torch.float)
        
        # # image data
        img = np.array(Image.open(self.img_list[idx]).convert('RGB'))
        # img = img.crop(self.crop_area)
        # img = self.transform(img)
        
        # ground truth
        gt = np.array(self.csv_file.iloc[idx, 6:].values.tolist())
        gt = torch.tensor(gt, dtype= torch.float)
        
        # return
        return sig, img, gt, self.sig_list[idx]