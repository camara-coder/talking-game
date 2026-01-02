"""
Text-based math parsing and computation utilities
Converts spoken math questions to deterministic calculations
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# Number word mappings
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000
}

# Operator mappings
OPERATORS = {
    # Addition
    "plus": "add",
    "add": "add",
    "added to": "add",
    "and": "add",  # "5 and 5" context-dependent

    # Subtraction
    "minus": "subtract",
    "subtract": "subtract",
    "take away": "subtract",
    "less": "subtract",

    # Multiplication
    "times": "multiply",
    "multiply": "multiply",
    "multiplied by": "multiply",

    # Division
    "divided by": "divide",
    "divide": "divide",
    "divided": "divide",
}

# Response templates
RESPONSE_TEMPLATES = {
    "add": "{a} plus {b} is {result}.",
    "subtract": "{a} minus {b} is {result}.",
    "multiply": "{a} times {b} is {result}.",
    "divide": "{a} divided by {b} is {result}.",
}


def text_to_number(text: str) -> Optional[int]:
    """
    Convert text number to integer

    Args:
        text: Text representation of number (e.g., "five", "42", "twenty three")

    Returns:
        Integer value or None if can't parse
    """
    text = text.lower().strip()

    # Check if already a digit
    if text.isdigit():
        return int(text)

    # Try direct word lookup
    if text in NUMBER_WORDS:
        return NUMBER_WORDS[text]

    # Try compound numbers (e.g., "twenty three" -> 23)
    parts = text.split()
    if len(parts) == 2:
        if parts[0] in NUMBER_WORDS and parts[1] in NUMBER_WORDS:
            return NUMBER_WORDS[parts[0]] + NUMBER_WORDS[parts[1]]

    # Handle "a" as 1
    if text == "a" or text == "an":
        return 1

    logger.debug(f"Could not parse number: '{text}'")
    return None


def is_math_query(text: str) -> bool:
    """
    Check if text contains a math query

    Args:
        text: Input text

    Returns:
        True if math query detected
    """
    text = text.lower()

    # Check for operator keywords
    for operator_word in OPERATORS.keys():
        if operator_word in text:
            return True

    # Check for "what is" or "what's" + numbers
    if ("what is" in text or "what's" in text) and any(c.isdigit() for c in text):
        return True

    # Check for number words + operator
    has_number = any(word in text for word in NUMBER_WORDS.keys())
    has_operator = any(op in text for op in OPERATORS.keys())

    return has_number and has_operator


def parse_math_expression(text: str) -> Optional[Tuple[str, float, float]]:
    """
    Parse math expression from text

    Args:
        text: Input text (e.g., "what is five plus five")

    Returns:
        Tuple of (operator, operand1, operand2) or None if can't parse
    """
    text = text.lower().strip()

    # Remove common question words
    text = re.sub(r'\b(what is|what\'s|whats|tell me|calculate)\b', '', text)
    text = text.strip()

    logger.debug(f"Parsing math expression: '{text}'")

    # Try to find operator
    operator = None
    operator_word = None

    for op_word, op_name in OPERATORS.items():
        if op_word in text:
            operator = op_name
            operator_word = op_word
            break

    if not operator:
        logger.debug("No operator found")
        return None

    # Split by operator
    parts = text.split(operator_word, 1)
    if len(parts) != 2:
        logger.debug(f"Could not split by operator: {parts}")
        return None

    left_text = parts[0].strip()
    right_text = parts[1].strip()

    # Extract numbers
    left_num = extract_number(left_text)
    right_num = extract_number(right_text)

    if left_num is None or right_num is None:
        logger.debug(f"Could not extract numbers: left='{left_text}', right='{right_text}'")
        return None

    logger.info(f"Parsed: {left_num} {operator} {right_num}")
    return (operator, left_num, right_num)


def extract_number(text: str) -> Optional[float]:
    """
    Extract a number from text

    Args:
        text: Text containing a number

    Returns:
        Number as float or None
    """
    text = text.strip()

    # Try to find digits
    digit_match = re.search(r'-?\d+\.?\d*', text)
    if digit_match:
        return float(digit_match.group())

    # Try number words
    words = text.split()
    for word in words:
        num = text_to_number(word)
        if num is not None:
            return float(num)

    # Try compound numbers
    num = text_to_number(text)
    if num is not None:
        return float(num)

    return None


def compute_math(operator: str, a: float, b: float) -> Tuple[Optional[float], Optional[str]]:
    """
    Compute math operation

    Args:
        operator: Operation (add, subtract, multiply, divide)
        a: First operand
        b: Second operand

    Returns:
        Tuple of (result, error_message)
        If error, result is None and error_message is set
    """
    try:
        if operator == "add":
            return (a + b, None)
        elif operator == "subtract":
            return (a - b, None)
        elif operator == "multiply":
            return (a * b, None)
        elif operator == "divide":
            if b == 0:
                return (None, "I can't divide by zero. Try another number.")
            return (a / b, None)
        else:
            return (None, f"Unknown operator: {operator}")

    except Exception as e:
        logger.error(f"Error computing math: {e}")
        return (None, "I had trouble with that calculation.")


def format_math_response(operator: str, a: float, b: float, result: float) -> str:
    """
    Format math response in kid-friendly way

    Args:
        operator: Operation
        a: First operand
        b: Second operand
        result: Result

    Returns:
        Formatted response text
    """
    # Convert floats to ints if whole numbers
    a_str = number_to_words(int(a) if a == int(a) else a)
    b_str = number_to_words(int(b) if b == int(b) else b)
    result_str = number_to_words(int(result) if result == int(result) else result)

    template = RESPONSE_TEMPLATES.get(operator, "{a} {operator} {b} equals {result}.")

    response = template.format(a=a_str.capitalize(), b=b_str, result=result_str)

    return response


def number_to_words(num: float) -> str:
    """
    Convert number to words (for simple numbers)

    Args:
        num: Number to convert

    Returns:
        Word representation
    """
    # For now, just return string representation
    # Could be enhanced to convert to words
    if isinstance(num, float) and num == int(num):
        num = int(num)

    # For numbers 0-20, use words
    if isinstance(num, int) and 0 <= num <= 20:
        words_map = {v: k for k, v in NUMBER_WORDS.items() if isinstance(v, int) and v <= 20}
        if num in words_map:
            return words_map[num]

    return str(num)
