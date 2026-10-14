# AI Food Preparation Advisor

# Installation & Set-up 

## Method 1 (Docker):
You can run the program virtually via Docker without pulling the Git Repository

1. Create an `.env` file in a new local folder and paste this inside:
    GROQ_API_KEY= YourActualKey
2. Open Command Prompt & Navigate to your folder path
3. Copy & Run the following command:

    `docker run --rm -it --env-file .env -v "%cd%:/app/data" evorron/hawkerai:v2`

## Method 2 (Clone Git Repo + Docker):
You can also run the program by cloning the Github Repository

1. Clone the Github Repository

`git clone `

2. Execute installation of required modules

    `pip install requirements.txt`

3. Build & Run Docker

    `docker build ...`
    
    `docker run ...`

