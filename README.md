# Dependencies: Backend Server
- Python 3.13.6+
- uv 0.8.9+
- [FastAPI](https://github.com/fastapi/fastapi)
- [LangChain](https://github.com/langchain-ai/langchain/blob/master/docs/docs/introduction.mdx)
- [LangChain-OpenAI](https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html)
- [Pydantic](https://github.com/pydantic/pydantic)
- [Pydantic-Settings](https://github.com/pydantic/pydantic-settings)

# Quickstart: Backend Server
Below is a basic guide to running the backend server, either locally on your machine or by containerizating it. No, it doesn't really matter what OS you run this on (especially since Docker is an option) AFAIK.

Since we're using FastAPI for the server, you can view the documentation at the `/docs` route... wherever you end up running it.

## Requirements
You *WILL* need an OpenAI API key. You can throw it in an environment variable or an `.env` file - whichever you prefer. Just make sure that you:
- initialize it at the top level of the repo, and
- call the variable `OPENAI_API_KEY`, otherwise Pydantic Settings will throw errors.

## Local Usage
If you want to try out the backend server locally, you can easily run it by navigating to the `src/api/` directory and running the following command:
```bash
fastapi dev app.py
```
> Alternately, if you prefer `uv`, you can run `uv run fastapi dev` instead.

## Containerization
This repo comes with a Dockerfile if you're interested in deploying it with Docker. In the future, we will have Docker Compose file once the frontend service is added to the project.

In order to run the backend server, you must do the following:

1. Build the Docker image by running `docker build -t license-guard .` in the terminal.
2. Run the Docker image by running `docker run -p 80:80 --env-file .env license-guard` in the terminal. Make sure you're in the root directory when you run this command! You can access the server at `http://localhost:80`.