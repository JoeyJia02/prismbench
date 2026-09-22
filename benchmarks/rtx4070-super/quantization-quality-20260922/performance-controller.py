"""Local controller for the predeclared rotating deployment lifetimes."""
import json
from pathlib import Path
import sys

from prismbench.config import from_dict
from prismbench.hardware import sample
from prismbench.io import hash_file, save_json
from prismbench.runner import run

repo = Path(__file__).resolve().parents[2]
manifest = json.loads((repo / 'outputs/quality-study/prepared-v2/manifest.json').read_text())
models = {row['label']: row for row in manifest['models']}
output = repo / 'outputs/quality-study/performance'
output.mkdir(exist_ok=False)
order = ['F16', 'Q8_0', 'Q4_K_M', 'Q8_0', 'Q4_K_M', 'F16', 'Q4_K_M', 'F16', 'Q8_0']
receipt = {'order': order, 'controller_sha256': hash_file(Path(__file__)), 'python': sys.executable,
           'status': 'RUNNING', 'runs': []}
save_json(output / 'sequence.json', receipt)
for index, label in enumerate(order, 1):
    baseline = sample(0)
    if baseline.get('system_ram_available_mib', 0) < 10240:
        raise RuntimeError('Insufficient available RAM before deployment lifetime')
    model = models[label]
    raw = {'backend': 'llama_cpp', 'server': str(Path(manifest['runtime_dir']) / 'llama-server.exe'),
           'model': model['path'], 'model_id': manifest['model_id'], 'quantization': label,
           'expected_model_sha256': model['sha256'], 'repetitions': 1, 'seed': 42, 'quality': False,
           'gpu_index': 0, 'load_timeout_seconds': 90, 'request_timeout_seconds': 90,
           'sample_interval_seconds': 0.5,
           'notes': 'Uncontrolled desktop; rotating quantization order. Separate from likelihood workload.',
           'cases': [{'name': 'ctx2k', 'context_size': 2048, 'prompt_tokens': 1792,
                      'output_tokens': 128, 'gpu_layers': 99, 'threads': 6,
                      'batch_size': 512, 'ubatch_size': 128, 'cache_type_k': 'f16',
                      'cache_type_v': 'f16', 'flash_attention': 'on', 'fallbacks': []}]}
    name = f'{index:02d}-{label}'
    save_json(output / f'{name}.config.json', raw)
    print(f'Deployment lifetime {index}/9 {label}', flush=True)
    session = run(from_dict(raw), output / name)
    passed = len(session['attempts']) == 1 and session['attempts'][0]['status'] == 'SUCCESS'
    receipt['runs'].append({'label': label, 'order': index, 'path': name, 'success': passed})
    receipt['status'] = 'RUNNING' if passed else 'FAILED'
    save_json(output / 'sequence.json', receipt)
    if not passed:
        raise RuntimeError('Deployment lifetime failed; queue stopped without score selection')
receipt['status'] = 'SUCCESS'
save_json(output / 'sequence.json', receipt)
print('All nine deployment lifetimes completed.', flush=True)
