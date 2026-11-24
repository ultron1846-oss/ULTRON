import torch
from torch import nn
from torch.nn import functional as F

class SparseRouter(nn.Module):
    def __init__(self, hidden_size: int, num_experts: int, top_k: int):
        super().__init__()
        if not 1 <= top_k <= num_experts: raise ValueError("invalid top_k")
        self.num_experts,self.top_k=num_experts,top_k
        self.proj=nn.Linear(hidden_size,num_experts,bias=False)

    def forward(self,x:torch.Tensor):
        logits=self.proj(x)
        probs=F.softmax(logits.float(),dim=-1).to(logits.dtype)
        weights,indices=torch.topk(probs,self.top_k,dim=-1)
        weights=weights/weights.sum(dim=-1,keepdim=True).clamp_min(1e-9)
        return logits,weights,indices

def load_balance_loss(logits:torch.Tensor,indices:torch.Tensor)->torch.Tensor:
    if logits.numel()==0: return logits.new_zeros(())
    probs=F.softmax(logits.float(),dim=-1)
    n=logits.shape[-1]
    importance=probs.mean(dim=tuple(range(probs.ndim-1)))
    assignments=F.one_hot(indices,num_classes=n).float().sum(dim=-2)
    frequency=assignments.reshape(-1,n).mean(dim=0)
    return n*torch.sum(importance*frequency.to(importance.dtype))
