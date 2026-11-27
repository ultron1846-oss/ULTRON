import unittest

from ultron_core.resource_monitor import MemoryUsage, RuntimeMemoryMonitor, sample_memory_usage


class RuntimeMemoryMonitorTests(unittest.TestCase):
    def test_native_sampler_reports_positive_process_rss(self):
        usage = sample_memory_usage()
        self.assertGreater(usage.process_rss_bytes, 0)
        self.assertGreaterEqual(usage.cuda_reserved_bytes, 0)

    def test_usage_combines_process_rss_and_cuda_reserved_bytes(self):
        usage = MemoryUsage(process_rss_bytes=700, cuda_reserved_bytes=250)
        self.assertEqual(usage.total_bytes, 950)
        self.assertEqual(usage.as_dict(), {
            "process_rss_bytes": 700,
            "cuda_reserved_bytes": 250,
            "total_bytes": 950,
        })

    def test_check_accepts_usage_at_budget_boundary(self):
        monitor = RuntimeMemoryMonitor(
            1000,
            usage_provider=lambda device: MemoryUsage(750, 250),
        )
        sampled = monitor.check("pre-step", device="cpu")
        self.assertEqual(sampled.total_bytes, 1000)
        self.assertEqual(monitor.peak_bytes, 1000)
        self.assertEqual(monitor.samples, 1)

    def test_check_rejects_over_budget_with_stage_and_breakdown(self):
        monitor = RuntimeMemoryMonitor(
            999,
            usage_provider=lambda device: MemoryUsage(750, 250),
        )
        with self.assertRaisesRegex(
                MemoryError, "pre-step.*1,000 bytes.*RSS 750.*CUDA reserved 250"):
            monitor.check("pre-step")
        self.assertEqual(monitor.peak_bytes, 1000)
        self.assertEqual(monitor.last_stage, "pre-step")

    def test_check_accepts_mapping_provider(self):
        monitor = RuntimeMemoryMonitor(
            500,
            usage_provider=lambda device: {
                "process_rss_bytes": 400,
                "cuda_reserved_bytes": 50,
            },
        )
        self.assertEqual(monitor.check("startup").total_bytes, 450)

    def test_rejects_invalid_budget_and_provider(self):
        for budget in (0, -1, True, 1.5):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    RuntimeMemoryMonitor(budget)
        with self.assertRaisesRegex(TypeError, "usage_provider"):
            RuntimeMemoryMonitor(100, usage_provider=42)

    def test_rejects_invalid_sample_values_and_return_types(self):
        for value in (-1, True, 1.25):
            with self.subTest(value=value):
                monitor = RuntimeMemoryMonitor(
                    100, usage_provider=lambda device, value=value: {
                        "process_rss_bytes": value,
                        "cuda_reserved_bytes": 0,
                    },
                )
                with self.assertRaises(ValueError):
                    monitor.check("sample")
        monitor = RuntimeMemoryMonitor(100, usage_provider=lambda device: None)
        with self.assertRaisesRegex(TypeError, "must return"):
            monitor.check("sample")

    def test_summary_reports_measurement_and_boundary_limitation(self):
        monitor = RuntimeMemoryMonitor(
            1000, usage_provider=lambda device: MemoryUsage(100, 0)
        )
        monitor.check("startup")
        summary = monitor.summary()
        self.assertEqual(summary["budget_bytes"], 1000)
        self.assertEqual(summary["peak_sampled_bytes"], 100)
        self.assertEqual(summary["samples"], 1)
        self.assertIn("controller boundaries", summary["limitation"])


if __name__ == "__main__":
    unittest.main()
