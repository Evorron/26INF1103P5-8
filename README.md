<h1>AI Food Preparation Advisor</h1>
An AI Hawker advisor targeting new hawker stall owners and pop-up vendors to navigate the challenge of estimating food preparation quantities and sales tracking.

As new stall owners have no prior knowledge in this field with no established operational workflow, food demand from customers are often misjudged. This AI advisor seeks to be that modern tool to assist in that process.

This tool is able to do the following:
- **Record daily sales**
- **Tracking historical sales data based on food items and date range**
- **Generate forecasts on food demand based on historical data and key calendar dates**

<h1>Installation & Set-up</h1> 

<h2>Method 1 (Docker):</h2>
You can run the program virtually via Docker without pulling the Git Repository

1. Place the `.env` file in a new local folder and paste this inside:
    GROQ_API_KEY= YourActualKey
2. Open Command Prompt & Navigate to your folder path
3. Copy & Run the following command:

    `docker run --rm -it --env-file .env -v "%cd%:/app/data" evorron/hawkerai:latest`

<h2>Method 2 (Clone Git Repo + Docker):</h2>
You can also run the program by cloning the Github Repository

1. Clone the Github Repository

`git clone `

2. Execute installation of required modules

    `pip install requirements.txt`

3. Build & Run Docker

    `docker build ...`
    
    `docker run ...`

