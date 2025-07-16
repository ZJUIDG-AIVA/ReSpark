# ReSpark

ReSpark is a system that leverages past data reports as references to generate new ones using Large Language Models (LLMs).

The frontend of ReSpark is built with Vue 3, Vite, and Pinia.

The backend of ReSpark is built with Flask.

## Requirements

To use and develop ReSpark, make sure your environment meets the following requirements.

* **Node.js**: >= 18.3
* **Python**: >= 3.11
* **Dependencies**:
  * Please refer to the `requirements.txt` file for the complete list of dependencies.

## Project Setup

Follow these steps to start the frontend:

```bash
npm install
npm run dev
```

Follow these steps to start the backend:

```bash
conda create --name your_env python=3.11
conda activate your_env
pip install -r requirements.txt 
python app.py
```

## Usage

### API Deployment

You need to set the API key and other related variables for APIs in the `.env` file to ensure the proper functioning of the APIs.

The APIs you need to deploy include:

* **Cohere**
* **OpenAI**
  * GPT-4 Turbo with Vision (can be replaced with other language models that have vision abilities)
  * GPT-4o (can be replaced with other language models)
  * text-embedding

Please ensure that the variables are correctly defined and do not conflict with the global environment settings.

### Cache

ReSpark features a caching system that stores previously generated results, including analysis objectives and corresponding report content. In the "Settings" panel and the "Upload Report" dialog, options for managing the cache system are provided:

- **Use Cache**: All responses will be retrieved from the cache if available.
- **Update Cache**: Newly generated responses will be stored in the cache (and old ones will be overwritten).
- **Select Cache**: Select an existing cache file or create a new cache file. 

For an optimal experience exploring the system, we recommend using the dataset *"Crime Data from 2020 to 2023 in LA.csv"* along with the reference report *"CHICAGO CRIME SPIKES IN 2022, BUT FIRST DROP IN MURDER SINCE PANDEMIC"* and the cache file `crime_case_cache`. All of these are provided in the database of the system.
