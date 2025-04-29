import asyncio 
import traceback  
import os 
import re 

# Langchain imports
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough 

from .utils import process_documents, get_retriever
from .web_scraper import google_search, scrape_url, query_llm as sync_query_llm, extract_clean_answer

try:
    import httpx
    ASYNC_HTTP_CLIENT = httpx.AsyncClient()
except ImportError:
    ASYNC_HTTP_CLIENT = None


class SubjectAgent:
    def __init__(self, subject):
        """
        Initializes an agent for a specific subject.

        Args:
            subject (str): The subject this agent specializes in (e.g., "Math").
        """
        self.subject = subject
        self.subject_persist_dir_name = f"chroma_db_{self.subject.replace(' ', '_').lower()}"
        self.vector_store = None 
        self.qa_chain = None 

        self.llm = ChatOllama(model="deepseek-r1:1.5b", temperature=0.3)
        print(f"Initialized SubjectAgent for: {self.subject}")

    def get_custom_prompt(self):
        """Returns a subject-specific prompt template for RAG."""
        if self.subject == "Computer Science":
            system_message = (
                f"You are an educational assistant specialized in {self.subject}. "
                "When asked to define or explain a concept using the provided context, provide a clear and concise definition or explanation based *only* on that context. "
                "Avoid discussing unrelated topics such as job market impact unless explicitly requested and present in the context. "
                "If the context doesn't contain the answer, state that."
            )
        elif self.subject == "Math":
            system_message = (
                f"You are an educational assistant specialized in {self.subject}. "
                "Using *only* the provided context, provide precise definitions and step-by-step explanations for mathematical concepts. "
                "Include examples and proofs *if* they are available in the context. "
                "If the context doesn't contain the answer, state that."
            )
        elif self.subject == "Physics":
            system_message = (
                f"You are an educational assistant specialized in {self.subject}. "
                "Using *only* the provided context, offer clear definitions and detailed explanations for physics concepts. "
                "Use real-world examples *if* they are present in the context. "
                "If the context doesn't contain the answer, state that."
            )
        else:
            system_message = (
                f"You are an educational assistant for {self.subject}. Provide clear, concise, and accurate answers based *only* on the given context. "
                "If the context doesn't contain the answer, state that."
            )

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "Based *only* on the context above, provide a precise and well-structured answer."
            )
        ])

    async def create_knowledge_base(self, uploaded_files_or_paths):
        """
        Processes uploaded files/paths and creates/updates the vector store asynchronously.
        Accepts either Django UploadedFile objects or file paths.

        Args:
            uploaded_files_or_paths (list): List of Django UploadedFile objects or file paths.
        """
        print(f"Starting knowledge base creation for {self.subject} using dir name: {self.subject_persist_dir_name}")
        try:
            loop = asyncio.get_running_loop()
            self.vector_store = await loop.run_in_executor(
                None, 
                process_documents, 
                uploaded_files_or_paths, 
                self.subject_persist_dir_name
            )
            self.qa_chain = None  
            if self.vector_store:
                print(f"Knowledge base creation/update finished successfully for {self.subject}.")
            else:
                print(f"Knowledge base creation/update failed for {self.subject} (process_documents returned None).")

        except Exception as e:
             print(f"Exception during knowledge base creation for {self.subject}: {e}")
             traceback.print_exc()
             self.vector_store = None
             self.qa_chain = None
             raise e 

    def initialize_qa_chain(self):
        """Initializes the RetrievalQA chain (synchronous)."""
        if self.qa_chain:
            return True
        print(f"Attempting to initialize QA chain for {self.subject} using dir name: {self.subject_persist_dir_name}")
        try:
            retriever = get_retriever(subject_persist_dir_name=self.subject_persist_dir_name)
            if not retriever:
                print(f"Failed to get retriever for {self.subject} from dir name: {self.subject_persist_dir_name}")
                self.qa_chain = None
                return False
            self.qa_chain = RetrievalQA.from_chain_type(
                self.llm,
                retriever=retriever,
                chain_type="stuff",
                chain_type_kwargs={"prompt": self.get_custom_prompt()},
            )
            print(f"QA chain initialized successfully for {self.subject}.")
            return True
        except Exception as e:
            print(f"Error initializing QA chain for {self.subject}: {e}")
            print(traceback.format_exc())
            self.qa_chain = None
            return False

    async def get_rag_answer(self, question):
        """Gets an answer using the agent's RAG setup asynchronously."""
        print(f"Getting RAG answer for {self.subject}...")
        if not self.initialize_qa_chain():
             return f"Error initializing QA chain for {self.subject}. Knowledge base might be missing or corrupt. Please try creating/updating it."

        if self.qa_chain:
            try:
                print(f"Invoking RAG chain asynchronously for {self.subject}...")
                response = await self.qa_chain.ainvoke({"query": question})
                print(f"Async RAG response received for {self.subject}.")

                if isinstance(response, dict) and "result" in response:
                     result_text = response["result"].strip()
                     non_answer_phrases = ["cannot find relevant information", "context doesn't contain", "context does not contain", "based on the context provided", "based on the text provided", "information provided does not", "i cannot answer"]
                     is_non_answer = any(phrase in result_text.lower() for phrase in non_answer_phrases)
                     is_too_short = len(result_text) < 50 and ("based on" in result_text.lower() or "context" in result_text.lower())
                     if is_non_answer or is_too_short:
                         print(f"RAG chain for {self.subject} indicated answer not in context.")
                         return f"The documents for {self.subject} do not seem to contain an answer to this question."
                     return result_text
                else:
                     print(f"Unexpected async RAG response format for {self.subject}: {response}")
                     return "Received an unexpected response format from the RAG system."

            except NotImplementedError:
                 print("Warning: ainvoke not implemented for RAG chain, falling back to sync.")
                 try:
                     loop = asyncio.get_running_loop()
                     response = await loop.run_in_executor(None, self.qa_chain.invoke, {"query": question})
                     if isinstance(response, dict) and "result" in response:
                          result_text = response["result"].strip()
                          non_answer_phrases = ["cannot find relevant information", "context doesn't contain", "context does not contain", "based on the context provided", "based on the text provided", "information provided does not", "i cannot answer"]
                          is_non_answer = any(phrase in result_text.lower() for phrase in non_answer_phrases)
                          is_too_short = len(result_text) < 50 and ("based on" in result_text.lower() or "context" in result_text.lower())
                          if is_non_answer or is_too_short: return f"The documents for {self.subject} do not seem to contain an answer (sync fallback)."
                          return result_text
                     else: return "Unexpected sync RAG response format."
                 except Exception as sync_e:
                     print(f"Error invoking sync fallback RAG chain for {self.subject}: {sync_e}")
                     print(traceback.format_exc())
                     return f"An error occurred retrieving RAG answer (sync fallback)."

            except Exception as e:
                print(f"Error invoking async RAG chain for {self.subject}: {e}")
                print(traceback.format_exc())
                return f"An error occurred while retrieving the RAG answer."
        else:
             return f"QA chain for {self.subject} could not be initialized."


    async def get_llm_answer(self, question):
        """Gets a baseline answer directly from the LLM asynchronously."""
        print(f"Getting direct LLM answer asynchronously for {self.subject}...")
        try:
            prompt = f"You are an AI expert in {self.subject}. Answer the following question accurately and concisely.\n\nQuestion: {question}\n\nAnswer:"
            response = await self.llm.ainvoke(prompt)
            print("Async direct LLM response received.")
            return response.content if response else "LLM returned an empty response."
        except NotImplementedError:
             print("Warning: ainvoke not implemented for LLM, falling back to sync.")
             try:
                  loop = asyncio.get_running_loop()
                  response = await loop.run_in_executor(None, self.llm.invoke, prompt)
                  return response.content if response else "LLM returned empty (sync fallback)."
             except Exception as sync_e:
                  print(f"Error invoking sync fallback LLM for {self.subject}: {sync_e}")
                  print(traceback.format_exc())
                  return "An error occurred contacting LLM (sync fallback)."
        except Exception as e:
            print(f"Error invoking async direct LLM for {self.subject}: {e}")
            print(traceback.format_exc())
            return "An error occurred while contacting the Language Model."

    async def _process_web_content(self, question, urls):
        """Scrapes URLs, synthesizes answer using LLM asynchronously."""
        print(f"Starting async web content processing for {self.subject}...")
        web_content = ""
        successful_scrapes = 0
        failed_scrapes = 0

        async def scrape_in_executor(url):
             loop = asyncio.get_running_loop()
             return await loop.run_in_executor(None, scrape_url, url)

        scrape_tasks = [scrape_in_executor(url) for url in urls]
        scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        for i, result in enumerate(scrape_results):
             if isinstance(result, Exception) or not result:
                  failed_scrapes += 1
                  if isinstance(result, Exception):
                      print(f"Scraping task failed for url {urls[i]}: {result}")
             else:
                  web_content += result + "\n\n"
                  successful_scrapes += 1
        print(f"Async web scraping finished for {self.subject}. Success: {successful_scrapes}, Failed: {failed_scrapes}")

        if not web_content:
             if successful_scrapes == 0 and failed_scrapes > 0: return "Found websites, but failed to scrape content from any of them."
             if successful_scrapes == 0 and failed_scrapes == 0: return "No websites provided for scraping." # Should not happen if urls has items
             return "Scraped some websites, but could not extract meaningful content."

        max_length = 15000
        truncated_content = web_content[:max_length]
        print(f"Sending {len(truncated_content)} chars of web content to LLM for async synthesis.")

        prompt = f"""
        You are an educational assistant specialized in {self.subject}.
        Based *only* on the following web content, answer the question concisely and clearly.
        If the answer is not found in the content, state that clearly and do not invent information.

        Web Content:
        {truncated_content}

        Question: {question}
        Answer:
        """
        try:
            loop = asyncio.get_running_loop()
            llm_response = await loop.run_in_executor(
                None,             # Use default executor
                sync_query_llm,   # The synchronous function from web_scraper.py
                prompt            # Argument for the function
            )

            if isinstance(llm_response, str) and "Error:" in llm_response:
                 print(f"Web synthesis LLM failed internally: {llm_response}")
                 return "Error synthesizing answer from web content." # Return generic error

            clean_answer, _ = extract_clean_answer(llm_response) # Sync extraction is fine
            print(f"Async web answer synthesized for {self.subject}.")

            # Non-answer detection
            non_answer_phrases = ["cannot find relevant information", "answer is not found", "content does not provide", "based on the provided content", "information given does not", "i cannot answer", "provided text does not contain"]
            is_non_answer = any(phrase in clean_answer.lower() for phrase in non_answer_phrases)
            is_error_message = "error" in clean_answer.lower() and ("llm" in clean_answer.lower() or "generating response" in clean_answer.lower())
            is_too_short = len(clean_answer) < 60 and ("based on" in clean_answer.lower() or "content" in clean_answer.lower())

            if is_non_answer or is_too_short:
                print(f"Web synthesis for {self.subject} indicated answer not in content.")
                return "Could not find a specific answer from the scraped web content."
            elif is_error_message: # Catch errors explicitly returned by query_llm
                 print(f"Web synthesis LLM failed: {clean_answer}")
                 return "Error synthesizing answer from web content."

            return clean_answer
        except Exception as e:
             # Catch errors from run_in_executor or extract_clean_answer
             print(f"Error during async LLM synthesis step for web content: {e}")
             print(traceback.format_exc())
             return "Error synthesizing answer from web content."

    async def aggregate_answers(self, question, rag_answer, llm_answer, web_answer):
        """Combines answers asynchronously and cleans the output."""
        print(f"Aggregating answers asynchronously for {self.subject}...")

        # Availability checks (refined)
        rag_unavailable_msgs = ["please create", "error initializing", "cannot get rag", "qa chain for", "failed to load", "unexpected response format", "an error occurred", "do not seem to contain", "failed/returned none"]
        llm_unavailable_msgs = ["llm returned an empty", "an error occurred", "failed/returned none"]
        web_unavailable_msgs = ["web search failed", "could not find relevant websites", "failed to scrape content", "could not extract meaningful content", "could not find a specific answer", "error synthesizing answer", "no websites provided", "failed/returned none"]

        rag_is_available = isinstance(rag_answer, str) and rag_answer and not any(msg in rag_answer.lower() for msg in rag_unavailable_msgs)
        llm_is_available = isinstance(llm_answer, str) and llm_answer and not any(msg in llm_answer.lower() for msg in llm_unavailable_msgs)
        web_is_available = isinstance(web_answer, str) and web_answer and not any(msg in web_answer.lower() for msg in web_unavailable_msgs)

        rag_input = rag_answer if rag_is_available else "Not available or not found in documents."
        llm_input = llm_answer if llm_is_available else "LLM baseline failed or unavailable."
        web_input = web_answer if web_is_available else "Not available or not found on web."

        if not rag_is_available and not llm_is_available and not web_is_available:
             print("Aggregation skipped: No valid answers found.")
             failures = [f"Documents: {rag_answer}", f"LLM: {llm_answer}", f"Web: {web_answer}"]
             failure_details = "\n".join(failures)
             return f"Sorry, I could not find a reliable answer from any source.\nDetails:\n{failure_details}"

        aggregator_prompt_template = ChatPromptTemplate.from_messages([
             SystemMessagePromptTemplate.from_template(
                 f"You are a highly intelligent AI assistant specializing in {self.subject}. Your task is to synthesize information from up to three different sources: a knowledge base (RAG), a general language model (LLM), and web search results (Web). Analyze the provided answers below, noting consensus and discrepancies. Construct a single, comprehensive, accurate, and well-structured final answer to the user's original question. Prioritize information confirmed by multiple sources, especially the RAG source if it provided a relevant answer. If sources conflict significantly on key points, you may briefly mention the differing views if crucial for understanding, but aim for a unified answer. Ignore sources marked as 'Not available' or similar. Do not mention the source names (RAG, LLM, Web) or the aggregation process in your final output. Focus solely on providing the best possible answer to the original question based on the information provided.\nIMPORTANT: DO NOT include <think>...</think> tags in your final output."
             ),
             HumanMessagePromptTemplate.from_template(
                 "Original Question: {question}\n\n---\nAnswer from Document Knowledge Base (RAG):\n{rag_answer}\n\n---\nAnswer from General Language Model (LLM):\n{llm_answer}\n\n---\nAnswer from Web Search (Web):\n{web_answer}\n\n---\nSynthesized Final Answer:"
             )
        ])
        prompt = aggregator_prompt_template.format(question=question, rag_answer=rag_input, llm_answer=llm_input, web_answer=web_input)

        def clean_llm_output(text):
            if not isinstance(text, str):
                return text # Return as is if not a string
            cleaned = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
            return cleaned.strip() # Remove leading/trailing whitespace

        try:
            final_response = await self.llm.ainvoke(prompt)
            print("Async aggregation complete.")
            raw_content = final_response.content if final_response else ""
            cleaned_content = clean_llm_output(raw_content)
            return cleaned_content if cleaned_content else "Aggregation LLM returned an empty response after cleaning."

        except NotImplementedError:
             print("Warning: ainvoke not implemented for aggregation LLM, falling back to sync.")
             try:
                  loop = asyncio.get_running_loop()
                  final_response = await loop.run_in_executor(None, self.llm.invoke, prompt)
                  raw_content = final_response.content if final_response else ""
                  cleaned_content = clean_llm_output(raw_content)
                  return cleaned_content if cleaned_content else "Aggregation LLM returned empty (sync fallback) after cleaning."
             except Exception as sync_e:
                   print(f"Error invoking sync fallback aggregation for {self.subject}: {sync_e}")
                   print(traceback.format_exc())
                   # Fallback logic
                   if rag_is_available: return f"(Aggregation Failed) Best answer from documents: {rag_input}"
                   if web_is_available: return f"(Aggregation Failed) Best answer from web: {web_input}"
                   if llm_is_available: return f"(Aggregation Failed) Best answer from baseline LLM: {llm_input}"
                   return "An error occurred during aggregation (sync fallback), and no fallback source was available."
        except Exception as e:
            print(f"Error during async answer aggregation for {self.subject}: {e}")
            print(traceback.format_exc())
            # Fallback logic
            if rag_is_available: return f"(Aggregation Failed) Best answer from documents: {rag_input}"
            if web_is_available: return f"(Aggregation Failed) Best answer from web: {web_input}"
            if llm_is_available: return f"(Aggregation Failed) Best answer from baseline LLM: {llm_input}"
            return "An error occurred during final answer aggregation, and no fallback source was available."


    async def get_comprehensive_answer(self, question):
        """Fetches answers asynchronously and aggregates."""
        print(f"Starting async comprehensive answer generation for: {question} (Subject: {self.subject})")
        results = { "rag": None, "llm": None, "web": None, "final": "Processing...", "sources": [] }

        web_urls = []
        initial_web_error = None
        try:
            loop = asyncio.get_running_loop()
            # Wrap synchronous google_search call
            web_urls = await loop.run_in_executor(None, google_search, question)

            if web_urls and isinstance(web_urls, list) and not any("Error" in str(s) or "Missing" in str(s) for s in web_urls):
                results["sources"] = web_urls
            elif web_urls and isinstance(web_urls, list):
                 initial_web_error = f"Web search failed: {web_urls[0]}"
                 results["web"] = initial_web_error
                 results["sources"] = ["Web search failed."]
            else: # Empty list returned
                 initial_web_error = "Could not find relevant websites for this question."
                 results["web"] = initial_web_error
                 results["sources"] = ["No relevant websites found."]
        except Exception as search_e:
            print(f"Error during Google Search execution for {self.subject}: {search_e}")
            initial_web_error = "An error occurred during web search."
            results["web"] = initial_web_error
            results["sources"] = ["Web search error."]
            print(traceback.format_exc())

        tasks_to_run = []
        tasks_to_run.append(self.get_rag_answer(question))
        tasks_to_run.append(self.get_llm_answer(question))
        should_run_web_task = web_urls and not initial_web_error
        if should_run_web_task:
            tasks_to_run.append(self._process_web_content(question, web_urls))
        else:
            async def web_result_placeholder(): return results["web"]
            tasks_to_run.append(web_result_placeholder())

        try:
            task_results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

            results["rag"] = task_results[0] if not isinstance(task_results[0], Exception) else f"Error in RAG task: {task_results[0]}"
            results["llm"] = task_results[1] if not isinstance(task_results[1], Exception) else f"Error in LLM task: {task_results[1]}"
            if not initial_web_error: # Only update if search succeeded initially
                results["web"] = task_results[2] if not isinstance(task_results[2], Exception) else f"Error in Web Processing task: {task_results[2]}"

            for i, res in enumerate(task_results):
                if isinstance(res, Exception):
                    print(f"Exception occurred in gathered task {i}: {res}")
                    if hasattr(res, '__traceback__'):
                         traceback.print_exception(type(res), res, res.__traceback__)

        except Exception as gather_e:
             print(f"Critical error during asyncio.gather: {gather_e}")
             traceback.print_exc()
             results["rag"] = results["rag"] or "Error during concurrent fetch"
             results["llm"] = results["llm"] or "Error during concurrent fetch"
             results["web"] = results["web"] or "Error during concurrent fetch"

        rag_res = results.get("rag") if isinstance(results.get("rag"), str) else "RAG process did not return a valid string."
        llm_res = results.get("llm") if isinstance(results.get("llm"), str) else "LLM process did not return a valid string."
        web_res = results.get("web") if isinstance(results.get("web"), str) else "Web process did not return a valid string."

        try:
             results["final"] = await self.aggregate_answers(question, rag_res, llm_res, web_res)
        except Exception as agg_e:
             print(f"Error calling aggregate_answers: {agg_e}")
             results["final"] = "An error occurred during final answer aggregation."
             print(traceback.format_exc())

        if not results["final"]:
            results["final"] = "Aggregation resulted in an empty answer."

        print(f"Async comprehensive answer generation complete for {self.subject}.")
        return results # Return the full results dictionary