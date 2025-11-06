# Project Overview

This project is a voice-enabled customer support system that combines Parlant's AI agent framework with Pipecat's real-time voice pipeline. The system is designed to handle customer queries through a voice interface, with a specific focus on processing refund requests.

The architecture consists of three main components:

*   **Parlant:** The AI agent backend that manages conversation journeys, implements business logic (e.g., refund eligibility), and connects to the PostgreSQL database.
*   **Pipecat:** The voice interface layer that handles WebRTC audio streaming, speech-to-text (STT), and text-to-speech (TTS).
*   **PostgreSQL:** The database that stores the product catalog and order history.

These services are orchestrated using Docker Compose, which allows for a one-command deployment.

# Building and Running

To build and run the project, you need to have Docker and Docker Compose installed.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/parlant-pipecat-voice.git
    cd parlant-pipecat-voice
    ```
2.  **Configure the environment:**
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your OpenAI API key.
3.  **Start all services:**
    ```bash
    docker-compose up -d
    ```
4.  **Access the application:**
    *   Parlant UI: `http://localhost:8800`
    *   Voice Client: `http://localhost:7860/client`
    *   Database: `localhost:5432`

# Development Conventions

The project follows a microservices architecture, with each service having its own Dockerfile and `requirements.txt` file. The `parlant` service is written in Python and uses the Parlant SDK, while the `voice` service uses the Pipecat framework.

The `parlant` service defines the core AI agent logic, including the conversation journeys and tools. The `voice` service handles the real-time voice interface and communicates with the Parlant agent through an event-driven bridge.

The project also includes a `postgres` service with an `init.sql` script for initializing the database schema and seeding it with sample data.

For more information on Parlant, please refer to the official repository: [https://github.com/emcie-co/parlant](https://github.com/emcie-co/parlant)
For ParkWhiz API documentation, please refer to: [https://developer.parkwhiz.com/v4/](https://developer.parkwhiz.com/v4/)
For Freshdesk API documentation, please refer to: [https://developers.freshdesk.com/api/](https://developers.freshdesk.com/api/)