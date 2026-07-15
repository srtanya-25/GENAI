# GEN-AI

Generative AI notebooks — transformer fine-tuning (BERT), image generation (Stable Diffusion), and Retrieval-Augmented Generation (RAG), including a from-scratch RAG pipeline built on a locally-hosted Ollama model.

## What's in here

| Path | Description |
|---|---|
| `BERT_Warmup.ipynb` | Intro to BERT — tokenizer basics, sentence tokenization |
| `BERT_Usecase_Sentiment_Analysis.ipynb` | Sentiment analysis on a public dataset using BERT |
| `Diffusion_Model-2.ipynb` | Text-to-image generation with Stable Diffusion (`runwayml/stable-diffusion-v1-5` via `diffusers`) |
| `RAG_Step_by_Step-2.ipynb` | RAG explained with small, from-scratch examples — chunking, embeddings, retrieval |
| `RAG_Langchain_Example.ipynb` | RAG built with LangChain — document loading, chunking, embeddings, Chroma vector store, retriever |
| `ollama.ipynb` | End-to-end RAG pipeline against a **local Ollama server**: embeds `cat-facts.txt` into an in-memory vector store, retrieves relevant chunks by cosine similarity, and generates an answer with a local Llama model |
| `cat-facts.txt` | Small sample dataset used by `ollama.ipynb` |

## Running `ollama.ipynb`

This notebook talks to a local [Ollama](https://ollama.com) server, not a hosted API — you need Ollama installed and two models pulled before running it:

```bash
ollama pull hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF        # generation
ollama pull hf.co/CompendiumLabs/bge-base-en-v1.5-gguf         # embeddings
```

By default Ollama stores pulled models under `%USERPROFILE%\.ollama\models` on Windows. To store them elsewhere, set `OLLAMA_MODELS` to your preferred folder before pulling and restart the Ollama server so it picks up the change.

A dedicated virtual environment (`ollama-check/`, gitignored) with `ollama`, `numpy`, and `ipykernel` is used to run this notebook — select the **"Python (ollama-check)"** kernel in Jupyter/VS Code, or create your own:

```bash
python -m venv ollama-check
ollama-check\Scripts\activate
pip install ollama numpy ipykernel
```

## Running the other notebooks

```bash
pip install -r ../requirements.txt
pip install transformers diffusers torch langchain langchain-community chromadb
jupyter notebook
```

`Diffusion_Model-2.ipynb` downloads multi-GB Stable Diffusion weights on first run via Hugging Face — these are cached outside the repo (see the root `cache/` folder, which is gitignored) rather than committed.
