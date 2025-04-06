# api/web_scraper.py

import requests
import re
import os
from bs4 import BeautifulSoup
from ollama import generate # Using direct synchronous ollama generate
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
import time
import concurrent.futures
import traceback # For error logging

# Load environment variables (ensure .env is accessible from where Django runs)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Default system prompt (can be overridden by agent)
SYSTEM_PROMPT = (
    "You are an educational assistant. Based *only* on the provided web content, "
    "answer the user's question accurately and concisely. If the answer is not "
    "found in the content, state that clearly. Do not add outside information."
)

# NOTE: Removed @st.cache_data decorator. Use Django's caching framework
# if caching is needed for google_search in the backend.
def google_search(query, num_results=5):
    """Fetch top search results using Google Custom Search API."""
    print(f"Performing Google Search for: {query}")
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
         # Log error instead of using st.error
         print("❌ ERROR: Google API Key or CSE ID missing in .env file.")
         # Return a consistent error format expected by the agent
         return ["Error: Missing Google API credentials."]

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {"q": query, "key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "num": num_results}

    try:
        # Using synchronous requests library
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        results = response.json()
        urls = [item["link"] for item in results.get("items", []) if "link" in item]

        if not urls:
            print("⚠️ No valid URLs found in Google Search results.")
            return [] # Return empty list, let the calling function handle it

        print(f"Found URLs: {urls}")
        return urls

    except requests.exceptions.RequestException as e:
        print(f"❌ Google API Request Error: {e}")
        return [f"Error: Google API request failed: {e}"] # Return error message in list
    except Exception as e:
        print(f"❌ Error processing Google Search results: {e}")
        traceback.print_exc()
        return [f"Error: Processing search results failed: {e}"] # Return error message in list


# NOTE: Removed @st.cache_data decorator. Use Django's caching framework
# if caching is needed for scrape_url in the backend.
def scrape_url(url):
    """Scrape the main textual content from a webpage (synchronously)."""
    print(f"Scraping URL: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        decoded_url = unquote(url)
        # Using synchronous requests library
        response = requests.get(decoded_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            print(f"Skipping non-HTML content ({content_type}) at: {url}")
            return ""

        # Using BeautifulSoup (synchronous)
        try:
            soup = BeautifulSoup(response.text, 'lxml')
        except:
            soup = BeautifulSoup(response.text, 'html.parser')

        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'input', 'select', 'textarea', 'label', 'iframe', 'noscript', 'img', 'svg', 'figure', 'figcaption']):
            element.decompose()

        main_content = soup.find('main') or \
                       soup.find('article') or \
                       soup.find('div', role='main') or \
                       soup.find('div', id='main') or \
                       soup.find('div', id='content') or \
                       soup.find('div', class_='content') or \
                       soup.find('div', class_='main') or \
                       soup.body # Fallback to body

        if not main_content:
             print(f"Could not find body or main content area for {url}")
             return ""

        text_content = main_content.get_text(separator='\n', strip=True)
        cleaned_text = re.sub(r'\n\s*\n', '\n', text_content).strip()

        if len(cleaned_text) < 100:
            # print(f"Scraped content too short ({len(cleaned_text)} chars) for: {url}") # Can be noisy
            return ""

        # print(f"Successfully scraped {len(cleaned_text)} characters from: {url}") # Can be noisy
        return cleaned_text

    except requests.exceptions.Timeout:
        print(f"Timeout error scraping {url}")
        return ""
    except requests.exceptions.HTTPError as e:
         print(f"HTTP error scraping {url}: {e.response.status_code}")
         return ""
    except requests.exceptions.RequestException as e:
        print(f"Request error scraping {url}: {e}")
        return ""
    except Exception as e:
        print(f"General error scraping {url}: {str(e)}")
        # Optionally log traceback for unexpected errors
        # traceback.print_exc()
        return ""


# This remains SYNCHRONOUS as it uses ollama.generate
def query_llm(prompt, model="deepseek-r1:1.5b", temperature=0.3):
    """Generate an AI response using Ollama (synchronously)."""
    print(f"Querying Ollama model {model} synchronously...")
    try:
        # Using synchronous ollama.generate
        response_data = generate(
            model=model,
            prompt=prompt,
            stream=False,
            options={'temperature': temperature}
        )
        response_text = response_data.get("response", "")
        if not response_text:
             print("Sync Ollama returned an empty response.")
             return "Error: LLM returned an empty response."
        print("Sync Ollama response received.")
        return response_text
    except Exception as e:
        print(f"Error querying Ollama model {model} synchronously: {e}")
        traceback.print_exc() # Log full error
        error_message = f"Error generating response from LLM ({model})."
        if "connection refused" in str(e).lower():
             error_message += " Is Ollama running?"
        # Return error message, don't raise exception here, let caller handle
        return error_message


def extract_clean_answer(llm_response):
    """
    Cleans LLM output. Currently just strips whitespace.
    """
    clean_answer = llm_response.strip()
    thinking_process = None # Not used currently
    return clean_answer, thinking_process


# Standalone test function - NOTE: This requires Streamlit to run
# To run: Install streamlit (pip install streamlit) then run: streamlit run api/web_scraper.py
# This main block will NOT run when imported by Django/Agent.
def web_scraper_main():
    # Import streamlit here only for the main block
    try:
        import streamlit as st
    except ImportError:
        print("Streamlit is not installed. Cannot run the test interface.")
        print("To run this test, install streamlit: pip install streamlit")
        print("Then run: streamlit run api/web_scraper.py")
        return

    st.title("🧪 Web Scraper & Summarizer Test (Sync)")
    st.warning("This test interface runs functions synchronously and requires Streamlit.")

    user_question = st.text_area("Enter a question:")

    if st.button("Search, Scrape & Summarize") and user_question:
        st.write("---")
        st.subheader("1. Google Search Results")
        with st.spinner("Searching Google..."):
            # Call synchronous version directly
            urls = google_search(user_question)
        if not urls or (isinstance(urls, list) and "Error" in urls[0]):
            st.error(f"Failed to get URLs: {urls[0] if urls else 'No results'}")
            return
        for url in urls:
            st.markdown(f"- [{url}]({url})")

        st.write("---")
        st.subheader("2. Scraping Content")
        web_content = ""
        scraped_urls = []

        # Use ThreadPoolExecutor for concurrent scraping in the test interface
        # scrape_url is synchronous, so this is okay here.
        with st.spinner("Scraping websites concurrently..."):
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {executor.submit(scrape_url, url): url for url in urls}
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        content = future.result()
                        if content:
                            st.write(f"✅ Scraped: {url} ({len(content)} chars)")
                            web_content += f"\n\n--- Content from {url} ---\n\n{content}"
                            scraped_urls.append(url)
                        else:
                            st.write(f"⚪ Skipped or empty content: {url}")
                    except Exception as exc:
                        st.write(f"❌ Failed to scrape {url}: {exc}")

        if not web_content:
            st.error("Failed to retrieve any useful content from the websites.")
            return

        st.write("---")
        st.subheader("3. Generating Summary")
        max_length = 15000 # Limit context for the test LLM call
        prompt = f"""
        {SYSTEM_PROMPT}

        Based *only* on the following combined web content, answer the question concisely.

        Web Content:
        {web_content[:max_length]}

        Question: {user_question}
        Answer:
        """

        with st.spinner("Asking LLM to synthesize answer..."):
            # Call synchronous version directly
            llm_response = query_llm(prompt)

        st.write("---")
        st.subheader("✅ Synthesized Answer")
        st.markdown(llm_response)

        with st.expander("View Raw Scraped Content (Truncated)"):
             st.text(web_content[:max_length])


if __name__ == "__main__":
    web_scraper_main()