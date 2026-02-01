"""
Sample Application for Testing AI Documentation Generator
This file contains various Python functions to test documentation generation.
"""

import math
from typing import List, Dict, Optional


def calculate_circle_area(radius: float) -> float:
    """
    Calculate the area of a circle given its radius.
    
    Args:
        radius: The radius of the circle
        
    Returns:
        The area of the circle
        
    Raises:
        ValueError: If radius is negative
    """
    if radius < 0:
        raise ValueError("Radius cannot be negative")
    
    return math.pi * radius ** 2


def greet_user(name: str, greeting: str = "Hello") -> str:
    """Simple greeting function."""
    return f"{greeting}, {name}!"


def find_max_value(numbers: List[float]) -> Optional[float]:
    """
    Find the maximum value in a list of numbers.
    
    Args:
        numbers: List of numbers to search
        
    Returns:
        Maximum value or None if list is empty
    """
    if not numbers:
        return None
    
    max_val = numbers[0]
    for num in numbers:
        if num > max_val:
            max_val = num
    
    return max_val


def process_user_data(user_data: Dict[str, any]) -> Dict[str, any]:
    """
    Process and validate user data from a form submission.
    
    This function takes raw user data, validates it, and returns
    a cleaned version with proper formatting.
    """
    processed = {}
    
    # Validate name
    if "name" in user_data:
        processed["name"] = user_data["name"].strip().title()
    
    # Validate email
    if "email" in user_data:
        email = user_data["email"].strip().lower()
        if "@" in email:
            processed["email"] = email
    
    # Validate age
    if "age" in user_data:
        try:
            age = int(user_data["age"])
            if 0 < age < 150:
                processed["age"] = age
        except ValueError:
            pass
    
    return processed


class Calculator:
    """A simple calculator class with basic operations."""
    
    def __init__(self):
        """Initialize calculator with zero memory."""
        self.memory = 0
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """
        Divide a by b.
        
        Raises:
            ZeroDivisionError: If b is zero
        """
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b
    
    def store(self, value: float) -> None:
        """Store a value in memory."""
        self.memory = value
    
    def recall(self) -> float:
        """Recall value from memory."""
        return self.memory


def fibonacci(n: int) -> List[int]:
    """
    Generate Fibonacci sequence up to n terms.
    
    Args:
        n: Number of terms to generate
        
    Returns:
        List containing the Fibonacci sequence
        
    Example:
        >>> fibonacci(5)
        [0, 1, 1, 2, 3]
    """
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])
    
    return sequence


def is_prime(number: int) -> bool:
    """
    Check if a number is prime.
    
    A prime number is a natural number greater than 1 that has
    no positive divisors other than 1 and itself.
    """
    if number < 2:
        return False
    
    if number == 2:
        return True
    
    if number % 2 == 0:
        return False
    
    for i in range(3, int(math.sqrt(number)) + 1, 2):
        if number % i == 0:
            return False
    
    return True


def merge_sorted_lists(list1: List[int], list2: List[int]) -> List[int]:
    """
    Merge two sorted lists into one sorted list.
    
    Args:
        list1: First sorted list
        list2: Second sorted list
        
    Returns:
        A new sorted list containing all elements from both input lists
    """
    result = []
    i = j = 0
    
    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1
    
    # Add remaining elements
    result.extend(list1[i:])
    result.extend(list2[j:])
    
    return result


def word_frequency(text: str) -> Dict[str, int]:
    """
    Count the frequency of each word in a text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary with words as keys and their frequencies as values
    """
    # Convert to lowercase and split into words
    words = text.lower().split()
    
    # Count frequencies
    frequency = {}
    for word in words:
        # Remove punctuation
        clean_word = ''.join(c for c in word if c.isalnum())
        if clean_word:
            frequency[clean_word] = frequency.get(clean_word, 0) + 1
    
    return frequency


def binary_search(sorted_list: List[int], target: int) -> int:
    """
    Perform binary search on a sorted list.
    
    Args:
        sorted_list: A sorted list of integers
        target: The value to search for
        
    Returns:
        Index of target if found, -1 otherwise
    """
    left = 0
    right = len(sorted_list) - 1
    
    while left <= right:
        mid = (left + right) // 2
        
        if sorted_list[mid] == target:
            return mid
        elif sorted_list[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1


def validate_email(email: str) -> bool:
    """
    Basic email validation.
    
    Checks if the email has @ symbol and a domain extension.
    Note: This is a simple validation, not RFC-compliant.
    """
    if not email or "@" not in email:
        return False
    
    parts = email.split("@")
    if len(parts) != 2:
        return False
    
    username, domain = parts
    
    if not username or not domain:
        return False
    
    if "." not in domain:
        return False
    
    return True


def temperature_converter(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert temperature between Celsius, Fahrenheit, and Kelvin.
    
    Args:
        value: Temperature value to convert
        from_unit: Source unit ('C', 'F', or 'K')
        to_unit: Target unit ('C', 'F', or 'K')
        
    Returns:
        Converted temperature value
        
    Raises:
        ValueError: If units are invalid
    """
    # Convert to Celsius first
    if from_unit == 'C':
        celsius = value
    elif from_unit == 'F':
        celsius = (value - 32) * 5/9
    elif from_unit == 'K':
        celsius = value - 273.15
    else:
        raise ValueError(f"Invalid from_unit: {from_unit}")
    
    # Convert from Celsius to target
    if to_unit == 'C':
        return celsius
    elif to_unit == 'F':
        return (celsius * 9/5) + 32
    elif to_unit == 'K':
        return celsius + 273.15
    else:
        raise ValueError(f"Invalid to_unit: {to_unit}")


if __name__ == "__main__":
    # Test some functions
    print("Circle area (radius=5):", calculate_circle_area(5))
    print("Greeting:", greet_user("Alice"))
    print("Max value:", find_max_value([1, 5, 3, 9, 2]))
    print("Fibonacci(10):", fibonacci(10))
    print("Is 17 prime?", is_prime(17))
    print("Temperature conversion (0°C to °F):", temperature_converter(0, 'C', 'F'))