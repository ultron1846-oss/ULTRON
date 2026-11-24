import unittest

from ultron_core.benchmark import bootstrap_median_ci, percentile


class BenchmarkStatisticsTests(unittest.TestCase):
    def test_bootstrap_interval_is_deterministic(self):
        values = [1.0, 2.0, 2.0, 3.0, 4.0]
        first = bootstrap_median_ci(values, seed=17, resamples=500)
        second = bootstrap_median_ci(values, seed=17, resamples=500)
        self.assertEqual(first, second)
        self.assertLessEqual(first[0], 2.0)
        self.assertGreaterEqual(first[1], 2.0)

    def test_percentile_interpolates_and_validates(self):
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.95), 3.85, places=12)
        with self.assertRaisesRegex(ValueError, "q must"):
            percentile([1.0, 2.0], 1.1)
        with self.assertRaisesRegex(ValueError, "at least one"):
            percentile([], 0.5)

    def test_bootstrap_rejects_single_sample(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            bootstrap_median_ci([1.0])

    def test_bootstrap_rejects_invalid_resamples(self):
        with self.assertRaisesRegex(ValueError, "at least 100"):
            bootstrap_median_ci([1.0, 2.0], resamples=10)

    def test_bootstrap_rejects_invalid_confidence(self):
        with self.assertRaisesRegex(ValueError, "confidence"):
            bootstrap_median_ci([1.0, 2.0], confidence=1.0)


if __name__ == "__main__":
    unittest.main()
