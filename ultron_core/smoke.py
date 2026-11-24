import argparse
import json
import time
import torch
from .config import NeuroSparseConfig
from .model import NeuroSparseModel
from .training import causal_language_model_loss


def run(device='cpu', batch=2, sequence=16, profile=False):
    target = torch.device(device)
    if target.type == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but unavailable')
    config = NeuroSparseConfig()
    model = NeuroSparseModel(config).to(target)
    ids = torch.randint(1, config.vocab_size, (batch, sequence), device=target)
    model.train()
    if target.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(target)
    start = time.perf_counter()
    output = model(ids)
    loss = causal_language_model_loss(output['logits'], ids, output['load_balance_loss'], output['prediction_error'])
    loss.backward()
    result = {'device': str(target), 'input_shape': list(ids.shape),
        'loss': float(loss.detach().cpu()), 'backward': True,
        'parameters_total': sum(p.numel() for p in model.parameters()),
        'expert_selected_fraction': config.top_k / config.num_experts,
        'latency_seconds': time.perf_counter() - start,
        'peak_cuda_memory_bytes': torch.cuda.max_memory_allocated(target) if target.type == 'cuda' else None,
        'note': 'Forward/backward smoke only; no optimizer step or training run.'}
    if profile:
        activities = [torch.profiler.ProfilerActivity.CPU]
        if target.type == 'cuda':
            activities.append(torch.profiler.ProfilerActivity.CUDA)
        with torch.profiler.profile(activities=activities, record_shapes=True,
                profile_memory=True, with_flops=True) as profiler:
            model(ids)
        result['profiler_table'] = profiler.key_averages().table(
            sort_by='self_cuda_time_total' if target.type == 'cuda' else 'self_cpu_time_total', row_limit=20)
        result['profiler_flops'] = sum(int(item.flops or 0) for item in profiler.key_averages())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--batch', type=int, default=2)
    parser.add_argument('--sequence', type=int, default=16)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.device, args.batch, args.sequence, args.profile), indent=2))


if __name__ == '__main__':
    main()
