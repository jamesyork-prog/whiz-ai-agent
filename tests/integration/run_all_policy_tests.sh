#!/bin/bash
# Run all policy-based decision integration tests

echo "================================================================================"
echo "Running All Policy-Based Decision Integration Tests"
echo "================================================================================"
echo ""

TESTS=(
    "test_policy_decision_real_ticket.py"
    "test_policy_decision_edge_cases.py"
    "test_policy_decision_performance.py"
)

PASSED=0
FAILED=0

for test in "${TESTS[@]}"; do
    echo "--------------------------------------------------------------------------------"
    echo "Running: $test"
    echo "--------------------------------------------------------------------------------"
    
    if docker-compose exec -T parlant python /app/tests/integration/$test; then
        echo "✓ $test PASSED"
        ((PASSED++))
    else
        echo "✗ $test FAILED"
        ((FAILED++))
    fi
    
    echo ""
done

echo "================================================================================"
echo "Test Summary"
echo "================================================================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ ALL TESTS PASSED"
    exit 0
else
    echo "✗ SOME TESTS FAILED"
    exit 1
fi
