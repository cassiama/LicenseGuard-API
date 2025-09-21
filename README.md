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

In short:

- have Docker Desktop/Engine installed on your local machine
- access to a SQL Database
- the required table(s) in your SQL database
- have an OpenAI API key
- environment variables for generating JWTs and storing the database's URL

---

Make sure you have Docker Desktop (or Docker Engine) installed on your machine. If you don't, download it from [Docker's website](https://docs.docker.com/get-started/get-docker/).

Our application expects a SQL database connection. It's not picky about which dialect you prefer, just make sure to create the "Events" and "Users" tables using the following commands:

#### Events Table

| *Dialect*         | *SQL Statement*                                                                 |
|------------------|--------------------------------------------------------------------------------|
| **PostgreSQL (recommended)** | `CREATE TABLE Events (UserID VARCHAR(32) NOT NULL, ProjectName VARCHAR(100) NOT NULL, Event VARCHAR(18) NOT NULL, Timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, Content TEXT NULL);` |
| **MySQL**            | `CREATE TABLE Events (UserID VARCHAR(32) NOT NULL, ProjectName VARCHAR(100) NOT NULL, Event VARCHAR(18) NOT NULL, Timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, Content TEXT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;` |
| **SQLite**           | `CREATE TABLE Events (UserID TEXT NOT NULL, ProjectName TEXT NOT NULL, Event TEXT NOT NULL, Timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, Content TEXT);` |
| **SQL Server**       | `CREATE TABLE Events (UserID NVARCHAR(32) NOT NULL, ProjectName NVARCHAR(100) NOT NULL, Event NVARCHAR(18) NOT NULL, Timestamp DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), Content NVARCHAR(MAX) NULL);` |

#### Users Table

| *Dialect*                      | *SQL Statement*                                                                                                                                                                                                                                                                                                                       |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PostgreSQL (recommended)** | `CREATE TABLE Users (Id UUID PRIMARY KEY, Username VARCHAR(100) NOT NULL UNIQUE CHECK (char_length(Username) >= 4), Email VARCHAR(255) NULL UNIQUE, FullName VARCHAR(255) NULL, HashedPassword TEXT NOT NULL);`                               |
| **MySQL**                    | `CREATE TABLE Users (Id CHAR(32) NOT NULL PRIMARY KEY, Username VARCHAR(100) NOT NULL UNIQUE, Email VARCHAR(255) NULL UNIQUE, FullName VARCHAR(255) NULL, HashedPassword TEXT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`                       |
| **SQLite**                   | `CREATE TABLE Users (Id TEXT PRIMARY KEY, Username TEXT NOT NULL UNIQUE CHECK (length(Username) BETWEEN 4 AND 100), Email TEXT NULL UNIQUE, FullName TEXT NULL, HashedPassword TEXT NOT NULL);`                                                       |
| **SQL Server**               | `CREATE TABLE Users (Id UNIQUEIDENTIFIER NOT NULL PRIMARY KEY, Username NVARCHAR(100) NOT NULL UNIQUE CHECK (LEN(Username) BETWEEN 4 AND 100), Email NVARCHAR(255) NULL UNIQUE, FullName NVARCHAR(255) NULL, HashedPassword NVARCHAR(MAX) NOT NULL);` |

If the server fails to start, this will likely be one of the reasons. You *MUST* create these tables for the server to run.

#### Environment Variables

You *WILL* need an OpenAI API key. You can throw it into an environment variable or an `.env` file - whichever you prefer. Just make sure that you call the variable `OPENAI_API_KEY`, otherwise the server will fail to run and you will see errors.

You will also need environment variables for generating JSON Web Tokens (`JWT_SECRET_KEY`) and storing the database's URL (`DB_URL`). The former can be generated by running `openssl rand -hex 32` in your terminal.

### Usage

For the purposes of this guide, we're going to assume that you want to pull the image from Docker Hub. However, you can also download the image from the GitHub Container Registry (GHCR) instead if you'd like.

#### Downloading the Docker Image

Run the following command to download the image from Docker Hub on your machine:

```bash
docker pull licenseguard/license-guard:api-latest
```

> NOTE: If you want a specific version, then pull the `licenseguard/license-guard:api-v{x.y.z}` image instead (`x.y.z` refers to the [semantic verisoning number](https://semver.org/)).

> NOTE: For those who prefer GHCR, replace any reference to `licenseguard/license-guard` with `ghcr.io/cassiama/license-guard` for any of the commands below, and you'll be good. 👍🏿

#### Running the Docker Image

**With `.env` file:**
Run the Docker image by running `docker run -p 80:80 --env-file .env licenseguard/license-guard:api-latest` in the terminal.

**With an environment variable:**
Run the Docker image by running `docker run -p 80:80 -e OPENAI_API_KEY=YOUR_ACTUAL_API_KEY -e JWT_SECRET_KEY=$(openssl rand -hex 32) -e DB_URL=YOUR_ACTUAL_DB_URL licenseguard/license-guard:api-latest` in the terminal.

> NOTE: This command runs the server in **production** mode, not dev mode.

> NOTE: **You** are responsible for any HTTPS-related concerns. For example, if you are running this behind a TLS Termination Proxy, you need to [add "--proxy-headers" to the `CMD` line in the Dockerfile](https://fastapi.tiangolo.com/deployment/docker/#behind-a-tls-termination-proxy). Please view [FastAPI's documentation on HTTPS](https://fastapi.tiangolo.com/deployment/https/) for more general information on this topic.

You can access the server at `http://localhost:80`.

Once you have the server running, you can view the documentation by navigating to `http://localhost:80/docs`.

## Available Routes

For the latest image of the API on Docker Hub, you can access the following routes:

- `POST /analyze`: Accepts a `requirements.txt` file upload and a project name, analyzes each license associated with the dependencies in the `requirements.txt` file, and returns the analysis.
  - Sample Request:
    - a `requirements.txt` (`multipart/form-data`; should be `text/plain` MIME type),
    - a name for your project
  - Sample Response:

    - Success:

      ```json
        {
          "id": "7ec3952b6cc447f8ae99fcba261f6a52",
          "status": "completed",
          "result": {
            "analysis_date": "2025-08-30",
            "files": [
              {
                "confidence_score": 0.8,
                "license": "BSD-3-Clause",
                "name": "contourpy",
                "version": "1.3.1"
              },
              {
                "confidence_score": 0.8,
                "license": "BSD-3-Clause",
                "name": "contourpy",
                "version": "1.3.1"
              }
            ],
            "project_name": "MyCoolCompleteProject"
          }
        }
        ```

    - Failure:

      ```json
      {
        "id": "8a4365f380b044668e8db8c66a319933",
        "status": "failed",
        "result": null
      }
      ```

### Deprecated Routes

The following routes are deprecated (as of v0.3.0), so you should avoid using them. You can still access them if you want (not sure why, but you do you 🤷🏿‍♂️). But all routes will return a `HTTP 410 Gone` status code with `Deprecation` and `Sunset` headers:

- `GET /`:

  > *Originally*: Returns a JSON response with a message that says "Hello World!"

  - Returns a message that explains the route is retired:
    - Sample Response (**Status Code:** `HTTP 410 Gone`):

        ```json
        {
          "detail": "GET / has been retired. It may return in the future."
        }
        ```

- `POST /llm/guess`:

  > *Originally*: Takes a string (the prompt to the LLM) as its body. The LLM expects a prompt that lists Python packages. Returns a JSON response that guesses the licenses of the packages mentioned in the prompt.

  - Returns a message that explains the route is retired:
    - Sample Response (**Status Code:** `HTTP 410 Gone`):

        ```json
        {
            "detail": "POST /llm/guess has been retired."
        }
        ```

- `GET /status/{project_id}`:

  > *Originally*: Returns the status and (if present) result for a given project_id.

  - Returns a message that explains the route is retired:
    - Sample Response (**Status Code:** `HTTP 410 Gone`):

      ```json
      {
          "detail": "GET /status/{project_id} has been retired."
      }
      ```
