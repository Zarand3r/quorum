"""Exercise the real hosted molecular controls, including HTTP and concurrent stepping."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import pytest

import server
import vesicle
from config import load_config


def _await_gate(engine, tick=0):
    for _ in range(100):
        gate = engine.snapshot()["gate"]
        if gate is not None and gate["tick"] == tick:
            return gate
        threading.Event().wait(0.01)
    raise AssertionError(f"gate did not complete at tick {tick}")


@pytest.fixture
def sim(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(threading.Thread, "start", lambda self: None)
        sim = server.Sim(load_config(server._CONFIG), 7, 30,
                         make_engine=lambda seed: vesicle.VesicleEngine(
                             seed=seed, n_lip=8, L=12, phi=0.3), knob_names=())
    sim.pseudo = sim.engine.pseudo_knobs()
    sim.defaults = {k: get() for k, (get, _) in sim.pseudo.items()}
    sim.mins = {"chi_HT": -1, "chi_TW": -1, "chi_HH": -1, "chi_WW": 0, "kT": 0.05}
    sim.ranges = {"chi_HT": 1, "chi_TW": 1, "chi_HH": 1, "chi_WW": 2, "kT": 1.5}
    yield sim
    sim._stop = True


def test_chemistry_changes_preserve_positions_velocity_rng_and_clock(sim):
    e = sim.engine
    for _ in range(3):
        e.step()
    X, v = e.X.copy(), e.ig.v.copy()
    rng_state = e.ig.rng.bit_generator.state
    sim.set_knobs({"chi_HT": -0.5, "chi_TW": -0.3})
    np.testing.assert_array_equal(e.X, X)
    np.testing.assert_array_equal(e.ig.v, v)
    assert e.ig.rng.bit_generator.state == rng_state
    assert e.t == 3
    np.testing.assert_allclose(e.ig.F, e.field.forces(X), atol=1e-12)
    assert abs(e.ig.F.sum(axis=0)).max() < 1e-9
    assert e.ig.tf.f is e.field


@pytest.mark.parametrize("updates", [
    {"kT": "nan"}, {"chi_HT": "inf"}, {"kT": 0}, {"chi_WW": 3},
    {"not_a_knob": 1}, {"chi_HT": -0.4, "kT": "bad"},
])
def test_invalid_updates_do_not_partially_modify_the_experiment(sim, updates):
    before = {k: get() for k, (get, _) in sim.pseudo.items()}
    with pytest.raises(ValueError):
        sim.set_knobs(updates)
    assert {k: get() for k, (get, _) in sim.pseudo.items()} == before


def test_restart_and_reset_bind_controls_to_the_current_engine(sim):
    sim.set_knobs({"kT": 0.8, "chi_HT": -0.5})
    old_run = sim.run_id
    sim.restart()
    assert sim.run_id != old_run
    assert sim.engine.kT == 0.8
    assert sim.engine.chi[0, 1] == -0.5
    sim.set_knobs(sim.defaults)
    assert sim.engine.kT == 0.45
    assert sim.engine.chi[0, 1] == -0.25
    assert sim.engine.t == 0
    assert sim.state()["pos_bound"] == 6  # engine geometry, not legacy config
    assert sim.state()["aliveness"] is None


def test_current_gate_is_not_the_recorded_source_gate(sim):
    before = _await_gate(sim.engine)
    sim.engine.t = vesicle.GATE_INTERVAL
    after = _await_gate(sim.engine, vesicle.GATE_INTERVAL)
    assert before["tick"] == 0
    assert after["tick"] == vesicle.GATE_INTERVAL
    assert sim.engine.source_gate is None


def test_stream_serializes_once_and_refreshes_for_paused_controls(sim):
    sim.set_paused(True)
    _await_gate(sim.engine)
    first = sim.stream_frame()
    assert sim.stream_frame() is first
    sim.set_knobs({"chi_HT": -0.4})
    changed = sim.stream_frame()
    assert changed is not first
    assert json.loads(changed[1])["knobs"]["chi_HT"] == -0.4
    sim.engine.gate = {"tick": 0, "vesicle": False, "score": 0.25}
    gate_changed = sim.stream_frame()
    assert gate_changed[0] != changed[0]
    assert json.loads(gate_changed[1])["gate"]["score"] == 0.25
    sim.restart(seed=7)
    assert sim.stream_frame()[0] != gate_changed[0]


def test_pause_acknowledges_the_end_of_an_inflight_step(sim):
    entered, release, paused = threading.Event(), threading.Event(), threading.Event()
    def slow_step():
        entered.set()
        assert release.wait(3)
    sim.engine.step = slow_step
    worker = threading.Thread(target=sim._run)
    worker.start()
    assert entered.wait(3)
    def pause():
        sim.set_paused(True)
        paused.set()
    controller = threading.Thread(target=pause)
    controller.start()
    assert not paused.wait(0.05)
    release.set()
    assert paused.wait(3)
    sim._stop = True
    controller.join(3)
    worker.join(3)
    assert not worker.is_alive()


def test_step_failure_is_reported_and_restart_recovers(sim):
    initial = sim.engine.X.copy()
    def fail():
        sim.engine.X[:] = np.nan
    sim.engine.step = fail
    worker = threading.Thread(target=sim._run)
    worker.start()
    # Acquire the lock once the failure has been handled.
    for _ in range(100):
        with sim.lock:
            if sim.error:
                break
        threading.Event().wait(0.01)
    sim._stop = True
    worker.join(3)
    assert sim.state()["status"] == "error"
    np.testing.assert_array_equal(sim.engine.X, initial)
    with pytest.raises(ValueError, match="restart"):
        sim.set_paused(False)
    sim.restart(seed=7)
    assert sim.state()["status"] == "running"
    assert sim.error is None


def test_http_routes_queries_validation_and_stream(sim):
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    http.sim = sim
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}/vivarium"
    def request(path, method="GET"):
        return urlopen(Request(base + path, method=method), timeout=5)
    try:
        with request("/", "HEAD") as response:
            assert response.status == 200
            assert response.read() == b""
            assert int(response.headers["Content-Length"]) > 0
        with request("/state?fresh=1") as response:
            s = json.load(response)
            assert s["seed"] == 7
            assert response.headers["Content-Type"] == "application/json"
            assert "no-store" in response.headers["Cache-Control"]
        with pytest.raises(HTTPError) as exc:
            request("/set?kT=nan", "POST")
        assert exc.value.code == 400
        assert "finite" in json.load(exc.value)["error"]
        with request("/pause", "POST"):
            pass
        with request("/restart?same=1", "POST"):
            pass
        assert sim.seed == 7
        with request("/restart", "POST"):
            pass
        assert sim.seed == 8
        with request("/stream?fresh=1") as response:
            line = response.readline()
            assert line.startswith(b"data: ")
            assert json.loads(line[6:])["seed"] == 8
    finally:
        sim._stop = True
        http.shutdown()
        http.server_close()
        thread.join(3)


@pytest.mark.parametrize("args", [["--hz", "0"], ["--hz", "nan"],
                                  ["--vesicle", "--polar"], ["--autopause", "-1"]])
def test_invalid_launch_arguments_fail_before_starting(args):
    with pytest.raises(SystemExit) as exc:
        server.main(args)
    assert exc.value.code == 2
