#!/usr/bin/env python3
"""
Tripgain Gemini Integration - Intelligent Webpage Summarization
Analyzes live webpages and generates analytical summaries using Google Gemini 2.5 Flash API.
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from typing import Tuple
import google.generativeai as genai

# Configuration
GEMINI_MODEL = "gemini-2.5-flash"
OUTPUT_FILE = "summary_output.txt"

# Supported webpage sources
WEBPAGE_SOURCES = {
    1: "https://en.wikipedia.org/wiki/Artificial_intelligence",
    2: "https://www.bbc.com/news/technology",
    3: "https://edition.cnn.com/business"
}


def fetch_webpage(url: str) -> str:
    """
    Fetch raw HTML content from a given URL.

    Args:
        url: The URL to fetch

    Returns:
        Raw HTML content as string

    Raises:
        Exception: If the webpage cannot be fetched
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch webpage: {str(e)}")


def clean_html(html_content: str) -> str:
    """
    Clean HTML content by removing scripts, styles, navigation, and irrelevant text.

    Args:
        html_content: Raw HTML content

    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()

    # Remove meta tags and comments
    for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.string))):
        if isinstance(comment, str) and comment.name is None:
            comment.extract()

    # Get text
    text = soup.get_text(separator=' ', strip=True)

    # Clean up excessive whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)

    # Limit text length to avoid token overflow (approximately 8000 chars)
    if len(text) > 8000:
        text = text[:8000]

    return text


def setup_gemini_api(api_key: str = None) -> None:
    """
    Initialize Gemini API with the provided API key.

    Args:
        api_key: Optional Google API key. If not provided, uses GOOGLE_API_KEY env variable

    Raises:
        ValueError: If API key is not provided or not found in environment
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError(
            "Google API key not provided. Set GOOGLE_API_KEY environment variable "
            "or pass api_key parameter."
        )

    genai.configure(api_key=api_key)


def create_custom_prompt(content_type: str = "technology") -> str:
    """
    Create a well-structured custom prompt for Gemini.

    Args:
        content_type: Type of content (default: technology)

    Returns:
        Custom prompt string
    """
    prompt = f"""You are an expert content analyst specializing in {content_type} insights. 
Analyze the provided webpage content and deliver a structured analytical summary following these requirements:

1. Summarize the content into exactly 3-5 focused bullet points
2. Each bullet point should highlight a key theme, finding, or important development
3. Focus on: emerging trends, critical insights, and {content_type} implications
4. After the bullet points, provide ONE analytical insight (2-3 sentences max) that:
   - Explains what these points collectively suggest about the current state
   - Interprets the overall theme or broader implications
   - Offers perspective on where this is heading

OUTPUT FORMAT (DO NOT DEVIATE):
• [First key point]
• [Second key point]
• [Third key point]
[Additional bullet points if relevant]

Insight: [Your analytical interpretation here]

Webpage Content to Analyze:
"""
    return prompt


def analyze_with_gemini(cleaned_content: str, api_key: str = None) -> Tuple[str, str]:
    """
    Send cleaned content to Gemini API and get summarized response with insight.

    Args:
        cleaned_content: Cleaned webpage content
        api_key: Optional Google API key

    Returns:
        Tuple of (summary, insight)
    """
    try:
        setup_gemini_api(api_key)

        # Create custom prompt
        base_prompt = create_custom_prompt(content_type="technology and business trends")
        full_prompt = base_prompt + cleaned_content

        # Initialize Gemini model
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Generate response
        print("[*] Sending request to Gemini 2.5 Flash API...")
        response = model.generate_content(full_prompt)

        # Extract response text
        response_text = response.text

        # Parse summary and insight from response
        summary, insight = parse_gemini_response(response_text)

        return summary, insight

    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")


def parse_gemini_response(response_text: str) -> Tuple[str, str]:
    """
    Parse Gemini response to extract summary bullets and insight.

    Args:
        response_text: Raw response from Gemini

    Returns:
        Tuple of (formatted_summary, insight)
    """
    lines = response_text.strip().split('\n')

    summary_lines = []
    insight = ""
    parsing_insight = False

    for line in lines:
        line = line.strip()

        if line.lower().startswith('insight:'):
            parsing_insight = True
            insight = line.replace('Insight:', '').replace('insight:', '').strip()
        elif parsing_insight:
            if insight:
                insight += " " + line
            else:
                insight = line
        elif line.startswith('•') or (line and summary_lines):
            if line.startswith('•'):
                summary_lines.append(line)
            elif line:
                if summary_lines:
                    summary_lines[-1] += " " + line

    summary = "\n".join(summary_lines)

    return summary, insight


def format_output(summary: str, insight: str) -> str:
    """
    Format the final output according to specifications.

    Args:
        summary: Summary bullet points
        insight: Analytical insight

    Returns:
        Formatted output string
    """
    output = f"""Summary:
{summary}

Insight:
{insight}"""
    return output


def save_output(content: str, filename: str = OUTPUT_FILE) -> None:
    """
    Save the formatted output to a file.

    Args:
        content: Content to save
        filename: Output filename
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[✓] Output saved to {filename}")
    except IOError as e:
        print(f"[✗] Error saving output: {str(e)}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Tripgain Gemini Integration - Intelligent Webpage Summarization")
    print("=" * 70)
    print()

    # Display available sources
    print("Available webpage sources:")
    for key, url in WEBPAGE_SOURCES.items():
        print(f"  {key}. {url}")
    print()

    # Get user choice or use default
    try:
        choice = input("Enter your choice (1-3) [default: 1]: ").strip()
        choice = int(choice) if choice else 1

        if choice not in WEBPAGE_SOURCES:
            print("[✗] Invalid choice. Using default (Wikipedia AI).")
            choice = 1
    except ValueError:
        print("[✗] Invalid input. Using default (Wikipedia AI).")
        choice = 1

    selected_url = WEBPAGE_SOURCES[choice]
    print(f"\n[*] Selected URL: {selected_url}")
    print()

    try:
        # Step 1: Fetch webpage
        print("[1/4] Fetching webpage content...")
        html_content = fetch_webpage(selected_url)
        print("[✓] Webpage fetched successfully")
        print()

        # Step 2: Clean HTML
        print("[2/4] Cleaning HTML content...")
        cleaned_content = clean_html(html_content)
        print(f"[✓] Content cleaned (length: {len(cleaned_content)} characters)")
        print()

        # Step 3: Analyze with Gemini
        print("[3/4] Analyzing with Gemini 2.5 Flash...")
        summary, insight = analyze_with_gemini(cleaned_content)
        print("[✓] Analysis complete")
        print()

        # Step 4: Format and display output
        print("[4/4] Formatting output...")
        formatted_output = format_output(summary, insight)
        print()
        print("=" * 70)
        print("RESULT:")
        print("=" * 70)
        print(formatted_output)
        print("=" * 70)
        print()

        # Save to file
        save_output(formatted_output)

    except Exception as e:
        print(f"[✗] Error: {str(e)}")
        print("\nPlease ensure:")
        print("  1. Google API key is set in GOOGLE_API_KEY environment variable")
        print("  2. Internet connection is available")
        print("  3. Required packages are installed: pip install google-generativeai requests beautifulsoup4")
        sys.exit(1)


if __name__ == "__main__":
    main()
