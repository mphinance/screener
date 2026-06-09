"""Pytest config: register the live marker so live API tests can be selected."""


def pytest_configure(config):
    config.addinivalue_line("markers", "live: hits the real tradingview endpoint over the network")
