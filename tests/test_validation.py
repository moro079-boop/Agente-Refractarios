"""Las verificaciones analiticas del solver, como tests."""

import pytest

from ladle_thermal.validation import ALL_CHECKS


@pytest.mark.parametrize("check_fn", ALL_CHECKS, ids=[f.__name__ for f in ALL_CHECKS])
def test_analytic_check(check_fn):
    check = check_fn()
    assert check.passed, f"{check.name}: error {check.error:.3e} > tol {check.tolerance:.1e} ({check.detail})"
