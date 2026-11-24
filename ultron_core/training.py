import torch
from torch.nn import functional as F

def causal_language_model_loss(logits:torch.Tensor,input_ids:torch.Tensor,
                               load_balance:torch.Tensor|None=None,balance_weight:float=0.01):
    if logits.ndim!=3 or input_ids.ndim!=2: raise ValueError("expected logits [B,T,V] and ids [B,T]")
    if logits.shape[:2]!=input_ids.shape: raise ValueError("shape mismatch")
    if input_ids.shape[1]<2: raise ValueError("sequence length must be >=2")
    loss=F.cross_entropy(logits[:,:-1].reshape(-1,logits.shape[-1]),input_ids[:,1:].reshape(-1))
    return loss+(balance_weight*load_balance if load_balance is not None else 0)

def make_optimizer(model:torch.nn.Module,learning_rate:float=3e-4,weight_decay:float=0.01):
    if learning_rate<=0 or weight_decay<0: raise ValueError("invalid optimizer values")
    return torch.optim.AdamW(model.parameters(),lr=learning_rate,weight_decay=weight_decay)
