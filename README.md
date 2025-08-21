# LicenseGuard (API)
LicenseGuard is designed to help you easily understand the software licenses of your project's dependencies.

Here's what it offers:
- **Effortless License Checking**: Simply provide your project's `requirements.txt`, and LicenseGuard will analyze it for you.
- **Clear License Identification**: The system identifies the software licenses associated with your dependencies.
- **Understandable Reports**: Get a straightforward JSON report detailing the licenses found, along with a confidence score.
- **Simple Integration**: You can interact with LicenseGuard through a user-friendly API to submit your dependency list and retrieve the analysis results.

LicenseGuard simplifies the process of checking software licenses, giving you a quick and clear picture of your project's licensing landscape.


## Quickstart
The fastest and easiest way to get this running on your machine is to use Docker. 


### Requirements
Make sure you have Docker Desktop (or Docker Engine) installed on your machine. If you don't, download it from [Docker's website](https://docs.docker.com/get-started/get-docker/).

You *WILL* need an OpenAI API key. You can throw it into an environment variable or an `.env` file - whichever you prefer. Just make sure that you call the variable `OPENAI_API_KEY`, otherwise the server will fail to run and you will see errors.


### Usage
Run the following command to download the image on your machine: `docker pull licenseguard/license-guard:api-latest`.
> NOTE: If you want a specific version, then pull the `licenseguard/license-guard:api-v{x.y.z}` image instead (`x.y.z` refers to the [semantic verisoning number](https://semver.org/)).

**With `.env` file:**
Run the Docker image by running `docker run -p 80:80 --env-file .env licenseguard/license-guard:api-latest` in the terminal.

**With an environment variable:**
Run the Docker image by running `docker run -p 80:80 -e OPENAI_API_KEY=YOUR_ACTUAL_API_KEY licenseguard/license-guard:api-latest` in the terminal.

> NOTE: This command runs the server in **production** mode, not dev mode.

> NOTE: **You** are responsible for any HTTPS-related concerns. Please view [FastAPI's documentation on HTTPS](https://fastapi.tiangolo.com/deployment/https/) for more information.

You can access the server at `http://localhost:80`.

Once you have the server running, you can view the documentation by navigating to `http://localhost:80/docs`.


## Available Routes
For the latest image of the API on Docker Hub, you can access the following routes:
- `GET /`: Returns a JSON response with a message that says "Hello World!":
    - Sample LlmResponse:
        ```json
        {
            "message": "Hello World!"
        }
        ```
- `POST /llm/guess`: Takes a string (the prompt to the LLM) as its body. The LLM expects a prompt that lists Python packages. Returns a JSON response that guesses the licenses of the packages mentioned in the prompt.
    - Sample Request: `"numpy, matplotlib, uv"`
    - Sample LlmResponse:
        ```json
        {
            "text": "Based on the software packages you've mentioned:\n\n1. **NumPy** - This package is typically licensed under the BSD License.\n2. **Matplotlib** - This package is usually licensed under the Matplotlib License, which is a permissive license similar to the BSD License.\n3. **uv** - I'm not familiar with a specific software package named \"uv.\" If you could provide more context or details about it, I might be able to help further.\n\nIf you have any other packages or need more information, feel free to ask!"
        }
        ```