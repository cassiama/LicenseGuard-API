# LicenseGuard (API)
LicenseGuard is designed to help you easily understand the software licenses of your project's dependencies.

Here's what it offers:
- **Effortless License Checking**: Simply provide your project's `requirements.txt`, and LicenseGuard will analyze it for you.
- **Clear License Identification**: The system identifies the software licenses associated with your dependencies.
- **Understandable Reports**: Get a straightforward JSON report detailing the licenses found, along with a confidence score.
- **Simple Integration**: You can interact with LicenseGuard through a user-friendly API to submit your dependency list and retrieve the analysis results.

LicenseGuard simplifies the process of checking software licenses, giving you a quick and clear picture of your project's licensing landscape.


## Dependencies: API Server
- Python 3.13.6+
- uv 0.8.9+
- [FastAPI](https://github.com/fastapi/fastapi)
- [LangChain](https://github.com/langchain-ai/langchain/blob/master/docs/docs/introduction.mdx)
- [LangChain-OpenAI](https://python.langchain.com/srv_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html)
- [Pydantic](https://github.com/pydantic/pydantic)
- [Pydantic-Settings](https://github.com/pydantic/pydantic-settings)

## Quickstart: API Server
Below is a basic guide to running the API server, either locally on your machine or by containerizating it. No, it doesn't really matter what OS you run this on (especially since Docker is an option) AFAIK.

Since we're using FastAPI for the server, you can view the documentation at the `/docs` route... wherever you end up running it.

### Requirements
You *WILL* need an OpenAI API key. You can throw it in an environment variable or an `.env` file - whichever you prefer. Just make sure that you:
- initialize it at the top level of the repo, and
- call the variable `OPENAI_API_KEY`, otherwise Pydantic Settings will throw errors.

### Local Usage
If you want to try out the API server locally, you can easily run it by navigating to the `src/srv/` directory and running the following command:
```bash
fastapi dev app.py
```
> Alternately, if you prefer `uv`, you can run `uv run fastapi dev` instead.

### Containerization
This repo comes with a Dockerfile if you're interested in deploying it with Docker. In the future, we will have Docker Compose file once the frontend service is added to the project.

In order to run the API server, you must do the following:

1. Build the Docker image by running `docker build -t LicenseGuard-API .` in the terminal.
2. Run the Docker image by running `docker run -p 80:80 --env-file .env LicenseGuard-API` in the terminal. Make sure you're in the root directory when you run this command! You can access the server at `http://localhost:80`.