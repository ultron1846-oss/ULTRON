import torch
from torch import nn
from torch.nn import functional as F

class PredictiveRefiner(nn.Module):
    def __init__(self,hidden_size:int,max_refinements:int,halt_threshold:float):
        super().__init__()
        self.max_refinements=max_refinements; self.halt_threshold=halt_threshold
        self.predictor=nn.Sequential(nn.Linear(hidden_size,hidden_size),nn.GELU(),nn.Linear(hidden_size,hidden_size))
        self.refine=nn.GRUCell(hidden_size,hidden_size)

    def forward(self,state:torch.Tensor):
        batch,seq,hidden=state.shape
        z=state.reshape(batch*seq,hidden); steps=torch.zeros(z.shape[0],device=z.device,dtype=torch.long)
        error=z.new_zeros(z.shape[0])
        for _ in range(self.max_refinements):
            prediction=self.predictor(z)
            error=F.mse_loss(prediction,z,reduction="none").mean(dim=-1)
            active=error>self.halt_threshold
            if not bool(active.any()): break
            z=torch.where(active.unsqueeze(-1),self.refine(prediction,z),z)
            steps=steps+active.long()
        return z.reshape(batch,seq,hidden),error.mean(),steps.max()
