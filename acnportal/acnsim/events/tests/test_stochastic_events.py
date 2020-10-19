import unittest
from unittest.mock import Mock, call
from acnportal.acnsim.events.stochastic_events import StochasticEvents
import numpy as np
from datetime import datetime
from acnportal.acnsim import Battery, EV
from typing import List


class TestStochasticEvents(unittest.TestCase):
    def setUp(self):
        self.period = 5
        self.periods_per_hour = 60 / self.period
        self.periods_per_day = self.periods_per_hour * 24
        self.voltage = 208
        self.max_battery_power = 7
        self.sessions_per_day = [3]

    def _default_tests(self, evs: List[EV]):
        with self.subTest("test_length_of_evs"):
            self.assertEqual(3, len(evs))

        with self.subTest("test_arrival_times"):
            self.assertListEqual([ev.arrival for ev in evs],
                                 [78, 99, 120])

        with self.subTest("test_station_ids"):
            self.assertListEqual([ev.station_id for ev in evs],
                                 [f"station_{i}" for i in range(3)])

        with self.subTest("test_session_ids"):
            self.assertListEqual([ev.session_id for ev in evs],
                                 [f"session_{i}" for i in range(3)])

        with self.subTest("test_battery"):
            for ev in evs:
                self.assertIsInstance(ev._battery, Battery)
                self.assertEqual(ev.maximum_charging_power, self.max_battery_power)

    def test_generate_events(self):
        samples = np.array([[6.5, 8, 10], [8.3, 6.05, 3], [10, 3, 6.6]])
        gen = StochasticEvents()
        gen.sample = Mock(return_value=samples)
        queue = gen.generate_events(self.sessions_per_day, self.period, self.voltage, self.max_battery_power)
        evs = [event[1].ev for event in queue.queue]
        self._default_tests(evs)

        with self.subTest("test_departure_time"):
            self.assertListEqual([ev.departure for ev in evs],
                                 [174, 172, 156])

        with self.subTest("test_requested_energy"):
            self.assertListEqual([ev.requested_energy for ev in evs],
                                 [10, 3, 6.6])

    def test_generate_events_with_force_feasible(self):
        samples = np.array([[6.5, 1, 10], [8.3, 6.05, 3], [10, 3, 6.6]])
        gen = StochasticEvents()
        gen.sample = Mock(return_value=samples)
        queue = gen.generate_events(self.sessions_per_day, self.period, self.voltage, self.max_battery_power,
                                         force_feasible=True)
        evs = [event[1].ev for event in queue.queue]
        self._default_tests(evs)

        with self.subTest("test_departure_time"):
            self.assertListEqual([ev.departure for ev in evs],
                                 [90, 172, 156])

        with self.subTest("test_requested_energy"):
            self.assertListEqual([ev.requested_energy for ev in evs],
                                 [self.max_battery_power, 3, 6.6])

    def test_generate_events_with_max_len(self):
        samples = np.array([[6.5, 8, 10], [8.3, 6.05, 3], [10, 3, 6.6]])
        gen = StochasticEvents()
        gen.sample = Mock(return_value=samples)
        queue = gen.generate_events(self.sessions_per_day, self.period, self.voltage, self.max_battery_power,
                                         max_len=3)
        evs = [event[1].ev for event in queue.queue]
        self._default_tests(evs)

        with self.subTest("test_departure_time"):
            self.assertListEqual([ev.departure for ev in evs],
                                 [114, 135, 156])

        with self.subTest("test_requested_energy"):
            self.assertListEqual([ev.requested_energy for ev in evs],
                                 [10, 3, 6.6])

    def test_generate_events_with_max_len_and_force_feasible(self):
        samples = np.array([[6.5, 8, 10], [8.3, 6.05, 3], [10, 3, 15]])
        gen = StochasticEvents()
        gen.sample = Mock(return_value=samples)
        queue = gen.generate_events(self.sessions_per_day, self.period, self.voltage, self.max_battery_power,
                                         max_len=1, force_feasible=True)
        evs = [event[1].ev for event in queue.queue]
        self._default_tests(evs)

        with self.subTest("test_departure_time"):
            self.assertListEqual([ev.departure for ev in evs],
                                 [90, 111, 132])

        with self.subTest("test_requested_energy"):
            self.assertListEqual([ev.requested_energy for ev in evs],
                                 [self.max_battery_power, 3, self.max_battery_power])

    def test_generate_events_multi_day(self):
        samples = np.array([[6.5, 8, 10], [8.3, 6.05, 3], [10, 3, 15]])
        gen = StochasticEvents()

        # sample expects an argument n_samples. We need to copy the array to prevent
        # changing it in the function between calls to sample.
        gen.sample = Mock(side_effect=lambda n: samples.copy())
        queue = gen.generate_events([3, 3], self.period, self.voltage, self.max_battery_power)

        gen.sample.assert_has_calls([call(3), call(3)])

        evs = [event[1].ev for event in queue.queue]
        with self.subTest("test_length_of_evs"):
            self.assertEqual(6, len(evs))

        with self.subTest("test_arrival_times"):
            self.assertListEqual([ev.arrival for ev in evs],
                                 [78, 99, 120,
                                  self.periods_per_day + 78, self.periods_per_day + 99, self.periods_per_day + 120])

        with self.subTest("test_departure_time"):
            self.assertListEqual([ev.departure for ev in evs],
                                 [174, 172, 156,
                                  self.periods_per_day + 174, self.periods_per_day + 172, self.periods_per_day + 156])

    def test_generate_events_multi_day_with_0_sessions(self):
        samples = np.array([[6.5, 8, 10], [8.3, 6.05, 3], [10, 3, 15]])
        gen = StochasticEvents()

        # sample expects an argument n_samples. We need to copy the array to prevent
        # changing it in the function between calls to sample.
        gen.sample = Mock(side_effect=lambda n: samples.copy())
        queue = gen.generate_events([3, 0, 3], self.period, self.voltage, self.max_battery_power)

        gen.sample.assert_has_calls([call(3), call(3)])

        evs = [event[1].ev for event in queue.queue]
        with self.subTest("test_length_of_evs"):
            self.assertEqual(6, len(evs))

        with self.subTest("test_arrival_times"):
            self.assertListEqual([ev.arrival for ev in evs],
                                 [78, 99, 120,
                                  2*self.periods_per_day + 78, 2*self.periods_per_day + 99, 2*self.periods_per_day + 120])

        with self.subTest("test_departure_time"):
            self.assertListEqual([ev.departure for ev in evs],
                                 [174, 172, 156,
                                  2*self.periods_per_day + 174, 2*self.periods_per_day + 172, 2*self.periods_per_day + 156])

    def test_extract_training_data(self):
        sessions = [
            {
                "connectionTime": datetime(2020, 1, 1, 0, 0),
                "disconnectTime": datetime(2020, 1, 1, 8, 30),
                "kWhDelivered": 8.24
            },
            {
                "connectionTime": datetime(2020, 1, 1, 7, 24),
                "disconnectTime": datetime(2020, 1, 1, 10, 0),
                "kWhDelivered": 1
            },
            {
                "connectionTime": datetime(2020, 1, 1, 8, 0),
                "disconnectTime": datetime(2020, 1, 1, 13, 0),
                "kWhDelivered": 12.3
            }
        ]
        expected = np.array([
            [0, 8.5, 8.24],
            [7.4, 2.6, 1],
            [8, 5, 12.3]
        ])
        np.testing.assert_equal(StochasticEvents.extract_training_data(sessions),
                                expected)
if __name__ == '__main__':
    unittest.main()
