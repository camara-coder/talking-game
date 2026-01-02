"""
Unit tests for math text processing
"""
import pytest
from app.utils.text_math import (
    text_to_number,
    is_math_query,
    parse_math_expression,
    extract_number,
    compute_math,
    format_math_response,
    number_to_words
)


class TestTextToNumber:
    """Test number text parsing"""

    def test_parse_single_digit(self):
        """Test parsing single digit numbers"""
        assert text_to_number("five") == 5
        assert text_to_number("zero") == 0
        assert text_to_number("nine") == 9

    def test_parse_teens(self):
        """Test parsing teen numbers"""
        assert text_to_number("thirteen") == 13
        assert text_to_number("fifteen") == 15
        assert text_to_number("nineteen") == 19

    def test_parse_tens(self):
        """Test parsing tens"""
        assert text_to_number("twenty") == 20
        assert text_to_number("thirty") == 30
        assert text_to_number("ninety") == 90

    def test_parse_compound(self):
        """Test parsing compound numbers"""
        assert text_to_number("twenty three") == 23
        assert text_to_number("forty two") == 42
        assert text_to_number("ninety nine") == 99

    def test_parse_digits(self):
        """Test parsing digit strings"""
        assert text_to_number("5") == 5
        assert text_to_number("42") == 42
        assert text_to_number("100") == 100

    def test_parse_invalid(self):
        """Test parsing invalid input"""
        assert text_to_number("hello") is None
        assert text_to_number("") is None

    def test_parse_special_words(self):
        """Test parsing special words like 'a'"""
        assert text_to_number("a") == 1
        assert text_to_number("an") == 1


class TestMathDetection:
    """Test math question detection"""

    def test_detect_math_queries(self):
        """Test detection of math questions"""
        assert is_math_query("what is five plus five")
        assert is_math_query("5 plus 5")
        assert is_math_query("ten minus three")
        assert is_math_query("what's 12 divided by 4")
        assert is_math_query("6 times 7")

    def test_reject_non_math(self):
        """Test rejection of non-math questions"""
        assert not is_math_query("what is your name")
        assert not is_math_query("tell me a story")
        assert not is_math_query("hello there")
        assert not is_math_query("I like apples")


class TestMathParsing:
    """Test parsing of math expressions"""

    def test_parse_addition(self):
        """Test parsing of addition"""
        result = parse_math_expression("what is five plus five")
        assert result is not None
        operator, a, b = result
        assert operator == "add"
        assert a == 5.0
        assert b == 5.0

    def test_parse_subtraction(self):
        """Test parsing of subtraction"""
        result = parse_math_expression("ten minus three")
        assert result is not None
        operator, a, b = result
        assert operator == "subtract"
        assert a == 10.0
        assert b == 3.0

    def test_parse_multiplication(self):
        """Test parsing of multiplication"""
        result = parse_math_expression("6 times 7")
        assert result is not None
        operator, a, b = result
        assert operator == "multiply"
        assert a == 6.0
        assert b == 7.0

    def test_parse_division(self):
        """Test parsing of division"""
        result = parse_math_expression("12 divided by 4")
        assert result is not None
        operator, a, b = result
        assert operator == "divide"
        assert a == 12.0
        assert b == 4.0

    def test_parse_with_digits(self):
        """Test parsing with digit numbers"""
        result = parse_math_expression("5 plus 5")
        assert result is not None
        operator, a, b = result
        assert a == 5.0
        assert b == 5.0

    def test_parse_invalid(self):
        """Test parsing from invalid input"""
        assert parse_math_expression("hello world") is None
        assert parse_math_expression("what is your name") is None


class TestExtractNumber:
    """Test number extraction from text"""

    def test_extract_digits(self):
        """Test extracting digit numbers"""
        assert extract_number("5") == 5.0
        assert extract_number("42") == 42.0
        assert extract_number("100") == 100.0

    def test_extract_words(self):
        """Test extracting word numbers"""
        assert extract_number("five") == 5.0
        assert extract_number("twenty") == 20.0
        assert extract_number("the number is ten") == 10.0

    def test_extract_from_sentence(self):
        """Test extracting numbers from sentences"""
        assert extract_number("give me 5 apples") == 5.0
        assert extract_number("I have twenty dollars") == 20.0

    def test_extract_invalid(self):
        """Test extracting from text with no numbers"""
        assert extract_number("hello world") is None
        assert extract_number("no numbers here") is None


class TestMathComputation:
    """Test math computation"""

    def test_addition(self):
        """Test addition computation"""
        result, error = compute_math("add", 5, 5)
        assert result == 10
        assert error is None

    def test_subtraction(self):
        """Test subtraction computation"""
        result, error = compute_math("subtract", 10, 3)
        assert result == 7
        assert error is None

    def test_multiplication(self):
        """Test multiplication computation"""
        result, error = compute_math("multiply", 6, 7)
        assert result == 42
        assert error is None

    def test_division(self):
        """Test division computation"""
        result, error = compute_math("divide", 12, 4)
        assert result == 3
        assert error is None

    def test_division_by_zero(self):
        """Test division by zero handling"""
        result, error = compute_math("divide", 5, 0)
        assert result is None
        assert error is not None
        assert "divide by zero" in error.lower()

    def test_invalid_operator(self):
        """Test invalid operator handling"""
        result, error = compute_math("invalid", 5, 5)
        assert result is None
        assert error is not None


class TestMathFormatting:
    """Test math response formatting"""

    def test_format_addition(self):
        """Test formatting addition response"""
        response = format_math_response("add", 5, 5, 10)
        assert "plus" in response.lower()
        assert "10" in response or "ten" in response.lower()

    def test_format_subtraction(self):
        """Test formatting subtraction response"""
        response = format_math_response("subtract", 10, 3, 7)
        assert "minus" in response.lower()

    def test_format_multiplication(self):
        """Test formatting multiplication response"""
        response = format_math_response("multiply", 6, 7, 42)
        assert "times" in response.lower()

    def test_format_division(self):
        """Test formatting division response"""
        response = format_math_response("divide", 12, 4, 3)
        assert "divided" in response.lower()


class TestNumberToWords:
    """Test number to words conversion"""

    def test_convert_small_numbers(self):
        """Test converting small numbers to words"""
        assert number_to_words(5) == "five"
        assert number_to_words(10) == "ten"
        assert number_to_words(0) == "zero"

    def test_convert_large_numbers(self):
        """Test converting large numbers (returns string)"""
        assert number_to_words(100) == "100"
        assert number_to_words(1000) == "1000"

    def test_convert_floats(self):
        """Test converting float numbers"""
        assert number_to_words(5.5) == "5.5"
        assert number_to_words(10.0) == "ten"  # Should convert to int


class TestEndToEnd:
    """Test end-to-end math processing"""

    @pytest.mark.parametrize("input_text,expected_result", [
        ("what is five plus five", 10),
        ("10 minus 3", 7),
        ("6 times 7", 42),
        ("twelve divided by four", 3),
    ])
    def test_full_math_pipeline(self, input_text, expected_result):
        """Test full math processing pipeline"""
        # Check it's detected as math
        assert is_math_query(input_text)

        # Parse expression
        parsed = parse_math_expression(input_text)
        assert parsed is not None

        # Compute result
        operator, a, b = parsed
        result, error = compute_math(operator, a, b)

        assert error is None
        assert result == expected_result

    def test_full_pipeline_with_formatting(self):
        """Test pipeline including response formatting"""
        input_text = "what is five plus five"

        # Parse
        parsed = parse_math_expression(input_text)
        assert parsed is not None

        # Compute
        operator, a, b = parsed
        result, error = compute_math(operator, a, b)

        assert error is None
        assert result == 10

        # Format
        response = format_math_response(operator, a, b, result)
        assert isinstance(response, str)
        assert len(response) > 0
