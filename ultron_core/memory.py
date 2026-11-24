import torch
from torch import nn

class FastWeightMemory(nn.Module):
    """Bounded lossy associative matrix; not an exact episodic store."""
    def __init__(self,hidden_size:int,slots:int,decay:float=0.995):
        super().__init__()
        if not 0.0<=decay<=1.0: raise ValueError("decay must be in [0,1]")
        self.decay=decay
        self.key=nn.Linear(hidden_size,hidden_size,bias=False)
        self.value=nn.Linear(hidden_size,hidden_size,bias=False)
        self.query=nn.Linear(hidden_size,hidden_size,bias=False)
        self.gate=nn.Linear(hidden_size,1)
        self.register_buffer("memory",torch.zeros(slots,hidden_size,hidden_size))
        self.register_buffer("cursor",torch.zeros((),dtype=torch.long))

    def reset_memory(self):
        self.memory.zero_(); self.cursor.zero_()

    def forward(self,x:torch.Tensor,write:bool=False)->torch.Tensor:
        k=torch.tanh(self.key(x)); v=self.value(x); q=torch.tanh(self.query(x))
        recalled=torch.matmul(q,self.memory.mean(dim=0).to(dtype=x.dtype))
        if write and self.training:
            with torch.no_grad():
                gates=torch.sigmoid(self.gate(x)).squeeze(-1)
                for b in range(x.shape[0]):
                    for t in range(x.shape[1]):
                        key=k[b,t].detach(); value=v[b,t].detach()
                        prediction=torch.mv(self.memory[0],key)
                        delta=(value-prediction)*gates[b,t].detach()
                        update=torch.outer(delta,key)/(key.square().sum()+1e-6)
                        slot=int(self.cursor.item())
                        self.memory[slot].mul_(self.decay).add_(update)
                        self.cursor.add_(1).remainder_(self.memory.shape[0])
        return recalled
