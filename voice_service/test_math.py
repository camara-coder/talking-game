"""
Quick test of math parsing and computation
"""
from app.utils.text_math import (
    is_math_query,
    parse_math_expression,
    compute_math,
    format_math_response
)


def test_math():
    """Test math utilities"""
    print("Testing Math Utilities")
    print("=" * 60)

    test_cases = [
        "what is five plus five",
        "what's 7 plus 3",
        "ten minus two",
        "what is 3 times 4",
        "12 divided by 3",
        "100 divided by 0",
        "what is a cat",  # Not math
    ]

    for test in test_cases:
        print(f"\nTest: '{test}'")

        # Check if math query
        is_math = is_math_query(test)
        print(f"  Is math: {is_math}")

        if is_math:
            # Parse expression
            parsed = parse_math_expression(test)
            if parsed:
                operator, a, b = parsed
                print(f"  Parsed: {a} {operator} {b}")

                # Compute
                result, error = compute_math(operator, a, b)

                if error:
                    print(f"  Error: {error}")
                else:
                    print(f"  Result: {result}")

                    # Format response
                    if result is not None:
                        response = format_math_response(operator, a, b, result)
                        print(f"  Response: '{response}'")
            else:
                print(f"  Could not parse expression")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_math()
