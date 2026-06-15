import torch
import torch.nn as nn
import timm

from .stmem import ST_MEM_ViT

class AveragewithProj(nn.Module):
    def __init__(self, dropout=0.5, pretrain_path=None, convnext_pretrained=False):
        super(AveragewithProj, self).__init__()
        # ST-MEM setting
        self.stmem = ST_MEM_ViT(
            seq_len= 2250,
            patch_size= 75,
            num_leads= 12,
            num_classes= 768,
            depth= 12
        )

        if pretrain_path:
            pretrain = torch.load(pretrain_path, map_location="cpu")
            pretrain_state_dict = pretrain['model'] if 'model' in pretrain else pretrain
            model_state_dict = self.stmem.state_dict()

            filtered_dict = {
                k: v for k, v in pretrain_state_dict.items()
                if k in model_state_dict and v.shape == model_state_dict[k].shape
            }

            model_state_dict.update(filtered_dict)
            self.stmem.load_state_dict(model_state_dict)
        
        # ConvNeXt setting
        self.convnext = timm.create_model(
            'convnext_base',
            pretrained=convnext_pretrained,
            num_classes= 768,
            drop_path_rate= 0.5
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(768, 5)
    def forward(self, sig, img):
        x_sig = self.stmem(sig)
        x_img = self.convnext(img)
        
        x_avg = (x_sig + x_img) / 2
        x_avg = self.dropout(x_avg)
        x_avg = self.fc(x_avg)
        return x_avg
