"""Mock-only checkpoint transfer/recovery and streaming scan contracts."""
import hashlib
import random
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from torch.utils.data import DataLoader, Dataset

import ultron_core.checkpoint as checkpoint_module
from ultron_core.checkpoint import (
    inspect_checkpoint_resume_metadata,
    load_checkpoint,
    save_checkpoint,
)
from ultron_core.config import NeuroSparseConfig
from ultron_core.dataset_stream_scan import scan_jsonl_structure
from ultron_core.resumable_sampler import ResumableRandomSampler


class _TinyModel(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([float(value)]))
        self.config = NeuroSparseConfig.foundation()


class _IndexDataset(Dataset):
    def __len__(self):
        return 5

    def __getitem__(self, index):
        return index


def _cursor(dataset_hash):
    return {
        "epoch": 0,
        "next_batch_index": 1,
        "next_sample_index": 2,
        "dataset_manifest_sha256": dataset_hash,
        "dataset_size": 5,
        "batch_size": 2,
        "seed": 19,
        "gradient_accumulation_steps": 1,
        "training_settings": {
            "precision": "fp32",
            "seed": 19,
            "gradient_accumulation_steps": 1,
        },
        "sampler_state": {
            "schema_version": 1,
            "dataset_size": 5,
            "dataset_manifest_sha256": dataset_hash,
            "seed": 19,
            "epoch": 0,
            "next_index": 2,
        },
    }


class CheckpointTransferRecoveryTests(unittest.TestCase):
    DATASET_HASH = "a" * 64

    def test_fresh_objects_restore_model_optimizer_scheduler_and_sampler_cursor(self):
        dataset = _IndexDataset()
        source_model = _TinyModel(3.25)
        source_optimizer = torch.optim.SGD(
            source_model.parameters(), lr=0.037, momentum=0.9
        )
        # Seed optimizer state directly: this exercises serialization without
        # performing an optimizer step on any model weights.
        source_optimizer.state[source_model.weight]["momentum_buffer"] = torch.tensor([0.125])
        source_scheduler = torch.optim.lr_scheduler.StepLR(
            source_optimizer, step_size=3, gamma=0.5
        )
        source_sampler = ResumableRandomSampler(
            dataset, seed=19, dataset_manifest_sha256=self.DATASET_HASH,
            next_index=2,
        )
        cursor = _cursor(self.DATASET_HASH)
        cursor["sampler_state"] = source_sampler.state_dict()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean-runtime.pt"
            save_checkpoint(
                path, source_model, source_model.config,
                optimizer=source_optimizer, scheduler=source_scheduler, step=17,
                data_state=cursor, dataset_manifest_sha256=self.DATASET_HASH,
                training_settings=cursor["training_settings"],
            )

            restored_model = _TinyModel(-4.0)
            restored_optimizer = torch.optim.SGD(
                restored_model.parameters(), lr=0.9, momentum=0.9
            )
            restored_scheduler = torch.optim.lr_scheduler.StepLR(
                restored_optimizer, step_size=1, gamma=0.1
            )
            restored_sampler = ResumableRandomSampler(
                dataset, seed=19, dataset_manifest_sha256=self.DATASET_HASH
            )
            metadata = load_checkpoint(
                path, restored_model, optimizer=restored_optimizer,
                scheduler=restored_scheduler, expected_dataset_manifest_sha256=self.DATASET_HASH,
            )
            restored_sampler.load_state_dict(metadata["data_state"]["sampler_state"])
            restored_loader = DataLoader(
                dataset, batch_size=2, sampler=restored_sampler,
                num_workers=0, drop_last=False,
            )
            self.assertEqual(restored_sampler.state_dict(), cursor["sampler_state"])
            expected_sampler = ResumableRandomSampler(
                dataset, seed=19, dataset_manifest_sha256=self.DATASET_HASH
            )
            expected_order = list(iter(expected_sampler))
            remaining_indices = list(iter(restored_loader.sampler))

            self.assertEqual(restored_sampler.state_dict()["next_index"], len(dataset))
            self.assertEqual(metadata["step"], 17)
            self.assertTrue(metadata["optimizer_restored"])
            self.assertTrue(metadata["scheduler_restored"])
            self.assertEqual(metadata["data_state"], cursor)
            self.assertEqual(float(restored_model.weight.detach().item()), 3.25)
            self.assertAlmostEqual(restored_optimizer.param_groups[0]["lr"], 0.037)
            self.assertAlmostEqual(restored_optimizer.param_groups[0]["momentum"], 0.9)
            self.assertTrue(torch.equal(
                restored_optimizer.state[restored_model.weight]["momentum_buffer"],
                torch.tensor([0.125]),
            ))
            self.assertEqual(
                restored_scheduler.state_dict(), source_scheduler.state_dict()
            )
            self.assertEqual(restored_loader.num_workers, 0)
            self.assertEqual(remaining_indices, expected_order[2:])

    def test_checkpoint_bundle_copies_and_restores_from_another_directory(self):
        source_model = _TinyModel(2.5)
        optimizer = torch.optim.SGD(source_model.parameters(), lr=0.04)
        cursor = _cursor(self.DATASET_HASH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "checkpoint.pt"
            destination = root / "transfer" / "checkpoint.pt"
            source.parent.mkdir()
            destination.parent.mkdir()
            save_checkpoint(
                source, source_model, source_model.config, optimizer=optimizer,
                step=8, data_state=cursor, dataset_manifest_sha256=self.DATASET_HASH,
                training_settings=cursor["training_settings"],
            )
            for suffix in ("", ".sha256", ".metadata.json"):
                shutil.copy2(Path(str(source) + suffix), Path(str(destination) + suffix))

            report = inspect_checkpoint_resume_metadata(
                destination,
                expected_dataset_manifest_sha256=self.DATASET_HASH,
                expected_dataset_size=5,
                expected_batch_size=2,
                expected_seed=19,
                expected_gradient_accumulation_steps=1,
                expected_config=source_model.config.to_dict(),
            )
            self.assertTrue(report["compatible"], report["blockers"])
            restored = _TinyModel(0.0)
            metadata = load_checkpoint(
                destination, restored, expected_dataset_manifest_sha256=self.DATASET_HASH
            )
            self.assertEqual(metadata["step"], 8)
            self.assertEqual(metadata["data_state"], cursor)
            self.assertEqual(float(restored.weight.detach().item()), 2.5)

    def test_rng_restore_failure_rolls_back_model_optimizer_scheduler_and_rng(self):
        source = _TinyModel(2.75)
        source_optimizer = torch.optim.SGD(
            source.parameters(), lr=0.03, momentum=0.9
        )
        source_optimizer.state[source.weight]["momentum_buffer"] = torch.tensor([0.125])
        source_scheduler = torch.optim.lr_scheduler.StepLR(
            source_optimizer, step_size=2, gamma=0.5
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rng-rollback.pt"
            save_checkpoint(
                path, source, source.config,
                optimizer=source_optimizer, scheduler=source_scheduler, step=4,
            )
            payload = torch.load(path, map_location="cpu", weights_only=True)
            # The Python state is valid but intentionally different. The following
            # CPU state is malformed, so restore fails after partially changing RNG.
            payload["rng"]["python"] = random.Random(444).getstate()
            payload["rng"]["torch_cpu"] = torch.tensor([1], dtype=torch.uint8)
            torch.save(payload, path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix(path.suffix + ".sha256").write_text(
                digest + "  " + path.name + "\\n", encoding="utf-8"
            )
            metadata_path = Path(str(path) + ".metadata.json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["checkpoint_sha256"] = digest
            metadata_path.write_text(
                json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\\n",
                encoding="utf-8",
            )

            target = _TinyModel(-8.0)
            target_optimizer = torch.optim.SGD(
                target.parameters(), lr=0.8, momentum=0.1
            )
            target_optimizer.state[target.weight]["momentum_buffer"] = torch.tensor([0.9])
            target_scheduler = torch.optim.lr_scheduler.StepLR(
                target_optimizer, step_size=7, gamma=0.2
            )
            model_before = target.weight.detach().clone()
            optimizer_lr_before = target_optimizer.param_groups[0]["lr"]
            optimizer_momentum_before = target_optimizer.state[target.weight]["momentum_buffer"].clone()
            scheduler_before = target_scheduler.state_dict()
            random.seed(23)
            torch.manual_seed(29)
            python_rng_before = random.getstate()
            torch_rng_before = torch.random.get_rng_state().clone()

            with self.assertRaises(Exception):
                load_checkpoint(
                    path, target,
                    optimizer=target_optimizer,
                    scheduler=target_scheduler,
                    restore_rng=True,
                )

            self.assertTrue(torch.equal(target.weight, model_before))
            self.assertEqual(target_optimizer.param_groups[0]["lr"], optimizer_lr_before)
            self.assertTrue(torch.equal(
                target_optimizer.state[target.weight]["momentum_buffer"],
                optimizer_momentum_before,
            ))
            self.assertEqual(target_scheduler.state_dict(), scheduler_before)
            self.assertEqual(random.getstate(), python_rng_before)
            self.assertTrue(torch.equal(torch.random.get_rng_state(), torch_rng_before))

    def test_interrupted_manifest_commit_recovers_previous_verified_checkpoint(self):
        model = _TinyModel(1.5)
        config = model.config
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "atomic.pt"
            save_checkpoint(path, model, config, step=2, dataset_manifest_sha256=self.DATASET_HASH)
            with torch.no_grad():
                model.weight.fill_(9.0)
            manifest_path = Path(str(path) + ".sha256")
            real_replace = checkpoint_module.os.replace

            def fail_manifest_commit(source, destination):
                if Path(destination) == manifest_path:
                    raise OSError("simulated interruption during manifest commit")
                return real_replace(source, destination)

            with patch("ultron_core.checkpoint.os.replace", side_effect=fail_manifest_commit):
                with self.assertRaisesRegex(OSError, "simulated interruption"):
                    save_checkpoint(
                        path, model, config, step=3, dataset_manifest_sha256="b" * 64
                    )

            self.assertEqual(list(Path(directory).glob(".atomic.pt.*.tmp")), [])
            self.assertEqual(list(Path(directory).glob(".atomic.pt.sha256.*.tmp")), [])

            restored = _TinyModel(-2.0)
            metadata = load_checkpoint(
                path, restored, restore_rng=False,
                expected_dataset_manifest_sha256=self.DATASET_HASH,
            )
            self.assertEqual(metadata["step"], 2)
            self.assertTrue(metadata["source_path"].endswith(".bak"))
            self.assertEqual(float(restored.weight.detach().item()), 1.5)


class StreamingDatasetScanTests(unittest.TestCase):
    def _row(self, *, topic="arithmetic", index=0):
        return {
            "example_id": "c" * 64,
            "generator_version": "0.5.0",
            "topic": topic,
            "difficulty": 1,
            "input_text": "1 + 1",
            "target_text": "2",
            "exact_answer": "2",
            "seed": 1,
            "index": index,
            "generation_parameters": {"a": 1},
            "validation_status": "semantically_checked",
            "provenance": "synthetic test fixture",
        }

    def test_stream_scan_reports_digest_counts_and_explicit_scope(self):
        encoded = (
            json.dumps(self._row(index=0), sort_keys=True, separators=(",", ":")) + "\n"
            + json.dumps(self._row(topic="linear_equations", index=1), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.jsonl"
            path.write_bytes(encoded)
            report = scan_jsonl_structure(path, expected_sha256=digest)
        self.assertEqual(report["bytes_scanned"], len(encoded))
        self.assertEqual(report["example_count"], 2)
        self.assertEqual(report["sha256"], digest)
        self.assertEqual(report["topic_counts"], {"arithmetic": 1, "linear_equations": 1})
        self.assertFalse(report["semantic_answers_checked"])
        self.assertFalse(report["duplicate_example_ids_checked"])
        self.assertFalse(report["training_performed"])

    def test_stream_scan_rejects_empty_dataset_and_bad_field_types(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.jsonl"
            path.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "at least one row"):
                scan_jsonl_structure(path)
            row = self._row()
            row["difficulty"] = True
            path.write_bytes(json.dumps(row, separators=(",", ":")).encode("utf-8") + b"\n")
            with self.assertRaisesRegex(ValueError, "invalid difficulty"):
                scan_jsonl_structure(path)

    def test_stream_scan_rejects_hash_mismatch_duplicate_keys_and_limits(self):
        valid = json.dumps(self._row(), separators=(",", ":")).encode("utf-8") + b"\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.jsonl"
            path.write_bytes(valid)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                scan_jsonl_structure(path, expected_sha256="d" * 64)
            two_rows = valid + json.dumps(self._row(index=1), separators=(",", ":")).encode("utf-8") + b"\n"
            path.write_bytes(two_rows)
            with self.assertRaisesRegex(ValueError, "row limit"):
                scan_jsonl_structure(path, max_rows=1)
            duplicate_key = b'{"topic":"arithmetic","topic":"rational_arithmetic"}\n'
            path.write_bytes(duplicate_key)
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                scan_jsonl_structure(path)
            path.write_bytes(valid)
            with self.assertRaisesRegex(ValueError, "line byte limit"):
                scan_jsonl_structure(path, max_line_bytes=16)


if __name__ == "__main__":
    unittest.main()
