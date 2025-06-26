# auto-ria-scraper

A two-stage scraper for auto.ria.com listings:

1. **Scrapy Spider** (`autoriaspider`) to extract car details and store them in PostgreSQL.  
2. **Selenium Parser** (`parse.py`) to fetch phone numbers in parallel using multiple worker processes.

---

## Features
 
- Extract URL, title, price (USD), odometer reading, seller username, main image, image count, car number, VIN, and timestamp  
- Store initial data in a PostgreSQL table `cars` via a custom Scrapy pipeline  
- Post-process records with a multiprocessing Selenium script that clicks to reveal phone numbers and updates the database  
- Dockerized setup with `docker-compose` for easy startup and teardown  
- `docker-wait-for-db.sh` ensures that services wait for PostgreSQL and the `cars` table before starting  

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/)  
- [Docker Compose](https://docs.docker.com/compose/install/)  
- (Optional) Python 3.8+ and pip (if running outside Docker)  
- Google Chrome or Chromium (for Selenium)  

---

## Getting Started

Clone the repository and navigate into the project directory:

```bash
git clone https://github.com/d-stegantsev/auto-ria-scraper.git
cd auto-ria-scraper
```

Copy the example environment files in root and selenium folders and adjust values as needed:

```bash
cp .env.example .env
# Or manually create a .env file with the following variables:
# DB_NAME=autodb
# DB_USER=autoria
# DB_PASS=autoria
# DB_HOST=postgres
# DB_PORT=5432
```

---

## Configuration

Environment variables are read from `.env`:

```dotenv
DB_NAME=autodb
DB_USER=autoria
DB_PASS=autoria
DB_HOST=postgres
DB_PORT=5432
```

---

## Usage

### Build and Start All Services (Docker)

```bash
docker-compose up --build
```

This will:

- Pull or build Docker images for PostgreSQL, the Scrapy spider, and the Selenium parser  
- Start PostgreSQL and wait until the `cars` table exists  
- Run the Scrapy spider to populate initial data  
- Launch the multiprocessing Selenium parser to fetch phone numbers  

### Run Scrapy Spider Only (Docker)

```bash
docker-compose run --rm scrapy scrapy crawl autoriaspider
```

### Run Selenium Parser Only (Docker)

```bash
docker-compose run --rm selenium-parser
```

### Run Locally (Without Docker)

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2. Ensure `.env` is configured (see above).
3. Create the `cars` table in PostgreSQL manually:
    ```bash
    psql -U <user> -d <db> -c "CREATE TABLE cars (
      id SERIAL PRIMARY KEY,
      url TEXT UNIQUE,
      title TEXT,
      price_usd INTEGER,
      odometer INTEGER,
      username TEXT,
      phone_number TEXT,
      phone_status TEXT DEFAULT 'pending',
      image_url TEXT,
      images_count INTEGER,
      car_number TEXT,
      car_vin TEXT,
      datetime_found TIMESTAMPTZ
    );"
    ```
4. Run the Scrapy spider:
    ```bash
    scrapy crawl autoriaspider
    ```
5. Run the Selenium parser:
    ```bash
    python parse.py
    ```

---

## Project Structure

```
├── autoriaspider.py         # Scrapy spider definition
├── items.py                 # Item schema for Scrapy
├── pipelines.py             # Postgres pipeline for Scrapy
├── settings.py              # Scrapy settings
├── parse.py                 # Multiprocessing Selenium parser
├── Dockerfile               # Dockerfile for Selenium parser or main service
├── docker-compose.yml       # Defines Postgres, scrapy, and selenium-parser services
├── docker-wait-for-db.sh    # Wait script for Postgres readiness
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment variables file
└── README.md                # This file
```

---

## Using pgAdmin for PostgreSQL Management

You can use **pgAdmin** (a web interface for managing PostgreSQL databases) via the included Docker service.

### How to Access pgAdmin

1. **Start all services:**

   ```bash
   docker-compose up -d
   ```

2. **Open your browser and go to:**  
   [http://localhost:5050](http://localhost:5050)

3. **Login credentials:**

   - **Email:** `admin@admin.com`
   - **Password:** `admin`

   > You can change these credentials in the `docker-compose.yml` file.

4. **Add a new PostgreSQL server in pgAdmin:**

   - Click **Add New Server**.
   - Go to the **General** tab and enter a name, e.g. `Postgres (Docker)`.
   - Go to the **Connection** tab and fill in:
     - **Host name/address:** `postgres`
     - **Port:** `5432`
     - **Username:** `autoria`
     - **Password:** `autoria`

   > The host must match the service name of your PostgreSQL container (usually `postgres`).

5. **Click Save.**  
   You can now view, query, and manage your database via the pgAdmin web UI.

---

### Example Server Connection Settings

| Field         | Value          |
| ------------- | -------------- |
| Host          | `postgres`     |
| Port          | `5432`         |
| Username      | `autoria`      |
| Password      | `autoria`      |
| Database      | `autodb`       |

---

**Tip:**  
You can find or change these credentials in your `.env` file or directly in the `docker-compose.yml`.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.