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

1. Open Command Prompt & navigate to a path you wish to use
2. Copy & Run the following command:

    `docker run --rm -it -v "%cd%:/app/data" evorron/hawkerai:demo-image`

<h2>Method 2 (Clone Git Repo + Build Docker Image):</h2>
You can also run the program by cloning the Github Repository and building the Docker Image yourself

1. Clone the Github Repository

`git clone "https://github.com/Evorron/26INF1103P5-8"`

2. Modify the `.env` file with your Grok API key

    ` GROQ_API_KEY= YourActualKey`

2. Build the Docker Image
    `docker build -t <image_name> .`

3. Run the Docker image

    `docker run --rm -it --env-file .env -v "%cd%:/app/data" <image_name>>`

