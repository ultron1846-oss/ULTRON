"""Read-only Dataset/DataLoader adapter for verified ULTRON JSONL splits."""
from __future__ import annotations
import torch
from torch.utils.data import DataLoader, Dataset, SequentialSampler
from .dataset_split_manifest import load_verified_split_rows
from .math_tokenizer import MathTokenizer, MathVocabulary
from .resumable_sampler import ResumableRandomSampler

class VerifiedMathDataset(Dataset):
    """Tokenize selected rows from an integrity-verified existing dataset."""
    def __init__(self,dataset_path,split_manifest_path,*,split_name:str,tokenizer:MathTokenizer|None=None,max_sequence_length:int=2048):
        if split_name not in ("train","validation","test"): raise ValueError("split_name must be train, validation, or test")
        if isinstance(max_sequence_length,bool) or not isinstance(max_sequence_length,int) or not 2<=max_sequence_length<=2048: raise ValueError("max_sequence_length must be in [2, 2048]")
        verified,rows=load_verified_split_rows(dataset_path,split_manifest_path,split_name=split_name)
        self.dataset_manifest_sha256=verified.dataset_sha256
        self.split_manifest_sha256=verified.split_manifest_sha256
        self.split_name=split_name
        self.tokenizer=tokenizer or MathTokenizer(MathVocabulary.default())
        self.max_sequence_length=max_sequence_length
        self._records=tuple((r["example_id"],r["input_text"],r["target_text"]) for r in rows)
    def __len__(self): return len(self._records)
    def __getitem__(self,index):
        if isinstance(index,bool) or not isinstance(index,int): raise TypeError("dataset index must be an integer")
        if not 0<=index<len(self._records): raise IndexError(index)
        example_id,prompt,answer=self._records[index]
        token_ids=self.tokenizer.encode(f"Question: {prompt}\nAnswer: {answer}",add_bos=True,add_eos=True)
        if len(token_ids)>self.max_sequence_length:
            raise ValueError(f"example {example_id} exceeds {self.max_sequence_length} tokens; truncation is disabled")
        if len(token_ids)<3: raise ValueError(f"example {example_id} token sequence is too short")
        return {"input_ids":torch.tensor(token_ids,dtype=torch.long)}

def collate_verified_math_batch(items:list[dict],*,pad_token_id:int=0):
    """Right-pad verified token sequences; pad ID 0 is loss-ignored."""
    if not items: raise ValueError("cannot collate an empty batch")
    if isinstance(pad_token_id,bool) or not isinstance(pad_token_id,int) or pad_token_id!=0: raise ValueError("canonical ULTRON padding token ID must be 0")
    sequences=[item.get("input_ids") if isinstance(item,dict) else None for item in items]
    if any(not isinstance(x,torch.Tensor) or x.ndim!=1 or x.dtype!=torch.long or x.numel()<2 for x in sequences):
        raise ValueError("each item must contain a 1D int64 input_ids sequence")
    width=max(x.numel() for x in sequences)
    batch=torch.full((len(sequences),width),pad_token_id,dtype=torch.long)
    for row,x in enumerate(sequences): batch[row,:x.numel()]=x
    return {"input_ids":batch,"attention_mask":batch.ne(pad_token_id)}

def build_verified_split_loader(dataset_path,split_manifest_path,*,split_name:str,batch_size:int,seed:int,max_sequence_length:int=2048,tokenizer:MathTokenizer|None=None,shuffle:bool|None=None)->DataLoader:
    """Construct a verified split loader; does not create a model or train."""
    if isinstance(batch_size,bool) or not isinstance(batch_size,int) or not 1<=batch_size<=1024: raise ValueError("batch_size must be in [1, 1024]")
    if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<2**63: raise ValueError("seed must be in [0, 2**63)")
    if split_name not in ("train","validation","test"): raise ValueError("invalid split_name")
    if shuffle is None: shuffle=(split_name=="train")
    if not isinstance(shuffle,bool): raise TypeError("shuffle must be boolean")
    if split_name!="train" and shuffle: raise ValueError("validation/test loaders must not shuffle")
    dataset=VerifiedMathDataset(dataset_path,split_manifest_path,split_name=split_name,tokenizer=tokenizer,max_sequence_length=max_sequence_length)
    sampler=ResumableRandomSampler(dataset,seed=seed,dataset_manifest_sha256=dataset.dataset_manifest_sha256) if shuffle else SequentialSampler(dataset)
    loader=DataLoader(dataset,batch_size=batch_size,sampler=sampler,num_workers=0,drop_last=False,collate_fn=collate_verified_math_batch)
    loader.dataset_manifest_sha256=dataset.dataset_manifest_sha256
    loader.split_manifest_sha256=dataset.split_manifest_sha256
    loader.split_name=split_name
    return loader
