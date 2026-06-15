import torch
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score

def evaluate(model, modality, loader, device, n_class):
    trues, preds = [], []

    if isinstance(model, torch.nn.DataParallel) or isinstance(model, torch.nn.parallel.DistributedDataParallel):
        net = model.module
    else:
        net = model

    net.eval()
    with torch.no_grad():
        for sig, img, gt in loader:
            if modality == 'sig':
                sig, gt = sig.to(device), gt.to(device)
                pred = net(sig)
            elif modality == 'img':
                img, gt = img.to(device), gt.to(device)
                pred = net(img)
            elif modality == 'multi':
                sig, img, gt = sig.to(device), img.to(device), gt.to(device)
                pred = net(sig, img)

            trues.append(gt.cpu().numpy())
            preds.append(torch.sigmoid(pred).cpu().numpy())

    trues = np.vstack(trues)
    preds = np.vstack(preds)

    accs, aucs, f1s, precisions, recalls = [], [], [], [], []
    for i in range(n_class):
        accs.append(accuracy_score(trues[:, i], (preds[:, i] > 0.5).astype(int)))
        aucs.append(roc_auc_score(trues[:, i], preds[:, i]))
        f1s.append(f1_score(trues[:, i], (preds[:, i] > 0.5).astype(int), average='binary', zero_division=0))
        precisions.append(precision_score(trues[:, i], (preds[:, i] > 0.5).astype(int), average='binary', zero_division=0))
        recalls.append(recall_score(trues[:, i], (preds[:, i] > 0.5).astype(int), average='binary', zero_division=0))

    return {
        'f1': f1s, 'f1_avg': np.average(f1s),
        'precision': precisions, 'precision_avg': np.average(precisions),
        'recall': recalls, 'recall_avg': np.average(recalls),
        'auc': aucs, 'auc_avg': np.average(aucs),
        'acc': accs, 'acc_avg': np.average(accs)
    }