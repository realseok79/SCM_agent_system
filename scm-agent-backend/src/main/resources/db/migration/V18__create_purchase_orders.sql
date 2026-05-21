CREATE TABLE purchase_orders (
    id BIGSERIAL PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    rejection_reason VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
