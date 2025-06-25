CREATE TABLE cars (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    price_usd INTEGER,
    odometer INTEGER,
    username TEXT,
    phone_number TEXT,
    image_url TEXT,
    images_count INTEGER,
    car_number TEXT,
    car_vin TEXT,
    datetime_found TIMESTAMP,
    phone_status VARCHAR(16) DEFAULT 'pending'
);
