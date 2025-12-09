CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

BEGIN;

CREATE TABLE IF NOT EXISTS product_type (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    coefficient     NUMERIC(6,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS material_type (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL UNIQUE,
    loss_percent    NUMERIC(5,4) NOT NULL
);

CREATE TABLE IF NOT EXISTS workshop_type (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS workshop (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL UNIQUE,
    workshop_type_id    INTEGER NOT NULL REFERENCES workshop_type(id),
    workers_required    INTEGER NOT NULL CHECK (workers_required > 0)
);

CREATE TABLE IF NOT EXISTS product (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL UNIQUE,
    article             VARCHAR(50) NOT NULL UNIQUE,
    product_type_id     INTEGER NOT NULL REFERENCES product_type(id),
    material_type_id    INTEGER NOT NULL REFERENCES material_type(id),
    min_partner_price   NUMERIC(12,2) NOT NULL CHECK (min_partner_price >= 0)
);

CREATE TABLE IF NOT EXISTS product_workshop (
    id                      SERIAL PRIMARY KEY,
    product_id              INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    workshop_id             INTEGER NOT NULL REFERENCES workshop(id),
    production_time_hours   NUMERIC(6,2) NOT NULL CHECK (production_time_hours > 0),
    CONSTRAINT uq_product_workshop UNIQUE (product_id, workshop_id)
);

COMMIT;
